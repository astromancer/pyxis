"""
Enable construction of containers with uniform item type(s)
"""

# std libs
import warnings as wrn
from abc import ABCMeta
from collections import abc, UserList


# local libs
from recipes.iter import first_true_index
from recipes.functionals import echo0, raises as bork


class OfTypes(ABCMeta):
    """
    Factory that creates TypeEnforcer classes. Allows for the following usage
    pattern:

    >>> class Container(UserList, OfTypes(int)):
    ...     pass

    which creates a container class `Container` that will only allow integer
    items inside. This constructor assigns a tuple of allowed types as class
    attribute `_allowed_types`
    """

    # NOTE: inherit from ABCMeta to avoid metaclass conflict with UserList which
    # has metaclass abc.ABCMeta

    def __new__(cls, *args, **kws):

        if isinstance(args[0], str):
            # This results from an internal call below during construction
            name, bases, attrs = args
            # create class
            return super().__new__(cls, name, cls.make_bases(name, bases),
                                   attrs, **kws)

        # we are here if invoked by direct call:
        # >>> cls = OfType(int)

        # create TypeEnforcer class that inherits from _TypeEnforcer.
        # args gives allowed types for this container.
        # `_allowed_types` class attribute set to tuple of allowed types

        # check arguments are given and class objects
        if len(args) == 0:
            raise ValueError(f'{cls.__name__!r}s constructor requires at least '
                             'one argument: the allowed type(s).')
        for kls in args:
            if not isinstance(kls, type):
                raise TypeError(f'Arguments to {cls.__name__!r} constructor '
                                'should be classes.')

        # create the type
        return super().__new__(cls, 'ListOf', (_TypeEnforcer, ),
                               {'_allowed_types': tuple(args)}, **kws)

    @classmethod
    def _get_allowed_types(cls, bases):

        idx_enf = None
        idx_cnt = None
        previous_allowed_types = []
        for i, base in enumerate(bases):
            # print('BASS', base)
            if issubclass(base, abc.Container):
                idx_cnt = i

            # base is a TypeEnforcer class
            if issubclass(base, _TypeEnforcer):
                # _TypeEnforcer !
                # print('_TypeEnforcer !', base,  base._allowed_types)
                requested_allowed_types = base._allowed_types
                idx_enf = i

            # look for other `_TypeEnforcer`s in the inheritance diagram so we
            # consolidate the type checking
            for bb in base.__bases__:
                if isinstance(bb, cls):
                    # this is a `_TypeEnforcer` base
                    previous_allowed_types.extend(bb._allowed_types)
                    # print(previous_allowed_types)
                    # base_enforcers.append(bb)
                    # original_base = base

        return idx_enf, idx_cnt, requested_allowed_types, previous_allowed_types

    @staticmethod
    def _check_allowed_types(name, requested_allowed_types,
                             previous_allowed_types):

        # consolidate allowed types
        if previous_allowed_types:
            # new_allowed_types = []
            # loop through currently allowed types
            for allowed in previous_allowed_types:
                for new in requested_allowed_types:
                    if issubclass(new, allowed):
                        # type restriction requested is a subclass of already
                        # existing restriction type.  This means we narrow the
                        # restriction to the new (subclass) type
                        # new_allowed_types.append(new)
                        break

                    # requested type restriction is a new type unrelated to
                    # existing restriction. Disallow.
                    raise TypeError(
                        f'Multiple incompatible type restrictions ({new}, '
                        f'{allowed}) requested in different bases of container'
                        f' class {name}.'
                    )

    @classmethod
    def make_bases(cls, name, bases):
        """
        sneakily place `_TypeEnforcer` ahead of `abc.Container` types in the
        inheritance order so that type checking happens on __init__ of classes
        of this metaclass.

        also check if there is another TypeEnforcer in the list of bases and
        make sure the `_allowed_types` are consistent - if any is a subclass
        of a type in the already defined `_allowed_types` higher up
        TypeEnforcer this is allowed, else raise TypeError since it will lead
        to type enforcement being done for different types at different levels
        in the class heirarchy which is nonsensical.
        """

        # TODO: might want to do the same for ObjectArray1d.  If you register
        #   your classes as ABCs you can do this in one foul swoop!

        # enforcers = []
        # base_enforcers = []
        # indices = []
        # new_bases = list(bases)

        *indices, requested, currently_allowed = cls._get_allowed_types(bases)
        idx_enf, idx_cnt = indices
        
        # print('=' * 80)
        # print(name, bases)
        # print('requested', requested_allowed_types)
        # print('current', previous_allowed_types)

        # deal with multiple enforcers
        # en0, *enforcers = enforcers
        # ite, *indices = indices
        # if len(enforcers) > 0:
        #     # multiple enforcers defined like this:
        #     # >>> class Foo(list, OfType(int), OfType(float))
        #     # instead of like this:
        #     # >>> class Foo(list, OfTypes(int, float))
        #     # merge type checking
        #     warnings.warn(f'Multiple `TypeEnforcer`s in bases of {name}. '
        #                   'Please use `OfType(clsA, clsB)` to allow multiple '
        #                   'types in your containers')

        #     for i, ix in enumerate(indices):
        #         new_bases.pop(ix - i)

        cls._check_allowed_types(name, requested, currently_allowed)

        if idx_cnt is None:
            if cls is ListOf:
                # No container types in list of parents. Add it!
                bases = (*bases[:idx_enf], UserList, *bases[idx_enf:])
            else:
                requested = ', '.join(kls.__name__ for kls in requested)
                raise TypeError(f'Using "{cls.__name__}({requested})" without '
                                f'preceding container type in inheritence '
                                f'diagram. Did you mean to use '
                                f'"ListOf({requested})"?')

        if (idx_enf is None) or (idx_cnt is None):
            return bases

        if idx_cnt < idx_enf:
            # _TypeEnforcer is before UserList in inheritance order so that
            # types get checked before initialization of the `Container`
            _bases = list(bases)
            _bases.insert(idx_cnt, _bases.pop(idx_enf))
            # print('new_bases', _bases)
            return tuple(_bases)

        return bases


