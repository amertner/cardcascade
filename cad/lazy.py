"""A module that is imported the first time it is used, not when it is named.

Importing a part module loads build123d — four seconds of start-up a catalogue
path has no use for. A `lazy(...)` stands in and imports on the first
attribute read, so call sites stay `box_part.slot_band(d)` and the cost lands
only on a caller that uses it.
"""
import importlib


class _LazyModule:
    def __init__(self, name, package):
        self.__dict__["_spec"] = (name, package)
        self.__dict__["_mod"] = None

    def __getattr__(self, attr):
        mod = self.__dict__["_mod"]
        if mod is None:
            name, package = self.__dict__["_spec"]
            mod = self.__dict__["_mod"] = importlib.import_module(name, package)
        return getattr(mod, attr)

    def __repr__(self):
        return f"<lazy module {self.__dict__['_spec'][0]!r}>"


def lazy(name, package=None):
    """`lazy(".parts.box", __package__)` in place of `from .parts import box`."""
    return _LazyModule(name, package)
