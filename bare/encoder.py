from abc import ABC, abstractmethod
import io
import struct
from enum import Enum, auto
from functools import partial
import typing
from collections import OrderedDict
import logging

logger = logging.getLogger(__name__)

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
    # type          func to encode             func to decode    python native type    byte size
    BareType.U8:  (partial(struct.pack, '<B'), partial(struct.unpack, '<B'), int, 1),
    BareType.U16: (partial(struct.pack, '<H'), partial(struct.unpack, '<H'), int, 2),
    BareType.U32: (partial(struct.pack, '<I'), partial(struct.unpack, '<I'), int, 4),
    BareType.U64: (partial(struct.pack, '<Q'), partial(struct.unpack, '<Q'), int, 8),
    BareType.I8:  (partial(struct.pack, '<b'), partial(struct.unpack, '<b'), int, 1),
    BareType.I16: (partial(struct.pack, '<h'), partial(struct.unpack, '<h'), int, 2),
    BareType.I32: (partial(struct.pack, '<i'), partial(struct.unpack, '<i'), int, 4),
    BareType.I64: (partial(struct.pack, '<q'), partial(struct.unpack, '<q'), int, 8),
    BareType.F32: (partial(struct.pack, '<f'), partial(struct.unpack, '<f'), float, 4),
    BareType.F64: (partial(struct.pack, '<d'), partial(struct.unpack, '<d'), float, 8),
    BareType.Bool: (partial(struct.pack, '<?'), partial(struct.unpack, '<?'), bool, 1),
    BareType.String: (None, None, str),
    BareType.Data:   (None, None, bytes),
    BareType.Void: (lambda x: None, lambda x: None, None) # No OP
    #(BareType.UINT, None, None, int),
    #(BareType.INT, None, None, int),
}

def _write_string(fp: typing.BinaryIO, val: str):
    encoded = val.encode(encoding='utf-8') # utf-8 is the default, but doing this for clarity
    _write_varint(fp, len(encoded), signed=False)
    fp.write(encoded)


def _write_varint(fp: typing.BinaryIO, val: int, signed=True):
    if isinstance(val, float):
        logger.warning("Casting %d to int, possible loss of precision", val)
        val = int(val)
    if val < 0 and not signed:
        raise ValueError("Attempting to write a signed number as unsigned.")
    if signed:
        val = val * 2
        if val < 0:
            val ^= val
    while True:
        fp.write(struct.pack('<B', (val & 0xff) | 0x80))
        val >>= 7
        if val <= 0x80:
            break

class Field(ABC):
    """
    Field is a descritor that wraps a value, a BARE type, and some other
    metadata. It implements a `pack` method which writes the corresponding
    bytes for `type` to a provided file-like object.
    """

    _type = BareType.Void
    _value = None

    def __init__(self, value=None, optional=False):
        if value is None:
            value = self.__class__._value
        self._value = value
        self._optional = optional

    @property
    def type(self):
        return self.__class__._type

    @property
    def value(self):
        return self._value

    def pack(self, fp=None) -> typing.Optional[bytes]:
        buffered = False
        if not fp:
            fp = io.BytesIO()
            buffered = True
        _dump(fp, self)
        if buffered:
            return fp

    @classmethod
    def unpack(cls, fp: typing.Union[typing.BinaryIO, bytes]) -> 'Field':
        # If it's a bytes-like, wrap it in a io buffer
        if hasattr(fp, 'decode'):
            fp = io.BytesIO(fp)
        if primitive_types.get(cls._type) is not None:
            value = primitive_types.get(cls._type)[1](fp)
            return cls(cls._type, value)

class Int(Field):

    _type = BareType.INT
    _value = 0

class Str(Field):

    _type = BareType.String
    _value = ""

class U8(Field):

    _type = BareType.U8
    _value = 0

class Struct(ABC):

    _type = BareType.Struct

    def __init__(self, *args, **kwargs):
        # loop through defined fields, if they have a corresponding kwarg entry, set the value
        for name, field in filter(lambda x: isinstance(x[1], Field), self.__class__.__dict__.items()):
            if name in kwargs:
                setattr(self, name, kwargs[name])
            else:
                setattr(self, name, field.value)

    @property
    def fields(self) -> typing.OrderedDict[str, Field]:
        return OrderedDict(filter(lambda x: isinstance(x[1], Field), self.__class__.__dict__.items()))

    def pack(self, fp=None) -> bytes:
        ret = False
        if not fp:
            fp = io.BytesIO()
            ret = True
        for field, type in self.fields.items():
            _dump(fp, type, getattr(self, field))
        if ret:
            return fp.getvalue()

    @classmethod
    def unpack(cls, data: typing.Union[typing.BinaryIO, bytes]):
        """
        unpack deserializes data into a type. If
        """
        if hasattr(data, 'decode'):
            fp = io.BytesIO(data)
        else:
            fp = data
        for field, type in self.fields.items():
            _load(fp, type, getattr(self, field))
        raise NotImplementedError("This hasn't been implemented yet")

class Union(ABC):

    _members: typing.Tuple[typing.Union[Field, Struct],...] = ()

    @property
    def members(self) -> typing.Tuple[typing.Union[Field, Struct], ...]:
        return self.__class__._members

class Map(ABC):

    _key: Field=None
    _value: Field=None

def _dump(fp, field: Field, val):
    if not isinstance(field, Field):
        raise ValueError(f"Cannot dump non bare.Field: type: {type(val)}")
    if field.type == BareType.String:
        _write_string(fp, val)
    elif field.type in (BareType.INT, BareType.UINT):
        _write_varint(fp, val, signed=field.type==BareType.INT)
    elif field.type == BareType.Union:
        # must be a composite type, do compisitey things
        #type = next((x for x in )) # TODO: resume here, need UnionType, instance object
        pass
    elif primitive_types.get(field.type) is not None:
        # it's primitive, use the stored struct.pack method
        fp.write(primitive_types.get(field.type)[0](val))

def _load(fp, fields: Field):
    pass
