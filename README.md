# chat-prompt-shape

`chat-prompt-shape` is a small offline Python CLI for checking the turn shape of **normalized synthetic chat-generation fixtures** stored as JSON Lines. It validates every row before producing a result and never prints fixture IDs, roles, content, file paths, or parse exceptions.

## Install and run

Requires Python 3.10 or newer. The package has no runtime dependencies.

```console
python -m pip install .
chat-prompt-shape examples/valid.jsonl
```

The output is one JSON object containing `status`, `record_count`, and sorted one-based `invalid_turn_lines`. Exit codes are `0` for valid input and turn shapes, `1` when valid records contain turn issues, and `2` for invalid files, schema, or arguments. `--help` prints usage and exits successfully.

## Fixture grammar

Each nonblank physical JSONL row has exactly an `id` string and a `messages` array. Each message has exactly a `role` and `content`: roles are `system`, `user`, or `assistant`, and content is any string, including the empty string. At most 10,000 messages are accepted per row. A file may be empty. UTF-8 and JSON are strict; duplicate JSON keys, duplicate IDs, malformed rows, non-finite numbers, and surrogate code points are rejected.

A shape-valid prompt has an optional single `system` message first, then a nonempty sequence alternating `user`, `assistant`, `user`, and so on, ending with `user`. Thus a user-only prompt, system-plus-user prompt, and user-assistant-user prompt are valid. This is one explicit grammar for synthetic generation fixtures. It does not describe a universal chat protocol.

The command reports structural turn-shape results only. It does not render or tokenize prompts, verify chat templates or provider APIs, run models or networks, or assess safety, prompt injection, quality, or novelty.

## Development

```console
python -m pip install pytest
python -m pytest -q
```

CI installs the built project non-editably and runs the suite on Ubuntu and Windows with Python 3.10 and 3.13.
