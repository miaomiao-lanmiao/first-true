# Echo / 回声助手

一个已有终端、TUI 和本地 Web 界面的 Python AI 聊天助手原型。
An existing Python assistant prototype with terminal, TUI, and loopback Web interfaces.

This repository is worth maintaining: it contains real application code and a
working starting point. The original project lives in [`echo/`](echo/).

## Install from source / 源码安装

Requires Python 3.11+ for the tested development environment.

```sh
git clone https://github.com/miaomiao-lanmiao/first-true.git
cd first-true
python -m venv .venv
# Activate .venv for your shell, then:
python -m pip install ./echo
echo-chat --help
echo-chat providers
echo-chat web
```

Visit `http://127.0.0.1:8000`. Use `echo-chat chat` for the TUI, or
`echo-chat chat "Explain this code"` for a single request. The legacy `echo`
entry point is retained, but shell built-ins may shadow it; prefer `echo-chat`
or `python -m echo`.

Configure a provider/model in the local settings panel or CLI. For API keys,
prefer `ECHO_API_KEY` supplied by your environment/secret manager; command-line
arguments may remain in shell history. `ECHO_BASE_URL` and `ECHO_MODEL` override
the corresponding settings. Provider/model choices are examples; check your
provider account for current availability and pricing.

## Storage and privacy / 存储与隐私

`ECHO_CONFIG_DIR` sets an explicit data directory. The default remains
`~/.config/echo`. Conversations, settings, skills and task history are stored
locally. Saved API keys are **plaintext**, not encrypted; environment-managed
credentials are preferable. Atomic config/session writes restrict new files on
POSIX systems; Windows relies on the user's directory ACL.

Configuration displays omit stored keys. Settings fields remain blank to retain
existing credentials; enter `clear` to remove a key. Browser-direct speech
services require a key re-entered for the current page, since saved credentials
are not returned to JavaScript. Browser-native voice functions do not need this.

The web server accepts loopback hosts and same-origin browser API calls only;
remote access/authentication is outside this prototype's scope. Chat requests
send your conversation to the chosen AI provider. Optional external speech
features send audio/text to the configured endpoint. Scheduled tasks can also
contact that provider when enabled; leave tasks disabled unless intended.
Bundled browser assets load locally without a CDN.

## Verification / 验证

```sh
python -m pip install -r requirements-dev.txt
python -m pip install --no-deps -e ./echo
python -m unittest discover -s echo/tests -v
python -m build echo
python tools/check_package.py
```

The tests use synthetic keys and temporary data directories. They never read
personal assistant settings or call real AI services. CI runs on Linux and
Windows with Python 3.11/3.13. Optional browser QA is in `tools/browser-check.cjs`;
set `ECHO_PLAYWRIGHT_PATH` to an installed Playwright module and run it with Node.

See [the improvement report](docs/REPOSITORY_REVIEW.md),
[contribution guide](CONTRIBUTING.md), and [security policy](SECURITY.md).

## License

MIT, matching the existing package's declared license. Vendored browser libraries
retain their own licenses under `echo/echo/web_static/vendor/`.
