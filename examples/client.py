# -*- encoding: utf-8 -*-

from gevent import monkey; monkey.patch_all()
from bjson_wsrpc import *
from time import sleep


c = RPCClient("ws://127.0.0.1:9091")
c.connect()
print c.call("test").get()
#print c.call("test").get()
sleep(5)