from unittest.mock import MagicMock, Mock

import httpx
import pytest
from unihttp.clients.httpx import HTTPXSyncClient
from unihttp.exceptions import NetworkError, RequestTimeoutError
from unihttp.http.request import HTTPRequest


@pytest.fixture
def mock_httpx_client():
    return MagicMock(spec=httpx.Client)


def test_httpx_sync_make_request(mock_request_dumper, mock_response_loader, mock_httpx_client):
    client = HTTPXSyncClient(
        base_url="http://base",
        request_dumper=mock_request_dumper,
        response_loader=mock_response_loader,
        session=mock_httpx_client
    )

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.cookies = {}
    mock_response.json.return_value = {"key": "value"}
    mock_response.content = b'{"key": "value"}'
    mock_response.text = '{"key": "value"}'

    mock_httpx_client.request.return_value = mock_response

    request = HTTPRequest(
        url="/test",
        method="POST",
        header={"Auth": "123"},
        path={},
        query={"q": "1"},
        body={"data": "abc"},
        file={},
        form={}
    )

    response = client.make_request(request)

    mock_httpx_client.request.assert_called_once_with(
        method="POST",
        url="http://base/test",
        headers={"Auth": "123", "Content-Type": "application/json"},
        params={"q": "1"},
        data={},
        files=None,
        content='{"data": "abc"}'
    )

    assert response.status_code == 200
    assert response.data == {"key": "value"}


def test_httpx_sync_close(mock_request_dumper, mock_response_loader, mock_httpx_client):
    client = HTTPXSyncClient(
        "http://base",
        mock_request_dumper,
        mock_response_loader,
        session=mock_httpx_client
    )
    client.close()
    mock_httpx_client.close.assert_called_once()


def test_httpx_sync_network_error(mock_request_dumper, mock_response_loader, mock_httpx_client):
    client = HTTPXSyncClient("http://base", mock_request_dumper, mock_response_loader, session=mock_httpx_client)
    mock_httpx_client.request.side_effect = httpx.NetworkError("failures")

    request = HTTPRequest(
        url="/test",
        method="GET",
        header={},
        path={},
        query={},
        body={},
        file={},
        form={}
    )

    with pytest.raises(NetworkError):
        client.make_request(request)


def test_httpx_sync_timeout_error(mock_request_dumper, mock_response_loader, mock_httpx_client):
    client = HTTPXSyncClient("http://base", mock_request_dumper, mock_response_loader, session=mock_httpx_client)
    mock_httpx_client.request.side_effect = httpx.TimeoutException("timed out")

    request = HTTPRequest(
        url="/test",
        method="GET",
        header={},
        path={},
        query={},
        body={},
        file={},
        form={}
    )

    with pytest.raises(RequestTimeoutError):
        client.make_request(request)


def test_httpx_sync_body_and_form_error(mock_request_dumper, mock_response_loader, mock_httpx_client):
    client = HTTPXSyncClient(
        base_url="http://base",
        request_dumper=mock_request_dumper,
        response_loader=mock_response_loader,
        session=mock_httpx_client
    )

    request = HTTPRequest(
        url="/test",
        method="POST",
        header={},
        path={},
        query={},
        body={"some": "body"},
        file=None,
        form={"some": "form"}
    )

    with pytest.raises(ValueError, match="Cannot use Body with Form or File"):
        client.make_request(request)


def test_httpx_sync_file_list_conversion(mock_request_dumper, mock_response_loader, mock_httpx_client):
    from unihttp.http import UploadFile

    client = HTTPXSyncClient(
        base_url="http://base",
        request_dumper=mock_request_dumper,
        response_loader=mock_response_loader,
        session=mock_httpx_client
    )

    # Mock response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = b'{}'
    mock_response.text = '{}'
    mock_httpx_client.request.return_value = mock_response

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

    mock_httpx_client.request.assert_called_once()
    call_kwargs = mock_httpx_client.request.call_args[1]
    files = call_kwargs["files"]

    # Verify order and content
    assert files[0] == ("files", ("f1.txt", b"content1", "application/octet-stream"))
    assert files[1] == ("files", ("f2.txt", b"content2"))
    assert files[2] == ("single_upload_file", ("f3.txt", b"content3", "application/octet-stream"))
    assert files[3] == ("single_tuple", ("f4.txt", b"content4"))
