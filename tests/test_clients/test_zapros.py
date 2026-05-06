import io
from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from typing import cast
from unittest.mock import AsyncMock, Mock

import pytest
import zapros

from unihttp.clients.base import BaseAsyncClient, BaseSyncClient
from unihttp.clients.zapros import (
    ZaprosAsyncClient,
    ZaprosSyncClient,
    _stringify_pairs,
    _to_bytes,
)
from unihttp.exceptions import NetworkError, RequestTimeoutError
from unihttp.http import HTTPRequest, UploadFile


class TestToBytes:
    def test_bytes_pass_through(self):
        data = b"abc"
        assert _to_bytes(data) is data

    def test_bytearray(self):
        result = _to_bytes(bytearray(b"abc"))
        assert isinstance(result, bytes)
        assert result == b"abc"

    def test_memoryview(self):
        result = _to_bytes(memoryview(b"abc"))
        assert isinstance(result, bytes)
        assert result == b"abc"

    def test_path(self, tmp_path: Path):
        f = tmp_path / "x.bin"
        f.write_bytes(b"contents")
        assert _to_bytes(f) == b"contents"

    def test_file_like_returns_bytes(self):
        assert _to_bytes(io.BytesIO(b"streamed")) == b"streamed"

    def test_file_like_returning_str_raises(self):
        text_handle = io.StringIO("text-mode")
        with pytest.raises(TypeError, match="expected bytes"):
            _to_bytes(text_handle)

    def test_unsupported_type_raises(self):
        with pytest.raises(TypeError, match="Unsupported file content type"):
            _to_bytes(12345)
        with pytest.raises(TypeError, match="Unsupported file content type"):
            _to_bytes("string-not-bytes")


class TestStringifyPairs:
    def test_strings_pass_through(self):
        assert _stringify_pairs({"q": "hello"}) == [("q", "hello")]

    def test_int_and_float(self):
        assert _stringify_pairs({"page": 1, "ratio": 0.5}) == [
            ("page", "1"),
            ("ratio", "0.5"),
        ]

    def test_bool_lowercased(self):
        # bool is a subclass of int — must be detected first
        assert _stringify_pairs({"flag": True, "off": False}) == [
            ("flag", "true"),
            ("off", "false"),
        ]

    def test_none_becomes_empty(self):
        assert _stringify_pairs({"x": None}) == [("x", "")]

    def test_list_value_expands_to_repeated_keys(self):
        assert _stringify_pairs({"id": [1, 2, 3]}) == [
            ("id", "1"),
            ("id", "2"),
            ("id", "3"),
        ]

    def test_tuple_value_also_expands(self):
        assert _stringify_pairs({"tag": ("a", "b")}) == [("tag", "a"), ("tag", "b")]

    def test_empty_mapping(self):
        assert _stringify_pairs({}) == []


def _mock_response(*, status: int = 200, content: bytes = b"{}") -> Mock:
    response = Mock(spec=zapros.Response)
    response.status = status
    response.headers = {}
    response.read = Mock(return_value=content)
    response.aread = AsyncMock(return_value=content)
    return response


@pytest.fixture
def sync_client(mock_request_dumper, mock_response_loader) -> Generator[BaseSyncClient, None, None]:
    client = ZaprosSyncClient(
        base_url="http://test.com",
        request_dumper=mock_request_dumper,
        response_loader=mock_response_loader,
    )
    yield client
    client.close()


@pytest.fixture
async def async_client(mock_request_dumper, mock_response_loader) -> AsyncGenerator[BaseAsyncClient, None]:
    client = ZaprosAsyncClient(
        base_url="http://test.com",
        request_dumper=mock_request_dumper,
        response_loader=mock_response_loader,
    )
    yield client
    await client.close()


