import http.client
import urllib.error
from contextlib import AsyncExitStack, ExitStack, contextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import httpx
import httpx2
import niquests
import pytest
import requests
import zapros
from unihttp.clients.aiohttp import AiohttpAsyncClient, _AiohttpChunkStream
from unihttp.clients.httpx import (
    HTTPXAsyncClient,
    HTTPXSyncClient,
    _HTTPXAsyncChunkStream,
    _HTTPXChunkStream,
)
from unihttp.clients.httpx2 import (
    HTTPX2AsyncClient,
    HTTPX2SyncClient,
    _HTTPX2AsyncChunkStream,
    _HTTPX2ChunkStream,
)
from unihttp.clients.niquests import (
    NiquestsAsyncClient,
    NiquestsSyncClient,
    _NiquestsAsyncChunkStream,
    _NiquestsChunkStream,
)
from unihttp.clients.requests import RequestsSyncClient, _RequestsChunkStream
from unihttp.clients.urllib import UrllibSyncClient, _UrllibChunkStream
from unihttp.clients.zapros import (
    ZaprosAsyncClient,
    ZaprosSyncClient,
    _ZaprosAsyncChunkStream,
    _ZaprosChunkStream,
)
from unihttp.exceptions import (
    NetworkError,
    NonRetryableError,
    RequestTimeoutError,
    UniHTTPError,
)
from unihttp.http.request import HTTPRequest


def http_request(url="/x"):
    return HTTPRequest(
        url=url, method="GET", header={}, path={}, query={}, body={}, file={}, form={}
    )


def make_client(cls, base_url="http://test", **kwargs):
    return cls(
        base_url=base_url, request_dumper=MagicMock(), response_loader=MagicMock(), **kwargs
    )


def case_id(value):
    if isinstance(value, BaseException):
        return type(value).__name__
    return getattr(value, "__name__", None)


@contextmanager
def raises_exactly(expected, cause=None):
    # pytest.raises(UniHTTPError) would also pass for its subclass NetworkError.
    with pytest.raises(expected) as info:
        yield
    assert type(info.value) is expected
    if cause is not None:
        assert info.value.__cause__ is cause


def one_chunk_then(exc):
    yield b"a"
    raise exc


async def one_async_chunk_then(exc):
    yield b"a"
    raise exc


def assert_second_chunk_raises(stream, exc, expected):
    assert next(stream) == b"a"
    with raises_exactly(expected, cause=exc):
        next(stream)


async def assert_second_async_chunk_raises(stream, exc, expected):
    assert await anext(stream) == b"a"
    with raises_exactly(expected, cause=exc):
        await anext(stream)


TRUNCATED = {"headers": ["Content-Length: 100"], "body": b"x" * 10}


@pytest.fixture(
    params=[
        SimpleNamespace(
            exceptions=requests.exceptions,
            client=RequestsSyncClient,
            stream=_RequestsChunkStream,
        ),
        SimpleNamespace(
            exceptions=niquests.exceptions,
            client=NiquestsSyncClient,
            stream=_NiquestsChunkStream,
        ),
    ],
    ids=["requests", "niquests"],
)
def requests_like(request):
    return request.param


REQUESTS_CASES = pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("ConnectTimeout", RequestTimeoutError),  # also a ConnectionError
        ("ReadTimeout", RequestTimeoutError),
        ("ConnectionError", NetworkError),
        ("ProxyError", NetworkError),
        ("SSLError", NetworkError),
        ("ChunkedEncodingError", NetworkError),
        ("RetryError", NetworkError),
        ("MissingSchema", NonRetryableError),
        ("InvalidSchema", NonRetryableError),
        ("InvalidURL", NonRetryableError),
        ("InvalidHeader", NonRetryableError),
        ("InvalidJSONError", NonRetryableError),
        ("URLRequired", NonRetryableError),
        ("TooManyRedirects", NonRetryableError),
        ("ContentDecodingError", NonRetryableError),
        ("UnrewindableBodyError", NonRetryableError),
        # Status, misuse and unknown errors: plain UniHTTPError, never retried.
        ("HTTPError", UniHTTPError),
        ("StreamConsumedError", UniHTTPError),
        ("RequestException", UniHTTPError),
    ],
    ids=case_id,
)


@REQUESTS_CASES
def test_requests_like_errors(requests_like, name, expected):
    exc = getattr(requests_like.exceptions, name)("x")
    session = MagicMock()
    session.request.side_effect = exc

    with raises_exactly(expected, cause=exc):
        make_client(requests_like.client, session=session).make_request(http_request())


