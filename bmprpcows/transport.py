# -*- encoding: utf-8 -*-

import hooks
from time import sleep, time
from collections import OrderedDict
from ws4py.server.geventserver import WSGIServer
from ws4py.websocket import WebSocket
from ws4py.server.geventserver import WebSocketWSGIApplication
from ws4py.client.geventclient import WebSocketClient


class BaseClient(object):
    def __init__(self, ws):
        self._connected = False
        self._ws = ws
        self._ws.remove_call_hooks()
        self._ws.after_call("opened", self.on_connected)
        self._ws.after_call("opened", lambda: setattr(self, "_connected", True))
        self._ws.after_call("closed", lambda *a, **kw: setattr(self, "_connected", False))
        self._ws.after_call("closed", lambda *a, **kw: self.on_disconnected())
        self._ws.after_call("received_message", lambda m: self.on_read(m))

    @property
    def local_address(self):
        return self._ws.local_address

    @property
    def peer_address(self):
        return self._ws.peer_address

    def on_connected(self):
        pass

    def on_disconnected(self):
        pass

    def on_read(self, msg):
        pass

    def on_write(self, data):
        pass

    def write(self, data):
        self._ws.send(data, binary=True)
        self.on_write(data)

    def connect(self):
        pass

    def disconnect(self):
        self._ws.close()

    @property
    def connected(self):
        return self._connected


class Client(BaseClient):
    def __init__(self, url, heartbeat_freq=None):
        WrappedWebSocketClient = hooks.create_class(WebSocketClient)
        ws = WrappedWebSocketClient(url, protocols=["http-only", "chat"])
        # TODO: add in constructor when this commit will be in release
        # https://github.com/Lawouach/WebSocket-for-Python/commit/3befaef6d279e84d9bbf7ee1c4d2c61980d45b95
        ws.heartbeat_freq = heartbeat_freq 
        super(Client, self).__init__(ws=ws)

    def connect(self):
        if not self.connected:
            self._ws.connect()
            self._connected = True


class ServerClient(BaseClient):
    def __init__(self, ws, server):
        self.server = server
        super(ServerClient, self).__init__(ws=ws)


class Server(object):
    def __init__(self):
        self._clients = OrderedDict()

    def on_connected(self, client):
        self._clients[client] = time()

    def on_disconnected(self, client):
        self._clients.pop(client, None)

    @property
    def clients(self):
        return self._clients.keys()

    def write(self, data):
        for client in self.clients:
            client.write(data)

    def _create_client(self, ws):
        return ServerClient(ws=ws, server=self)

    def _client_factory(self, *args, **kwargs):
        WrappedWebSocket = hooks.create_class(WebSocket)
        ws = WrappedWebSocket(*args, **kwargs)

        client = self._create_client(ws)
        ws.after_call("opened", lambda: self.on_connected(client))
        ws.after_call("closed", lambda *a, **kw: self.on_disconnected(client))

        return ws

    def listen(self, host, port):
        server = WSGIServer((host, port), WebSocketWSGIApplication(handler_cls=self._client_factory))
        server.serve_forever()



