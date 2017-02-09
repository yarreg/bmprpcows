# -*- encoding: utf-8 -*-

#JSON-RPC 2.0 error-codes
PARSE_ERROR           = -32700
INVALID_REQUEST       = -32600
METHOD_NOT_FOUND      = -32601
INVALID_METHOD_PARAMS = -32602  #invalid number/type of parameters
INTERNAL_ERROR        = -32603  #"all other errors"
USER_ERROR            = -32000
USER_ERROR_START      = -32000
USER_ERROR_END        = -32099


class RPCError(Exception):
    pass


class RPCRequestError(RPCError):
    def __init__(self, code, message=""):
        self.code = code
        self.message = message

    def __str__(self):
        return "RPCError (%d): %s" % (self.code, self.message)

    def __repr__(self):
        return self.__str__()

    def to_obj(self):
        return [self.code, self.message]


class RPCRequestTimeout(RPCError):
    def __init__(self, msg="Request result wait timeout"):
        super(RPCRequestTimeout, self).__init__(msg)


