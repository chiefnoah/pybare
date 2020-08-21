import io
import logging
import struct
import typing
from abc import ABC, abstractmethod
from collections import OrderedDict
from enum import Enum, auto
from functools import partial
from collections.abc import Mapping

class ValidationError(ValueError):
    pass

class BareType(Enum):
    UINT = auto()
    U8 = auto()
    U16 = auto()
    U32 = auto()
    U64 = auto()
    INT = auto()
    I8 = auto()
    I16 = auto()
    I32 = auto()
    I64 = auto()
    F32 = auto()
    F64 = auto()
    Bool = auto()
    String = auto()
    Data = auto()
    DataFixed = auto()
    Void = auto()
    Optional = auto()
    Array = auto()
    ArrayFixed = auto()
    Map = auto()
    Union = auto()
    Struct = auto()
    UserType = auto()


primitive_types = {
    # type          func to encode      struct format    python native type    byte size
    BareType.U8: (partial(struct.pack, "<B"), "<B", int, 1),
    BareType.U16: (partial(struct.pack, "<H"), "<H", int, 2),
    BareType.U32: (partial(struct.pack, "<I"), "<I", int, 4),
    BareType.U64: (partial(struct.pack, "<Q"), "<Q", int, 8),
    BareType.I8: (partial(struct.pack, "<b"), "<b", int, 1),
    BareType.I16: (partial(struct.pack, "<h"), "<h", int, 2),
    BareType.I32: (partial(struct.pack, "<i"), "<i", int, 4),
    BareType.I64: (partial(struct.pack, "<q"), "<q", int, 8),
    BareType.F32: (partial(struct.pack, "<f"), "<f", float, 4),
    BareType.F64: (partial(struct.pack, "<d"), "<d", float, 8),
    BareType.Bool: (partial(struct.pack, "<?"), partial(struct.unpack, "<?"), bool, 1),
    BareType.String: (None, None, str),
    BareType.Data: (None, None, bytes),
    BareType.Void: (lambda x: None, lambda x: None, None)  # No OP
    # (BareType.UINT, None, None, int),
    # (BareType.INT, None, None, int),
}


class Field(ABC):
    """
    Field is a descritor that wraps a value, a BARE type, and some other
    metadata. It implements a `pack` method which writes the corresponding
    bytes for `type` to a provided file-like object.
    """

    _type = BareType.Void
    _default = None

    def __init__(self, value=None):
        if value is None:
            value = self.__class__._default
        if not self.validate(value):
            raise ValidationError(f"{value} is invalid for BARE type {self._type}")
        self._value = value

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        else:
            return getattr(instance, f"_{self.name}")

    def __set__(self, instance, value):
        if instance is None:
            raise AttributeError("Unable to assign value when not attached to class")
        if not self.validate(value):
            raise ValidationError(f"{value} is invalid for BARE type {self._type}")
        setattr(instance, f"_{self.name}", value)

    @classmethod
    @abstractmethod
    def validate(cls, value) -> bool:
        return cls._default == None  # This is valid for BareType.Void

    @property
    def type(self):
        return self.__class__._type

    @property
    def value(self):
        return self._value

    @value.setter
    def set_value(self, value):
        if not self.validate(value):
            raise ValidationError(f"{value} is invalid for BARE type {self._type}")
        self._value = value

    def pack(self, fp=None) -> typing.Optional[bytes]:
        buffered = False
        if not fp:
            fp = io.BytesIO()
            buffered = True
        _dump(fp, self, self.value)
        if buffered:
            return fp

    @classmethod
    def unpack(cls, fp: typing.BinaryIO) -> "Field":
        # If it's a bytes-like, wrap it in a io buffer
        if hasattr(fp, "decode"):
            fp = io.BytesIO(fp)
        if primitive_types.get(cls._type) is not None:
            value = primitive_types.get(cls._type)[1](fp)
            return cls(cls._type, value)


class Struct(ABC):

    _type = BareType.Struct

    def __init__(self, *args, **kwargs):
        # loop through defined fields, if they have a corresponding kwarg entry, set the value
        for name, field in filter(
            lambda x: isinstance(x[1], Field), self.__class__.__dict__.items()
        ):
            if name in kwargs:
                setattr(self, name, kwargs[name])
            else:
                setattr(self, name, field.value)

    @classmethod
    def fields(cls) -> typing.OrderedDict[str, Field]:
        return OrderedDict(
            filter(lambda x: isinstance(x[1], Field), cls.__dict__.items())
        )

    def pack(self, fp=None) -> typing.Optional[bytes]:
        """
        pack: encodes struct and all of it's fields in the order as defined in the class definition.
        All subclasses of Field are treated as struct fields. If fp is provided, the output is written to that,
        otherwise a bytes instance is returned with the encoded data.
        """
        ret = False
        if not fp:
            fp = io.BytesIO()
            ret = True
        for field, type in self.fields().items():
            _dump(fp, type, getattr(self, field))
        if ret:
            return fp.getvalue()

    @classmethod
    def unpack(cls, data: typing.Union[typing.BinaryIO, bytes]):
        """
        unpack deserializes data into a type. If
        """
        if hasattr(data, "decode"):
            fp = io.BytesIO(data)
        else:
            fp = data
        # for field, type in cls.fields().items():
        #    _load(fp, type)
        return _load(fp, cls)


