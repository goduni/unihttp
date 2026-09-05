"""Contract tests for the snippets in the consolidated serialization guide."""

import importlib
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx
import pytest

from examples import optional_fields, recipes
from examples.serialization import customization
from unihttp.clients.httpx import HTTPXSyncClient
from unihttp.http import UploadFile
from unihttp.serializers.adaptix import DEFAULT_RETORT, AdaptixDumper, AdaptixLoader


@pytest.mark.parametrize("backend", ["adaptix", "pydantic", "msgspec"])
def test_serializer_setup_tab(backend):
    module = importlib.import_module(f"examples.serialization.{backend}")
    method = module.CreateUser(user_name="Ada")
    assert module.request_dumper.dump(method)["body"] == {"user_name": "Ada"}
    response_data = {"id": 1, "user_name": "Ada"}
    user = module.response_loader.load(response_data, module.User)
    assert user == module.User(id=1, user_name="Ada")

    def handler(request):
        assert request.method == "POST"
        assert request.content == b'{"user_name": "Ada"}'
        return httpx.Response(201, json=response_data)

    with HTTPXSyncClient(
        base_url="https://api.example.com",
        request_dumper=module.request_dumper,
        response_loader=module.response_loader,
        session=httpx.Client(transport=httpx.MockTransport(handler)),
    ) as client:
        assert client.call_method(method) == user


@pytest.mark.parametrize(
    "retort", [customization.global_retort, customization.scoped_retort]
)
def test_adaptix_name_mapping_both_directions(retort):
    dumper = AdaptixDumper(retort)
    loader = AdaptixLoader(retort)
    assert dumper.dump(customization.CreateUser(user_name="Ada"))["body"] == {
        "userName": "Ada"
    }
    assert loader.load(
        {"id": 1, "userName": "Ada"}, customization.User
    ) == customization.User(1, "Ada")


def test_adaptix_scoped_mapping_does_not_rename_other_models():
    @dataclass
    class OtherUser:
        user_name: str

    assert customization.scoped_retort.dump(OtherUser("Ada")) == {"user_name": "Ada"}
    assert customization.global_retort.dump(OtherUser("Ada")) == {"userName": "Ada"}
    assert DEFAULT_RETORT.dump(customization.User(1, "Ada")) == {
        "id": 1,
        "user_name": "Ada",
    }


def test_adaptix_normalization_only_changes_the_outgoing_value():
    method = customization.CreateUser(user_name="  Ada  ")
    dumper = AdaptixDumper(customization.normalized_retort)
    loader = AdaptixLoader(customization.normalized_retort)
    assert dumper.dump(method)["body"] == {"userName": "Ada"}
    assert method.user_name == "  Ada  "
    assert (
        loader.load({"id": 1, "userName": "  Ada  "}, customization.User).user_name
        == "  Ada  "
    )


def test_adaptix_custom_timestamp_format():
    instant = datetime(2024, 1, 1, tzinfo=UTC)
    dumper = AdaptixDumper(customization.timestamp_retort)
    loader = AdaptixLoader(customization.timestamp_retort)
    assert dumper.dump(customization.CreateEvent(starts_at=instant))["body"] == {
        "starts_at": 1704067200.0
    }
    assert loader.load(
        {"id": 1, "starts_at": 1704067200}, customization.Event
    ) == customization.Event(1, instant)
    with pytest.raises(Exception):
        loader.load({"id": 1, "starts_at": "not a timestamp"}, customization.Event)


@pytest.mark.parametrize(
    "retort",
    [
        customization.global_retort,
        customization.scoped_retort,
        customization.normalized_retort,
        customization.timestamp_retort,
    ],
)
def test_adaptix_recipes_keep_unihttp_providers(retort):
    dumper = AdaptixDumper(retort)
    assert dumper.dump(optional_fields.CreateUser(name="Ada"))["body"] == {"name": "Ada"}
    assert (
        recipes.PutBytes(content=b"payload").build_http_request(dumper).raw == b"payload"
    )
    request = recipes.UploadAvatar(
        user_id=1, caption="Portrait", avatar=UploadFile(b"image", filename="avatar.png")
    ).build_http_request(dumper)
    assert request.url == "/users/1/avatar"
    assert request.form == {"caption": "Portrait"}
    assert request.file["avatar"][0] == "avatar.png"
    assert AdaptixLoader(retort).load(
        {"id": 1, "name": "Ada", "extra": 42}, recipes.User
    ) == recipes.User(1, "Ada")
