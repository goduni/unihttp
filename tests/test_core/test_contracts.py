from unittest.mock import Mock

from unihttp.http.response import HTTPResponse
from unihttp.method import BaseMethod


def test_response_type_extraction():
    class StrMethod(BaseMethod[str]):
        __url__ = "/"
        __method__ = "GET"

    assert StrMethod.__returning__ == str

    class IntMethod(BaseMethod[int]):
        pass

    assert IntMethod.__returning__ == int

    class ListMethod(BaseMethod[list[str]]):
        pass

    assert ListMethod.__returning__ == list[str]


def test_make_response_contract():
    class StrMethod(BaseMethod[str]):
        __url__ = "/"
        __method__ = "GET"

    method = StrMethod()
    response = HTTPResponse(200, {}, {"key": "val"}, {}, None)
    loader = Mock()
    loader.load.return_value = "parsed"

    result = method.make_response(response, loader)

    assert result == "parsed"
    loader.load.assert_called_once_with({"key": "val"}, str)


def test_make_response_contract_complex():
    class DictMethod(BaseMethod[dict[str, int]]):
        __url__ = "/"
        __method__ = "GET"

    method = DictMethod()
    response = HTTPResponse(200, {}, {"a": 1}, {}, None)
    loader = Mock()
    loader.load.return_value = {"a": 1}

    method.make_response(response, loader)

    loader.load.assert_called_once_with({"a": 1}, dict[str, int])