class Optional(ABC):
    pass


class Union(ABC):

    _members: typing.Tuple[typing.Union[Field, Struct], ...] = ()

    @property
    def members(self) -> typing.Tuple[typing.Union[Field, Struct], ...]:
        return self.__class__._members


class Map(Field):

    _type = BareType.Map
    _key: Field = None
    _value: Field = None
    _default = dict()

    def __init__(self, default=None):
        if default:
            if not self.__class__.validate(default):
                raise ValidationError(f"{default} is invalid for BARE type {self._type}")
            self._default = default

    @property
    def value(self):
        return self.__class__._default

    @classmethod
    def validate(cls, value: Mapping):
        if value is None:
            return False
        keytype = cls._key
        valtype = cls._value
        for k, v in value.items():
            if not keytype.validate(k): return False
            if not valtype.validate(v): return False
        return True


def _write_string(fp: typing.BinaryIO, val: str):
    encoded = val.encode(
        encoding="utf-8"
    )  # utf-8 is the default, but doing this for clarity
    _write_varint(fp, len(encoded), signed=False)
    fp.write(encoded)


def _read_string(fp: typing.BinaryIO) -> str:
    length = _read_varint(fp, signed=False)
    return fp.read(length).decode("utf-8")


# This is adapted from https://git.sr.ht/~martijnbraam/bare-py/tree/master/bare/__init__.py#L29
def _write_varint(fp: typing.BinaryIO, val: int, signed=True):
    if signed:
        if val < 0:
            val = (2 * abs(val)) - 1
        else:
            val = 2 * val
    while val >= 0x80:
        fp.write(struct.pack("<B", (val & 0xFF) | 0x80))
        val >>= 7

    fp.write(struct.pack("<B", val))


def _read_varint(fp: typing.BinaryIO, signed=True) -> int:
    output = 0
    offset = 0
    while True:
        b = fp.read(1)[0]
        if b < 0x80:
            value = output | b << offset
            if signed:
                sign = value % 2
                value = value // 2
                if sign:
                    value = -(value + 1)
            return value
        output |= (b & 0x7F) << offset
        offset += 7


def _dump(fp, field: "Field", val):
    if not isinstance(field, (Field, Struct, Map, Optional, Map)):
        raise ValueError(f"Cannot dump non bare.Field: type: {type(val)}")
    if field.type == BareType.String:
        _write_string(fp, val)
    elif field.type in (BareType.INT, BareType.UINT):
        _write_varint(fp, val, signed=field.type == BareType.INT)
    elif field.type == BareType.Union:
        # must be a composite type, do compisitey things
        # type = next((x for x in )) # TODO: resume here, need UnionType, instance object
        pass
    elif field.type == BareType.Map:
        if not isinstance(val, Mapping):
            raise TypeError(f"You can't to write type {type(val)} as BareType.Map")
        length = len(val)
        # Write the number of elements as a UINT
        _write_varint(fp, length, signed=False)
        # followed by each key/value pair concatenatedA
        for k, v in val.items():
            _dump(fp, field.__class__._key, k)
            _dump(fp, field.__class__._value, v)

    elif primitive_types.get(field.type) is not None:
        # it's primitive, use the stored struct.pack method
        b = primitive_types.get(field.type)[0](val)
        fp.write(b)


def _load(fp, field: typing.Union[Field, typing.Type[Struct], Map, Optional]):
    # if not isinstance(field, (Field, Struct, Map, Optional)):
    #    raise ValueError(f"Cannot decode into a non bare.Field type: {field}")
    if field._type == BareType.Struct:
        values = {}
        for name, baretype in field.fields().items():
            values[name] = _load(fp, baretype)
        return field(**values)
    elif field.type == BareType.String:
        return _read_string(fp)
    elif field.type in (BareType.INT, BareType.UINT):
        return _read_varint(fp, signed=field.type == BareType.INT)
    elif field.type == BareType.Map:
        count = _read_varint(fp, signed=False)
        output = OrderedDict()
        for _ in range(count):
            key = _load(fp, field.__class__._key)
            val = _load(fp, field.__class__._value)
            output[key] = val
        return output
    elif primitive_types.get(field.type) is not None:
        format = primitive_types.get(field.type)[1]
        size = struct.calcsize(format)
        buf = fp.read(size)
        return struct.unpack(format, buf)[0]
