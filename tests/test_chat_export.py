import json

from scripts.export_project_chats import export_session, fenced, selected_records


def response(role, text, **extra):
    return {'type': 'response_item', 'payload': {
        'type': 'message', 'role': role,
        'content': [{'type': 'input_text', 'text': text}], **extra}}


def event(kind, text):
    return {'type': 'event_msg', 'payload': {'type': 'item_completed',
            'item': {'type': kind, 'content': [{'type': 'text', 'text': text}]}}}


def test_export_excludes_runtime_instructions_and_internal_records():
    rows = [response('developer', 'internal instructions'), response('system', 'internal system'),
            response('assistant', 'private internal', channel='analysis'),
            {'type': 'response_item', 'payload': {'type': 'reasoning', 'summary': 'internal'}},
            event('Reasoning', 'internal'), response('user', 'Բարեւ\n```example```'),
            response('assistant', 'Public answer', phase='final_answer')]
    result = list(selected_records(rows))
    assert [(kind, text) for _, kind, text in result] == [
        ('user', 'Բարեւ\n```example```'), ('assistant', 'Public answer')]
    assert fenced('```example```').startswith('````\n')


def test_duplicate_storage_records_do_not_remove_repeated_user_messages():
    rows = [event('UserMessage', 'yes'), response('user', 'yes'),
            event('UserMessage', 'yes'), response('user', 'yes'),
            event('AgentMessage', 'UI-only message')]
    assert [(kind, text) for _, kind, text in selected_records(rows)] == [
        ('user', 'yes'), ('user', 'yes'), ('assistant', 'UI-only message')]


def test_export_is_bound_to_project_and_preserves_original_text_and_source(tmp_path):
    text = 'Բարեւ\n  original spacing  \n'
    meta = {'type': 'session_meta', 'payload': {'id': 'test-session',
            'cwd': str(tmp_path), 'timestamp': '2026-11-01T12:00:00Z'}}
    source = tmp_path / 'source.jsonl'
    source.write_text('\n'.join(json.dumps(r) for r in [meta, response('user', text)]) + '\n')
    original = source.read_bytes()
    output = tmp_path / 'chats'
    output.mkdir()
    assert export_session(source, output, tmp_path / 'other-project') is None
    assert list(output.iterdir()) == []
    result = export_session(source, output, tmp_path)
    assert text in (output / result['export_file']).read_text(encoding='utf-8')
    assert source.read_bytes() == original
    assert result['exported_records'] == 1 and not result['incomplete_tail']


def test_tool_outputs_keep_text_but_exclude_internal_transport_fields():
    body = 'Original tool output: Բարեւ\n  unchanged  '
    rows = [{'type': 'response_item', 'payload': {
        'type': 'function_call_output', 'call_id': 'original-call', 'output': body,
        'encrypted_content': 'internal transport',
        'internal_chat_message_metadata_passthrough': {'internal': True}}}]
    _, kind, text = next(selected_records(rows))
    assert kind == 'function_call_output'
    value = json.loads(text)
    assert value['output'] == body and value['call_id'] == 'original-call'
    assert 'encrypted_content' not in value
    assert 'internal_chat_message_metadata_passthrough' not in value


def test_internal_guardian_review_is_not_exported_as_a_project_conversation(tmp_path):
    source = tmp_path / 'review.jsonl'
    meta = {'type': 'session_meta', 'payload': {'id': 'internal-review',
            'cwd': str(tmp_path), 'thread_source': 'guardian_review',
            'source': {'subagent': {'other': 'guardian'}}}}
    source.write_text(json.dumps(meta) + '\n' + json.dumps(response('user', 'review input')))
    out = tmp_path / 'chats'
    out.mkdir()
    assert export_session(source, out, tmp_path) is None
    assert list(out.iterdir()) == []
