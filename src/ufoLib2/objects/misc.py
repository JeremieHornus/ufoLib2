import attr
from collections import namedtuple

try:
    from collections.abc import Mapping, MutableMapping
except ImportError:
    from collections import Mapping, MutableMapping


# sentinel value to signal a "lazy" object hasn't been loaded yet
_NOT_LOADED = object()


@attr.s(repr=False)
class DataStore(MutableMapping):
    listdir = None
    readf = None
    writef = None
    deletef = None

    _data = attr.ib(default=attr.Factory(dict), type=dict)

    def __attrs_post_init__(self):
        self._scheduledForDeletion = set()

    @classmethod
    def read(cls, reader, lazy=True):
        self = cls()
        for fileName in cls.listdir(reader):
            if lazy:
                self._data[fileName] = _NOT_LOADED
            else:
                self._data[fileName] = cls.readf(reader, fileName)
        if lazy:
            self.reader = reader
        return self

    # MutableMapping methods

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def __getitem__(self, fileName):
        if self._data[fileName] is _NOT_LOADED:
            self._data[fileName] = self.__class__.readf(self.reader, fileName)
        return self._data[fileName]

    def __setitem__(self, fileName, data):
        # should we forbid overwrite?
        self._data[fileName] = data
        if fileName in self._scheduledForDeletion:
            self._scheduledForDeletion.remove(fileName)

    def __delitem__(self, fileName):
        del self._data[fileName]
        self._scheduledForDeletion.add(fileName)

    def write(self, writer, saveAs=False):
        # if in-place, remove deleted data
        if not saveAs:
            for fileName in self._scheduledForDeletion:
                self.__class__.deletef(writer, fileName)
        # write data
        for fileName, data in self.items():
            self.__class__.writef(writer, fileName, data)
        self._scheduledForDeletion = set()
        if saveAs and hasattr(self, "reader"):
            # all data was read by now, ref to reader no longer needed
            delattr(self, "reader")

    @property
    def fileNames(self):
        return list(self._data.keys())


class Transformation(
    namedtuple(
        "Transformation",
        ["xScale", "xyScale", "yxScale", "yScale", "xOffset", "yOffset"],
    )
):
    def __repr__(self):
        return "<%s [%r %r %r %r %r %r]>" % ((self.__class__.__name__,) + self)


Transformation.__new__.__defaults__ = (1, 0, 0, 1, 0, 0)


class AttrDictMixin(Mapping):
    """ Read attribute values using mapping interface. For use with Anchors and
    Guidelines classes, where client code expects them to behave as dict.
    """

    def __getitem__(self, key):
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(key)

    def __iter__(self):
        for key in attr.fields_dict(self.__class__):
            if getattr(self, key) is not None:
                yield key

    def __len__(self):
        return sum(1 for _ in self)
