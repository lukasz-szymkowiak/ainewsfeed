from verified import parse_judge_reply

FALLBACK = {"supported": False, "reason": "judge output unparseable"}


def test_clean_json_is_parsed():
    text = '{"supported": true, "reason": "stated in source"}'
    assert parse_judge_reply(text) == {"supported": True, "reason": "stated in source"}


def test_fenced_json_is_parsed():
    text = '```json\n{"supported": true, "reason": "stated in source"}\n```'
    assert parse_judge_reply(text) == {"supported": True, "reason": "stated in source"}


def test_garbage_gives_fallback():
    assert parse_judge_reply("I think this is supported") == FALLBACK


def test_missing_supported_key_gives_fallback():
    assert parse_judge_reply('{"reason": "no verdict"}') == FALLBACK