@REQUESTS_CASES
async def test_niquests_async_errors(name, expected):
    exc = getattr(niquests.exceptions, name)("x")
    session = MagicMock()
    session.request = AsyncMock(side_effect=exc)

    with raises_exactly(expected, cause=exc):
        await make_client(NiquestsAsyncClient, session=session).make_request(http_request())


def test_niquests_multiplexing_error():
    exc = niquests.exceptions.MultiplexingError("x")
    session = MagicMock()
    session.request.side_effect = exc

    with raises_exactly(NetworkError, cause=exc):
        make_client(NiquestsSyncClient, session=session).make_request(http_request())


@pytest.mark.parametrize(
    ("name", "expected"),
    [("ChunkedEncodingError", NetworkError), ("ContentDecodingError", NonRetryableError)],
    ids=case_id,
)
def test_requests_like_stream_errors(requests_like, name, expected):
    exc = getattr(requests_like.exceptions, name)("x")
    response = MagicMock()
    response.iter_content.return_value = one_chunk_then(exc)

    stream = requests_like.stream(response, chunk_size=5)
    assert_second_chunk_raises(stream, exc, expected)


async def test_niquests_async_stream_error():
    exc = niquests.exceptions.ChunkedEncodingError("x")
    stream = _NiquestsAsyncChunkStream(MagicMock(), one_async_chunk_then(exc))

    await assert_second_async_chunk_raises(stream, exc, NetworkError)


@pytest.fixture(
    params=[
        SimpleNamespace(
            module=httpx,
            client=HTTPXSyncClient,
            async_client=HTTPXAsyncClient,
            stream=_HTTPXChunkStream,
            async_stream=_HTTPXAsyncChunkStream,
        ),
        SimpleNamespace(
            module=httpx2,
            client=HTTPX2SyncClient,
            async_client=HTTPX2AsyncClient,
            stream=_HTTPX2ChunkStream,
            async_stream=_HTTPX2AsyncChunkStream,
        ),
    ],
    ids=["httpx", "httpx2"],
)
def httpx_like(request):
    return request.param


HTTPX_CASES = pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("ConnectTimeout", RequestTimeoutError),  # also a RequestError
        ("ReadTimeout", RequestTimeoutError),
        ("ConnectError", NetworkError),
        ("ReadError", NetworkError),
        ("RemoteProtocolError", NetworkError),  # server hung up
        ("ProxyError", NetworkError),
        ("InvalidURL", NonRetryableError),
        ("UnsupportedProtocol", NonRetryableError),
        ("LocalProtocolError", NonRetryableError),  # our malformed request
        ("TooManyRedirects", NonRetryableError),
        ("DecodingError", NonRetryableError),
        ("HTTPStatusError", UniHTTPError),
    ],
    ids=case_id,
)

HTTPX_STREAM_CASES = pytest.mark.parametrize(
    ("name", "expected"),
    [("RemoteProtocolError", NetworkError), ("DecodingError", NonRetryableError)],
    ids=case_id,
)


def make_httpx_error(module, name):
    if name == "HTTPStatusError":
        return module.HTTPStatusError("x", request=MagicMock(), response=MagicMock())
    return getattr(module, name)("x")


@HTTPX_CASES
def test_httpx_like_errors(httpx_like, name, expected):
    exc = make_httpx_error(httpx_like.module, name)
    session = MagicMock()
    session.send.side_effect = exc

    with raises_exactly(expected, cause=exc):
        make_client(httpx_like.client, session=session).make_request(http_request())


@HTTPX_CASES
async def test_httpx_like_async_errors(httpx_like, name, expected):
    exc = make_httpx_error(httpx_like.module, name)
    session = MagicMock()
    session.send = AsyncMock(side_effect=exc)

    with raises_exactly(expected, cause=exc):
        await make_client(httpx_like.async_client, session=session).make_request(http_request())


# A real session: a null byte makes build_request (not send) raise InvalidURL.
def test_httpx_like_real_invalid_url(httpx_like):
    with httpx_like.module.Client() as session, raises_exactly(NonRetryableError):
        make_client(httpx_like.client, session=session).make_request(http_request(url="a\x00"))


async def test_httpx_like_async_real_invalid_url(httpx_like):
    async with httpx_like.module.AsyncClient() as session:
        client = make_client(httpx_like.async_client, session=session)
        with raises_exactly(NonRetryableError):
            await client.make_request(http_request(url="a\x00"))


