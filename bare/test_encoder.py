from .encoder import *
import pytest

class Example(Struct):

    testint = Int()
    teststr = Str(optional=True)
    testuint = U8()

def test_example_struct():
    ex = Example(testint=11, teststr="a test")
    assert hasattr(ex, 'testint')
    assert hasattr(ex, 'teststr')
    assert ex.testint == 11
    assert ex.teststr == 'a test'
    ex2 = Example(testint=12, teststr='another test')
    assert ex2.testint == 12
    assert ex2.teststr == 'another test'
    # Check that the values in the original instance haven't been modified
    assert ex.testint == 11
    assert ex.teststr == 'a test'
    result = ex.pack()
    ex3 = Example.unpack(result)
    assert ex3.testint == ex.testing
    assert ex3.teststr == ex.testing

