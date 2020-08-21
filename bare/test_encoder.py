from .types import *
from .encoder import Struct, Map # TODO: fix import structure, structs should be somewhere else
import pytest
from collections import OrderedDict

class Nested(Struct):
    s = Str()

class ExampleMap(Map):
    _key = Str()
    _value = Int()

class Example(Struct):

    testint = Int()
    teststr = Str()
    testuint = U8()
    n = Nested()
    m = ExampleMap()


def test_example_struct():
    ex = Example(testint=11, teststr="a test", m={'test': 1})
    assert hasattr(ex, 'testint')
    assert hasattr(ex, 'teststr')
    assert ex.testint == 11
    assert ex.teststr == 'a test'
    assert ex.m == OrderedDict(test=1)
    ex2 = Example(testint=12, teststr='another test')
    assert ex2.testint == 12
    assert ex2.teststr == 'another test'
    # Check that the values in the original instance haven't been modified
    assert ex.testint == 11
    assert ex.teststr == 'a test'
    result = ex.pack()
    ex3 = Example.unpack(result)
    assert ex3.testint == ex.testint
    assert ex3.testint == ex.testint
    assert ex3.m == ex.m
    breakpoint()


