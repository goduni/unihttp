---
title: Install unihttp
description: Install unihttp on Python 3.12–3.14. Choose an HTTP backend and serializer, copy the pip or uv command, and verify your installation.
---

<div class="uh-install" markdown="1">

Getting started
{ .uh-eyebrow }

# Install unihttp

A small core. The dependencies you choose.
{ .uh-lead }

Install an HTTP backend and a serializer, then start building your API client.
No need to install every integration.

Python **3.12–3.14** · pip or uv
{ .uh-install-requirements }

## 1. Install your stack {#choose-your-extras}

Choose your HTTP library, then your model serializer. Run **one** of the two
commands shown. If you are following the quickstart, keep **Adaptix** selected.
Not sure which transport fits? [Compare the backends](../integrations/backends.md).

<details class="uh-install-help" markdown="1">
<summary>Starting fresh? Set up an environment first.</summary>

For pip, create an isolated environment with a supported Python interpreter.
Activate it before running the installation command.

=== "macOS / Linux"

    ```bash
    python3.12 -m venv .venv
    source .venv/bin/activate
    ```

=== "Windows (PowerShell)"

    ```powershell
    py -3.12 -m venv .venv
    .venv\Scripts\Activate.ps1
    ```

Python 3.13 or 3.14 also works; replace the interpreter version above.

For a new uv project, run the following, then use `uv add` below.
uv manages the project's environment; you do not need to activate it.

```bash
uv init --python 3.12 my-api-client
cd my-api-client
```

