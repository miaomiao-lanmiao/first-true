# Echo v0.1.1 verification

Date: 2026-10-23 (Asia/Shanghai). Local platform: Windows, Python 3.11.15.

- New legacy-session, shared-session listing, invalid-record and nested-list
  redaction cases reproduced failures in the prior source.
- All 24 unit tests passed, including title filenames with spaces, compatibility
  with the previous underscore format, isolated TUI startup and existing safety
  checks. Invalid stored records remain untouched.
- A browser regression reproduced missing messages after reload. The repaired
  browser test now opens both freshly persisted and legacy conversations, checks
  visible text and restored chat history, and confirms no external asset requests
  or page errors. No real AI service was called.
- Wheel/source builds passed with SPDX license metadata. The package gate installs
  the wheel offline into temporary storage and checks its package version and CLI
  from outside the source checkout, as well as bundled frontend assets.

Four Linux/Windows Python 3.11/3.13 hosted jobs are the remote gate. Consult the
maintenance PR and Actions for the hosted result. Private user data and actual
provider compatibility were not tested.
