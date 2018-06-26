# -*- encoding: utf-8 -*-

from gevent import monkey; monkey.patch_all()
from bmprpcows import *


class H(BaseHandler):
    def test(self):
        return "hello"

s = RPCServer(handler_cls=H)
s.listen("127.0.0.1", 9091, '/test/ws')