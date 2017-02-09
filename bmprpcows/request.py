# -*- encoding: utf-8 -*-

import error
from threading import Event


class Request(object):
    def __init__(self):
        self._result = None
        self._error = None
        self._setted = False
        self._finished = Event()

    def set_result(self, result, error):
        self._result = result
        self._error = error
        self._setted = True
        self.finish()

    @property
    def result(self):
        return self._result

    @property
    def error(self):
        return self._error

    @property
    def is_response_available(self):
        return self._finished.isSet() and self._setted

    @property
    def finished(self):
        return self._finished.isSet()

    def wait(self, timeout=None):
        return self._finished.wait(timeout)

    def get(self, timeout=None):
        if not self.wait(timeout):
            raise error.RPCRequestTimeout("RPC request timeout")
        if not self._setted:
            raise error.RPCError("Request terminated")
        if self._error:
            if type(self._error) is list and len(self._error) == 2:
                raise error.RPCRequestError(self._error[0], self._error[1])
            elif type(self._error) is dict and "code" in self._error and "message" in self._error:
                raise error.RPCRequestError(self._error["code"], self._error["message"])
            raise error.RPCRequestError(error.USER_ERROR, self._error)
        return self.result

    def finish(self):
        self._finished.set()




