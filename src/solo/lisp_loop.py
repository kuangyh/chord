# -*- coding: utf-8 -*-

import lisp
import proc
import pycode
import context

def prim_loop(compiler, src):
    if src[2] != lisp.Symbol('<-'):
	raise SyntaxError, src[:3]
    loop_binding = src[1]
    loop_init = src[3]
    loop_body = src[4:]
    
    loop_name = pycode.name('loop')
    context.curr().setdefault('LOOP_STACK', []).append(loop_name)

    tpl = \
	    '%s = $#\n' % (loop_name,) + \
	    'while True:\n' + \
	    '  try:\n' + \
	    '    $#\n' + \
	    '  except _ME:\n' + \
	    '    break\n' + \
	    '  $#\n' + \
	    '  break\n' + \
	    loop_name

    output_code = pycode.create(
	    tpl,
	    compiler.compile(loop_init),
	    compiler.compile((lisp.Symbol('='), loop_binding, lisp.Symbol(loop_name))),
	    compiler.compile_block(loop_body))
    context.curr()['LOOP_STACK'].pop()
    return output_code

def prim_cont(compiler, src):
    if len(src) == 1:
	return pycode.create('continue\nNone')
    loop_name = context.curr()['LOOP_STACK'][-1]
    return pycode.create(
	    '%s = $#\ncontinue\n%s' % (loop_name, loop_name),
	    compiler.compile(src[1]))

def prim_break(compiler, src):
    if len(src) == 1:
	return pycode.create('break\nNone')
    loop_name = context.curr()['LOOP_STACK'][-1]
    return pycode.create(
	    '%s = $#\nbreak\n%s' % (loop_name, loop_name),
	    compiler.compile(src[1]))


PRIMS = { 
	'loop' : prim_loop,
	'cont' : prim_cont,
	'break' : prim_break }

