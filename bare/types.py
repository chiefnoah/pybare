"""
bare.types contains primitive types
"""
from .encoder import (
    Field,
    BareType,
    _write_string,
    _write_varint,
    _read_string,
    _read_varint,
)
import typing
import struct
from enum import IntEnum

ValidationMessage = typing.Tuple[bool, str]


class Simple(Field):
    _fmt = None
    _bytesize = 0

    def _pack(self, fp: typing.BinaryIO, value=None):
        if value is None:
            value = self._value
        fp.write(struct.pack(self.__class__._fmt, value))

    def _unpack(self, fp: typing.BinaryIO):
        buf = fp.read(self._bytesize)
        return self.__class__(value=(struct.unpack(self._fmt, buf)[0]))


class U8(Simple):
    """
    An unsigned 8bit integer
    """

    _type = BareType.U8
    _default = 0
    _fmt = "<B"
    _bytesize = 1

    def validate(self, value) -> ValidationMessage:
        if not isinstance(value, int):
            return False, f"type: {type(value)} must be <int>"
        if value < 0 or value > 0xFFFF:
            return (
                False,
                f"value: {value} is outside of valid range for this type: {self.__class__._type}",
            )
        return True, None


class U16(Simple):
    _type = BareType.U16
    _default = 0
    _fmt = "<H"
    _bytesize = 2

    def validate(self, value) -> ValidationMessage:
        if not isinstance(value, int):
            return False, f"type: {type(value)} must be <int>"
        if value < 0 or value > 0xFFFFFFFF:
            return (
                False,
                f"value: {value} is outside of valid range for this type: {self.__class__._type}",
            )
        return True, None


class U32(Simple):
    _type = BareType.U32
    _default = 0
    _fmt = "<I"
    _bytesize = 4

    def validate(self, value) -> ValidationMessage:
        if not isinstance(value, int):
            return False, f"type: {type(value)} must be <int>"
        if value < 0 or value > 0xFFFFFFFF:
            return (
                False,
                f"value: {value} is outside of valid range for this type: {self.__class__._type}",
            )
        return True, None


class U64(Simple):

    _type = BareType.U64
    _default = 0
    _fmt = "<Q"
    _bytesize = 8

    def validate(self, value) -> ValidationMessage:
        if not isinstance(value, int):
            return False, f"type: {type(value)} must be <int>"
        if value < 0 or value > 0xFFFFFFFFFFFFFFFF:
            return (
                False,
                f"value: {value} is outside of valid range for this type: {self.__class__._type}",
            )
        return True, None


class I8(Simple):
    _type = BareType.I8
    _default = 0
    _fmt = "<b"
    _bytesize = 1

    def validate(self, value) -> ValidationMessage:
        if not isinstance(value, int):
            return False, f"type: {type(value)} must be <int>"
        if value < -128 or value > 127:
            return (
                False,
                f"value: {value} is outside of valid range for this type: {self.__class__._type}",
            )
        return True, None


class I16(Simple):
    _type = BareType.I16
    _default = 0
    _fmt = "<h"
    _bytesize = 2

    @classmethod
    def validate(self, value) -> ValidationMessage:
        if not isinstance(value, int):
            return False, f"type: {type(value)} must be <int>"
        if value < -32768 or value > 32767:
            return (
                False,
                f"value: {value} is outside of valid range for this type: {self.__class__._type}",
            )
        return True, None


class I32(Simple):
    _type = BareType.I32
    _default = 0
    _fmt = "<i"
    _bytesize = 4

    def validate(self, value) -> ValidationMessage:
        if not isinstance(value, int):
            return False, f"type: {type(value)} must be <int>"
        if value < -2147483648 or value > 2147483647:
            return (
                False,
                f"value: {value} is outside of valid range for this type: {self.__class__._type}",
            )
        return True, None


class I64(Simple):
    _type = BareType.I64
    _default = 0
    _fmt = "<q"
    _bytesize = 8

    def validate(self, value) -> ValidationMessage:
        if not isinstance(value, int):
            return False, f"type: {type(value)} must be <int>"
        if value < -9223372036854775808 or value > 9223372036854775807:
            return (
                False,
                f"value: {value} is outside of valid range for this type: {self.__class__._type}",
            )
        return True, None


class F32(Simple):
    _type = BareType.F32
    _default = 0.0
    _fmt = "<f"
    _bytesize = 4

    def validate(self, value) -> ValidationMessage:
        if not isinstance(value, float):
            return False, f"type: {type(value)} must be <int>"
        return True, None


class F64(Simple):
    _type = BareType.F32
    _default = 0.0
    _fmt = "<d"
    _bytesize = 8

    def validate(self, value) -> ValidationMessage:
        if not isinstance(value, float):
            return False, f"type: {type(value)} must be <int>"
        return True, None


class Bool(Simple):
    _type = BareType.Bool
    _default = False
    _fmt = "<?"
    _bytesize = 1

    def validate(self, value) -> ValidationMessage:
        if not isinstance(value, bool):
            return False, f"type: {type(value)} must be <int>"
        return True, None


