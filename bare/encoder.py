from abc import ABC, abstractmethod
import io
import struct
from enum import Enum, auto
from functools import partial
from typing import BinaryIO, Union
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
    TaggedUnion = auto()
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
    BareType.Data:   (None, None, bytes)
    #(BareType.UINT, None, None, int),
    #(BareType.INT, None, None, int),
}

def _write_primitive(fp: BinaryIO, obj, type: BareType):
    # call the primitive type's dump functions. This is probably a struct.pack partial
    fp.write(primitive_types[type][0](obj))


def _write_varint(fp: BinaryIO, val: int, signed=True):
    if isinstance(val, float):
        logger.warning("Casting %d to int, possible loss of precision", val)
        val = int(val)
    if obj < 0 and not signed:
        raise ValueError("Attempting to write a signed number as unsigned.")
    if signed:
        val = val * 2
        if val < 0:
            val ^= val
    while val >= 0x80:
        fp.write(val | 0x80)
        val >>= 7

def _read_primitive(fp: BinaryIO, type: BareType):
    # TODO: implement this
    fp.read()


class BareObject(ABC):
    # key: field name, value: field type
    _fields = OrderedDict()

    @property
    def fields() -> typing.OrderedDict[str, BareType]:
        return self._fields

    def pack(self, fp=None) -> bytes:
        if not fp:
            fp = io.BytesIO()
        for field, type in self.fields.items():
                dump(fp, field)

    @classmethod
    def unpack(cls, data: Union[BinaryIO, bytes]):
        """
        unpack deserializes data into a type. If
        """
        raise NotImplementedError("This hasn't been implemented yet")

class BareUnion(ABC):

    _members: List[BareObject] = []

    @property
    def members() -> List[BareObject]:
        return self._members

def _dump(fp, obj, type: BareType):
    if type is not BareType:
        raise ValueError("Cannot dump non BareType")
    if primitive_types.get(type) is not None:
        # it's primitive, use the stored struct.pack method
        fp.write(primitive_types.get(type)[0](obj))
    elif type in (BareType.INT, BareType.UINT):
        _write_primitive(fp, obj, type, signed=type==BareType.INT)
    elif type is BareType.Union:
        # must be a composite type, do compisitey things
        type = next((x for x in )) # TODO: resume here, need UnionType, instance object

