"""Run the response guides' exact examples together, in sync and async modes."""

import inspect
from contextlib import asynccontextmanager
from hashlib import sha256

import httpx
import pytest

from examples import (
    recipes,
    response_errors,
    response_metadata,
    response_retries,
    response_streaming,
)
from unihttp.exceptions import (
    ClientError,
    HTTPStatusError,
    NetworkError,
    RequestTimeoutError,
    ServerError,
)
from unihttp.serializers.adaptix import DEFAULT_RETORT, AdaptixDumper, AdaptixLoader


async def resolve(result):
    return await result if inspect.isawaitable(result) else result


@pytest.fixture(params=[False, True], ids=["sync", "async"])
def async_mode(request):
    return request.param


@asynccontextmanager
async def client_for(
    module, handler, async_mode, *, streaming=False, response_loader=None
):
    if streaming:
        cls = module.AsyncFileClient if async_mode else module.FileClient
    else:
        cls = module.AsyncUserClient if async_mode else module.UserClient
    session_cls = httpx.AsyncClient if async_mode else httpx.Client
    client = cls(
        base_url="https://api.example.com",
        request_dumper=AdaptixDumper(DEFAULT_RETORT),
        response_loader=response_loader
        if response_loader is not None
        else AdaptixLoader(DEFAULT_RETORT),
        session=session_cls(transport=httpx.MockTransport(handler)),
    )
    try:
        yield client
    finally:
        await resolve(client.close())


@pytest.fixture(autouse=True)
def no_retry_delays(monkeypatch):
    from unihttp.middlewares import AsyncRetryMiddleware, RetryMiddleware

    async def no_sleep(self, attempt):
        pass

    monkeypatch.setattr(RetryMiddleware, "_sleep", lambda self, attempt: None)
    monkeypatch.setattr(AsyncRetryMiddleware, "_sleep", no_sleep)


@pytest.mark.parametrize(
    "statuses,exception,attempts",
    [
        ([503, 503, 200], None, 3),
        ([503, 503, 503], ServerError, 3),
        ([404], recipes.UserNotFound, 1),
        ([401], ClientError, 1),
    ],
)
async def test_error_hook_mapper_and_retry_work_together(
    async_mode, statuses, exception, attempts
):
    seen = []

    def handler(request):
        status = statuses[len(seen)]
        seen.append(request)
        return httpx.Response(status, json={"id": 1, "name": "Ada"})

    async with client_for(response_retries, handler, async_mode) as client:
        if exception:
            with pytest.raises(exception):
                await resolve(client.get_user(user_id=1))
        else:
            assert await resolve(client.get_user(user_id=1)) == recipes.User(1, "Ada")
    assert len(seen) == attempts


async def test_post_has_status_handling_but_no_retry(async_mode):
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(503, json={"error": "unavailable"})

    async with client_for(response_retries, handler, async_mode) as client:
        with pytest.raises(ServerError):
            await resolve(client.create_user(name="Ada"))
    assert [request.method for request in seen] == ["POST"]


@pytest.mark.parametrize("failure", [httpx.ConnectError, httpx.ReadTimeout])
async def test_configured_transport_failures_retry(async_mode, failure):
    seen = []

    def handler(request):
        seen.append(request)
        if len(seen) < 3:
            raise failure("temporary failure", request=request)
        return httpx.Response(200, json={"id": 1, "name": "Ada"})

    async with client_for(response_retries, handler, async_mode) as client:
        assert (await resolve(client.get_user(user_id=1))).name == "Ada"
    assert len(seen) == 3


@pytest.mark.parametrize("status", [200, 404, 503])
async def test_call_site_fallback_and_status_metadata(async_mode, status, caplog):
    def handler(request):
        return httpx.Response(
            status, json={"id": 1, "name": "Ada"}, headers={"X-Request-ID": "request-123"}
        )

    find = response_errors.find_user_async if async_mode else response_errors.find_user
    async with client_for(response_errors, handler, async_mode) as client:
        if status == 503:
            with pytest.raises(ServerError) as caught:
                await resolve(find(client, 1))
            assert caught.value.status_code == 503
            assert caught.value.response.headers["X-Request-ID"] == "request-123"
            assert "request-123" in caplog.text
        else:
            result = await resolve(find(client, 1))
            assert result == (recipes.User(1, "Ada") if status == 200 else None)


@pytest.mark.parametrize(
    "failure,exception",
    [(httpx.ConnectError, NetworkError), (httpx.ReadTimeout, RequestTimeoutError)],
)
async def test_call_site_does_not_hide_transport_errors(async_mode, failure, exception):
    def handler(request):
        raise failure("unavailable", request=request)

    find = response_errors.find_user_async if async_mode else response_errors.find_user
    async with client_for(response_errors, handler, async_mode) as client:
        with pytest.raises(exception):
            await resolve(find(client, 1))


@pytest.mark.parametrize("status", [200, 503])
async def test_validation_handles_business_errors_without_intercepting_503(
    async_mode, status
):
    def handler(request):
        return httpx.Response(status, json={"ok": False, "error": "Account disabled"})

    mapper = (
        response_errors.async_status_errors
        if async_mode
        else response_errors.status_errors
    )
    async with client_for(response_errors, handler, async_mode) as client:
        with pytest.raises(response_errors.APIError if status == 200 else ServerError):
            await resolve(
                client.call_method(
                    response_errors.GetValidatedUser(1), middleware=[mapper]
                )
            )


