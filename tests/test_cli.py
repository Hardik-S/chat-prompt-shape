import json

import pytest

from chat_prompt_shape.cli import InvalidInput, main, validate


def row(messages, ident="fixture"):
    return json.dumps({"id": ident, "messages": messages}, ensure_ascii=True)


def msg(role, content=""):
    return {"role": role, "content": content}


@pytest.mark.parametrize("messages", [
    [msg("user")],
    [msg("system"), msg("user")],
    [msg("user"), msg("assistant"), msg("user")],
    [msg("system"), msg("user"), msg("assistant"), msg("user")],
])
def test_valid_shapes(messages):
    assert validate((row(messages) + "\n").encode())["status"] == "valid"


@pytest.mark.parametrize("messages", [
    [], [msg("system")], [msg("assistant")],
    [msg("user"), msg("assistant")],
    [msg("user"), msg("user")],
    [msg("system"), msg("assistant")],
    [msg("user"), msg("assistant"), msg("system"), msg("user")],
    [msg("user"), msg("system")],
])
def test_turn_issues(messages):
    result = validate((row(messages) + "\r\n").encode())
    assert result == {"status": "turn_issues", "record_count": 1, "invalid_turn_lines": [1]}


def test_rows_independent_sorted_physical_lines_and_unicode_content():
    data = "\n".join([
        row([msg("assistant")], "private1"),
        row([msg("user", " e\u0301\u2028\nvalue "), msg("assistant", "☃"), msg("user")], "private2"),
        row([], "private3"),
    ])
    assert validate(data.encode()) == {
        "status": "turn_issues", "record_count": 3, "invalid_turn_lines": [1, 3]
    }


def test_empty_file_and_only_final_terminator():
    assert validate(b"") == {"status": "valid", "record_count": 0, "invalid_turn_lines": []}
    assert validate((row([msg("user")]) + "\n").encode())["record_count"] == 1


@pytest.mark.parametrize("raw", [
    b"\n", b"{}", b'{"id":"x","messages":[]}\n\n',
    b'{"id":"x","id":"y","messages":[]}\n',
    b'{"id":"x","messages":[],"extra":1}\n',
    b'{"id":"x","messages":[{"role":"user","content":"x","extra":1}]}',
    b'{"id":"x","messages":[{"role":"tool","content":"x"}]}',
    b'{"id":"x","messages":[{"role":"user","content":NaN}]}',
    b'{"id":"x","messages":[{"role":"user","content":"\\ud800"}]}',
    b'{"id":"x","messages":[{"role":"user","content":"x"}]}\n{',
    b'{"id":"x","messages":[]}\n{"id":"x","messages":[]}',
    b'\xff',
])
def test_invalid_input(raw):
    with pytest.raises(InvalidInput):
        validate(raw)


def test_crlf_and_carriage_return_terminators():
    data = (row([msg("user")], "fixture-a") + "\r\n" + row([msg("user")], "fixture-b")).encode()
    assert validate(data)["record_count"] == 2


def test_unicode_separator_is_not_a_jsonl_delimiter():
    with pytest.raises(InvalidInput):
        validate((row([msg("user")]) + "\u2028" + row([msg("user")])).encode())


def test_message_limit_and_schema_type():
    assert validate((row([msg("user")] * 10000)).encode())["status"] == "turn_issues"
    with pytest.raises(InvalidInput):
        validate((row([msg("user")] * 10001)).encode())
    with pytest.raises(InvalidInput):
        validate(b'{"id":4,"messages":[]}')


def test_cli_help_and_private_argument_diagnostics(tmp_path, capsys):
    assert main(["--help"]) == 0
    assert "usage:" in capsys.readouterr().out
    assert main([]) == 2
    captured = capsys.readouterr()
    assert captured.out == '{"status":"invalid_input"}\n'
    assert captured.err == ""
    assert main(["private-fixture", "private-extra"]) == 2
    captured = capsys.readouterr()
    assert captured.out == '{"status":"invalid_input"}\n'
    assert captured.err == ""
    assert "private" not in captured.out + captured.err
    assert main(["--private-secret"]) == 2
    captured = capsys.readouterr()
    assert captured.out == '{"status":"invalid_input"}\n'
    assert captured.err == ""
    assert "private" not in captured.out + captured.err


@pytest.mark.parametrize("messages", [
    [{"role": "user", "content": "x", "typo": 1}],
    [{"role": "user"}],
    [{"role": 3, "content": "x"}],
])
def test_invalid_message_schema(messages):
    with pytest.raises(InvalidInput):
        validate(row(messages).encode())


def test_late_invalid_row_has_no_partial_stdout(tmp_path, capsys):
    path = tmp_path / "private-prompts.jsonl"
    path.write_text(row([msg("user")]) + "\n{" , encoding="utf-8")
    assert main([str(path)]) == 2
    assert capsys.readouterr().out == '{"status":"invalid_input"}\n'


def test_missing_file_is_private_and_fixed(tmp_path, capsys):
    assert main([str(tmp_path / "private-missing")]) == 2
    captured = capsys.readouterr()
    assert captured.out == '{"status":"invalid_input"}\n'
    assert captured.err == ""
    assert "private" not in captured.out + captured.err


@pytest.mark.parametrize("kind", ["missing", "extra", "unknown"])
def test_installed_private_argv_is_quiet(tmp_path, kind):
    import os
    import subprocess
    import sysconfig
    from pathlib import Path
    path = tmp_path / "PRIVATE_PATH.jsonl"
    path.write_text(row([msg("user", "PRIVATE_CONTENT")]), encoding="utf-8")
    args = {"missing": [], "extra": [str(path), "PRIVATE_EXTRA"],
            "unknown": ["--PRIVATE_OPTION", str(path)]}[kind]
    exe = Path(sysconfig.get_path("scripts")) / ("chat-prompt-shape.exe" if os.name == "nt" else "chat-prompt-shape")
    result = subprocess.run([str(exe), *args], capture_output=True, text=True)
    assert (result.returncode, result.stdout, result.stderr) == (2, '{"status":"invalid_input"}\n', "")


@pytest.mark.parametrize("depth", [400, 2000])
@pytest.mark.parametrize("late", [False, True])
def test_installed_nested_invalid_is_quiet(tmp_path, depth, late):
    import os
    import subprocess
    import sysconfig
    from pathlib import Path
    path = tmp_path / "PRIVATE_NESTED.jsonl"
    prefix = row([msg("user", "PRIVATE_CONTENT")]) + "\n" if late else ""
    path.write_bytes((prefix + "[" * depth + "0" + "]" * depth).encode())
    exe = Path(sysconfig.get_path("scripts")) / ("chat-prompt-shape.exe" if os.name == "nt" else "chat-prompt-shape")
    result = subprocess.run([str(exe), str(path)], capture_output=True, text=True)
    assert (result.returncode, result.stdout, result.stderr) == (2, '{"status":"invalid_input"}\n', "")