class TestZaprosSyncClient:
    def test_make_request(self, sync_client: BaseSyncClient, mocker):
        mock_response = _mock_response(content=b'{"key": "value"}')
        mock_request = mocker.patch("zapros.Client.request", return_value=mock_response)

        client = cast(ZaprosSyncClient, sync_client)
        request = HTTPRequest(
            url="/path",
            method="GET",
            header={"User-Agent": "test"},
            path={},
            query={"q": "search"},
            body=None,
            form=None,
            file={},
        )

        response = client.make_request(request)

        assert response.status_code == 200
        assert response.data == {"key": "value"}
        mock_request.assert_called_once_with(
            method="GET",
            url="http://test.com/path",
            headers={"User-Agent": "test"},
            params=[("q", "search")],
            form=None,
            body=None,
            multipart=None,
        )

    def test_request_with_body(self, sync_client: BaseSyncClient, mocker):
        mock_request = mocker.patch("zapros.Client.request", return_value=_mock_response())

        client = cast(ZaprosSyncClient, sync_client)
        request = HTTPRequest(
            url="/path", method="POST", header={}, path={}, query={},
            body={"key": "val"}, file={}, form=None,
        )

        client.make_request(request)
        kwargs = mock_request.call_args[1]
        assert kwargs["body"] == b'{"key": "val"}'
        assert kwargs["form"] is None
        assert kwargs["multipart"] is None
        assert request.header["Content-Type"] == "application/json"

    def test_request_with_form(self, sync_client: BaseSyncClient, mocker):
        mock_request = mocker.patch("zapros.Client.request", return_value=_mock_response())

        client = cast(ZaprosSyncClient, sync_client)
        request = HTTPRequest(
            url="/path", method="POST", header={}, path={}, query={},
            body=None, file={}, form={"f": "v"},
        )

        client.make_request(request)
        kwargs = mock_request.call_args[1]
        assert kwargs["form"] == [("f", "v")]
        assert kwargs["body"] is None
        assert kwargs["multipart"] is None

    def test_form_coerces_non_string_values(self, sync_client: BaseSyncClient, mocker):
        """Form values get the same coercion as query (bool/int/None/list)."""
        mock_request = mocker.patch("zapros.Client.request", return_value=_mock_response())
        client = cast(ZaprosSyncClient, sync_client)

        request = HTTPRequest(
            url="/path", method="POST", header={}, path={}, query={},
            body=None, file={},
            form={"flag": True, "page": 1, "opt": None, "tags": ["a", "b"]},
        )

        client.make_request(request)
        assert mock_request.call_args[1]["form"] == [
            ("flag", "true"),
            ("page", "1"),
            ("opt", ""),
            ("tags", "a"),
            ("tags", "b"),
        ]

    def test_query_coerces_non_string_values(self, sync_client: BaseSyncClient, mocker):
        mock_request = mocker.patch("zapros.Client.request", return_value=_mock_response())
        client = cast(ZaprosSyncClient, sync_client)

        request = HTTPRequest(
            url="/path", method="GET", header={},
            path={},
            query={"page": 1, "flag": False, "opt": None, "ids": [1, 2]},
            body=None, file={}, form=None,
        )

        client.make_request(request)
        assert mock_request.call_args[1]["params"] == [
            ("page", "1"),
            ("flag", "false"),
            ("opt", ""),
            ("ids", "1"),
            ("ids", "2"),
        ]

    def test_request_with_files_builds_multipart(self, sync_client: BaseSyncClient, mocker):
        mock_request = mocker.patch("zapros.Client.request", return_value=_mock_response())
        client = cast(ZaprosSyncClient, sync_client)

        request = HTTPRequest(
            url="/upload",
            method="POST",
            header={},
            path={},
            query={},
            body=None,
            file={
                "files": [
                    UploadFile(b"content1", filename="f1.txt"),
                    ("f2.txt", b"content2"),
                ],
                "single_upload_file": UploadFile(b"content3", filename="f3.txt"),
                "single_tuple": ("f4.txt", b"content4", "image/png"),
            },
            form={"caption": "hello", "count": 42, "active": True},
        )

        client.make_request(request)

        kwargs = mock_request.call_args[1]
        assert kwargs["body"] is None
        assert kwargs["form"] is None
        multipart = kwargs["multipart"]
        assert isinstance(multipart, zapros.Multipart)

        # Render to bytes to verify all parts are present.
        rendered = multipart.to_body()
        assert isinstance(rendered, bytes)
        assert b'name="caption"' in rendered
        assert b"hello" in rendered
        # int and bool form values must be coerced to strings
        assert b'name="count"' in rendered
        assert b"42" in rendered
        assert b'name="active"' in rendered
        assert b"true" in rendered
        assert b'filename="f1.txt"' in rendered
        assert b"content1" in rendered
        assert b'filename="f2.txt"' in rendered
        assert b"content2" in rendered
        assert b'filename="f3.txt"' in rendered
        assert b"content3" in rendered
        assert b'filename="f4.txt"' in rendered
        assert b"content4" in rendered
        assert b"image/png" in rendered

    def test_file_part_variants(self, sync_client: BaseSyncClient, mocker):
        """Cover BinaryIO read-path and raw-bytes value path in `_add_file_part`."""
        mock_request = mocker.patch("zapros.Client.request", return_value=_mock_response())
        client = cast(ZaprosSyncClient, sync_client)

        request = HTTPRequest(
            url="/upload", method="POST", header={}, path={}, query={},
            body=None, form={},
            file={
                "stream": UploadFile(io.BytesIO(b"streamed"), filename="s.bin"),
                "raw": b"naked-bytes",
            },
        )

        client.make_request(request)
        rendered = mock_request.call_args[1]["multipart"].to_body()
        assert b"streamed" in rendered
        assert b'filename="s.bin"' in rendered
        assert b"naked-bytes" in rendered
        assert b'name="raw"' in rendered

    def test_non_json_response_kept_as_bytes(self, sync_client: BaseSyncClient, mocker):
        mocker.patch(
            "zapros.Client.request",
            return_value=_mock_response(content=b"<html>not json</html>"),
        )
        client = cast(ZaprosSyncClient, sync_client)

        request = HTTPRequest(
            url="/path", method="GET", header={}, path={}, query={},
            body=None, file={}, form=None,
        )

        response = client.make_request(request)
        assert response.data == b"<html>not json</html>"

    def test_empty_body_with_file_does_not_error(self, sync_client: BaseSyncClient, mocker):
        """Dumper defaults `body` to `{}` — that must not preempt file uploads."""
        mock_request = mocker.patch("zapros.Client.request", return_value=_mock_response())
        client = cast(ZaprosSyncClient, sync_client)

        request = HTTPRequest(
            url="/upload", method="POST", header={}, path={}, query={},
            body={}, form={}, file={"doc": UploadFile(b"x", filename="x.txt")},
        )

        client.make_request(request)
        kwargs = mock_request.call_args[1]
        assert kwargs["body"] is None
        assert isinstance(kwargs["multipart"], zapros.Multipart)

    def test_body_and_form_error(self, sync_client: BaseSyncClient):
        client = cast(ZaprosSyncClient, sync_client)
        request = HTTPRequest(
            url="/path", method="POST", header={}, path={}, query={},
            body={"b": "v"}, file={}, form={"f": "v"},
        )
        with pytest.raises(ValueError, match="Cannot use Body with Form or File"):
            client.make_request(request)

    def test_timeout_error(self, sync_client: BaseSyncClient, mocker):
        mocker.patch(
            "zapros.Client.request",
            side_effect=zapros.ReadTimeoutError("Timeout Check"),
        )
        client = cast(ZaprosSyncClient, sync_client)
        request = HTTPRequest(
            url="/path", method="GET", header={}, path={}, query={},
            body=None, file={}, form=None,
        )
        with pytest.raises(RequestTimeoutError, match="Timeout Check"):
            client.make_request(request)

    def test_network_error(self, sync_client: BaseSyncClient, mocker):
        mocker.patch(
            "zapros.Client.request",
            side_effect=zapros.ConnectionError("Connection Check"),
        )
        client = cast(ZaprosSyncClient, sync_client)
        request = HTTPRequest(
            url="/path", method="GET", header={}, path={}, query={},
            body=None, file={}, form=None,
        )
        with pytest.raises(NetworkError, match="Connection Check"):
            client.make_request(request)

    def test_close(self, sync_client: BaseSyncClient, mocker):
        mock_close = mocker.patch("zapros.Client.close")
        sync_client.close()
        mock_close.assert_called_once()

    def test_init_with_session(self, mock_request_dumper, mock_response_loader):
        session = Mock(spec=zapros.Client)
        client = ZaprosSyncClient(
            base_url="http://base",
            request_dumper=mock_request_dumper,
            response_loader=mock_response_loader,
            session=session,
        )
        assert client._session is session
        client.close()


