import pytest

from llm_json import loads_lenient


def test_parses_plain_json():
    assert loads_lenient('[1, 2, 3]') == [1, 2, 3]


def test_tolerates_trailing_comma_in_array():
    # The exact bug seen in vectorless navigation ("[,]" / "[2,]").
    assert loads_lenient('[2, ]') == [2]
    assert loads_lenient('[,]') == []


def test_tolerates_trailing_comma_in_object():
    assert loads_lenient('{"a": 1, }') == {"a": 1}


def test_strips_code_fence():
    assert loads_lenient('```json\n[1, 2]\n```') == [1, 2]


def test_still_raises_on_truly_invalid():
    with pytest.raises(Exception):
        loads_lenient("not json at all")
