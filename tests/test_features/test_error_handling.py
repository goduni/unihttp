import pytest
from unihttp.exceptions import NetworkError, RequestTimeoutError, UniHTTPError
from unihttp.http.response import HTTPResponse


def test_exception_inheritance():
    assert issubclass(NetworkError, UniHTTPError)
    assert issubclass(RequestTimeoutError, UniHTTPError)


def test_custom_exception_propagation():
    # Verify that exceptions raised in validation/on_error are propagated
    from unittest.mock import Mock

    from unihttp.clients.base import BaseSyncClient
    from unihttp.method import BaseMethod

    class CustomError(Exception):
        pass

    class TestClient(BaseSyncClient):
        def make_request(self, req):
            return HTTPResponse(400, {}, {"error": "bad"}, {}, None)

    class TestMethod(BaseMethod[str]):
        __url__ = "/"
        __method__ = "GET"

        def on_error(self, response):
            raise CustomError("boom")

    mock_dumper = Mock()
    mock_dumper.dump.return_value = {}
    client = TestClient("http://base", mock_dumper, Mock())  # type: ignore
    method = TestMethod()

    with pytest.raises(CustomError):
        client.call_method(method)
