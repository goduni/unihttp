import pytest

from unihttp.http.request import HTTPRequest
from unihttp.http.response import HTTPResponse
from unihttp.method import BaseMethod, StreamMethod


class SimpleMethod(BaseMethod[str]):
    __url__ = "/users/{id}"
    __method__ = "GET"


def test_build_http_request(mock_request_dumper):
    method = SimpleMethod()

    # Mock dumper output
    mock_request_dumper.dump.return_value = {
        "header": {"Authorization": "Bearer token"},
        "path": {"id": 123},
        "query": {"active": "true"},
        "body": {"name": "test"},
        "file": {},
    }

    request = method.build_http_request(mock_request_dumper)

    assert isinstance(request, HTTPRequest)
    assert request.url == "/users/123"
    assert request.method == "GET"
    assert request.header == {"Authorization": "Bearer token"}
    assert request.path == {"id": 123}
    assert request.query == {"active": "true"}
    assert request.body == {"name": "test"}
    assert request.file == {}


def test_make_response(mock_response_loader):
    method = SimpleMethod()
    response = HTTPResponse(
        status_code=200, headers={}, cookies={}, data={"key": "value"}, raw_response=None,
    )

    mock_response_loader.load.return_value = "loaded_data"

    result = method.make_response(response, mock_response_loader)

    assert result == "loaded_data"
    mock_response_loader.load.assert_called_once_with({"key": "value"}, str)


def test_validate_response_default():
    method = SimpleMethod()
    response = HTTPResponse(200, {}, {}, {}, None)
    # Default implementation should do nothing
    method.validate_response(response)


def test_on_error_default():
    method = SimpleMethod()
    response = HTTPResponse(404, {}, {}, {}, None)
    # Default implementation does nothing
    method.on_error(response)


class SimpleStreamMethod(StreamMethod):
    __url__ = "/files/{id}"
    __method__ = "GET"


def test_stream_method_build_http_request(mock_request_dumper):
    method = SimpleStreamMethod()
    mock_request_dumper.dump.return_value = {
        "header": {"Authorization": "Bearer token"},
        "path": {"id": 42},
        "query": {},
        "raw": None,
    }

    request = method.build_http_request(mock_request_dumper)

    assert isinstance(request, HTTPRequest)
    assert request.url == "/files/42"
    assert request.method == "GET"
    assert request.header == {"Authorization": "Bearer token"}


def test_stream_method_on_error_default():
    method = SimpleStreamMethod()
    response = HTTPResponse(404, {}, {}, {}, None)
    method.on_error(response)


def test_build_http_request_raw_and_body_conflict(mock_request_dumper):
    method = SimpleMethod()
    mock_request_dumper.dump.return_value = {
        "header": {},
        "path": {},
        "query": {},
        "body": {"a": 1},
        "file": {},
        "form": {},
        "raw": b"bytes",
    }
    with pytest.raises(ValueError, match="Raw"):
        method.build_http_request(mock_request_dumper)


def test_build_http_request_body_and_form_conflict(mock_request_dumper):
    method = SimpleMethod()
    mock_request_dumper.dump.return_value = {
        "header": {},
        "path": {},
        "query": {},
        "body": {"a": 1},
        "file": {},
        "form": {"b": 2},
        "raw": None,
    }
    with pytest.raises(ValueError, match="Cannot use Body with Form or File"):
        method.build_http_request(mock_request_dumper)


def test_build_http_request_raw_only_ok(mock_request_dumper):
    method = SimpleMethod()
    mock_request_dumper.dump.return_value = {
        "header": {},
        "path": {"id": 1},
        "query": {},
        "body": {},
        "file": {},
        "form": {},
        "raw": b"payload",
    }
    request = method.build_http_request(mock_request_dumper)
    assert request.raw == b"payload"
