import copy
import dataclasses
import pickle
from dataclasses import dataclass

from unihttp.omitted import Omittable, Omitted


def test_singleton_identity():
    assert Omitted() is Omitted()


def test_copy_preserves_singleton():
    o = Omitted()
    assert copy.copy(o) is o
    assert copy.copy(o) == o


def test_deepcopy_preserves_singleton():
    o = Omitted()
    assert copy.deepcopy(o) is o
    assert copy.deepcopy(o) == o


def test_pickle_preserves_singleton():
    o = Omitted()
    restored = pickle.loads(pickle.dumps(o))
    assert restored is o
    assert restored == o


def test_deepcopy_memo_argument():
    o = Omitted()
    memo: dict[int, object] = {}
    assert copy.deepcopy(o, memo) is o


@dataclass
class _Model:
    name: str
    optional: Omittable[str] = Omitted()


def test_dataclass_equality_survives_deepcopy():
    a = _Model(name="a")
    b = copy.deepcopy(a)
    assert a == b
    assert a.optional == b.optional


def test_dataclass_equality_survives_pickle():
    a = _Model(name="a")
    b = pickle.loads(pickle.dumps(a))
    assert a == b
    assert a.optional == b.optional


def test_asdict_deepcopy_keeps_singleton():
    # dataclasses.asdict() deep-copies field values; the Omitted sentinel
    # must remain the singleton so downstream equality checks still hold.
    a = _Model(name="a")
    dumped = dataclasses.asdict(a)
    assert dumped["optional"] is Omitted()