More about [pip environments](https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/)
and [uv projects](https://docs.astral.sh/uv/guides/projects/).

</details>

<div class="uh-install-picker" markdown="1">

HTTP library
{ .uh-install-label }

=== "HTTPX"

    Sync and async.
    { .uh-install-mode }

    Model serialization
    { .uh-install-label }

    === "Adaptix"

        For dataclasses and TypedDicts. Used throughout the quickstarts.

        ```bash title="pip · activated virtual environment"
        python -m pip install "unihttp[httpx,adaptix]"
        ```

        ```bash title="uv · existing project"
        uv add "unihttp[httpx,adaptix]"
        ```

    === "Pydantic"

        For applications with Pydantic response models.

        ```bash title="pip · activated virtual environment"
        python -m pip install "unihttp[httpx,pydantic]"
        ```

        ```bash title="uv · existing project"
        uv add "unihttp[httpx,pydantic]"
        ```

    === "msgspec"

        For applications with msgspec.Struct response models.

        ```bash title="pip · activated virtual environment"
        python -m pip install "unihttp[httpx,msgspec]"
        ```

        ```bash title="uv · existing project"
        uv add "unihttp[httpx,msgspec]"
        ```

=== "requests"

    Sync only.
    { .uh-install-mode }

    Model serialization
    { .uh-install-label }

    === "Adaptix"

        For dataclasses and TypedDicts. Used throughout the quickstarts.

        ```bash title="pip · activated virtual environment"
        python -m pip install "unihttp[requests,adaptix]"
        ```

        ```bash title="uv · existing project"
        uv add "unihttp[requests,adaptix]"
        ```

    === "Pydantic"

        For applications with Pydantic response models.

        ```bash title="pip · activated virtual environment"
        python -m pip install "unihttp[requests,pydantic]"
        ```

        ```bash title="uv · existing project"
        uv add "unihttp[requests,pydantic]"
        ```

    === "msgspec"

        For applications with msgspec.Struct response models.

        ```bash title="pip · activated virtual environment"
        python -m pip install "unihttp[requests,msgspec]"
        ```

        ```bash title="uv · existing project"
        uv add "unihttp[requests,msgspec]"
        ```

=== "aiohttp"

    Async only.
    { .uh-install-mode }

    Model serialization
    { .uh-install-label }

    === "Adaptix"

        For dataclasses and TypedDicts. Used throughout the quickstarts.

        ```bash title="pip · activated virtual environment"
        python -m pip install "unihttp[aiohttp,adaptix]"
        ```

        ```bash title="uv · existing project"
        uv add "unihttp[aiohttp,adaptix]"
        ```

    === "Pydantic"

        For applications with Pydantic response models.

        ```bash title="pip · activated virtual environment"
        python -m pip install "unihttp[aiohttp,pydantic]"
        ```

        ```bash title="uv · existing project"
        uv add "unihttp[aiohttp,pydantic]"
        ```

    === "msgspec"

        For applications with msgspec.Struct response models.

        ```bash title="pip · activated virtual environment"
        python -m pip install "unihttp[aiohttp,msgspec]"
        ```

        ```bash title="uv · existing project"
        uv add "unihttp[aiohttp,msgspec]"
        ```

=== "HTTPX2"

    Sync and async.
    { .uh-install-mode }

    Model serialization
    { .uh-install-label }

    === "Adaptix"

        For dataclasses and TypedDicts. Used throughout the quickstarts.

        ```bash title="pip · activated virtual environment"
        python -m pip install "unihttp[httpx2,adaptix]"
        ```

        ```bash title="uv · existing project"
        uv add "unihttp[httpx2,adaptix]"
        ```

    === "Pydantic"

        For applications with Pydantic response models.

        ```bash title="pip · activated virtual environment"
        python -m pip install "unihttp[httpx2,pydantic]"
        ```

        ```bash title="uv · existing project"
        uv add "unihttp[httpx2,pydantic]"
        ```

    === "msgspec"

        For applications with msgspec.Struct response models.

        ```bash title="pip · activated virtual environment"
        python -m pip install "unihttp[httpx2,msgspec]"
        ```

        ```bash title="uv · existing project"
        uv add "unihttp[httpx2,msgspec]"
        ```

=== "niquests"

    Sync and async.
    { .uh-install-mode }

    Model serialization
    { .uh-install-label }

    === "Adaptix"

        For dataclasses and TypedDicts. Used throughout the quickstarts.

        ```bash title="pip · activated virtual environment"
        python -m pip install "unihttp[niquests,adaptix]"
        ```

        ```bash title="uv · existing project"
        uv add "unihttp[niquests,adaptix]"
        ```

    === "Pydantic"

        For applications with Pydantic response models.

        ```bash title="pip · activated virtual environment"
        python -m pip install "unihttp[niquests,pydantic]"
        ```

        ```bash title="uv · existing project"
        uv add "unihttp[niquests,pydantic]"
        ```

    === "msgspec"

        For applications with msgspec.Struct response models.

        ```bash title="pip · activated virtual environment"
        python -m pip install "unihttp[niquests,msgspec]"
        ```

        ```bash title="uv · existing project"
        uv add "unihttp[niquests,msgspec]"
        ```

=== "zapros"

    Sync and async.
    { .uh-install-mode }

    Model serialization
    { .uh-install-label }

    === "Adaptix"

        For dataclasses and TypedDicts. Used throughout the quickstarts.

        ```bash title="pip · activated virtual environment"
        python -m pip install "unihttp[zapros,adaptix]"
        ```

        ```bash title="uv · existing project"
        uv add "unihttp[zapros,adaptix]"
        ```

    === "Pydantic"

        For applications with Pydantic response models.

        ```bash title="pip · activated virtual environment"
        python -m pip install "unihttp[zapros,pydantic]"
        ```

        ```bash title="uv · existing project"
        uv add "unihttp[zapros,pydantic]"
        ```

    === "msgspec"

        For applications with msgspec.Struct response models.

        ```bash title="pip · activated virtual environment"
        python -m pip install "unihttp[zapros,msgspec]"
        ```

        ```bash title="uv · existing project"
        uv add "unihttp[zapros,msgspec]"
        ```

=== "urllib"

    Sync only · standard-library transport.
    { .uh-install-mode }

    Model serialization
    { .uh-install-label }

    === "Adaptix"

        For dataclasses and TypedDicts. Used throughout the quickstarts.

        ```bash title="pip · activated virtual environment"
        python -m pip install "unihttp[adaptix]"
        ```

        ```bash title="uv · existing project"
        uv add "unihttp[adaptix]"
        ```

    === "Pydantic"

        For applications with Pydantic response models.

        ```bash title="pip · activated virtual environment"
        python -m pip install "unihttp[pydantic]"
        ```

        ```bash title="uv · existing project"
        uv add "unihttp[pydantic]"
        ```

    === "msgspec"

        For applications with msgspec.Struct response models.

        ```bash title="pip · activated virtual environment"
        python -m pip install "unihttp[msgspec]"
        ```

        ```bash title="uv · existing project"
        uv add "unihttp[msgspec]"
        ```

</div>

Installing extras makes integrations available; it does **not** select them in
your code. When you create a client, choose its backend class and pass
`request_dumper` and `response_loader` explicitly.
{ .uh-install-note }

## 2. Check the installation

Run this in the same environment where you installed unihttp.
It prints the installed package version without making a network request.

=== "pip"

    ```bash
    python -c "from importlib.metadata import version; print(version('unihttp'))"
    ```

=== "uv"

    ```bash
    uv run python -c "from importlib.metadata import version; print(version('unihttp'))"
    ```

<details class="uh-install-help" markdown="1">
<summary>Package not found, or an import fails?</summary>

- **`PackageNotFoundError` or `No module named unihttp`:** activate the environment
  used for installation, or run your script with `uv run python`. Check that your
  editor uses that same interpreter.
- **A backend or serializer module is missing:** rerun the command for the
  combination you selected. The core package does not install optional integrations.
- **Python version is incompatible:** use Python 3.12, 3.13, or 3.14. Check the
  interpreter with `python --version` (or `uv run python --version`).
- **`from unihttp import BaseMethod` fails:** public types live in submodules.
  Use `from unihttp.method import BaseMethod`; see the
  [method reference](../reference/methods.md).

</details>

## 3. Make your first call

The quickstarts use dataclasses and Adaptix with a local demo API.
Choose the execution model that fits your application.

<div class="uh-install-next" markdown="1">

[**Build a sync client →** <span>HTTPX, requests, HTTPX2, niquests, zapros, or urllib.</span>](quickstart.md)

[**Build an async client →** <span>HTTPX, aiohttp, HTTPX2, niquests, or zapros.</span>](async.md)

</div>

Using existing models? The [serialization guide](../guides/serialization.md#connect-a-serializer)
shows Adaptix, Pydantic, and msgspec setup side by side.

## Other installation options

<details class="uh-install-help" markdown="1">
<summary>Core only, with custom serialization</summary>

```bash
python -m pip install unihttp
```

This installs the core package, not optional HTTP or serializer dependencies.
Provide your own [request dumper and response loader](../reference/serializers.md).
The urllib backend needs no HTTP extra; third-party backends need their matching
extra or an already-installed dependency.

</details>

<details class="uh-install-help" markdown="1">
<summary id="follow-development-documentation">Run the examples from this repository</summary>

For a normal application, use a published package and keep your dependency
version pinned or locked. To work with the same source as this documentation:

```bash
git clone https://github.com/goduni/unihttp.git
cd unihttp
uv sync --group docs
uv run --group docs python examples/quickstart.py
```

This particular example uses HTTPX's mock transport, so it needs no demo server.
See [versions and migration](../project/releases.md) for release details and
[contributing](../project/documentation.md) to work on the library or its documentation.

</details>

</div>