class Void(Field):
    _type = BareType.Void
    _default = None
    _fmt = None
    _bytesize = 0

    def _pack(self, fp: typing.BinaryIO, value=None):
        pass  # NO OP

    def _unpack(self, fp: typing.BinaryIO):
        return self.__class__(value=None)

    def validate(self, value):
        if value is not None:
            return False, f"type: {type(value)} must be <None>"
        return True, None


class Int(Field):

    _type = BareType.INT
    _default = 0

    def validate(self, value) -> ValidationMessage:
        if not isinstance(value, int):
            return False, f"type: {type(value)} must be <int>"
        return True, None

    def _pack(self, fp: typing.BinaryIO, value=None):
        if value is None:
            value = self._value
        _write_varint(fp, value, signed=True)

    def _unpack(self, fp: typing.BinaryIO) -> "Int":
        val = _read_varint(fp, signed=True)
        return self.__class__(value=val)


class UInt(Field):

    _type = BareType.UINT
    _default = 0

    def validate(self, value) -> ValidationMessage:
        if not isinstance(value, int):
            return False, f"type: {type(value)} must be <int>"
        if value < 0:
            return (
                False,
                f"value: {value} is outside of valid range for this type: {self.__class__._type}",
            )
        return True, None

    def _pack(self, fp: typing.BinaryIO, value=None):
        if value is None:
            value = self._value
        _write_varint(fp, value, signed=False)

    def _unpack(self, fp: typing.BinaryIO) -> "UInt":
        val = _read_varint(fp, signed=False)
        return self.__class__(value=val)


class Str(Field):

    _type = BareType.String
    _default = ""

    def validate(self, value) -> ValidationMessage:
        if not isinstance(value, str):
            return False, f"type: {type(value)} must be <str>"
        return True, None

    def _pack(self, fp: typing.BinaryIO, value=None):
        if value is None:
            value = self._value
        _write_string(fp, value)

    def _unpack(self, fp: typing.BinaryIO) -> "Str":
        val = _read_string(fp)
        return self.__class__(value=val)


class Data(Field):
    _type = BareType.Data
    _default = bytes()

    def validate(self, value) -> ValidationMessage:
        if not isinstance(value, bytes):
            return False, f"Fixed length raw data must be type '{bytes}' not '{type(value)}.'"
        return True, None

    def _pack(self, fp: typing.BinaryIO, value=None):
        if value is None:
            value = self._value
        length = len(value)
        if isinstance(value, str):
            value = value.encode("utf-8")
        _write_varint(fp, val=length, signed=False)
        fp.write(struct.pack(f"<{len(value)}s", value))

    def _unpack(self, fp: typing.BinaryIO) -> "Data":
        length = _read_varint(fp, signed=False)
        val = struct.unpack("<{length}s", fp)[0]
        return self.__class__(value=val)


class DataFixed(Field):
    _type = BareType.DataFixed
    _length = 0
    _default = bytes(_length)

    def __init__(self, length=0, value=None):
        """Fixed length raw data type

        :param int length: number in bytes this type should represent.
            Either this arg must be set, or this class subclassed and the
            _length class field overriden
        :param bytes value: an optional value to set
        """
        if length == 0 and self.__class__._length > 0:
            self._length = self.__class__._length
        else:
            self._length = length
        if value is not None:
            self._value = value
        else:
            self._value = self.__class__._default

    def validate(self, value) -> ValidationMessage:
        if not isinstance(value, bytes):
            return False, f"Fixed length raw data must be type '{bytes}' not '{type(value)}.'"
        
        if len(value) != self._length:
            return (
                False,
                f"Length of data {len(value)} not equal to fixed length {self._length}",
            )
        
        return True, None

    def _pack(self, fp: typing.BinaryIO, value=None):
        if value is None:
            value = self._value
        fp.write(struct.pack(f"<{self._length}s", value))

    def _unpack(self, fp: typing.BinaryIO, length=None) -> "DataFixed":
        if length is None:
            length = self._length
        val = struct.unpack(f"<{length}s", fp)[0]
        return self.__class__(value=val)


class Enum(UInt):
    def __init__(self, enum, *args, **kwargs):
        """Enum defines a BARE enum type

        Validate checks whether the provided value is an `int` and a valid enum member
        :param Enum enum: a standard `Enum` type. Values for enum members *must* be positive ints
        """
        self._enum = enum
        super().__init__(*args, **kwargs)

    def validate(self, value) -> ValidationMessage:
        if not isinstance(value, int):
            return False, f"type: {type(value)} is not valid for Enum, must be <int>"
        if value < 0:
            return (
                False,
                f"value is not a valid value for Enum {self.__class__.__name__}",
            )
        values = set(item.value for item in self._enum.__members__.values())
        if value not in values:
            return (
                False,
                f"value {value} is not a valid Enum type for {self.__class__.__name__}",
            )
        return True, None

    def _unpack(self, fp: typing.BinaryIO) -> "UInt":
        val = _read_varint(fp, signed=False)
        return self.__class__(self._enum, val)
