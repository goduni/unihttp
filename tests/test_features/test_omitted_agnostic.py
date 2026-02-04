from dataclasses import dataclass
from typing import Union

from unihttp.method import BaseMethod
from unihttp.markers import Body
from unihttp.omitted import Omitted
from unihttp.serializers.adaptix import DEFAULT_RETORT
from unihttp.serializers.pydantic import PydanticDumper

@dataclass
class OmittedMethod(BaseMethod[None]):
    __url__ = "/"
    __method__ = "POST"
    
    # Field with Omitted as default
    optional_field: Body[Union[str, Omitted]] = Omitted()
    
    # Ensure regular fields work too
    mandatory_field: Body[str] = "mandatory"

def test_omitted_bool():
    assert not Omitted()
    assert bool(Omitted()) is False

def test_pydantic_omitted_handling():
    dumper = PydanticDumper()
    
    # Case 1: Default (Omitted) -> key should be absent
    method = OmittedMethod()
    dumped = dumper.dump(method)
    assert "optional_field" not in dumped["body"]
    assert dumped["body"]["mandatory_field"] == "mandatory"
    
    # Case 2: Provided value -> key should be present
    method = OmittedMethod(optional_field="present")
    dumped = dumper.dump(method)
    assert dumped["body"]["optional_field"] == "present"

def test_adaptix_omitted_handling():
    # Adaptix dumper usually is used via retort.dump
    retort = DEFAULT_RETORT
    
    # Case 1: Default (Omitted) -> key should be absent
    method = OmittedMethod()
    dumped = retort.dump(method)
    assert "optional_field" not in dumped["body"]
    assert dumped["body"]["mandatory_field"] == "mandatory"
    
    # Case 2: Provided value -> key should be present
    method = OmittedMethod(optional_field="present")
    dumped = retort.dump(method)
    assert dumped["body"]["optional_field"] == "present"
