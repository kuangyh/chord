# -*- coding: utf-8 -*-

"""
Builtin library
"""

class Pipe(object):
    def __init__(self, *funcs):
	self.funcs = funcs

    def __call__(self, value):
	for func in self.funcs:
	    value = func(value)
	return value

def u(src):
    if isinstance(src, unicode):
	return src
    elif isinstance(src, str):
	return src.decode('utf-8')
    else:
	return str(src).decode('utf-8')
