# -*- encoding: utf-8 -*-

import thread
import transport
import msgpack
import error
from collections import OrderedDict
from utils import *
from log import logger
from request import Request


REQUEST_TYPE = 0
RESPONSE_TYPE = 1
NOTIFICATION_TYPE = 3


class BaseHandler(object):
    private_methods = list()

    def __init__(self, client):
        self.client = client


class BaseRPCClient(transport.BaseClient):
    def __init__(self, ws, handler_cls=BaseHandler):
        super(BaseRPCClient, self).__init__(ws=ws)
        self._packer = msgpack.Packer(encoding="utf-8")
        self._id_gen = NoSyncIDGenerator()
        self._unpacker = msgpack.Unpacker()
        self._handler_cls = handler_cls
        self._handler_obj = None
        self._requests = OrderedDict()

    def on_connected(self):
        self._handler_obj = self._handler_cls(self)

    def on_disconnected(self):
        for unfinished_result in self._requests.values():
            unfinished_result.finish()
        self._requests.clear()

    def on_read(self, msg):
        self._unpacker.feed(msg.data)
        for message in self._unpacker:
            if type(message) is list and len(message) in (3, 4):
                self.on_message(message)
                continue
            logger.warning('Unknown message = "%s"' % message)

    def on_message(self, message):
        if len(message) == 4 and message[0] == REQUEST_TYPE:
            self.on_request(message[1], message[2], message[3])
        elif len(message) == 4 and message[0] == RESPONSE_TYPE:
            self.on_response(message[1], message[2], message[3])
        elif len(message) == 3 and message[0] == NOTIFICATION_TYPE:
            self.on_notification(message[1], message[2])
        else:
            logger.warning('Unknown message = "%s"' % message)

    def on_response(self, msgid, error, result):
        request_obj = self._requests.pop(msgid, None)
        if request_obj:
            request_obj.set_result(result, error)
            return
        logger.warning("on_response: request id=%d not found" % msgid)

    @staticmethod
    def _exec_method(client, msgid, method, params):
        error_obj  = None
        result_obj =  None

        try:
            obj_method = getattr(client._handler_obj, method, None)
            if not obj_method:
                raise error.RPCRequestError(error.METHOD_NOT_FOUND, "Unknown method: %s" % method)

            private_methods = getattr(client._handler_obj, "private_methods", list())
            if method.startswith("_") or method in private_methods:
                raise error.RPCRequestError(error.METHOD_NOT_FOUND, "Private method: %s" % method)

            if not callable(obj_method):
                raise error.RPCRequestError(error.METHOD_NOT_FOUND, "Method not callable: %s" % method)

            result_obj = obj_method(*params)
        except error.RPCRequestError as e:
            error_obj = e.to_obj()

        except Exception as e:
            error_obj = error.RPCRequestError(error.INTERNAL_ERROR, str(e)).to_obj()

        finally:
            if client.connected and msgid is not None:
                logger.info('%s ----> %s. RESPONSE: msgid=%s, error="%s", result="%s"' %
                            (client.local_address[0], client.peer_address[0], msgid, error_obj, result_obj))
                client.send_message([RESPONSE_TYPE, msgid, error_obj, result_obj])

    def on_request(self, msgid, method, params):
        thread.start_new_thread(self._exec_method, (self, msgid, method, params))

    def on_notification(self, method, params):
        thread.start_new_thread(self._exec_method, (self, None, method, params))

    def send_message(self, message):
        data = self._packer.pack(message)
        return self.write(data)

    def call(self, method, *args):
        msgid = next(self._id_gen)
        request = Request()
        logger.info('%s ----> %s. REQUEST: msgid=%s, method="%s", args="%s"' %
                    (self.local_address[0], self.peer_address[0], msgid, method, args))
        self.send_message([REQUEST_TYPE, msgid, method, args])
        self._requests[msgid] = request
        return request

    def notify(self, method, *args):
        logger.info('%s ----> %s. NOTIFY: method="%s"' % (self.local_address, self.peer_address[0], method))
        return self.send_message([NOTIFICATION_TYPE, method, args])


class RPCClient(transport.Client, BaseRPCClient):
    def __init__(self, url, handler_cls=BaseHandler, heartbeat_freq=None):
        transport.Client.__init__(self, url, heartbeat_freq=heartbeat_freq)
        BaseRPCClient.__init__(self, ws=self._ws, handler_cls=handler_cls)


class RPCServerClient(transport.ServerClient, BaseRPCClient):
    def __init__(self, ws, server, handler_cls):
        transport.ServerClient.__init__(self, ws=ws, server=server)
        BaseRPCClient.__init__(self, ws=ws, handler_cls=handler_cls)


class RPCServer(transport.Server):
    def __init__(self, handler_cls=BaseHandler):
        super(RPCServer, self).__init__()
        self._handler_cls = handler_cls

    def _create_client(self, ws):
        return RPCServerClient(ws=ws, server=self, handler_cls=self._handler_cls)
