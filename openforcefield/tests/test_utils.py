#!/usr/bin/env python

#=============================================================================================
# MODULE DOCSTRING
#=============================================================================================

"""
Tests for utility methods

"""

#=============================================================================================
# GLOBAL IMPORTS
#=============================================================================================

import ast
import os

import pytest
from simtk import unit

from openforcefield import utils


#=============================================================================================
# TESTS
#=============================================================================================

def test_subclasses():
    """Test that all subclasses (and descendents) are correctly identified by all_subclasses()"""
    class Foo:
        pass
    class FooSubclass1(Foo):
        pass
    class FooSubclass2(Foo):
        pass
    class FooSubSubclass(FooSubclass1):
        pass

    subclass_names = [ cls.__name__ for cls in utils.all_subclasses(Foo) ]
    assert set(subclass_names) == set(['FooSubclass1', 'FooSubclass2', 'FooSubSubclass'])


def test_get_data_file_path():
    """Test get_data_file_path()"""
    from openforcefield.utils import get_data_file_path
    filename = get_data_file_path('test_forcefields/tip3p.offxml')
    assert os.path.exists(filename)


@pytest.mark.parametrize('unit_string,expected_unit',[
    ('kilocalories_per_mole', unit.kilocalories_per_mole),
    ('kilocalories_per_mole/angstrom**2', unit.kilocalories_per_mole/unit.angstrom**2),
    ('joule/(mole * nanometer**2)', unit.joule/(unit.mole * unit.nanometer**2)),
    ('picosecond**(-1)', unit.picosecond**(-1)),
    ('300.0 * kelvin', 300*unit.kelvin),
    ('1 * kilojoule + 500 * joule', 1.5*unit.kilojoule),
    ('1 / meter', 1.0 / unit.meter)
])
def test_ast_eval(unit_string, expected_unit):
    """Test that _ast_eval() correctly parses string quantities."""
    from openforcefield.utils.utils import _ast_eval
    ast_root_node = ast.parse(unit_string, mode='eval').body
    parsed_units = _ast_eval(ast_root_node)
    assert parsed_units == expected_unit
