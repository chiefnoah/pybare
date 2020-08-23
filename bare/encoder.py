import io
import logging
import struct
import typing
import inspect
from abc import ABC, abstractmethod
from collections import OrderedDict
from enum import Enum, auto
from functools import partial
from collections.abc import Mapping
from collections import UserDict, UserList


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
        setattr(owner, f"_{name}", self._value)

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        else:
            return getattr(instance, f"_{self.name}")

    def __set__(self, instance, value):
        if instance is None:
            raise AttributeError("Unable to assign value when not attached to object")
        valid, message = self.validate(value)
        if not valid:
            raise ValidationError(
                f"value is invalid for BARE type {self._type.__class__.__name__}: {message}"
            )
        setattr(instance, f"_{self.name}", value)

    @abstractmethod
    def validate(self, value) -> typing.Tuple[bool, str]:
        """
        Checks whether a give value is valid for the Field's data type. Returns a tuple of a boolean
        and an optional message for why
        """
        return self.__class__._default == None  # This is valid for BareType.Void

    @property
    def valid(self) -> typing.Tuple[bool, str]:
        return self.validate(self._value)

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

    @abstractmethod
    def _pack(self, fp, value=None):
        pass

    @abstractmethod
    def _unpack(self, fp: typing.BinaryIO) -> "Field":
        pass

    def pack(self, fp=None) -> typing.Optional[bytes]:
        buffered = False
        if not fp:
            fp = io.BytesIO()
            buffered = True
        self._pack(fp)
        if buffered:
            return fp.getvalue()

    def unpack(self, fp: typing.BinaryIO):
        # If it's a bytes-like, wrap it in a io buffer
        if hasattr(fp, "decode"):
            fp = io.BytesIO(fp)
        return self._unpack(fp)

    def to_dict(self, value=None):
        if value is None:
            value = self._value
        if isinstance(value, Field):
            return value.value
        else:
            return value


