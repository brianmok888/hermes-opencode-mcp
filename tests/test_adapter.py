from hermes_opencode_mcp.opencode_adapter import parse_opencode_output


def test_parse_opencode_output_collects_text_and_session():
    output = "\n".join([
        '{"sessionID":"ses_123","type":"text","part":{"text":"hello"}}',
        '{"type":"text","part":{"text":"world"}}',
    ])
    summary, session_id = parse_opencode_output(output)
    assert summary == "hello\n\nworld"
    assert session_id == "ses_123"
