import pytest
from app.impl_tags import tagsHaveChanged
from typing import Any, List
from app.orm_decl import Tag

# Test tagsHaveChanged with PyTest
def test_tagsHaveChanged() -> None:
    # Generate test data
    old_values: List[Tag] = []
    new_values = []
    for i in range(10):
        g = Tag()
        g.id =  i
        old_values.append(g)
        new_values.append({'id': i})
    # Test
    assert tagsHaveChanged(old_values, new_values) == False

# Test tagsHaveChanged with PyTest with different length
def test_tagsHaveChanged2() -> None:
    # Generate test data
    old_values: List[Tag] = []
    new_values = []
    for i in range(10):
        g = Tag()
        g.id =  i
        old_values.append(g)
        new_values.append({'id': i})
    new_values.append({'id': 10})
    # Test
    assert tagsHaveChanged(old_values, new_values) == True

# Test tagsHaveChanged with PyTest with different id
def test_tagsHaveChanged3() -> None:
    # Generate test data
    old_values: List[Tag] = []
    new_values = []
    for i in range(10):
        g = Tag()
        g.id =  i
        old_values.append(g)
        new_values.append({'id': i})
    new_values[5]['id'] = 10
    # Test
    assert tagsHaveChanged(old_values, new_values) == True

# Test tagsHaveChanged with PyTest with different id
def test_tagsHaveChanged4() -> None:
    # Generate test data
    old_values: List[Tag] = []
    new_values = []
    for i in range(10):
        g = Tag()
        g.id =  i
        old_values.append(g)
        new_values.append({'id': i})
    old_values[5].id = 10
    # Test
    assert tagsHaveChanged(old_values, new_values) == True