@HTTPX_STREAM_CASES
def test_httpx_like_stream_errors(httpx_like, name, expected):
    exc = getattr(httpx_like.module, name)("x")
    response = MagicMock()
    response.iter_bytes.return_value = one_chunk_then(exc)

    stream = httpx_like.stream(response, chunk_size=5)
    assert_second_chunk_raises(stream, exc, expected)


@HTTPX_STREAM_CASES
async def test_httpx_like_async_stream_errors(httpx_like, name, expected):
    exc = getattr(httpx_like.module, name)("x")
    response = MagicMock()
    response.aiter_bytes.return_value = one_async_chunk_then(exc)

    stream = httpx_like.async_stream(response, chunk_size=5)
    await assert_second_async_chunk_raises(stream, exc, expected)


ZAPROS_CASES = pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (zapros.ConnectTimeoutError("x"), RequestTimeoutError),
        (zapros.ConnectionError("x"), NetworkError),
        (zapros.SSLError("x"), NetworkError),
        (zapros.ReadError("x"), NetworkError),
        (zapros.WriteError("x"), NetworkError),
        (zapros.DecodingError("x"), NonRetryableError),
        (zapros.TooManyRedirectsError("x"), NonRetryableError),
        (zapros.UnhandledRequestError("x"), NonRetryableError),  # cassette miss
        (zapros.StatusCodeError(MagicMock()), UniHTTPError),
    ],
    ids=case_id,
)


@ZAPROS_CASES
def test_zapros_errors(exc, expected):
    session = MagicMock()
    session.request.side_effect = exc

    with raises_exactly(expected, cause=exc):
        make_client(ZaprosSyncClient, session=session).make_request(http_request())


@ZAPROS_CASES
async def test_zapros_async_errors(exc, expected):
    session = MagicMock()
    session.request = AsyncMock(side_effect=exc)

    with raises_exactly(expected, cause=exc):
        await make_client(ZaprosAsyncClient, session=session).make_request(http_request())


def test_zapros_body_read_error():
    exc = zapros.ReadError("x")
    session = MagicMock()
    session.request.return_value.read.side_effect = exc

    with raises_exactly(NetworkError, cause=exc):
        make_client(ZaprosSyncClient, session=session).make_request(http_request())


async def test_zapros_async_body_read_error():
    exc = zapros.ReadError("x")
    session = MagicMock()
    session.request = AsyncMock(return_value=MagicMock(aread=AsyncMock(side_effect=exc)))

    with raises_exactly(NetworkError, cause=exc):
        await make_client(ZaprosAsyncClient, session=session).make_request(http_request())


def test_zapros_stream_open_error():
    exc = zapros.ReadError("x")
    session = MagicMock()
    session.stream.return_value.__enter__.side_effect = exc

    with raises_exactly(NetworkError, cause=exc):
        make_client(ZaprosSyncClient, session=session).stream_make_request(http_request())


async def test_zapros_async_stream_open_error():
    exc = zapros.ReadError("x")
    session = MagicMock()
    session.stream.return_value.__aenter__.side_effect = exc

    with raises_exactly(NetworkError, cause=exc):
        await make_client(ZaprosAsyncClient, session=session).stream_make_request(http_request())


def test_zapros_stream_error():
    exc = zapros.DecodingError("x")
    response = MagicMock()
    response.iter_bytes.return_value = one_chunk_then(exc)

    stream = _ZaprosChunkStream(response, chunk_size=5, stack=ExitStack())
    assert_second_chunk_raises(stream, exc, NonRetryableError)


async def test_zapros_async_stream_error():
    exc = zapros.ReadError("x")
    response = MagicMock()
    response.async_iter_bytes.return_value = one_async_chunk_then(exc)

    stream = _ZaprosAsyncChunkStream(response, chunk_size=5, stack=AsyncExitStack())
    await assert_second_async_chunk_raises(stream, exc, NetworkError)


# Real zapros: it lets h11 errors and URL ValueErrors through unwrapped.
def test_zapros_real_truncated_body(raw_server):
    with make_client(ZaprosSyncClient, base_url=raw_server(**TRUNCATED)) as client:
        with raises_exactly(NetworkError):
            client.make_request(http_request())


def test_zapros_real_truncated_stream(raw_server):
    with make_client(ZaprosSyncClient, base_url=raw_server(**TRUNCATED)) as client:
        with raises_exactly(NetworkError), client.stream_make_request(http_request()).data as stream:
            b"".join(stream)


