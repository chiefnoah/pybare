# PyBARE
[![builds.sr.ht
status](https://builds.sr.ht/~chiefnoah/pybare/commits/.build.yml.svg)](https://builds.sr.ht/~chiefnoah/pybare/commits/.build.yml?)

An declarative implementation of the [BARE](https://baremessages.org/) message
format for Python 3.6+

---

pybare is a general purpose library for strongly typed primitives in Python that
supports serializing to and from BARE messages.

```shell
pip install pybare
```

## Goals

* Provide a declarative structure for defining types
* Validation on value updates
* Support streaming messages
* Codegen based on `.schema` files

## Status

pybare fully implements all BARE types for both encoding and decoding. This
includes reading multiple messages from the same `BinaryIO` stream.

### TODO

- [  ] Codegen based on `.schema` files
- [  ] Better documentation
- [  ] More tests
- [  ] Fast C implementation for encoding

## Examples

pybare currently requires you define your structures by hand. Examples can be
found in the
[tests](https://git.sr.ht/~chiefnoah/pybare/tree/master/bare/test_encoder.py).

### Quickstart

```python
from bare import Struct, Map, Str, UInt, Optional, DataFixed

# Alternatively, DataFixed(length=64)
class PubKey(DataFixed):
    _length = 64 # 512 bits

class User(Struct):
    username = Str()
    userid = Int()
    email = Optional(Str)
    keys = Map(Str, PubKey)
    repos = Array(Str) # variable length array


noah = User(username="chiefnoah", userid=1)
noah.username == 'chiefnoah' # True
noah.username = 'someoneelse'
noah.username == 'someoneelse' # True
noah.userid == 1 # True
noah.username = 1 # raise: bare.ValidationError
noah.keys # {} (empty dict)
noah.keys['my key'] = bytes(64) #\x00\x00...
noah.keys['oops'] = bytes(1) # raise: bare.ValidationError
noah.email is None: # True
noah.email = 12345 # raise: bare.ValidationError
noah.pack() # \x00\x01 ... (binary data)
```

#### 'Magic' values

pybare primitive types (refered to by their baseclass `Field`) and their
subclasses implement the
[descriptor protocol](https://docs.python.org/3/howto/descriptor.html) to get
their 'magic' behavior. When an _instance_ is declared as a _class field_, the
type can be treated as it's underlying value (ie. `noah.username` is just the
`str` "chiefnoah" instead of `bare.Str`), while also providing validation and the
ability to "pack" the values into their corresponding bare primitives.

Note: in order to be treated as `Struct` members, fields _must_ be declared as
instances, not just their types.

For example:

```python
class User(Struct):
    username = Str # this is ignored!
    email = Str() # this isn't!
```
`Struct` and it's subclasses do not implement the descriptor protocol, as they
are container types. On instances of `Struct`s (or any other object that declares
a `Field` type as a class field), the underlying value is stored as the class
field name prefixed with `_`.

Example:
```python
u = User(username="noah")
u.username # "noah"
u._username # "noah"
```

You *can* modify this 'internal' value directly to bypass any validation imposed
by the `Field` type (but why would you want to do that).

Despite all of this, it's generally safe to include functions and other data on
subclasses of `Field`s. Again, only fields that have been declared on the class
will be serialized with `pack`.



---

To contribute, send patches to [~chiefnoah/inbox@lists.sr.ht](mailto:~chiefnoah/inbox@lists.sr.ht)
