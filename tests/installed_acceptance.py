"""Shell-independent installed example acceptance check."""
import json
import subprocess
import sysconfig
import os
from pathlib import Path

exe = Path(sysconfig.get_path("scripts")) / ("chat-prompt-shape.exe" if os.name == "nt" else "chat-prompt-shape")
p = subprocess.run([str(exe), "examples/turn-issues.jsonl"], capture_output=True, text=True)
assert p.returncode == 1
assert p.stdout == json.dumps({"status":"turn_issues","record_count":2,"invalid_turn_lines":[1,2]}, separators=(",", ":")) + "\n"
assert p.stderr == ""
print("Installed turn-issues fixture PASS")
