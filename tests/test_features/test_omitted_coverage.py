from dataclasses import dataclass
from unihttp.method import BaseMethod
from unihttp.markers import Query
from unihttp.serializers.adaptix import DEFAULT_RETORT
from adaptix import name_mapping

@dataclass
class OmittedDefaultMethod(BaseMethod[None]):
    __url__ = "/"
    __method__ = "GET"
    
    q: Query[str] = "default"

def test_omitted_super_sieve_coverage():
    # We need to trigger line 59 in omitted.py: return super()._create_sieve(field)
    # This happens if a field has a default value (not Omitted) AND omit_default matches it.
    
    # Configure retort to omit default values for 'q'
    # "q" field has default "default".
    
    retort = DEFAULT_RETORT.extend(
        recipe=[
            name_mapping(omit_default=True)
        ]
    )
    
    # Case 1: Value equals default -> should be omitted
    method = OmittedDefaultMethod(q="default")
    dumped = retort.dump(method)
    assert "q" not in dumped["query"]
    
    # Case 2: Value differs -> should be present
    method = OmittedDefaultMethod(q="search")
    dumped = retort.dump(method)
    assert dumped["query"]["q"] == "search"
