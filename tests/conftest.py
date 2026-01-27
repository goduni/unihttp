from unittest.mock import Mock

import pytest
from unihttp.serialize import RequestDumper, ResponseLoader


@pytest.fixture
def mock_request_dumper():
    dumper = Mock(spec=RequestDumper)
    dumper.dump.return_value = {}
    return dumper


@pytest.fixture
def mock_response_loader():
    loader = Mock(spec=ResponseLoader)
    loader.load.return_value = "mocked_response"
    return loader


@pytest.fixture
async def integration_server(aiohttp_server):
    from tests.server import make_app
    app = await make_app()
    server = await aiohttp_server(app)
    return server
