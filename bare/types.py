from .encoder import Field, BareType

class Int(Field):

    _type = BareType.INT
    _default = 0

    @classmethod
    def validate(cls, value):
        return isinstance(value, int) # TODO: check whether within min/max allowed by 64-bit precision

class Str(Field):

    _type = BareType.String
    _default = ""

    @classmethod
    def validate(cls, value):
        return isinstance(value, str)

class U8(Field):

    _type = BareType.U8
    _default = 0

    @classmethod
    def validate(self, value):
        return isinstance(value, int) and value <= 255
