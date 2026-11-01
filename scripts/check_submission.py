"""Read-only audit of Git candidates, documentation links and saved chat-export hashes."""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

FORBIDDEN = ('.wav', '.mp3', '.flac', '.m4a', '.aac', '.ogg', '.opus', '.wma',
             '.webm', '.mp4', '.onnx', '.onnx.data', '.bin', '.pt', '.pth',
             '.ckpt', '.safetensors')
SECRET_PATTERNS = {
    'OpenAI-style token': r'\bsk-(?:proj-)?[A-Za-z0-9_-]{24,}',
    'HuggingFace-style token': r'\bhf_[A-Za-z0-9]{25,}',
    'GitHub-style token': r'\b(?:ghp|gho|ghu|ghs)_[A-Za-z0-9]{30,}',
    'AWS access key': r'\bAKIA[0-9A-Z]{16}\b',
    'private key': r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--report', type=Path)
    args = cli.parse_args()
    root = Path.cwd()
    raw = subprocess.check_output(['git', 'ls-files', '-co', '--exclude-standard', '-z'])
    paths = sorted({p for p in raw.decode().split('\0') if p and (root / p).is_file()})
    forbidden, secrets, broken_links = [], [], []
    for name in paths:
        lower = name.lower()
        if (lower.endswith(FORBIDDEN) or lower.startswith(('.cache/', '.venv/', 'data/local/',
                                                          'models/', 'reports/'))
                or Path(lower).name.startswith('.env')):
            forbidden.append(name)
        if Path(name).suffix in {'.md', '.py', '.json', '.toml', '.lock'}:
            content = (root / name).read_text(encoding='utf-8')
            for kind, pattern in SECRET_PATTERNS.items():
                if re.search(pattern, content):
                    # Report location/type only, never echo a matching value.
                    secrets.append({'file': name, 'kind': kind})
    for name in ('README.md', 'SUBMISSION_CHECKLIST.md', 'DEMO_GUIDE.md', 'CHAT_EXPORTS.md'):
        for target in re.findall(r'\]\(([^)]+)\)', (root / name).read_text(encoding='utf-8')):
            if '://' not in target and not target.startswith('#'):
                path = target.split('#')[0]
                if path and not (root / path).is_file():
                    broken_links.append({'file': name, 'target': target})
    manifest = json.loads((root / 'chats/EXPORT_MANIFEST.json').read_text(encoding='utf-8'))
    invalid_exports = []
    for entry in manifest['sessions']:
        path = root / 'chats' / entry['export_file']
        if (not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()
                != entry['export_sha256'] or entry['incomplete_tail']):
            invalid_exports.append(entry['session_id'])
    report = {'candidate_files': len(paths), 'forbidden_candidates': forbidden,
              'credential_pattern_matches': secrets, 'broken_delivery_links': broken_links,
              'exported_sessions': len(manifest['sessions']), 'invalid_exports': invalid_exports,
              'chat_scope_review_and_final_refresh_pending': True,
              'limitations': ['Pattern scan does not prove the absence of all secrets',
                              'This audit neither stages nor commits nor publishes any file']}
    report['passed'] = not (forbidden or secrets or broken_links or invalid_exports)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
