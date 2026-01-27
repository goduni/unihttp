from dataclasses import dataclass

import pytest
from adaptix import Retort
from unihttp.clients.aiohttp import AiohttpAsyncClient
from unihttp.method import BaseMethod
from unihttp.serialize import RequestDumper, ResponseLoader

# We need a real RequestDumper/ResponseLoader that uses adaptix
# Since unihttp doesn't bundle one by default (it's in the design to pass it),
# we will implement a simple Adaptix-based dumper/loader here.


@dataclass
class Address:
    city: str
    zip_code: int


@dataclass
class User:
    id: int
    name: str
    addresses: list[Address]


class AdaptixDumper(RequestDumper):
    def __init__(self, retort: Retort):
        self.retort = retort

    def dump(self, method):
        body = getattr(method, "body", {})
        # Serialize body using adaptix if it is not a dict
        if not isinstance(body, dict):
            # Serialize to dict first? No, dumper should return dict of parts.
            # But request.body expects dict or bytes?
            # unihttp.http.request.HTTPRequest.body types: dict | bytes | None
            # If we return a dict, it will be form-encoded by clients usually.
            # If we want JSON, we should probably dump to dict (and let client handle) or bytes.
            # But wait, unihttp design: dumper returns dict with keys "body", "header" etc.
            # The "body" value is passed to client.
            # Let's dump to dict for structured data.
            body = self.retort.dump(body)

        return {
            "path": {},
            "query": {},
            "header": getattr(method, "headers", {"Content-Type": "application/json"}),
            "body": body,
            "file": {}
        }


class AdaptixLoader(ResponseLoader):
    def __init__(self, retort: Retort):
        self.retort = retort

    def load(self, data, response_type):
        return self.retort.load(data, response_type)


@pytest.fixture
def adaptix_retort():
    return Retort()


@pytest.fixture
def adaptix_dumper(adaptix_retort):
    return AdaptixDumper(adaptix_retort)


@pytest.fixture
def adaptix_loader(adaptix_retort):
    return AdaptixLoader(adaptix_retort)


class CreateUserMethod(BaseMethod[User]):
    __url__ = "/complex"
    __method__ = "POST"

    def __init__(self, user: User):
        self.body = user


@dataclass
class ComplexResponse:
    received: User
    status: str


class CreateUserMethodWrapped(BaseMethod[ComplexResponse]):
    __url__ = "/complex"
    __method__ = "POST"

    def __init__(self, user: User):
        self.body = user


@pytest.mark.asyncio
async def test_complex_data_roundtrip(integration_server, adaptix_loader):
    base_url = str(integration_server.make_url("/"))
    import json

    # Define Dumper locally to ensure JSON serialization
    dumper = AdaptixDumper(adaptix_loader.retort)

    user = User(id=1, name="Alice", addresses=[Address("NY", 10001)])

    async with AiohttpAsyncClient(base_url, dumper, adaptix_loader) as client:
        method = CreateUserMethodWrapped(user)
        response = await client.call_method(method)

        assert isinstance(response, ComplexResponse)
        assert response.status == "processed"
        assert response.received == user