async def test_zapros_async_real_truncated_body(raw_server):
    async with make_client(ZaprosAsyncClient, base_url=raw_server(**TRUNCATED)) as client:
        with raises_exactly(NetworkError):
            await client.make_request(http_request())


def test_zapros_real_invalid_header(raw_server):
    request = http_request()
    request.header["X Y"] = "v"

    with make_client(ZaprosSyncClient, base_url=raw_server()) as client:
        with raises_exactly(NonRetryableError):
            client.make_request(request)


@pytest.mark.parametrize("base_url", ["gopher://x/", "http://exa mple.com/"])
def test_zapros_real_invalid_url(base_url):
    with make_client(ZaprosSyncClient, base_url=base_url) as client:
        with raises_exactly(NonRetryableError):
            client.make_request(http_request())

@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        # Also ClientConnectionErrors: the timeout must win.
        (aiohttp.ServerTimeoutError("x"), RequestTimeoutError),
        (aiohttp.ConnectionTimeoutError("x"), RequestTimeoutError),
        (aiohttp.SocketTimeoutError("x"), RequestTimeoutError),
        (TimeoutError("x"), RequestTimeoutError),
        (aiohttp.ClientConnectionError("x"), NetworkError),
        (aiohttp.ClientPayloadError("x"), NetworkError),
        (aiohttp.ClientHttpProxyError(MagicMock(), ()), NetworkError),
        # Also a ValueError: the network entry must win.
        (aiohttp.ClientConnectorCertificateError(MagicMock(), Exception("x")), NetworkError),
        (aiohttp.TooManyRedirects(MagicMock(), ()), NonRetryableError),
        (aiohttp.InvalidUrlClientError("http://x"), NonRetryableError),
        (aiohttp.NonHttpUrlClientError("ftp://x"), NonRetryableError),
        (ValueError("x"), NonRetryableError),
        (aiohttp.ClientResponseError(MagicMock(), (), status=404), UniHTTPError),
    ],
    ids=case_id,
)
async def test_aiohttp_errors(exc, expected):
    session = MagicMock()
    session.request = AsyncMock(side_effect=exc)

    with raises_exactly(expected, cause=exc):
        await make_client(AiohttpAsyncClient, session=session).make_request(http_request())


async def test_aiohttp_real_invalid_header(raw_server):
    request = http_request()
    request.header["X"] = "a\r\nb"

    async with make_client(AiohttpAsyncClient, base_url=raw_server()) as client:
        with raises_exactly(NonRetryableError):
            await client.make_request(request)


async def test_aiohttp_stream_error():
    exc = aiohttp.ClientPayloadError("x")
    response = MagicMock()
    response.content.iter_chunked.return_value = one_async_chunk_then(exc)

    stream = _AiohttpChunkStream(response, chunk_size=5)
    await assert_second_async_chunk_raises(stream, exc, NetworkError)


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (urllib.error.URLError(TimeoutError("x")), RequestTimeoutError),
        (urllib.error.URLError(ConnectionRefusedError("x")), NetworkError),
        (urllib.error.URLError("unknown url type: ftp"), NonRetryableError),
        # getresponse() raises these without wrapping them in URLError.
        (TimeoutError("x"), RequestTimeoutError),
        (http.client.RemoteDisconnected("x"), NetworkError),
        (http.client.BadStatusLine("x"), NetworkError),
        (http.client.InvalidURL("x"), NonRetryableError),
    ],
    ids=lambda v: repr(v) if isinstance(v, BaseException) else case_id(v),
)
def test_urllib_errors(exc, expected):
    opener = MagicMock()
    opener.open.side_effect = exc

    with raises_exactly(expected):
        make_client(UrllibSyncClient, opener=opener).make_request(http_request())


def test_urllib_malformed_url():
    # An empty base_url leaves the URL relative, which urllib.request.Request rejects.
    with raises_exactly(NonRetryableError):
        make_client(UrllibSyncClient, base_url="", opener=MagicMock()).make_request(http_request())


def test_urllib_stream_error():
    exc = http.client.IncompleteRead(b"")
    response = MagicMock()
    response.read.side_effect = [b"a", exc]

    assert_second_chunk_raises(_UrllibChunkStream(response, chunk_size=5), exc, NetworkError)


def test_urllib_read_interrupted_closes_response():
    response = MagicMock()
    response.read.side_effect = KeyboardInterrupt
    opener = MagicMock()
    opener.open.return_value = response

    with pytest.raises(KeyboardInterrupt):
        make_client(UrllibSyncClient, opener=opener).make_request(http_request())
    response.close.assert_called_once()
