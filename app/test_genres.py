import pytest
from app.impl_genres import genresHaveChanged
from typing import Any, List
from app.orm_decl import Genre

# Test genresHaveChanged with PyTest
def test_genresHaveChanged() -> None:
    # Generate test data
    old_values: List[Genre] = []
    new_values = []
    for i in range(10):
        g = Genre()
        g.id =  i
        old_values.append(g)
        new_values.append({'id': i})
    # Test
    assert genresHaveChanged(old_values, new_values) == False

# Test genresHaveChanged with PyTest with different length
def test_genresHaveChanged2() -> None:
    # Generate test data
    old_values: List[Genre] = []
    new_values = []
    for i in range(10):
        g = Genre()
        g.id =  i
        old_values.append(g)
        new_values.append({'id': i})
    new_values.append({'id': 10})
    # Test
    assert genresHaveChanged(old_values, new_values) == True

# Test genresHaveChanged with PyTest with different id
def test_genresHaveChanged3() -> None:
    # Generate test data
    old_values: List[Genre] = []
    new_values = []
    for i in range(10):
        g = Genre()
        g.id =  i
        old_values.append(g)
        new_values.append({'id': i})
    new_values[5]['id'] = 10
    # Test
    assert genresHaveChanged(old_values, new_values) == True

# Test genresHaveChanged with PyTest with different id
def test_genresHaveChanged4() -> None:
    # Generate test data
    old_values: List[Genre] = []
    new_values = []
    for i in range(10):
        g = Genre()
        g.id =  i
        old_values.append(g)
        new_values.append({'id': i})
    old_values[5].id = 10
    # Test
    assert genresHaveChanged(old_values, new_values) == True

