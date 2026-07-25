import pytest
import niquests
from collections.abc import AsyncGenerator, Generator
from typing import cast
from unittest.mock import AsyncMock, Mock

from unihttp.clients.base import BaseSyncClient, BaseAsyncClient
from unihttp.clients.niquests import NiquestsSyncClient, NiquestsAsyncClient, _NiquestsChunkStream, \
    _NiquestsAsyncChunkStream
from unihttp.exceptions import NetworkError, RequestTimeoutError
from unihttp.http import HTTPRequest
from unihttp.serialize import RequestDumper, ResponseLoader


@pytest.fixture
def sync_client(mock_request_dumper, mock_response_loader) -> Generator[BaseSyncClient, None, None]:
    client = NiquestsSyncClient(
        base_url="http://test.com",
        request_dumper=mock_request_dumper,
        response_loader=mock_response_loader,
    )
    yield client
    client.close()


@pytest.fixture
async def async_client(mock_request_dumper, mock_response_loader) -> AsyncGenerator[BaseAsyncClient, None]:
    client = NiquestsAsyncClient(
        base_url="http://test.com",
        request_dumper=mock_request_dumper,
        response_loader=mock_response_loader,
    )
    yield client
    await client.close()


class TestNiquestsSyncClient:
    def test_make_request(self, sync_client: BaseSyncClient, mocker):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.cookies = {}
        mock_response.content = b'{"key": "value"}'
        
        mock_session_request = mocker.patch("niquests.Session.request", return_value=mock_response)

        client = cast(NiquestsSyncClient, sync_client)
        
        request = HTTPRequest(
            url="/path",
            method="GET",
            header={"User-Agent": "test"},
            path={},
            query={"q": "search"},
            body=None,
            form=None,
            file={}
        )

        response = client.make_request(request)

        assert response.status_code == 200
        assert response.data == {"key": "value"}
        
        mock_session_request.assert_called_once_with(
            method="GET",
            url="http://test.com/path",
            headers={"User-Agent": "test"},
            params={"q": "search"},
            files=None,
            data=None,
            stream=False,
        )

    def test_network_error(self, sync_client: BaseSyncClient, mocker):
        mocker.patch("niquests.Session.request", side_effect=niquests.exceptions.ConnectionError("Connection Check"))
        
        client = cast(NiquestsSyncClient, sync_client)
        request = HTTPRequest(
            url="/path", method="GET", header={}, path={}, query={}, body=None, form=None, file={}
        )

        with pytest.raises(NetworkError, match="Connection Check"):
            client.make_request(request)

    def test_timeout_error(self, sync_client: BaseSyncClient, mocker):
        mocker.patch("niquests.Session.request", side_effect=niquests.exceptions.Timeout("Timeout Check"))
        
        client = cast(NiquestsSyncClient, sync_client)
        request = HTTPRequest(
            url="/path", method="GET", header={}, path={}, query={}, body=None, form=None, file={}
        )

        with pytest.raises(RequestTimeoutError, match="Timeout Check"):
            client.make_request(request)

    def test_close(self, sync_client: BaseSyncClient, mocker):
        mock_close = mocker.patch("niquests.Session.close")
        sync_client.close()
        mock_close.assert_called_once()

    def test_file_list_conversion(self, sync_client: BaseSyncClient, mocker):
        from unihttp.http import UploadFile
        
        mock_response = Mock(status_code=200, content=b"{}")
        mock_response.headers = {}
        mock_session_request = mocker.patch("niquests.Session.request", return_value=mock_response)
        client = cast(NiquestsSyncClient, sync_client)

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
                    ("f2.txt", b"content2")
                ],
                "single_upload_file": UploadFile(b"content3", filename="f3.txt"),
                "single_tuple": ("f4.txt", b"content4")
            },
            form={}
        )

        client.make_request(request)
        
        mock_session_request.assert_called_once()
        call_kwargs = mock_session_request.call_args[1]
        files = call_kwargs["files"]
        
        assert files[0] == ("files", ("f1.txt", b"content1", "application/octet-stream"))
        assert files[1] == ("files", ("f2.txt", b"content2"))
        assert files[2] == ("single_upload_file", ("f3.txt", b"content3", "application/octet-stream"))
        assert files[3] == ("single_tuple", ("f4.txt", b"content4"))

    def test_init_with_session(self, mock_request_dumper, mock_response_loader):
        session = Mock(spec=niquests.Session)
        client = NiquestsSyncClient(
            base_url="http://base",
            request_dumper=mock_request_dumper,
            response_loader=mock_response_loader,
            session=session
        )
        assert client._session is session
        client.close()

    def test_request_with_body(self, sync_client: BaseSyncClient, mocker):
        mock_response = Mock(status_code=200, headers={}, content=b"{}", cookies={})
        mock_session_request = mocker.patch("niquests.Session.request", return_value=mock_response)
        
        client = cast(NiquestsSyncClient, sync_client)
        request = HTTPRequest(
            url="/path", method="POST", header={}, path={}, query={}, body={"key": "val"}, file={}, form=None
        )
        
        client.make_request(request)
        mock_session_request.assert_called_once()
        assert mock_session_request.call_args[1]["data"] == '{"key": "val"}'
        assert request.header["Content-Type"] == "application/json"

    def test_request_with_form(self, sync_client: BaseSyncClient, mocker):
        mock_response = Mock(status_code=200, headers={}, content=b"{}", cookies={})
        mock_session_request = mocker.patch("niquests.Session.request", return_value=mock_response)
        
        client = cast(NiquestsSyncClient, sync_client)
        request = HTTPRequest(
            url="/path", method="POST", header={}, path={}, query={}, body=None, file={}, form={"f": "v"}
        )
        
        client.make_request(request)
        mock_session_request.assert_called_once()
        assert mock_session_request.call_args[1]["data"] == {"f": "v"}

    def test_generic_request_exception(self, sync_client: BaseSyncClient, mocker):
        mocker.patch("niquests.Session.request", side_effect=niquests.exceptions.RequestException("Generic Error"))
        client = cast(NiquestsSyncClient, sync_client)
        request = HTTPRequest(
            url="/path", method="GET", header={}, path={}, query={}, body=None, file={}, form=None
        )
        with pytest.raises(NetworkError, match="Generic Error"):
            client.make_request(request)

    def test_raw_body(self, sync_client: BaseSyncClient, mocker):
        mock_response = Mock(status_code=200, headers={}, cookies={}, content=b"{}")
        mock_session_request = mocker.patch("niquests.Session.request", return_value=mock_response)

        client = cast(NiquestsSyncClient, sync_client)
        request = HTTPRequest(
            url="/raw", method="POST", header={}, path={}, query={},
            body={}, file={}, form={}, raw=b"raw-payload"
        )
        client.make_request(request)

        assert mock_session_request.call_args[1]["data"] == b"raw-payload"

    def test_stream_make_request(self, sync_client: BaseSyncClient, mocker):
        mock_response = Mock(status_code=200, headers={}, cookies={})
        mock_response.iter_content = Mock(return_value=iter([b"a", b"b"]))
        mock_session_request = mocker.patch("niquests.Session.request", return_value=mock_response)

        client = cast(NiquestsSyncClient, sync_client)
        request = HTTPRequest(
            url="/download", method="GET", header={}, path={}, query={},
            body={}, file={}, form={}
        )
        result = client.stream_make_request(request, chunk_size=1234)

        assert result.status_code == 200
        assert mock_session_request.call_args[1]["stream"] is True

        chunks = list(result.data)
        assert chunks == [b"a", b"b"]
        mock_response.iter_content.assert_called_once_with(chunk_size=1234)
        mock_response.close.assert_called_once()

    def test_chunk_stream_mid_stream_error_translated(self):
        def gen():
            yield b"a"
            raise niquests.exceptions.ConnectionError("connection lost")

        response = Mock()
        response.iter_content.return_value = gen()

        stream = _NiquestsChunkStream(response, chunk_size=999)
        assert next(stream) == b"a"
        with pytest.raises(NetworkError):
            next(stream)

    def test_chunk_stream_mid_stream_timeout_translated(self):
        def gen():
            yield b"a"
            raise niquests.exceptions.Timeout("timed out")

        response = Mock()
        response.iter_content.return_value = gen()

        stream = _NiquestsChunkStream(response, chunk_size=999)
        assert next(stream) == b"a"
        with pytest.raises(RequestTimeoutError):
            next(stream)


