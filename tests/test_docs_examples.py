"""Contract checks for the exact Python files embedded in the public docs."""

import json
import importlib
import re
import sys
from pathlib import Path
from http.server import ThreadingHTTPServer
from threading import Thread

import httpx
import pytest

from examples import (
    async_client,
    demo_api,
    middleware_async,
    middleware_scope,
    middleware_sync,
    optional_fields,
    quickstart,
    recipes,
    response_metadata,
)
from unihttp.http import UploadFile
from unihttp.middlewares import RetryMiddleware, SyncErrorMapperMiddleware
from unihttp.serializers.adaptix import DEFAULT_RETORT, AdaptixDumper, AdaptixLoader
from unihttp.serializers.msgspec import MsgspecDumper, MsgspecLoader
from unihttp.serializers.pydantic import PydanticDumper, PydanticLoader


def test_quickstart():
    assert quickstart.main() == quickstart.User(id=1, name="Ada")


@pytest.fixture
def docs_demo_api():
    with ThreadingHTTPServer(("127.0.0.1", 0), demo_api.DemoAPIHandler) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}"
        finally:
            server.shutdown()
            thread.join(timeout=5)


@pytest.mark.parametrize(
    "backend", ["httpx", "requests", "httpx2", "niquests", "zapros", "urllib"]
)
def test_sync_backend_tab(backend, docs_demo_api, monkeypatch):
    module = importlib.import_module(f"examples.backends.{backend}_sync")
    original_close = module.UserClient.close
    closed = []

    def close(client):
        original_close(client)
        closed.append(True)

    monkeypatch.setattr(module.UserClient, "close", close)
    assert module.main(docs_demo_api) == module.User(id=1, name="Ada")
    assert closed == [True]


@pytest.mark.parametrize("backend", ["httpx", "aiohttp", "httpx2", "niquests", "zapros"])
async def test_async_backend_tab(backend, docs_demo_api, monkeypatch):
    module = importlib.import_module(f"examples.backends.{backend}_async")
    original_close = module.UserClient.close
    closed = []

    async def close(client):
        await original_close(client)
        closed.append(True)

    monkeypatch.setattr(module.UserClient, "close", close)
    assert await module.main(docs_demo_api) == module.User(id=1, name="Ada")
    assert closed == [True]


async def test_async_quickstart():
    assert await async_client.main() == async_client.User(id=1, name="Ada")


def client_for(handler, **kwargs):
    return recipes.UserClient(
        base_url="https://api.example.com",
        request_dumper=AdaptixDumper(DEFAULT_RETORT),
        response_loader=AdaptixLoader(DEFAULT_RETORT),
        session=httpx.Client(transport=httpx.MockTransport(handler)),
        **kwargs,
    )


def test_create_auth_and_partial_update():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"id": 1, "name": "Ada"})

    with client_for(handler, middleware=[recipes.BearerAuth("test-token")]) as client:
        assert client.create_user(name="Ada").name == "Ada"
        client.update_user(user_id=1, name=None)
        client.update_user(user_id=1)
    assert json.loads(seen[0].content) == {"name": "Ada"}
    assert seen[0].headers["Authorization"] == "Bearer test-token"
    assert json.loads(seen[1].content) == {"name": None}
    assert seen[1].method == "PATCH"
    assert seen[1].url.path == "/users/1"
    assert seen[2].content == b""  # Empty body is not encoded as {} by this backend.


def test_method_error_and_status_mapper():
    def handler(request):
        return httpx.Response(404, json={"error": "missing"})

    with client_for(handler) as client:
        with pytest.raises(recipes.UserNotFound):
            client.get_user(user_id=999)
    with client_for(
        handler, middleware=[SyncErrorMapperMiddleware({404: ValueError})]
    ) as client:
        with pytest.raises(ValueError, match="HTTP 404"):
            client.create_user(name="Ada")


def test_upload_and_stream():
    seen = []

    def handler(request):
        seen.append(request)
        if request.url.path.startswith("/files/"):
            return httpx.Response(200, content=b"downloaded content")
        return httpx.Response(200, json={"id": 1, "name": "Ada"})

    with client_for(handler) as client:
        client.upload_avatar(
            user_id=1,
            caption="portrait",
            avatar=UploadFile(b"image", filename="ada.png", content_type="image/png"),
        )
        response = client.download_file(file_id=1)
        with response.data as stream:
            assert b"".join(stream) == b"downloaded content"
    assert "multipart/form-data" in seen[0].headers["Content-Type"]
    assert b'filename="ada.png"' in seen[0].content
    assert b"portrait" in seen[0].content


