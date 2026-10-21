# Verification record

Local environment: 2026-10-22 (Asia/Shanghai), Windows, Python 3.11.15.

| Gate | Result |
| --- | --- |
| unittest | 19 passed, including isolated TUI startup and storage/API regressions |
| Package build | Wheel and source archive built successfully |
| Wheel contents | Web UI, local vendor assets and echo-chat entry point present; no bytecode |
| Installed command | echo-chat --help succeeded |
| Edge headless QA | Model selector, sanitized Markdown and session persistence passed |
| Browser network | No external browser asset requests or page errors during the test |

Tests used temporary storage and synthetic values. No real provider request or
personal assistant configuration was used. Browser screenshots and local logs
remain ignored in `reports/`.

The new CI workflow repeats tests/build/package checks on Linux/Windows with
Python 3.11/3.13. Consult the PR checks for hosted results; this local record does
not by itself establish that a hosted run succeeded.