class Struct(ABC):

    _type = BareType.Struct

    def __init__(self, *args, **kwargs):
        # loop through defined fields, if they have a corresponding kwarg entry, set the value
        for name, field in filter(
            lambda x: isinstance(x[1], (Field, Struct)), self.__class__.__dict__.items()
        ):
            if name in kwargs:
                setattr(self, name, kwargs[name])
            else:
                setattr(self, name, field.value)

    @classmethod
    def fields(cls) -> typing.OrderedDict[str, Field]:
        return OrderedDict(
            filter(lambda x: isinstance(x[1], (Field, Struct)), cls.__dict__.items())
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
        self._pack(fp)
        if ret:
            return fp.getvalue()

    def _pack(self, fp: typing.BinaryIO, value=None):
        if value is None:
            value = self
        for name, field in value.fields().items():
            val = getattr(value, name)  # this gets the underlying value
            field._pack(fp, value=val)

    @classmethod
    def _unpack(cls, fp: typing.BinaryIO):
        vals = {}
        for field, type in cls.fields().items():
            val = type._unpack(fp)
            vals[field] = val.value
        return cls(**vals)

    @classmethod
    def unpack(cls, data: typing.Union[typing.BinaryIO, bytes]):
        """
        unpack deserializes data into a type. If
        """
        if hasattr(data, "decode"):
            fp = io.BytesIO(data)
        else:
            fp = data
        return cls._unpack(fp)

    @property
    def value(self):
        # A structs value is itself
        return self

    def validate(self, s) -> typing.Tuple[bool, str]:
        try:
            for name, field in s.fields().items():
                valid, message = field.validate(getattr(s, name))
                if not valid:
                    return False, message
        except AttributeError:
            return False, f"{type(s)} is not a valid struct {type(self)}"
        return True, None

    @property
    def valid(self) -> typing.Tuple[bool, str]:
        for name, field in self.fields().items():
            valid, message = field.validate(getattr(self, name))
            if not valid:
                return False, message
        return True, None

    def to_dict(self, value=None) -> dict:
        if value is None:
            value = self
        output = {}
        for name, field in value.fields().items():
            val = getattr(value, name)
            output[name] = field.to_dict(value=val)
        return output


class _ValidatedList(UserList):
    def __init__(self, *args, instance: "Array" = None, **kwargs):
        if instance is None:
            raise ValueError(
                "Must specify backreference to Array. This is likely a bug in the library."
            )
        self._instance = instance
        super().__init__(*args, **kwargs)

    def append(self, item):
        valid, message = self._instance._validateitem(item, length=len(self.data) + 1)
        if not valid:
            raise ValidationError(message)
        self.data.append(item)

    def extend(self, other):
        # This is probably slow, but we get the validation logic from append for free
        for item in other:
            self.append(item)

    def __setitem__(self, i, item):
        valid, message = self._instance.validate(i, item)
        if not valid:
            raise ValidationError(message)
        self.data[i] = item


class Array(Field):

    _type: typing.Type[Field] = None
    _length = 0  # zero means variable length
    _default = None

    def __init__(self, type: typing.Type[Field] = None, length=0, values=None):
        if type is not None:
            if inspect.isclass(type):
                self._type = type()
            else:
                self._type = type
        elif self.__class__._type is None:
            raise TypeError(
                "Must either specify type as argument to init or _type class field"
            )
        else:
            self._type = self.__class__._type()
        # if the class _length is specified (in a subclass), it takes precidense over the arg length if it's 0
        if self.__class__._length > 0 and length == 0:
            self._length = self.__class__._length
        else:
            self._length = length
        if values:
            self.validate(values)
            self._value = _ValidatedList(values, instance=self)
        else:
            self._value = _ValidatedList(instance=self)

    def _validateitem(self, item, length=0) -> typing.Tuple[bool, str]:
        if length > self._length:
            return False, f"length {length} larger than array max: {self._length}"
        if self._length > 0 and len(self._value) + 1 > self._length:
            return False, "outside of length bounds"
        return self._type.validate(item)

    def validate(self, items: typing.Collection) -> typing.Tuple[bool, str]:
        if self._length > 0 and len(items) > self._length:
            return False, f"lenth {len(items)} larger than array max: {self._length}"
        if self._length > 0 and len(items) > self._length:
            return False, f"length {len(items)} greater than max length {self._length}"
        for item in items:
            if type(item) == type(self._type):
                valid, message = item.valid
            else:
                valid, message = self._type.validate(item)
            if not valid:
                return False, message
        return True, None

    def _pack(self, fp: typing.BinaryIO, value=None):
        if value is None:
            value = self._value
        if self._length == 0:
            length = len(value)
            _write_varint(fp, length, signed=False)
        else:
            default = None
            if isinstance(self._type, Field):
                default = self._type._default
            elif isinstance(self._type, Struct):
                default = self._type.__class__()
            value.extend(
                [default] * (self._length - len(value))
            )  # pad with default values
        for item in value:
            if isinstance(item, Field):
                self._type._pack(fp, item.value)
            else:
                self._type._pack(fp, item)

    def _unpack(self, fp: typing.BinaryIO) -> "Array":
        if self._length == 0:
            length = _read_varint(fp, signed=False)
        else:
            length = self._length
        values = []
        for _ in range(length):
            val = self._type._unpack(fp)
            values.append(val)
        return self.__class__(type=self._type, length=self._length, values=values)

    def to_dict(self, value=None):
        if value is None:
            value = self._value
        output = []

        for item in value:
            if isinstance(item, (Struct, Field)):
                output.append(item.to_dict())
            else:
                output.append(item)
        return output


class _ValidatedMap(UserDict):
    def __init__(self, *args, instance: "Map" = None, **kwargs):
        if instance is None:
            raise ValueError(
                "Must specify backreference to Map. This is likely a bug in the library."
            )
        self._instance = instance
        super().__init__(*args, **kwargs)

    def __setitem__(self, key, value):
        valid, message = self._instance.validate({key: value})
        if not valid:
            raise ValidationError(message)
        self.data[key] = value

    def update(self, other: Mapping):
        valid, message = self._instance.validate(other)
        if not valid:
            raise ValidationError(f"Unable to update map: {message}")
        self.data.update(other)


class Map(Field):
    _type = BareType.Map
    _keytype: typing.Type[Field] = None
    _valuetype: typing.Type[Field] = None
    _default = None

    def __init__(self, keytype: Field = None, valuetype: Field = None, value=None):
        if keytype is not None:
            if inspect.isclass(keytype):
                self._keytype = keytype()
            else:
                self._keytype = keytype
        elif self.__class__._keytype is None:
            raise TypeError(
                "Must either specify keytype as an argument to init or  _keytype class field"
            )
        else:
            self._keytype = self.__class__._keytype()
        if valuetype is not None:
            if inspect.isclass(valuetype):
                self._valuetype = valuetype()
            else:
                self._valuetype = valuetype
        elif self.__class__._valuetype is None:
            raise TypeError(
                "Must either specify valuetype as an argument to init or  _valuetype class field"
            )
        else:
            self._valuetype = self.__class__._valuetype()
        if value:
            for k, v in value.items():
                valid, message = self._validatekv(k, v)
                if not valid:
                    raise ValidationError(
                        f"Unable to assign value to key: {k}: {message}"
                    )
        self._value = _ValidatedMap(value, instance=self)

    def __set__(self, instance, value):
        if instance is None:
            raise AttributeError("Unable to assign value when not attached to class")
        valid, message = self.validate(value)
        if not valid:
            raise ValidationError(
                f"Attempting to assign invalid value to typed map: {message}"
            )
        wrapped = _ValidatedMap(value, instance=self)
        setattr(instance, f"_{self.name}", wrapped)

    def _validatekv(self, key, value) -> typing.Tuple[bool, str]:
        keyvalid, message = self._keytype.validate(key)
        if not keyvalid:
            return False, f"map key {message}"
        valvalid, message = self._valuetype.validate(value)
        if not valvalid:
            return False, f"map value {message}"
        return True, ""

    def validate(self, value: Mapping) -> typing.Tuple[bool, str]:
        if not isinstance(value, Mapping):
            return False, f"Invalid value type: {type(value)}"
        for k, v in value.items():
            valid, message = self._validatekv(k, v)
            if not valid:
                return False, message
        return True, None

    def _pack(self, fp: typing.BinaryIO, value=None):
        if value is None:
            value = self._value  # type: _ValidatedMap
        count = len(value)
        _write_varint(fp, count, signed=False)
        for k, v in value.items():
            self._keytype._pack(fp, value=k)
            self._valuetype._pack(fp, value=v)

    def _unpack(self, fp: typing.BinaryIO) -> "Map":
        count = _read_varint(fp, signed=False)
        values = {}
        for _ in range(count):
            key = self._keytype._unpack(fp)
            value = self._valuetype.unpack(fp)
            values[key] = value
        return self.__class__(
            keytype=self._keytype, valuetype=self._valuetype, value=values
        )

    def to_dict(self, value=None):
        if value is None:
            value = self._value
        output = {}
        for k, v in value.items():
            if isinstance(v, (Field, Struct)):
                k = v.to_dict()
            else:
                output[k] = v
        return output


class Optional(Field):
    def __init__(self, wrapped: typing.Union[typing.Type[Field], Field], value=None):
        if inspect.isclass(wrapped):
            if value is not None:
                self._wrapped = wrapped(value)
            else:
                self._wrapped = wrapped()
        else:
            self._wrapped = wrapped
        self._value = value

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        else:
            return getattr(instance, f"_{self.name}")

    def __set__(self, instance, value):
        if instance is None:
            raise AttributeError("Unable to assign value when not attached to object")
        valid, message = self.validate(value)
        if not valid:
            raise ValidationError(
                f"value is invalid for BARE type {self._type}: {message}"
            )
        setattr(instance, f"_{self.name}", value)

    def validate(self, value):
        if value is None:
            return True, None
        return self._wrapped.validate(value)

    def _pack(self, fp: typing.BinaryIO, value=None):
        if value is None:
            value = self._value
        if value is None:
            fp.write(struct.pack("<B", 0))
        else:
            fp.write(struct.pack("<B", 1))
            self._wrapped._pack(fp, value=value)

    def _unpack(self, fp: typing.BinaryIO) -> "Optional":
        buf = fp.read(1)
        check = struct.unpack("<B", buf)[0]
        if check == 0:
            return self.__class__(wrapped=self._wrapped, value=None)
        value = self._wrapped._unpack(fp)
        return self.__class__(wrapped=self._wrapped, value=value)


class Union(Field):

    _members: typing.Tuple[typing.Union[Field, Struct], ...] = ()

    def __init__(self, members: typing.Tuple = None, value=None):
        if members is None:
            members = self.__class__._members
        self._members = []
        for member in members:
            if inspect.isclass(member):
                self._members.append(member(value=value))
            else:
                self._members.append(member)
        if value is not None:
            valid, message = self.validate(value)
            if not valid:
                raise ValidationError(
                    f"Attempting to set incorrect value to Union type: {type(value)}"
                )
        self._value = value

    @property
    def members(self):
        return self._members

    def validate(self, value) -> typing.Tuple[bool, str]:
        if isinstance(value, Field) and value.__class__ in [
            x.__class__ for x in self._members
        ]:
            return value.validate(value.value)
        for member in self._members:
            valid, _ = member.validate(value)
            if valid:
                return True, None
        return False, f"type {type(value)} is not valid for one of {self._members}"

    def _pack(self, fp: typing.BinaryIO, value=None):
        if value is None:
            value = self._value
        for id, member in enumerate(self._members):
            if isinstance(value, (Field, Struct)):
                # it's a field, so we should try to check for type
                valid = type(member) == type(value)
            else:
                # no idea what it might be, maybe a python native value
                # do the less good validation check
                valid, _ = self.validate(value)
            if valid:
                _write_varint(fp, id, signed=False)
                member._pack(fp, value=value)
                return
        raise TypeError("Unable to determine Union member type for value.")

    def _unpack(self, fp: typing.BinaryIO):
        uid = _read_varint(fp, signed=False)
        value = self._members[uid]._unpack(fp)
        return self.__class__(members=self._members, value=value)

    def to_dict(self, value=None):
        if value is None:
            value = self._value
        return value.to_dict()


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
        try:
            b = fp.read(1)[0]
        except IndexError as e:
            raise RuntimeError("Not enough bytes in buffer to decode")
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

