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

pipe = Pipe
