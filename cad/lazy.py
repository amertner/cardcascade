"""A module that is imported the first time it is used, not when it is named.

`cad.assembly` is pure arithmetic and says so, but it is written in terms of
the part modules, and importing a part module loads build123d — four seconds
of start-up that `cad.assemble --list` spent on printing names. A `lazy(...)`
stands in for the module and imports it on the first attribute read, so the
call sites stay `box_part.slot_band(d)` and the cost lands only on a
caller that computes a placement.
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
