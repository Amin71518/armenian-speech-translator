"""Export stored project conversations without reconstructing text or runtime internals."""

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

VISIBLE_TOOLS = {
    'function_call', 'function_call_output', 'custom_tool_call', 'custom_tool_call_output',
}
INTERNAL_FIELDS = {'encrypted_content', 'internal_chat_message_metadata_passthrough'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def internal_review(meta):
    source = meta.get('source', {})
    return (meta.get('thread_source') == 'guardian_review'
            or (isinstance(source, dict)
                and source.get('subagent', {}).get('other') == 'guardian'))


def fenced(text):
    fence = '`' * max(3, max((len(s) + 1 for s in re.findall(r'`+', text)), default=3))
    return fence + '\n' + text + '\n' + fence


def text_content(content):
    if isinstance(content, str):
        return content
    return ''.join(c.get('text', '') for c in content if isinstance(c, dict))


def visible_tool_record(value):
    if isinstance(value, dict):
        return {k: visible_tool_record(v) for k, v in value.items() if k not in INTERNAL_FIELDS}
    if isinstance(value, list):
        return [visible_tool_record(v) for v in value]
    return value


def selected_records(rows):
    """Use stored message bodies, plus UI records absent from the model-message stream."""
    messages = Counter()
    for row in rows:
        p = row.get('payload', {})
        if (row.get('type') == 'response_item' and p.get('type') == 'message'
                and p.get('role') in {'user', 'assistant'}
                and p.get('phase') != 'analysis' and p.get('channel') != 'analysis'):
            messages[(p['role'], text_content(p.get('content', [])).strip())] += 1
    for line, row in enumerate(rows, 1):
        p = row.get('payload', {})
        if row.get('type') == 'response_item':
            if p.get('type') == 'message':
                if (p.get('role') not in {'user', 'assistant'} or p.get('phase') == 'analysis'
                        or p.get('channel') == 'analysis'):
                    continue
                yield line, p['role'], text_content(p.get('content', []))
                nontext = [c for c in p.get('content', [])
                           if isinstance(c, dict) and 'text' not in c]
                if nontext:
                    yield (line, 'attachment reference',
                           json.dumps(nontext, ensure_ascii=False, indent=2))
            elif p.get('type') in VISIBLE_TOOLS:
                yield (line, p['type'],
                       json.dumps(visible_tool_record(p), ensure_ascii=False, indent=2))
        elif row.get('type') == 'event_msg' and p.get('type') == 'item_completed':
            item = p['item']
            kind = item.get('type')
            if kind in {'Reasoning', 'ContextCompaction'} or item.get('phase') == 'analysis':
                continue
            if kind in {'UserMessage', 'AgentMessage'}:
                role = 'user' if kind == 'UserMessage' else 'assistant'
                body = text_content(item.get('content', []))
                key = role, body.strip()
                if messages[key]:
                    messages[key] -= 1
                    continue
                yield line, role, body
            else:
                yield (line, 'visible tool ' + str(kind),
                       json.dumps(visible_tool_record(item), ensure_ascii=False, indent=2))


def export_session(source, destination, project):
    raw = source.read_bytes()
    lines = raw.splitlines()
    # A live append can end inside the last JSON line; never invent the missing bytes.
    rows, incomplete_tail = [], False
    for i, line in enumerate(lines):
        try:
            rows.append(json.loads(line))
        except ValueError:
            if i != len(lines) - 1:
                raise
            incomplete_tail = True
    meta = rows[0]['payload']
    if internal_review(meta):
        return None
    cwd = Path(meta['cwd']).resolve()
    if str(cwd).casefold() != str(project.resolve()).casefold():
        return None
    records = list(selected_records(rows))
    title = f"# Codex conversation {meta['id']}\n\n"
    title += ('Exported from saved local records. Message bodies are verbatim; tool records are '
              'serialized as JSON. Runtime instructions and internal records are outside this '
              'conversation export. Original attachments remain referenced in their messages.\n\n')
    title += f"Session started: {meta.get('timestamp', '')}\n\n"
    if meta.get('parent_thread_id'):
        title += f"Parent session: {meta['parent_thread_id']}\n\n"
    title += f"Source SHA-256 at export: {digest(raw)}\n\n"
    body = title + '\n\n'.join(f'## {kind} source line {line}\n\n{fenced(text)}'
                                for line, kind, text in records) + '\n'
    name = meta['timestamp'][:10] + '_' + meta['id'] + '.md'
    target = destination / name
    target.write_text(body, encoding='utf-8', newline='\n')
    return {'session_id': meta['id'], 'parent_session_id': meta.get('parent_thread_id'),
            'source_file': source.name, 'source_sha256': digest(raw), 'source_bytes': len(raw),
            'source_lines_read': len(rows), 'incomplete_tail': incomplete_tail,
            'export_file': name, 'export_sha256': digest(target.read_bytes()),
            'exported_records': len(records),
            'record_types': dict(Counter(k for _, k, _ in records))}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--sessions', type=Path, default=Path.home() / '.codex' / 'sessions')
    cli.add_argument('--project', type=Path, default=Path.cwd())
    cli.add_argument('--output', type=Path, default=Path('chats'))
    args = cli.parse_args()
    sources = []
    for source in sorted(args.sessions.rglob('*.jsonl')):
        with source.open(encoding='utf-8') as stream:
            first = json.loads(stream.readline())
        cwd = first.get('payload', {}).get('cwd')
        if (cwd and not internal_review(first.get('payload', {}))
                and str(Path(cwd).resolve()).casefold() == str(args.project.resolve()).casefold()):
            sources.append(source)
    args.output.mkdir(parents=True, exist_ok=True)
    if not sources:
        raise FileNotFoundError('No saved sessions match this project; existing exports kept')
    exports = [export_session(p, args.output, args.project) for p in sources]
    manifest = {'format': 'Verbatim stored conversation text and visible tools in Markdown',
                'scope': 'All saved local sessions with this project working directory',
                'snapshot': True, 'refresh_before_submission': True,
                'not_an_official_ui_export': True, 'sessions': exports}
    (args.output / 'EXPORT_MANIFEST.json').write_text(
        json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps({'sessions': len(exports),
                      'records': sum(e['exported_records'] for e in exports),
                      'incomplete_tails': sum(e['incomplete_tail'] for e in exports)}))


if __name__ == '__main__':
    main()
