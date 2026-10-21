# Contributor instructions

- This is the existing Echo prototype; preserve its purpose and user history.
- Work on a feature branch and keep commits focused. The current user requested
  repository improvements, including pushing tested changes through a review PR.
- Tests must use synthetic credentials and temporary `ECHO_CONFIG_DIR` storage;
  never inspect personal settings, start real scheduled tasks or call AI services.
- Keep stored credentials out of config displays, errors and API responses.
- Validate storage identifiers before filesystem operations. Preserve the loopback
  host restriction and same-origin API checks. Do not introduce remote access.
- Sanitize rendered model Markdown. Browser assets are vendored with version and
  license records; review updates explicitly.
- Run unit tests, package build, `tools/check_package.py`, and relevant browser
  checks before pushing. Do not commit caches, virtualenvs, generated package
  metadata, data stores, or test screenshots.
- Do not publish to PyPI or delete/rename the repository as part of maintenance.