class TestZaprosAsyncClient:
    @pytest.mark.asyncio
    async def test_make_request(self, async_client: BaseAsyncClient, mocker):
        mock_response = _mock_response(content=b'{"key": "value"}')
        mock_request = mocker.patch(
            "zapros.AsyncClient.request",
            new_callable=AsyncMock,
            return_value=mock_response,
        )
        client = cast(ZaprosAsyncClient, async_client)

        request = HTTPRequest(
            url="/path",
            method="POST",
            header={"User-Agent": "test"},
            path={},
            query={},
            body={"some": "data"},
            form=None,
            file={},
        )

        response = await client.make_request(request)

        assert response.status_code == 200
        assert response.data == {"key": "value"}
        kwargs = mock_request.call_args[1]
        assert kwargs["url"] == "http://test.com/path"
        assert kwargs["body"] == b'{"some": "data"}'
        assert kwargs["headers"] == {"User-Agent": "test", "Content-Type": "application/json"}

    @pytest.mark.asyncio
    async def test_request_with_form(self, async_client: BaseAsyncClient, mocker):
        mock_request = mocker.patch(
            "zapros.AsyncClient.request",
            new_callable=AsyncMock,
            return_value=_mock_response(),
        )
        client = cast(ZaprosAsyncClient, async_client)

        request = HTTPRequest(
            url="/path", method="POST", header={}, path={}, query={},
            body=None, file={}, form={"f": "v"},
        )

        await client.make_request(request)
        assert mock_request.call_args[1]["form"] == [("f", "v")]

    @pytest.mark.asyncio
    async def test_request_with_files_builds_multipart(self, async_client: BaseAsyncClient, mocker):
        mock_request = mocker.patch(
            "zapros.AsyncClient.request",
            new_callable=AsyncMock,
            return_value=_mock_response(),
        )
        client = cast(ZaprosAsyncClient, async_client)

        request = HTTPRequest(
            url="/upload",
            method="POST",
            header={},
            path={},
            query={},
            body=None,
            file={"doc": UploadFile(b"content", filename="test.txt")},
            form={},
        )

        await client.make_request(request)

        multipart = mock_request.call_args[1]["multipart"]
        assert isinstance(multipart, zapros.Multipart)
        rendered = multipart.to_body()
        assert isinstance(rendered, bytes)
        assert b'filename="test.txt"' in rendered
        assert b"content" in rendered

    @pytest.mark.asyncio
    async def test_non_json_response_kept_as_bytes(self, async_client: BaseAsyncClient, mocker):
        mocker.patch(
            "zapros.AsyncClient.request",
            new_callable=AsyncMock,
            return_value=_mock_response(content=b"<html>not json</html>"),
        )
        client = cast(ZaprosAsyncClient, async_client)

        request = HTTPRequest(
            url="/path", method="GET", header={}, path={}, query={},
            body=None, file={}, form=None,
        )

        response = await client.make_request(request)
        assert response.data == b"<html>not json</html>"

    @pytest.mark.asyncio
    async def test_body_and_form_error(self, async_client: BaseAsyncClient):
        client = cast(ZaprosAsyncClient, async_client)
        request = HTTPRequest(
            url="/path", method="POST", header={}, path={}, query={},
            body={"b": "v"}, file={}, form={"f": "v"},
        )
        with pytest.raises(ValueError, match="Cannot use Body with Form or File"):
            await client.make_request(request)

    @pytest.mark.asyncio
    async def test_timeout_error(self, async_client: BaseAsyncClient, mocker):
        mocker.patch(
            "zapros.AsyncClient.request",
            new_callable=AsyncMock,
            side_effect=zapros.ConnectTimeoutError("Timeout Check"),
        )
        client = cast(ZaprosAsyncClient, async_client)
        request = HTTPRequest(
            url="/path", method="GET", header={}, path={}, query={},
            body=None, file={}, form=None,
        )
        with pytest.raises(RequestTimeoutError, match="Timeout Check"):
            await client.make_request(request)

    @pytest.mark.asyncio
    async def test_network_error(self, async_client: BaseAsyncClient, mocker):
        mocker.patch(
            "zapros.AsyncClient.request",
            new_callable=AsyncMock,
            side_effect=zapros.ConnectionError("Connection Check"),
        )
        client = cast(ZaprosAsyncClient, async_client)
        request = HTTPRequest(
            url="/path", method="GET", header={}, path={}, query={},
            body=None, file={}, form=None,
        )
        with pytest.raises(NetworkError, match="Connection Check"):
            await client.make_request(request)

    @pytest.mark.asyncio
    async def test_close(self, async_client: BaseAsyncClient, mocker):
        mock_close = mocker.patch("zapros.AsyncClient.aclose", new_callable=AsyncMock)
        await async_client.close()
        mock_close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_init_with_session(self, mock_request_dumper, mock_response_loader):
        session = AsyncMock(spec=zapros.AsyncClient)
        client = ZaprosAsyncClient(
            base_url="http://base",
            request_dumper=mock_request_dumper,
            response_loader=mock_response_loader,
            session=session,
        )
        assert client._session is session
        await client.close()
