from unihttp.http.request import HTTPRequest
from unihttp.http.response import HTTPResponse
from unihttp.middlewares.base import Middleware


class TestMiddlewareFeatures:
    def test_middleware_modifies_request(self):
        class HeaderMiddleware(Middleware):
            def handle(self, request, next_handler):
                request.header["X-Added"] = "true"
                return next_handler(request)

        handler = MockHandler()
        middleware = HeaderMiddleware()

        request = HTTPRequest("/", "GET", {}, {}, {}, {}, {}, {})
        middleware.handle(request, handler)

        assert handler.last_request.header.get("X-Added") == "true"

    def test_middleware_modifies_response(self):
        class ResponseMiddleware(Middleware):
            def handle(self, request, next_handler):
                response = next_handler(request)
                response.headers["X-Processed"] = "true"
                return response

        handler = MockHandler()
        middleware = ResponseMiddleware()

        request = HTTPRequest("/", "GET", {}, {}, {}, {}, {}, {})
        response = middleware.handle(request, handler)

        assert response.headers.get("X-Processed") == "true"

    def test_middleware_handles_exception(self):
        class ExceptionMiddleware(Middleware):
            def handle(self, request, next_handler):
                try:
                    return next_handler(request)
                except ValueError:
                    return HTTPResponse(500, {}, {"error": "caught"}, {}, None)

        def raising_handler(req):
            raise ValueError("boom")

        middleware = ExceptionMiddleware()
        request = HTTPRequest("/", "GET", {}, {}, {}, {}, {}, {})

        response = middleware.handle(request, raising_handler)
        assert response.status_code == 500
        assert response.data == {"error": "caught"}


class MockHandler:
    def __init__(self):
        self.last_request = None

    def __call__(self, request):
        self.last_request = request
        return HTTPResponse(200, {}, {}, {}, None)
