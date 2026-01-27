import asyncio
from unittest.mock import Mock, call

import pytest
from unihttp.http.request import HTTPRequest
from unihttp.http.response import HTTPResponse
from unihttp.middlewares.retry import AsyncRetryMiddleware, RetryMiddleware


class TestRetryMiddleware:
    def test_retry_on_status_code(self, mocker):
        # Mock time.sleep to run fast
        mock_sleep = mocker.patch("time.sleep")

        handler = Mock()
        # Fail twice, then succeed
        handler.side_effect = [
            HTTPResponse(500, {}, {}, {}, None),
            HTTPResponse(502, {}, {}, {}, None),
            HTTPResponse(200, {}, {}, {}, None),
        ]

        middleware = RetryMiddleware(retries=3, backoff=0.1, jitter=False)
        request = HTTPRequest("/", "GET", {}, {}, {}, {}, {}, {})

        response = middleware.handle(request, handler)

        assert response.status_code == 200
        assert handler.call_count == 3

        # Verify backoff
        # attempt 0: 0.1 * 2^0 = 0.1
        # attempt 1: 0.1 * 2^1 = 0.2
        assert mock_sleep.call_args_list == [call(0.1), call(0.2)]

    def test_retry_on_exception(self, mocker):
        mock_sleep = mocker.patch("time.sleep")

        handler = Mock()
        handler.side_effect = [
            ValueError("fail"),
            HTTPResponse(200, {}, {}, {}, None)
        ]

        middleware = RetryMiddleware(
            retries=3,
            backoff=0.1,
            exceptions=[ValueError],
            jitter=False
        )
        request = HTTPRequest("/", "GET", {}, {}, {}, {}, {}, {})

        response = middleware.handle(request, handler)

        assert response.status_code == 200
        assert handler.call_count == 2
        mock_sleep.assert_called_once_with(0.1)

    def test_max_retries_exceeded(self, mocker):
        mocker.patch("time.sleep")
        handler = Mock(return_value=HTTPResponse(500, {}, {}, {}, None))

        middleware = RetryMiddleware(retries=2, backoff=0.1, jitter=False)
        request = HTTPRequest("/", "GET", {}, {}, {}, {}, {}, {})

        response = middleware.handle(request, handler)

        assert response.status_code == 500
        assert handler.call_count == 3  # Initial + 2 retries

    def test_jitter(self, mocker):
        mock_sleep = mocker.patch("time.sleep")
        mock_random = mocker.patch("random.uniform", return_value=0.5)

        handler = Mock(return_value=HTTPResponse(500, {}, {}, {}, None))

        middleware = RetryMiddleware(retries=1, backoff=1.0, jitter=True)
        request = HTTPRequest("/", "GET", {}, {}, {}, {}, {}, {})

        middleware.handle(request, handler)

        # 1.0 * 2^0 + 0.5 = 1.5
        mock_sleep.assert_called_once_with(1.5)


@pytest.mark.asyncio
class TestAsyncRetryMiddleware:
    async def test_retry_on_status_code(self, mocker):
        mock_sleep = mocker.patch("asyncio.sleep")

        handler = Mock()
        # Async mocks need to return awaitables
        f1 = asyncio.Future()
        f1.set_result(HTTPResponse(500, {}, {}, {}, None))
        f2 = asyncio.Future()
        f2.set_result(HTTPResponse(200, {}, {}, {}, None))
        handler.side_effect = [f1, f2]

        middleware = AsyncRetryMiddleware(retries=3, backoff=0.1, jitter=False)
        request = HTTPRequest("/", "GET", {}, {}, {}, {}, {}, {})

        response = await middleware.handle(request, handler)

        assert response.status_code == 200
        assert handler.call_count == 2
        mock_sleep.assert_called_once_with(0.1)

    async def test_retry_on_exception(self, mocker):
        mock_sleep = mocker.patch("asyncio.sleep")

        handler = Mock()
        f_success = asyncio.Future()
        f_success.set_result(HTTPResponse(200, {}, {}, {}, None))

        handler.side_effect = [ValueError("fail"), f_success]

        middleware = AsyncRetryMiddleware(
            retries=3,
            backoff=0.1,
            exceptions=[ValueError],
            jitter=False
        )
        request = HTTPRequest("GET", "/", {}, {}, {}, {}, {}, {})

        response = await middleware.handle(request, handler)

        assert response.status_code == 200
        assert handler.call_count == 2
