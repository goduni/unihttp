from unittest.mock import MagicMock, Mock

import pytest
import requests
from unihttp.clients.requests import RequestsSyncClient, _RequestsChunkStream
from unihttp.exceptions import NetworkError, RequestTimeoutError
from unihttp.http.request import HTTPRequest


@pytest.fixture
def mock_session():
    return MagicMock(spec=requests.Session)


def test_requests_make_request(mock_request_dumper, mock_response_loader, mock_session):
    client = RequestsSyncClient(
        base_url="http://base",
        request_dumper=mock_request_dumper,
        response_loader=mock_response_loader,
        session=mock_session
    )

    # Mock response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.cookies = {}
    mock_response.json.return_value = {"key": "value"}
    mock_response.content = b'{"key": "value"}'
    mock_session.request.return_value = mock_response

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

    # Verify call arguments
    mock_session.request.assert_called_once_with(
        method="POST",
        url="http://base/test",
        headers={"Auth": "123", "Content-Type": "application/json"},
        params={"q": "1"},
        data='{"data": "abc"}',
        files={},
        stream=False
    )

    # Verify response mapping
    assert response.status_code == 200
    assert response.data == {"key": "value"}
    assert response.headers == {"Content-Type": "application/json"}


def test_requests_close(mock_request_dumper, mock_response_loader, mock_session):
    client = RequestsSyncClient(
        base_url="http://base",
        request_dumper=mock_request_dumper,
        response_loader=mock_response_loader,
        session=mock_session
    )
    client.close()
    mock_session.close.assert_called_once()


def test_requests_context_manager(mock_request_dumper, mock_response_loader, mock_session):
    with RequestsSyncClient(
            base_url="http://base",
            request_dumper=mock_request_dumper,
            response_loader=mock_response_loader,
            session=mock_session
    ) as client:
        pass
    mock_session.close.assert_called_once()


def test_requests_network_error(mock_request_dumper, mock_response_loader, mock_session):
    client = RequestsSyncClient("http://base", mock_request_dumper, mock_response_loader, session=mock_session)
    mock_session.request.side_effect = requests.exceptions.ConnectionError("Connection Refused")

    request = HTTPRequest("url", "GET", {}, {}, {}, {}, {}, {})

    with pytest.raises(NetworkError):
        client.make_request(request)


def test_requests_timeout_error(mock_request_dumper, mock_response_loader, mock_session):
    client = RequestsSyncClient("http://base", mock_request_dumper, mock_response_loader, session=mock_session)
    mock_session.request.side_effect = requests.exceptions.Timeout("Timed out")

    request = HTTPRequest("GET", "url", {}, {}, {}, {}, {}, {})

    with pytest.raises(RequestTimeoutError):
        client.make_request(request)


def test_requests_form_only(mock_request_dumper, mock_response_loader, mock_session):
    client = RequestsSyncClient(
        base_url="http://base",
        request_dumper=mock_request_dumper,
        response_loader=mock_response_loader,
        session=mock_session
    )

    # Mock response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = b'{}'
    mock_session.request.return_value = mock_response

    request = HTTPRequest(
        url="/form",
        method="POST",
        header={},
        path={},
        query={},
        body=None,
        file=None,
        form={"key": "val"}
    )

    client.make_request(request)

    mock_session.request.assert_called_once()
    call_kwargs = mock_session.request.call_args[1]
    assert call_kwargs["data"] == {"key": "val"}


def test_requests_raw_body(mock_request_dumper, mock_response_loader, mock_session):
    response = Mock()
    response.status_code = 200
    response.headers = {}
    response.cookies = {}
    response.content = b"{}"
    mock_session.request.return_value = response

    client = RequestsSyncClient("http://base", mock_request_dumper, mock_response_loader, session=mock_session)

    request = HTTPRequest(
        url="/raw", method="POST", header={}, path={}, query={},
        body={}, file={}, form={}, raw=b"raw-payload"
    )
    client.make_request(request)

    call_kwargs = mock_session.request.call_args.kwargs
    assert call_kwargs["data"] == b"raw-payload"


def test_requests_stream_make_request(mock_request_dumper, mock_response_loader, mock_session):
    response = Mock()
    response.status_code = 200
    response.headers = {}
    response.cookies = {}
    response.iter_content.return_value = iter([b"a", b"b"])
    mock_session.request.return_value = response

    client = RequestsSyncClient("http://base", mock_request_dumper, mock_response_loader, session=mock_session)

    request = HTTPRequest(
        url="/download", method="GET", header={}, path={}, query={},
        body={}, file={}, form={}
    )
    result = client.stream_make_request(request, chunk_size=1234)

    assert result.status_code == 200
    call_kwargs = mock_session.request.call_args.kwargs
    assert call_kwargs["stream"] is True

    chunks = list(result.data)
    assert chunks == [b"a", b"b"]
    response.iter_content.assert_called_once_with(chunk_size=1234)
    response.close.assert_called_once()


def test_requests_chunk_stream_mid_stream_error_translated():
    def gen():
        yield b"a"
        raise requests.exceptions.ConnectionError("connection lost")

    response = Mock()
    response.iter_content.return_value = gen()

    stream = _RequestsChunkStream(response, chunk_size=999)
    assert next(stream) == b"a"
    with pytest.raises(NetworkError):
        next(stream)


def test_requests_chunk_stream_mid_stream_timeout_translated():
    def gen():
        yield b"a"
        raise requests.exceptions.Timeout("timed out")

    response = Mock()
    response.iter_content.return_value = gen()

    stream = _RequestsChunkStream(response, chunk_size=999)
    assert next(stream) == b"a"
    with pytest.raises(RequestTimeoutError):
        next(stream)
