---
title: Contributing to unihttp
description: Set up unihttp for development, add regression tests, run code checks, and submit a pull request to the library.
---

# Contributing to unihttp

Help improve unihttp with a bug fix, a clearer type signature, a backend or
serializer improvement, or a better example. Small, focused contributions are
welcome; documentation changes follow the same pull-request workflow as code.

## Before you start

Check [existing issues](https://github.com/goduni/unihttp/issues) and
[pull requests](https://github.com/goduni/unihttp/pulls) for related work.
For a new feature or a change to the public API, open an issue first to discuss
the use case, proposed interface, and alternatives.

For a bug report, include:

- A minimal example that reproduces the problem.
- Expected and actual behavior, including a relevant traceback.
- Python and unihttp versions, plus the HTTP backend and serializer in use.

Remove credentials and private response data from reports. For a suspected
vulnerability, follow the [security policy](https://github.com/goduni/unihttp/blob/master/.github/SECURITY.md)
instead of opening a public issue. Follow the project's
[code of conduct](https://github.com/goduni/unihttp/blob/master/.github/CODE_OF_CONDUCT.md)
in discussions and reviews.

## Set up your environment

You need Git, uv, and Python 3.12–3.14. Fork the repository on GitHub, then
replace `YOUR-USERNAME` with your account name:

```bash
git clone https://github.com/YOUR-USERNAME/unihttp.git
cd unihttp
git switch -c fix/describe-your-change
uv sync --group dev --group docs
```

The `dev` group installs the supported optional integrations, test tools, Ruff,
and mypy. The `docs` group adds the documentation builder and its checks.
Run the commands below from the repository root.

## Find the right place

- `src/unihttp/` — method definitions, binding, markers, and shared HTTP types.
- `src/unihttp/clients/` — sync and async HTTP backend adapters.
- `src/unihttp/serializers/` — Adaptix, Pydantic, and msgspec integrations.
- `src/unihttp/middlewares/` — middleware interfaces and implementations.
- `tests/test_core/`, `tests/test_clients/`, and `tests/test_features/` — focused
  tests for the corresponding parts of the library.
- `tests/test_integration/` — tests that exercise components together.
- `examples/` and `site/` — runnable examples and public documentation.

Start with nearby implementations and tests. Keep changes scoped to the issue;
avoid unrelated refactoring or formatting in the same pull request.

## Add tests for the change

For a bug fix, add a regression test that fails before the fix. For new behavior,
cover the expected result and relevant failure cases. If a change affects a
shared contract, check the applicable sync/async clients or serializers, not
just the integration used in your first example.

Run a focused test while iterating, for example:

```bash
uv run --group docs pytest tests/test_core/test_method.py -q
```

Use mocks or a local test server where practical. Tests should not depend on
private credentials or a third-party API being available.

## Run the checks

Before opening a pull request, run the checks used by the library's CI:

```bash
uv run --group docs ruff check
uv run --group docs ruff format --check
uv run --group docs mypy
uv run --group docs pytest --cov src --cov-fail-under=80
```

CI runs the library checks on Python 3.12, 3.13, and 3.14 and requires at least
80% test coverage. Including `--group docs` locally also enables the documentation
tests instead of skipping them when their dependencies are absent.

For local library tests across all three Python versions, use the Nox sessions
configured in `noxfile.py`:

```bash
uv run --group docs nox
```

Nox creates separate test environments. The Python interpreters need to be
available; run the checks on your current interpreter first for faster feedback.

## Documentation

Update the relevant guide, API docstring, or example when changing public
behavior. Public pages live in `site/`, runnable examples in `examples/`, and
navigation in `zensical.toml`. Internal notes under `docs/` are not published.

Preview the site locally:

```bash
uv run --group docs zensical serve
```

Open `http://localhost:8000`. To validate the complete site and its examples:

```bash
uv run --group docs pytest tests/test_docs_examples.py tests/test_docs_serialization.py tests/test_docs_responses.py tests/test_docs_build.py -q
uv run --group docs python scripts/build_docs.py
```

The full build checks links, anchors, and API reference output, then generates
Markdown exports and `llms.txt`. Output goes to `.build/docs/`; do not edit
generated files or use `site/` as the output directory.

Give each page a title, description, and one top-level heading. Keep existing
URLs where possible. Include tested examples from `examples/` instead of
copying code into Markdown. Use the existing backend tabs for client-specific
alternatives, with consistent library labels across pages.

## Open a pull request

Push your branch to your fork and open a pull request against `master` in
[goduni/unihttp](https://github.com/goduni/unihttp). In the description:

1. Explain the problem and the change; link the relevant issue.
2. Include a small usage example if the public interface changes.
3. Describe the tests you added and the checks you ran.
4. Call out breaking changes and any migration steps explicitly.

Review your diff and complete the repository's pull-request checklist. If you
change dependencies in `pyproject.toml`, run `uv sync --group dev --group docs`
and re-run the relevant checks. The generated `uv.lock` stays local and is not
committed. Watch CI and respond to review feedback; keep follow-up changes
focused on the same task.