def test_retry_before_error_mapping():
    attempts = []

    def handler(request):
        attempts.append(request)
        return httpx.Response(
            503 if len(attempts) == 1 else 200, json={"id": 1, "name": "Ada"}
        )

    with client_for(
        handler,
        middleware=[
            SyncErrorMapperMiddleware({range(500, 600): RuntimeError}),
            RetryMiddleware(retries=1, backoff=0, jitter=False),
        ],
    ) as client:
        assert client.create_user(name="Ada").id == 1
    assert len(attempts) == 2


@pytest.mark.parametrize(
    "dumper,loader",
    [
        (AdaptixDumper(DEFAULT_RETORT), AdaptixLoader(DEFAULT_RETORT)),
        (PydanticDumper(), PydanticLoader()),
        (MsgspecDumper(), MsgspecLoader()),
    ],
)
def test_serializer_contract(dumper, loader):
    assert dumper.dump(recipes.CreateUser(name="Ada"))["body"] == {"name": "Ada"}
    assert dumper.dump(recipes.UpdateUser(user_id=1))["body"] == {}
    assert loader.load({"id": 1, "name": "Ada"}, recipes.User) == recipes.User(1, "Ada")


@pytest.mark.parametrize(
    "dumper",
    [AdaptixDumper(DEFAULT_RETORT), PydanticDumper(), MsgspecDumper()],
    ids=["adaptix", "pydantic", "msgspec"],
)
def test_optional_fields_across_methods_and_serializers(dumper):
    from unihttp.omitted import Omitted

    request = optional_fields.ListUsers().build_http_request(dumper)
    assert request.method == "GET"
    assert request.query == {}
    assert request.header == {}

    request = optional_fields.ListUsers(
        name="Ada", limit=10, accept="application/json"
    ).build_http_request(dumper)
    assert request.query == {"name": "Ada", "limit": 10}
    assert request.header == {"accept": "application/json"}
    assert dumper.dump(optional_fields.ListUsers(name="", limit=0))["query"] == {
        "name": "",
        "limit": 0,
    }
    assert dumper.dump(optional_fields.ListUsers(name=Omitted()))["query"] == {}

    for nickname, expected in [
        (Omitted(), {"name": "Ada"}),
        (None, {"name": "Ada", "nickname": None}),
        ("Countess", {"name": "Ada", "nickname": "Countess"}),
        ("", {"name": "Ada", "nickname": ""}),
    ]:
        request = optional_fields.CreateUser(
            name="Ada", nickname=nickname
        ).build_http_request(dumper)
        assert request.method == "POST"
        assert request.body == expected
    assert dumper.dump(optional_fields.CreateUser(name="Ada"))["body"] == {"name": "Ada"}

    assert dumper.dump(recipes.UpdateUser(user_id=1))["body"] == {}
    assert dumper.dump(recipes.UpdateUser(user_id=1, name=None))["body"] == {"name": None}
    assert dumper.dump(recipes.UpdateUser(user_id=1, name="Ada"))["body"] == {
        "name": "Ada"
    }


def test_raw_body_adaptix():
    request = recipes.PutBytes(content=b"payload").build_http_request(
        AdaptixDumper(DEFAULT_RETORT)
    )
    assert request.raw == b"payload"


def test_raw_upload_json_acknowledgement():
    def handler(request):
        assert request.method == "PUT"
        assert request.content == b"payload"
        return httpx.Response(200, json={"size": len(request.content)})

    with client_for(handler) as client:
        assert client.call_method(recipes.PutBytes(content=b"payload")) == {"size": 7}


def test_response_metadata():
    result = response_metadata.main()
    assert result.user == response_metadata.User(id=1, name="Ada")
    assert result.status_code == 200
    assert result.request_id == "request-123"


def test_middleware_scope(docs_demo_api, monkeypatch, capsys):
    from uuid import UUID

    seen = []
    make_request = middleware_scope.UserClient.make_request

    def record(client, request):
        seen.append(dict(request.header))
        return make_request(client, request)

    monkeypatch.setattr(middleware_scope.UserClient, "make_request", record)
    middleware_scope.main(docs_demo_api)
    assert capsys.readouterr().out.count("User(id=1, name='Ada')") == 3
    assert [headers.get("Cache-Control") for headers in seen] == [
        "no-cache",
        None,
        "no-cache",
    ]
    ids = [headers["X-Request-ID"] for headers in seen]
    assert len(set(ids)) == 3
    assert all(UUID(value).version == 4 for value in ids)


