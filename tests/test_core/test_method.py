from unihttp.http.request import HTTPRequest
from unihttp.http.response import HTTPResponse
from unihttp.method import BaseMethod


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
        "file": {}
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
        status_code=200,
        headers={},
        cookies={},
        data={"key": "value"},
        raw_response=None
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
    # Default implementation returns None
    assert method.on_error(response) is None
