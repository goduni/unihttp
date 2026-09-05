---
title: Versions and migration
description: Understand unihttp development documentation, release documentation, and how to check API changes before upgrading.
---

# Versions and migration

The `latest` Read the Docs version tracks `master`. It may document changes
that have not been published to PyPI. The package version in the source metadata
alone does not establish that every change is already released.

Use [GitHub releases](https://github.com/goduni/unihttp/releases) and
[PyPI](https://pypi.org/project/unihttp/) to identify published versions.
Compare the installed version with `python -m pip show unihttp`.

## Match documentation to your installation

Use documentation for your installed release when that version is available.
`stable`, when available, describes the current published release; `latest`
describes the development branch. Older releases may not have a documentation
site, so consult the README and source at their Git tag.

The current source supports Python 3.12–3.14. For another release, check that
release's package metadata rather than assuming the same Python requirements.
HTTP backends and serializers are optional dependencies with their own version
requirements.

## Upgrade checklist

Before upgrading, read the release notes and check the client backend,
serialization behavior, and any overridden response hooks. Run your API contract
tests, including errors and streaming cleanup.

When checking your client code, pay particular attention to these contracts:

- Pass `AdaptixDumper(DEFAULT_RETORT)` and `AdaptixLoader(DEFAULT_RETORT)`
  explicitly, not the retort itself.
- `call_method` returns the declared model, not an HTTP response wrapper.
- Returning a value from `on_error` does not replace the method's result.
- Extend Adaptix using `DEFAULT_RETORT.extend(recipe=[...])`.

These describe current behavior, not a list of changes introduced in a specific
release. Version-specific changes belong to the linked release notes. See
[errors](../guides/errors.md) and [serialization](../guides/serialization.md) for examples.
