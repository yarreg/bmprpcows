# -*- encoding: utf-8 -*-

import re
import hooks
from log import logger
from time import sleep, time
from collections import OrderedDict
from urlparse import parse_qs
from ws4py.server.geventserver import WSGIServer
from ws4py.websocket import WebSocket
from ws4py.server.geventserver import WebSocketWSGIApplication
from ws4py.client.geventclient import WebSocketClient
from ws4py.exc import HandshakeError


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
        self._ws.unhandled_error = self._unhandled_error

    def _unhandled_error(self, e):
        if not self._ws.sock:
            return
        logger.exception("Failed to receive data")

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
        if 'ws4py.socket' in self._ws.environ:
            self._ws.send(data, binary=True)
        else:
            self._ws._write(data)
        self.on_write(data)

    def disconnect(self, code=1000, reason=''):
        if 'ws4py.socket' in self._ws.environ:
            self._ws.close(code, reason)
        else:
            self._ws.close_connection()

    @property
    def connected(self):
        return self._connected


class Client(BaseClient):
    def __init__(self, url, heartbeat_freq=None):
        WrappedWebSocketClient = hooks.create_class(WebSocketClient)
        ws = WrappedWebSocketClient(url, protocols=["http-only", "chat"], heartbeat_freq=heartbeat_freq)
        super(Client, self).__init__(ws=ws)

    def connect(self):
        if not self.connected:
            self._ws.connect()
            self._connected = True


class ServerClient(BaseClient):
    def __init__(self, ws, server):
        self.server = server
        super(ServerClient, self).__init__(ws=ws)

    @property
    def query(self):
        return parse_qs(self._ws.environ.get('QUERY_STRING', ''))

    @property
    def path(self):
        return self._ws.environ.get('PATH_INFO')


class Server(object):
    def __init__(self):
        self._wsgi_app = None
        self._clients  = OrderedDict()

    def on_connected(self, client):
        self._clients[client] = time()

    def on_disconnected(self, client):
        self._clients.pop(client, None)

    def on_handshake_error(self, client, exc):
        raise exc

    @property
    def clients(self):
        return self._clients.keys()

    def write(self, data):
        for client in self.clients:
            client.write(data)

    def _create_client(self, ws):
        return ServerClient(ws=ws, server=self)

    def _handler_factory(self, *args, **kwargs):
        WrappedWebSocket = hooks.create_class(WebSocket)
        ws = WrappedWebSocket(*args, **kwargs)

        client = self._create_client(ws)
        ws.after_call("opened", lambda: self.on_connected(client))
        ws.after_call("closed", lambda *a, **kw: self.on_disconnected(client))

        return ws

    def get_wsgi_application(self):
        def wrapper(ws_app, environ, start_response):
            try:
                ws_app(environ, start_response)
            except HandshakeError as he:
                sock   = environ['wsgi.input'].rfile._sock
                ws     = self._handler_factory(sock, environ=environ)
                client = self._create_client(ws)
                self.on_handshake_error(client, he)
            return []

        if not self._wsgi_app:
            ws_app = WebSocketWSGIApplication(handler_cls=self._handler_factory)
            self._wsgi_app = lambda *args: wrapper(ws_app, *args)

        return self._wsgi_app

    def listen(self, host, port):
        server = WSGIServer((host, port), self.get_wsgi_application())
        server.serve_forever()


def run_server(host, port, routes):
    compiled_routes = [(re.compile(route), app) for route, app in routes]

    def router(environ, start_response):
        query_path = environ.get('PATH_INFO', '')
        for route, app in compiled_routes:
            if route.match(query_path):
                if hasattr(app, 'get_wsgi_application'):
                    app = app.get_wsgi_application()
                return app(environ, start_response)

        start_response("404 Not Found", [('Content-type', 'text/plain')])
        return []

    server = WSGIServer((host, port), router)
    server.serve_forever()

