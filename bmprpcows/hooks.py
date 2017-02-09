# -*- encoding: utf-8 -*-

from types import MethodType


class ObjectCallWrapper(object):
    def _get_hooks(self, hook_type):
        return self.__dict__.setdefault(hook_type, {})

    def _call_hooks(self, hook_type, method, args, kwargs):
        hooks = self._get_hooks(hook_type)
        hooks = hooks.get(method.__name__, [])
        for hook in hooks:
            hook(*args, **kwargs)

    def _add_call_hook(self, hook_type, method_name, func):
        if not hasattr(self, method_name) or not callable(getattr(self, method_name)):
            raise Exception("Bad method")
        hooks = self._get_hooks(hook_type)
        hooks = hooks.setdefault(method_name, [])
        hooks.append(func)

    def remove_call_hooks(self, hook_type=None):
        if hook_type:
            self._get_hooks(hook_type).clear()
        else:
            self._get_hooks("before").clear()
            self._get_hooks("after").clear()

    def before_call(self, method_name, func):
        self._add_call_hook("before", method_name, func)

    def after_call(self, method_name, func):
        self._add_call_hook("after", method_name, func)

    @staticmethod
    def _method_wrapper(obj, method):
        def _wrap(*args, **kwargs):
            obj._call_hooks("before", method, args, kwargs)
            ret = method(*args, **kwargs)
            obj._call_hooks("after", method, args, kwargs)
            return ret
        return _wrap

    def __getattribute__(self, name):
        attr = object.__getattribute__(self, name)
        if type(attr) is MethodType:
            if attr.__name__ not in ObjectCallWrapper.__dict__.keys():
                return ObjectCallWrapper._method_wrapper(self, attr)
        return attr


def create_class(cls):
    return type(cls.__name__, (cls, ObjectCallWrapper), {})
