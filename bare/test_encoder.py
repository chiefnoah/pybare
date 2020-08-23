from .types import *

# TODO: fix import structure, structs should be somewhere else
from .encoder import Struct, Map, Array, _ValidatedMap, ValidationError, Optional, Union
from collections import OrderedDict
import pytest
import enum
import io
import os


class Nested(Struct):
    s = Str()
    # a = Array(Int(), 3)


class Example(Struct):

    testint = Int()
    teststr = Str()
    testuint = U8()
    n = Nested()


def test_example_struct():
    n = Nested(s="nested")
    ex = Example(testint=11, teststr="a test", m={"test": 1}, n=n)
    assert hasattr(ex, "testint")
    assert hasattr(ex, "teststr")
    assert hasattr(ex, "n")
    assert hasattr(ex.n, "s")
    assert ex.testint == 11
    assert ex.teststr == "a test"
    assert ex.n.s == "nested"
    ex2 = Example(testint=12, teststr="another test")
    assert ex2.testint == 12
    assert ex2.teststr == "another test"
    # Check that the values in the original instance haven't been modified
    assert ex.testint == 11
    assert ex.teststr == "a test"


class ExampleMap(Map):
    _keytype = Str
    _valuetype = Str


class ExampleMapStruct(Struct):
    m = Map(Str, Int)
    m2 = Map(Int, Str)
    m3 = ExampleMap()


def test_map():
    ex = ExampleMapStruct()
    ex.m["test"] = 2
    ex.m2 = {0: "test"}
    ex.m3 = {"test": "test"}
    assert isinstance(ex.m, _ValidatedMap)
    assert isinstance(ex.m2, _ValidatedMap)
    assert isinstance(ex.m3, _ValidatedMap)
    assert ex.m2[0] == "test"
    assert ex.m["test"] == 2
    assert ex.m3["test"] == "test"
    with pytest.raises(ValidationError):
        ex.m2[0] = 0
    with pytest.raises(ValidationError):
        ex.m2 = {"test": "test"}
    with pytest.raises(ValidationError):
        ex.m3["3"] = 3
    map = Map(Str(), Str(), values={"test": "test"})
    assert map.value["test"] == "test"
    map2 = Map(Str(), Str())
    map2.value["another"] = "test"
    assert map2.value["another"] == "test"


class ArrayTest(Struct):
    a = Array(Int)
    n = Array(Nested, length=1)


def test_array():
    ex = ArrayTest()
    ex.a = [1, 2, 3]
    ex.n = [Nested(s="test")]
    assert ex.a == [1, 2, 3]
    with pytest.raises(ValidationError):
        ex.a = ["a", "b", "c"]
    Array(Int).validate([1, 2, 3])


class OptionalStruct(Struct):
    i = Int()
    s = Optional(Str)
    nested = Optional(Nested)


def test_optional():
    ex = OptionalStruct(i=1, s=None)
    assert ex.s is None
    assert ex.nested is None
    ex.s = "test"
    assert ex.s == "test"
    with pytest.raises(ValidationError):
        ex.s = 1
    ex.s = None
    assert ex.s is None

    ex.nested = Nested(s="test")
    assert ex.nested.s == "test"
    with pytest.raises(ValidationError):
        ex.nested = "test"


class ExampleUnion(Union):
    _members = (Str, Int)


class UnionTest(Struct):
    e = ExampleUnion()
    b = Union(members=(Str, Int))
    c = Union(members=(OptionalStruct,ArrayTest))
def test_union():
    ex = UnionTest(e=1, b="test", c=ArrayTest(a=[1], n=[Nested(s='s')])) # MUST specify values for union types when creating an object
    assert ex.e == 1
    ex.e = "1"
    assert ex.e == "1"
    with pytest.raises(ValidationError):
        ex.e = {"test": "test"}
    b = ex.pack()
    ex2 = UnionTest.unpack(b)
    assert ex.e == ex.e
    assert ex.b == ex.b
    assert ex.c.a == [1]
    assert ex.c.n[0].s == 's'
    assert ex.c.a == [1]

class EnumTest(enum.Enum):
    TEST = 0
    TEST2 = 1

class EnumTestStruct(Struct):
    e = Enum(EnumTest)

def test_enum():
    ex = EnumTestStruct(e=0)
    assert ex.e == 0
    with pytest.raises(ValidationError):
        ex.e = 100


class PublicKey(DataFixed):
    _length = 128

class Time(Str):
    pass

class Department(enum.Enum):
    ACCOUNTING = 0
    ADMINISTRATION = 1
    CUSTOMER_SERVICE = 2
    DEVELOPMENT = 3

    JSMITH = 99

class Address(Struct):
    address = Array(Str, length=4)
    city = Str()
    state = Str()
    country = Str()

class Order(Struct):
    orderID = I64()
    quantity = I32()

class Customer(Struct):
    name = Str()
    email = Str()
    address = Address()
    orders = Array(Order)
    metadata: Map(Str, Data)

class Employee(Struct):
    name = Str()
    email = Str()
    address = Address()
    department = Enum(Department)
    hireDate = Time()
    publicKey = Optional(PublicKey)
    metadata = Map(Str, Data)

class TerminatedEmployee(Void):
    pass

class Person(Union):
    _members = (Customer, Employee, TerminatedEmployee)

@pytest.mark.parametrize('file', ['customer.bin', 'employee.bin', 'people.bin', 'terminated.bin'])
def test_people(file):
    with open(os.path.join(os.path.dirname(__file__), '_examples', file), 'br') as f:
        p = Person().unpack(f)
        p.to_dict()
        f.seek(0)
        f = f.read()
        buf = io.BytesIO()
        p.pack(buf)
        #assert buf.getvalue() == f
    with open('./test.bin', 'bw') as f:
        p.pack(fp=f)