@pytest.mark.parametrize("case", ["list", "envelope", "metadata", "missing-header"])
async def test_response_shapes(async_mode, case):
    user = {"id": 1, "name": "Ada"}
    payload = [user] if case == "list" else {"data": user} if case == "envelope" else user
    headers = {} if case == "missing-header" else {"X-Request-ID": "request-123"}

    def handler(request):
        return httpx.Response(200, json=payload, headers=headers)

    methods = {
        "list": response_metadata.ListUsers(),
        "envelope": response_metadata.GetWrappedUser(1),
    }
    method = methods.get(case, response_metadata.GetUser(1))
    loader = response_metadata.envelope_loader if case == "envelope" else None
    async with client_for(
        response_errors, handler, async_mode, response_loader=loader
    ) as client:
        result = await resolve(client.call_method(method))
    expected = response_metadata.User(1, "Ada")
    if case == "list":
        assert result == [expected]
    elif case == "envelope":
        assert result == expected
    else:
        assert result == response_metadata.UserResponse(
            expected, 200, headers.get("X-Request-ID")
        )


def test_envelope_method_uses_default_response_hook():
    from unihttp.method import BaseMethod

    assert response_metadata.GetWrappedUser.make_response is BaseMethod.make_response


def test_envelope_retort_keeps_model_validation():
    from adaptix.load_error import AggregateLoadError

    with pytest.raises(AggregateLoadError):
        response_metadata.envelope_loader.load(
            {"data": {"id": "invalid", "name": "Ada"}}, response_metadata.User
        )


def test_envelope_recipe_only_changes_loading():
    user = response_metadata.User(1, "Ada")
    payload = {"data": {"id": 1, "name": "Ada"}}
    assert response_metadata.envelope_loader.load(payload, response_metadata.User) == user
    assert payload == {"data": {"id": 1, "name": "Ada"}}
    assert response_metadata.envelope_retort.dump(user) == {"id": 1, "name": "Ada"}
    assert (
        AdaptixLoader(DEFAULT_RETORT).load(payload["data"], response_metadata.User)
        == user
    )


def test_envelope_recipe_applies_to_nested_users_too():
    user = response_metadata.User(1, "Ada")
    assert response_metadata.envelope_loader.load(
        [{"data": {"id": 1, "name": "Ada"}}], list[response_metadata.User]
    ) == [user]
    with pytest.raises(KeyError, match="data"):
        response_metadata.envelope_loader.load(
            {"id": 1, "name": "Ada"}, response_metadata.User
        )


async def test_model_loading_failure_is_not_retried(async_mode):
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"unexpected": "not a User"})

    async with client_for(response_retries, handler, async_mode) as client:
        with pytest.raises(Exception) as caught:
            await resolve(client.get_user(user_id=1))
        assert not isinstance(caught.value, HTTPStatusError)
    assert len(seen) == 1


class DownloadBody(httpx.SyncByteStream, httpx.AsyncByteStream):
    def __init__(self, failure=None):
        self.failure = failure
        self.closed = False

    def __iter__(self):
        yield b"a" * 65536
        if self.failure:
            raise self.failure("read failed")
        yield b"b"

    async def __aiter__(self):
        for chunk in self:
            yield chunk

    def close(self):
        self.closed = True

    async def aclose(self):
        self.closed = True


@pytest.mark.parametrize("status", [200, 302, 404, 500])
async def test_stream_rejects_errors_and_closes(async_mode, status):
    body = DownloadBody()

    def handler(request):
        return httpx.Response(status, stream=body)

    checksum = (
        response_streaming.download_checksum_async
        if async_mode
        else response_streaming.download_checksum
    )
    async with client_for(
        response_streaming, handler, async_mode, streaming=True
    ) as client:
        if status == 200:
            assert (
                await resolve(checksum(client, 1))
                == sha256(b"a" * 65536 + b"b").hexdigest()
            )
        else:
            with pytest.raises(HTTPStatusError) as caught:
                await resolve(checksum(client, 1))
            assert caught.value.status_code == status
        assert body.closed  # Before closing the client itself.


@pytest.mark.parametrize(
    "failure,exception",
    [(httpx.ReadError, NetworkError), (httpx.ReadTimeout, RequestTimeoutError)],
)
async def test_stream_read_failure_propagates_and_closes(async_mode, failure, exception):
    body = DownloadBody(failure)

    def handler(request):
        return httpx.Response(200, stream=body)

    checksum = (
        response_streaming.download_checksum_async
        if async_mode
        else response_streaming.download_checksum
    )
    async with client_for(
        response_streaming, handler, async_mode, streaming=True
    ) as client:
        with pytest.raises(exception):
            await resolve(checksum(client, 1))
        assert body.closed


async def test_stream_consumer_failure_closes_response(async_mode, monkeypatch):
    body = DownloadBody()

    class BrokenConsumer:
        def update(self, chunk):
            raise ValueError("consumer failed")

    monkeypatch.setattr(response_streaming, "sha256", BrokenConsumer)

    def handler(request):
        return httpx.Response(200, stream=body)

    checksum = (
        response_streaming.download_checksum_async
        if async_mode
        else response_streaming.download_checksum
    )
    async with client_for(
        response_streaming, handler, async_mode, streaming=True
    ) as client:
        with pytest.raises(ValueError, match="consumer failed"):
            await resolve(checksum(client, 1))
        assert body.closed
