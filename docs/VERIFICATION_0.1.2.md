# Echo v0.1.2 verification

Date: 2026-11-09 (Asia/Shanghai). Local platform: Windows, Python 3.11.15.

## Reproduced failures

- The initial four new provider test methods ran 60 provider/mode/status cases.
  There were 50 failing subcases before the repair: HTTP failures returned empty
  results, explicit error payloads were ignored, and connection error text leaked
  synthetic request details. Successful response cases passed as a baseline.
- A CLI regression reproduced a failing invocation with no explanatory output.
- The browser regression reproduced blank streamed replies because the client
  expected `delta` while the local backend emitted `token`.
- A delayed conversation save reproduced an overlapping second chat request.
  The browser now waits for the save before accepting another turn.

## Gates

- 31 unit tests pass, including five provider adapters, HTTP 401/429/500,
  successful responses, explicit provider errors, connection failures and late
  read failures after a partial token. Public Web/CLI error behavior is covered.
- The browser check exercises persisted/legacy sessions, two successful mocked
  chat turns, a delayed conversation save, a failed response and an interrupted
  response. It checks visible text, separate replies and conversation history
  using local requests only.
- Wheel/sdist builds and the package gate verify bundled assets, offline wheel
  installation, source/installed version and the command outside the checkout.

Run `python -m unittest discover -s echo/tests -v`, `python -m build echo`, and
`python tools/check_package.py`. For optional Edge QA, set `ECHO_PLAYWRIGHT_PATH`
to an installed Playwright package and run `node tools/browser-check.cjs`.

Hosted Linux/Windows Python 3.11/3.13 CI is required before a release draft.
Tests use temporary local storage and synthetic values; they do not establish
current model availability or compatibility with real provider accounts.

HTTPX behavior was checked against its official
[exception hierarchy](https://github.com/encode/httpx/blob/0.28.1/docs/exceptions.md)
and [async streaming documentation](https://github.com/encode/httpx/blob/0.28.1/docs/async.md).
