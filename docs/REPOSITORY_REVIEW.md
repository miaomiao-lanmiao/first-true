# Repository review / 仓库检查

Date: 2026-10-22 (Asia/Shanghai).

## Decision

**Keep and improve.** `first-true` contains the Echo application's CLI, TUI, Web
frontend, provider adapters and session/task features. It has one prior source
upload and one star. A generic name or small audience is not evidence of garbage.
No repository is selected for deletion in this review.

The other pre-existing repository, `agent-config-audit`, has an MIT license,
documented tests, passing CI and a real v0.1.0 release. It should also be retained.
It already has a narrow maintained scope; no speculative rewrite is needed.

## Changes

- Added a discoverable root README, contribution/security guidance, package
  installation instructions and an `echo-chat` command that avoids shell `echo`.
- Fixed shared nested defaults and provider-default selection. Config displays
  and API responses omit saved credential values; provider errors are sanitized.
- Added explicit data-directory selection, private atomic configuration/session
  writes, validated session/skill paths, loopback Host checks and same-origin
  browser API restrictions.
- Included Web static assets in the wheel. Vendored the existing Markdown and
  highlighting assets and added DOMPurify for model output. Fixed model selector,
  session persistence and settings response mismatches.
- Removed tracked Python bytecode and generated egg-info metadata while retaining
  application source and history. Added ignore rules to prevent regeneration.
- Added reproducible regression tests, wheel-content checks and hosted CI.

The original regression suite had 11 tests: one passed and ten test methods failed
(16 individual assertions/subtest failures). The focused repairs are checked
against these reproductions; additional lifecycle/package/browser checks cover
the changed integration paths.

## Remaining scope

This is still a prototype: no independent provider compatibility run, remote
authentication, encrypted key store, scheduler persistence overhaul or PyPI
publication was performed. Existing provider/model lists are examples, not a
claim about current provider availability. Tests do not use real accounts.
