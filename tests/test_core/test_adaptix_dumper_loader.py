import pytest
from unittest.mock import Mock
from adaptix import Retort
from unihttp.serializers.adaptix.serialize import AdaptixDumper, AdaptixLoader


def test_adaptix_dumper():
    mock_retort = Mock(spec=Retort)
    mock_retort.dump.return_value = "dumped"
    
    dumper = AdaptixDumper(mock_retort)
    result = dumper.dump("obj")
    
    assert result == "dumped"
    mock_retort.dump.assert_called_once_with("obj")


def test_adaptix_loader():
    mock_retort = Mock(spec=Retort)
    mock_retort.load.return_value = "loaded"
    
    loader = AdaptixLoader(mock_retort)
    result = loader.load("data", str)
    
    assert result == "loaded"
    mock_retort.load.assert_called_once_with("data", str)
