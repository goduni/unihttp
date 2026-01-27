import logging
from unittest.mock import Mock

import pytest
from unihttp.http.request import HTTPRequest
from unihttp.http.response import HTTPResponse
from unihttp.middlewares.logging import AsyncLoggingMiddleware, LoggingMiddleware


class TestLoggingMiddleware:
    def test_logging(self):
        logger = Mock(spec=logging.Logger)
        middleware = LoggingMiddleware(logger=logger)

        handler = Mock(return_value=HTTPResponse(200, {}, {}, {}, None))
        request = HTTPRequest("/test", "GET", {}, {}, {}, {}, {}, {})

        middleware.handle(request, handler)

        assert logger.info.call_count == 2
        logger.info.assert_any_call("Request: %s %s", "GET", "/test")
        logger.info.assert_any_call("Response: %s", 200)

    def test_default_logger(self, mocker):
        mock_get_logger = mocker.patch("logging.getLogger")
        middleware = LoggingMiddleware()

        mock_get_logger.assert_called_once_with("unihttp")
        assert middleware.logger == mock_get_logger.return_value


class TestAsyncLoggingMiddleware:
    @pytest.mark.asyncio
    async def test_logging(self):
        logger = Mock(spec=logging.Logger)
        middleware = AsyncLoggingMiddleware(logger=logger)

        handler = Mock()

        # Async handler returns awaitable

        async def async_handler(req):
            return HTTPResponse(201, {}, {}, {}, None)

        handler.side_effect = async_handler

        request = HTTPRequest("/async", "POST", {}, {}, {}, {}, {}, {})

        await middleware.handle(request, handler)

        assert logger.info.call_count == 2
        logger.info.assert_any_call("Request: %s %s", "POST", "/async")
        logger.info.assert_any_call("Response: %s", 201)

    def test_default_logger(self, mocker):
        mock_get_logger = mocker.patch("logging.getLogger")
        middleware = AsyncLoggingMiddleware()

        mock_get_logger.assert_called_once_with("unihttp")
        assert middleware.logger == mock_get_logger.return_value
