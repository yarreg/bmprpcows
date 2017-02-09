# -*- encoding: utf-8 -*-

import re
import ast
from setuptools import setup


def get_module_info(mod_name):
    info = dict()
    with open("%s/__init__.py" % mod_name) as f:
        for line in f:
            ret = re.match(r"^__(.*)__", line)
            if ret:
                value = ast.parse(line).body[0].value.s
                info[ret.group(1)] = value
    return info


mod_name = "bmprpcows"
mod_info = get_module_info(mod_name)

setup(
    name=mod_info.get("name", mod_name),
    version=mod_info.get("version"),
    description="Bidirectional MSGPACK-RPC protocol implementation over WebSocket",
    long_description=mod_info.get("doc", mod_name),
    author=mod_info.get("author", mod_name),
    packages=[mod_info.get("name", mod_name)],
    license="MIT",
    platforms="any",
    zip_safe=False,
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Topic :: Communications",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Object Brokering",
        "Programming Language :: Python :: 2.7",
    ],
    install_requires=[
        "ws4py>=0.3.5",
        "msgpack-python>=0.4.8"
    ],
)


