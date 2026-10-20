"""Strict JSONL validation with deliberately non-disclosing diagnostics."""

import json
import re
import sys
from typing import Any


class InvalidInput(Exception):
    """Input file or command line does not satisfy the declared schema."""


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise InvalidInput
        result[key] = value
    return result


def _reject_constant(_: str) -> None:
    raise InvalidInput


def _has_surrogate(value: Any) -> bool:
    if isinstance(value, str):
        return any(0xD800 <= ord(char) <= 0xDFFF for char in value)
    if isinstance(value, list):
        return any(_has_surrogate(item) for item in value)
    if isinstance(value, dict):
        return any(_has_surrogate(k) or _has_surrogate(v) for k, v in value.items())
    return False


def _is_shape_valid(messages: list[dict[str, str]]) -> bool:
    if not messages:
        return False
    offset = 0
    if messages[0]["role"] == "system":
        offset = 1
        if len(messages) == 1 or any(m["role"] == "system" for m in messages[1:]):
            return False
    turns = messages[offset:]
    if not turns or any(m["role"] == "system" for m in turns):
        return False
    if turns[0]["role"] != "user" or turns[-1]["role"] != "user":
        return False
    return all(turns[i]["role"] != turns[i - 1]["role"] for i in range(1, len(turns)))


def validate(data: bytes) -> dict[str, Any]:
    """Validate all physical JSONL rows before returning aggregate output."""
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise InvalidInput from exc
    # Split only JSONL's CR, LF, and CRLF delimiters, not Unicode separators.
    if text == "":
        return {"status": "valid", "record_count": 0, "invalid_turn_lines": []}
    physical = re.split(r"\r\n|\r|\n", text)
    if physical[-1] == "" and text.endswith(("\r", "\n")):
        physical.pop()
    ids: set[str] = set()
    invalid_lines: list[int] = []
    record_count = 0
    for line_number, line in enumerate(physical, 1):
        if not line:
            raise InvalidInput
        try:
            value = json.loads(line, object_pairs_hook=_object, parse_constant=_reject_constant)
        except (json.JSONDecodeError, InvalidInput, ValueError) as exc:
            raise InvalidInput from exc
        if _has_surrogate(value):
            raise InvalidInput
        if not isinstance(value, dict) or set(value) != {"id", "messages"}:
            raise InvalidInput
        ident, messages = value["id"], value["messages"]
        if not isinstance(ident, str) or not ident or not isinstance(messages, list) or len(messages) > 10000:
            raise InvalidInput
        if ident in ids:
            raise InvalidInput
        ids.add(ident)
        for message in messages:
            if not isinstance(message, dict) or set(message) != {"role", "content"}:
                raise InvalidInput
            if message["role"] not in ("system", "user", "assistant") or not isinstance(message["content"], str):
                raise InvalidInput
        record_count += 1
        if not _is_shape_valid(messages):
            invalid_lines.append(line_number)
    return {
        "status": "turn_issues" if invalid_lines else "valid",
        "record_count": record_count,
        "invalid_turn_lines": invalid_lines,
    }


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args in (["-h"], ["--help"]):
        sys.stdout.write("usage: chat-prompt-shape PROMPTS.jsonl\nValidate normalized synthetic chat-generation turn shapes.\n")
        return 0
    if len(args) != 1:
        reason = "missing input path" if not args else ("extra arguments" if len(args) > 1 else "unknown option")
        sys.stderr.write(f"chat-prompt-shape: {reason}\n")
        sys.stdout.write('{"status":"invalid_input"}\n')
        return 2
    if args[0].startswith("-"):
        sys.stderr.write("chat-prompt-shape: unknown option\n")
        sys.stdout.write('{"status":"invalid_input"}\n')
        return 2
    try:
        with open(args[0], "rb") as source:
            result = validate(source.read())
    except (OSError, InvalidInput):
        sys.stdout.write('{"status":"invalid_input"}\n')
        return 2
    sys.stdout.write(json.dumps(result, separators=(",", ":"), ensure_ascii=True) + "\n")
    return 1 if result["status"] == "turn_issues" else 0


if __name__ == "__main__":
    raise SystemExit(main())