# alias
OfType = OfTypes


class ListOf(OfType):
    """
    Ensures inheritance from UserList
    
    >>> class Container(ListOf(int)):
    ...     pass
    """


class _TypeEnforcer:
    """
    Item type checking mixin for list-like containers
    """

    # TODO: inherit from UserList, so we can init like
    # from pyxides.typing import OfType

    # class Twinkie:
    #     """Yum!"""

    # class Box(OfType(Twinkie)):
    #     """So much YUM!"""

    # Box()

    _allowed_types = (object, )         # placeholder
    _actions = {-1: echo0,              # silently ignore
                0: wrn.warn,            # emit warning
                1: bork(TypeError)}     # raise TypeError
    emit = staticmethod(_actions[1])    # default action is to raise

    @classmethod
    def type_checking(cls, severity=1):
        cls.emit = staticmethod(cls._actions[int(severity)])

    def __init__(self, items=()):
        super().__init__(self.checks_type(items))
        # self.emit = self._actions[int(severity)]

    def checks_type(self, itr, raises=None, warns=None, silent=None):
        """Generator that checks types"""
        if raises is warns is silent is None:
            # default behaviour decided at init (default is to raise TypeError)
            raises = True

        emit = self._actions[1 - first_true_index((raises, warns, silent))]
        for i, obj in enumerate(itr):
            with wrn.catch_warnings():
                wrn.filterwarnings('once', 'Items in container class')
                self.check_type(obj, i, emit)
                yield obj

    def check_type(self, obj, i='', emit=None):
        """Type checker"""
        if isinstance(obj, self._allowed_types):
            return

        emit = emit or self.emit
        if emit is echo0:
            return

        many = len(self._allowed_types) > 1
        ok = self._allowed_types[... if many else 0]
        emit(f'Items in container class {self.__class__.__name__!r} must '
             f'derive from {"one of" if many else ""} {ok}. '
             f'Item {i}{" " * bool(i)} is of type {type(obj)!r}.')

    def append(self, item):
        self.check_type(item, len(self))
        super().append(item)

    def extend(self, itr):
        super().extend(self.checks_type(itr))