class TestNiquestsAsyncClient:
    @pytest.mark.asyncio
    async def test_make_request(self, async_client: BaseAsyncClient, mocker):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.cookies = {}
        mock_response.content = b'{"key": "value"}'
        
        # AsyncSession.request is an async method
        mock_session_request = mocker.patch("niquests.AsyncSession.request", new_callable=AsyncMock)
        mock_session_request.return_value = mock_response

        client = cast(NiquestsAsyncClient, async_client)
        
        request = HTTPRequest(
            url="/path",
            method="POST",
            header={"User-Agent": "test"},
            path={},
            query={},
            body={"some": "data"},
            form=None,
            file={}
        )

        response = await client.make_request(request)

        assert response.status_code == 200
        assert response.data == {"key": "value"}
        
        mock_session_request.assert_awaited_once_with(
            method="POST",
            url="http://test.com/path",
            headers={"User-Agent": "test", "Content-Type": "application/json"},
            params={},
            files=None,
            data='{"some": "data"}',
            stream=False,
        )

    @pytest.mark.asyncio
    async def test_raw_body(self, async_client: BaseAsyncClient, mocker):
        mock_response = Mock(status_code=200, headers={}, cookies={}, content=b"{}")
        mock_session_request = mocker.patch("niquests.AsyncSession.request", new_callable=AsyncMock)
        mock_session_request.return_value = mock_response

        request = HTTPRequest(
            url="/raw", method="POST", header={}, path={}, query={},
            body={}, file={}, form={}, raw=b"raw-payload"
        )
        await async_client.make_request(request)

        assert mock_session_request.call_args[1]["data"] == b"raw-payload"

    @pytest.mark.asyncio
    async def test_network_error(self, async_client: BaseAsyncClient, mocker):
        mocker.patch("niquests.AsyncSession.request", side_effect=niquests.exceptions.ConnectionError("Connection Check"))
        
        client = cast(NiquestsAsyncClient, async_client)
        request = HTTPRequest(
            url="/path", method="GET", header={}, path={}, query={}, body=None, form=None, file={}
        )

        with pytest.raises(NetworkError, match="Connection Check"):
            await client.make_request(request)

    @pytest.mark.asyncio
    async def test_timeout_error(self, async_client: BaseAsyncClient, mocker):
        mocker.patch("niquests.AsyncSession.request", side_effect=niquests.exceptions.Timeout("Timeout Check"))
        
        client = cast(NiquestsAsyncClient, async_client)
        request = HTTPRequest(
            url="/path", method="GET", header={}, path={}, query={}, body=None, form=None, file={}
        )

        with pytest.raises(RequestTimeoutError, match="Timeout Check"):
            await client.make_request(request)

    @pytest.mark.asyncio
    async def test_close(self, async_client: BaseAsyncClient, mocker):
        mock_close = mocker.patch("niquests.AsyncSession.close", new_callable=AsyncMock)
        await async_client.close()
        mock_close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_file_list_conversion(self, async_client: BaseAsyncClient, mocker):
        from unihttp.http import UploadFile
        
        mock_response = Mock(status_code=200, content=b"{}")
        mock_response.headers = {}
        mock_session_request = mocker.patch("niquests.AsyncSession.request", new_callable=AsyncMock)
        mock_session_request.return_value = mock_response
        
        client = cast(NiquestsAsyncClient, async_client)

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
                    ("f2.txt", b"content2")
                ],
                "single_upload_file": UploadFile(b"content3", filename="f3.txt"),
                "single_tuple": ("f4.txt", b"content4")
            },
            form={}
        )

        await client.make_request(request)
        
        mock_session_request.assert_awaited_once()
        call_kwargs = mock_session_request.call_args[1]
        files = call_kwargs["files"]
        
        assert files[0] == ("files", ("f1.txt", b"content1", "application/octet-stream"))
        assert files[1] == ("files", ("f2.txt", b"content2"))
        assert files[2] == ("single_upload_file", ("f3.txt", b"content3", "application/octet-stream"))
        assert files[3] == ("single_tuple", ("f4.txt", b"content4"))

    @pytest.mark.asyncio
    async def test_init_with_session(self, mock_request_dumper, mock_response_loader):
        session = AsyncMock(spec=niquests.AsyncSession)
        client = NiquestsAsyncClient(
            base_url="http://base",
            request_dumper=mock_request_dumper,
            response_loader=mock_response_loader,
            session=session
        )
        assert client._session is session
        await client.close()

    @pytest.mark.asyncio
    async def test_request_with_form(self, async_client: BaseAsyncClient, mocker):
        mock_response = Mock(status_code=200, headers={}, content=b"{}", cookies={})
        mock_session_request = mocker.patch("niquests.AsyncSession.request", new_callable=AsyncMock)
        mock_session_request.return_value = mock_response
        
        client = cast(NiquestsAsyncClient, async_client)
        request = HTTPRequest(
            url="/path", method="POST", header={}, path={}, query={}, body=None, file={}, form={"f": "v"}
        )
        
        await client.make_request(request)
        mock_session_request.assert_awaited_once()
        assert mock_session_request.call_args[1]["data"] == {"f": "v"}

    @pytest.mark.asyncio
    async def test_generic_request_exception(self, async_client: BaseAsyncClient, mocker):
        mocker.patch("niquests.AsyncSession.request", side_effect=niquests.exceptions.RequestException("Generic Error"))
        client = cast(NiquestsAsyncClient, async_client)
        request = HTTPRequest(
            url="/path", method="GET", header={}, path={}, query={}, body=None, file={}, form=None
        )
        with pytest.raises(NetworkError, match="Generic Error"):
            await client.make_request(request)

    @pytest.mark.asyncio
    async def test_stream_make_request(self, async_client: BaseAsyncClient, mocker):
        mock_response = Mock(status_code=200, headers={}, cookies={})

        async def gen():
            yield b"a"
            yield b"b"

        mock_response.iter_content = AsyncMock(return_value=gen())
        mock_response.close = AsyncMock()
        mocker.patch("niquests.AsyncSession.request", new_callable=AsyncMock, return_value=mock_response)

        client = cast(NiquestsAsyncClient, async_client)
        request = HTTPRequest(
            url="/download", method="GET", header={}, path={}, query={},
            body={}, file={}, form={}
        )
        result = await client.stream_make_request(request, chunk_size=1234)

        assert result.status_code == 200
        chunks = [chunk async for chunk in result.data]
        assert chunks == [b"a", b"b"]
        mock_response.iter_content.assert_awaited_once_with(chunk_size=1234)
        mock_response.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_chunk_stream_mid_stream_error_translated(self):
        async def gen():
            yield b"a"
            raise niquests.exceptions.ConnectionError("connection lost")

        response = Mock()
        stream = _NiquestsAsyncChunkStream(response, gen())
        assert await anext(stream) == b"a"
        with pytest.raises(NetworkError):
            await anext(stream)

    @pytest.mark.asyncio
    async def test_chunk_stream_mid_stream_timeout_translated(self):
        async def gen():
            yield b"a"
            raise niquests.exceptions.Timeout("timed out")

        response = Mock()
        stream = _NiquestsAsyncChunkStream(response, gen())
        assert await anext(stream) == b"a"
        with pytest.raises(RequestTimeoutError):
            await anext(stream)
