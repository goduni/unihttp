from unittest.mock import MagicMock, Mock

import pytest
import requests
from unihttp.clients.requests import RequestsSyncClient
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
        files={}
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


def test_requests_body_and_form_error(mock_request_dumper, mock_response_loader, mock_session):
    client = RequestsSyncClient(
        base_url="http://base",
        request_dumper=mock_request_dumper,
        response_loader=mock_response_loader,
        session=mock_session
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
