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

## Upgrading from 0.3.x to 0.4.0

- **Backend exceptions:** error translation now covers more failures when
  sending requests and reading buffered or streamed responses. Update handlers
  that catch backend-specific exceptions to use the corresponding
  `unihttp.exceptions` types. The original exception is available as `__cause__`;
  exceptions outside each backend's mapping still propagate unchanged.
- **Retry policy:** the new `NonRetryableError` identifies deterministic failures
  such as invalid URLs and redirect loops. Opt into `NetworkError` and
  `RequestTimeoutError` for transport retries. Avoid retrying the base
  `UniHTTPError`, which also includes `NonRetryableError`. See
  [error handling](../guides/errors.md) and [retries](../recipes/retries.md).
- **Omitted values:** `copy.copy`, `copy.deepcopy`, and pickle round trips now
  preserve the `Omitted()` singleton, including inside dataclasses. See
  [copying and pickling](../recipes/partial-updates.md#copying-and-pickling).
- **zapros:** the minimum supported version increased from `0.11.0` to `0.12.0`.
  Update any dependency pins or lockfiles that still select an older version;
  the `unihttp[zapros]` extra declares the new minimum.

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

These checklist items describe existing contracts rather than changes introduced
in 0.4.0. See the migration notes above and the linked release notes for
version-specific changes. See
[errors](../guides/errors.md) and [serialization](../guides/serialization.md) for examples.