@pytest.mark.parametrize("module", [middleware_sync, middleware_async, middleware_scope])
def test_middleware_examples_are_standalone(module, tmp_path, docs_demo_api):
    import ast
    import shutil
    import subprocess

    source = Path(module.__file__).read_text()
    tree = ast.parse(source)
    assert "--8<--" not in source
    assert "MockTransport" not in source
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            assert node in tree.body, "Keep imports at module level"
            modules = (
                [node.module or ""]
                if isinstance(node, ast.ImportFrom)
                else [alias.name for alias in node.names]
            )
            assert all(not name.startswith("examples") for name in modules)
        if isinstance(node, ast.ClassDef):
            assert node in tree.body, "Keep classes at module level"
    script = tmp_path / Path(module.__file__).name
    shutil.copyfile(module.__file__, script)
    runner = (
        "import asyncio, inspect, runpy, sys; "
        "main = runpy.run_path(sys.argv[1])['main']; "
        "asyncio.run(main(sys.argv[2])) if inspect.iscoroutinefunction(main) else main(sys.argv[2])"
    )
    result = subprocess.run(
        [sys.executable, "-c", runner, str(script), docs_demo_api],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
        timeout=15,
    )
    assert "User(id=1, name='Ada')" in result.stdout


def test_sync_timing_middleware_connection(docs_demo_api, caplog):
    with caplog.at_level("INFO", logger="unihttp.timing"):
        middleware_sync.main(docs_demo_api)
    messages = [
        record.getMessage()
        for record in caplog.records
        if record.name == "unihttp.timing"
    ]
    assert len(messages) == 1
    assert re.fullmatch(r"GET → 200 in \d+\.\d ms", messages[0])


async def test_async_timing_middleware_connection(docs_demo_api, caplog):
    with caplog.at_level("INFO", logger="unihttp.timing"):
        await middleware_async.main(docs_demo_api)
    messages = [
        record.getMessage()
        for record in caplog.records
        if record.name == "unihttp.timing"
    ]
    assert len(messages) == 1
    assert re.fullmatch(r"GET → 200 in \d+\.\d ms", messages[0])


@pytest.mark.parametrize("is_async", [False, True], ids=["sync", "async"])
async def test_timing_middleware_preserves_response_and_errors(
    is_async, monkeypatch, caplog
):
    from unihttp.http.request import HTTPRequest
    from unihttp.http.response import HTTPResponse

    module = middleware_async if is_async else middleware_sync
    middleware = module.AsyncTimingMiddleware() if is_async else module.TimingMiddleware()
    ticks = iter([1.0, 1.125, 2.0])
    monkeypatch.setattr(module, "perf_counter", lambda: next(ticks))
    request = HTTPRequest(
        method="GET",
        url="/private?token=secret",
        header={"Authorization": "secret"},
        path={},
        query={},
        body={},
        file={},
        form={},
    )
    response = HTTPResponse(
        status_code=200,
        data={"secret": "payload"},
        headers={},
        cookies={},
        raw_response=None,
    )
    seen = []

    def send(received):
        seen.append(received)
        return response

    async def async_send(received):
        return send(received)

    with caplog.at_level("INFO", logger="unihttp.timing"):
        result = (
            await middleware.handle(request, async_send)
            if is_async
            else middleware.handle(request, send)
        )
    assert result is response
    assert seen == [request]
    assert [record.getMessage() for record in caplog.records] == ["GET → 200 in 125.0 ms"]

    error = RuntimeError("transport failed")

    def fail(received):
        raise error

    async def async_fail(received):
        raise error

    caplog.clear()
    with (
        caplog.at_level("INFO", logger="unihttp.timing"),
        pytest.raises(RuntimeError) as raised,
    ):
        if is_async:
            await middleware.handle(request, async_fail)
        else:
            middleware.handle(request, fail)
    assert raised.value is error
    assert not caplog.records


def test_custom_json_codec():
    pytest.importorskip("orjson")
    from examples import json_codec

    assert json_codec.main() == json_codec.User(id=1, name="Ada")


@pytest.mark.parametrize("status", [302, 404, 500])
def test_stream_error_closes_before_hook(status):
    observed = []

    class Download(recipes.DownloadFile):
        def on_error(self, response):
            observed.append((response.status_code, list(response.data)))

    def handler(request):
        return httpx.Response(status, content=b"error details")

    with client_for(handler) as client:
        response = client.call_method_stream(Download(file_id=1))
        assert response.status_code == status
        assert list(response.data) == []
    assert observed == [(status, [])]


def test_readme_links_to_documentation():
    import tomllib

    root = Path(__file__).resolve().parents[1]
    config = tomllib.loads((root / "zensical.toml").read_text())
    url = config["project"]["site_url"]
    assert f"[Documentation]({url})" in (root / "README.md").read_text()
