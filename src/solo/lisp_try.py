# -*- coding: utf-8 -*-

import lisp
import proc
import pycode
import context

"""
Try ... except ... finally
"""

def prim_try(compiler, source):
    curr_stat = 'try'

    # Step 1: Parse the list
    try_block = []
    except_blocks = []
    finally_block = []

    try_var = pycode.name('try')
    exc_var = pycode.name('exc')

    for item in source[1:]:
	if lisp.getop(item) == 'except':
	    if type(item[1]) != lisp.Symbol:
		raise SyntaxError, item
	    curr_stat = 'except'
	    (except_blocks.append((item[1].name, item[2:])))
	elif lisp.getop(item) == 'finally':
	    finally_block.extend(item[1:])
	else:
	    if curr_stat != 'try':
		raise SyntaxError, source
	    try_block.append(item)

    if not except_blocks and not finally_block:
	raise SyntaxError, source

    # Try part
    output_tpl = 'try:\n  %s = $#\n' % (try_var,)
    output_codes = [compiler.compile_block(try_block)]
    # Except part
    lisp.env_push(exc_var)
    for type_sym, code in except_blocks:
	output_tpl += 'except %s:\n  %s = $#\n' % (exc_var, try_var)
	output_codes.append(compiler.compile_block(code))
    lisp.env_pop()
    if finally_block:
	output_tpl += 'finally:\n  $#\n'
	output_codes.append(compiler.compile_block(finally_block))
    output_tpl += try_var
    return pycode.create(output_tpl, *output_codes)

def prim_raise(compiler, source):
    return pycode.create('raise $#\nNone', compiler.compile(source[1]))

PRIMS = { 'try' : prim_try, 'raise' : prim_raise }
