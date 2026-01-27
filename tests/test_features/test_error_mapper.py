from unittest.mock import Mock

import pytest
from unihttp.http.request import HTTPRequest
from unihttp.http.response import HTTPResponse
from unihttp.middlewares.error_mapper import (
    AsyncErrorMapperMiddleware,
    SyncErrorMapperMiddleware,
)


class CustomError(Exception):
    def __init__(self, msg, response=None):
        super().__init__(msg)
        self.response = response


class TestErrorMapperMiddleware:
    def test_map_int(self):
        middleware = SyncErrorMapperMiddleware({
            404: CustomError
        })
        handler = Mock(return_value=HTTPResponse(404, {}, {}, {}, None))
        request = HTTPRequest("/", "GET", {}, {}, {}, {}, {}, {})

        with pytest.raises(CustomError) as exc:
            middleware.handle(request, handler)
        assert exc.value.response.status_code == 404

    def test_map_range(self):
        middleware = SyncErrorMapperMiddleware({
            range(500, 600): CustomError
        })
        handler = Mock(return_value=HTTPResponse(502, {}, {}, {}, None))
        request = HTTPRequest("/", "GET", {}, {}, {}, {}, {}, {})

        with pytest.raises(CustomError):
            middleware.handle(request, handler)

    def test_map_tuple(self):
        middleware = SyncErrorMapperMiddleware({
            (400, 422): CustomError
        })
        handler = Mock(return_value=HTTPResponse(422, {}, {}, {}, None))
        request = HTTPRequest("/", "GET", {}, {}, {}, {}, {}, {})

        with pytest.raises(CustomError):
            middleware.handle(request, handler)

    def test_map_callable(self):
        def factory(resp):
            return CustomError("Factory error", resp)

        middleware = SyncErrorMapperMiddleware({
            418: factory
        })
        handler = Mock(return_value=HTTPResponse(418, {}, {}, {}, None))
        request = HTTPRequest("/", "GET", {}, {}, {}, {}, {}, {})

        with pytest.raises(CustomError) as exc:
            middleware.handle(request, handler)
        assert str(exc.value) == "Factory error"

    def test_no_map(self):
        middleware = SyncErrorMapperMiddleware({
            404: CustomError
        })
        handler = Mock(return_value=HTTPResponse(200, {}, {}, {}, None))
        request = HTTPRequest("/", "GET", {}, {}, {}, {}, {}, {})

        response = middleware.handle(request, handler)
        assert response.status_code == 200


@pytest.mark.asyncio
class TestAsyncErrorMapperMiddleware:
    async def test_map_async(self):
        middleware = AsyncErrorMapperMiddleware({
            404: CustomError
        })

        async def async_handler(req):
            return HTTPResponse(404, {}, {}, {}, None)

        handler = Mock(side_effect=async_handler)
        request = HTTPRequest("/", "GET", {}, {}, {}, {}, {}, {})

        with pytest.raises(CustomError):
            await middleware.handle(request, handler)

    async def test_map_async_no_match(self):
        middleware = AsyncErrorMapperMiddleware({
            404: CustomError
        })

        async def async_handler(req):
            return HTTPResponse(200, {}, {}, {}, None)

        handler = Mock(side_effect=async_handler)
        request = HTTPRequest("/", "GET", {}, {}, {}, {}, {}, {})

        response = await middleware.handle(request, handler)
        assert response.status_code == 200
