# Launch checklist

1. Use Python 3.10 or newer and install with `python -m pip install .`.
2. Run `chat-prompt-shape examples/valid.jsonl` and confirm status `valid`, count `2`, and no invalid turn lines.
3. Run `chat-prompt-shape examples/turn-issues.jsonl` and confirm status `turn_issues`, count `2`, line `[1,2]`, and exit code `1`.
4. Use synthetic fixtures only. This tool checks the documented normalized prompt turn grammar; it is not a renderer, tokenizer, provider compatibility checker, model runner, or security/content assessment.

Invalid files produce only `{"status":"invalid_input"}` on standard output and exit `2`. Inspect and correct the input privately before rerunning; the tool intentionally does not identify or echo the failing content.
