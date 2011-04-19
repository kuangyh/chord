# -*- coding: utf-8 -*-

import lisp
import pycode

def prim_class(compiler, source):
    class_name = source[1].name
    if len(source) > 2 and lisp.getop(source[2]) == ':':
	extends = [x.name for x in source[2][1:]]
	block = source[3:]
    else:
	extends = ['object']
	block = source[2:]

    tpl = 'class %s(%s):\n' % (class_name, ','.join(extends))
    if block:
	tpl += '  $#\n' + class_name
	return pycode.create(tpl, compiler.compile_block(block))
    else:
	tpl += '  pass\n' + class_name
	return pycode.create(tpl)

PRIMS = { 'class' : prim_class }

