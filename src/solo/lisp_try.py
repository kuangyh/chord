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

    for item in source[1:]:
	if lisp.getop(item) == 'except':
	    if not type(item[1]) is tuple and len(item[1]) == 2 and (
		    type(item[1][0]) is lisp.Symbol and
		    type(item[1][1]) is lisp.Symbol):
		raise SyntaxError, item
	    curr_stat = 'except'
	    (except_blocks.append((item[1][0].name, item[1][1].name, item[2:])))
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
    for type_sym, bind_sym, code in except_blocks:
	output_tpl += 'except %s, %s:\n  %s = $#\n' % (
		type_sym, bind_sym, try_var)	
	output_codes.append(compiler.compile_block(code))
    if finally_block:
	output_tpl += 'finally:\n  $#\n'
	output_codes.append(compiler.compile_block(finally_block))
    output_tpl += try_var
    return pycode.create(output_tpl, *output_codes)

def prim_raise(compiler, source):
    return pycode.create('raise $#\nNone', compiler.compile(source[1]))

PRIMS = { 'try' : prim_try, 'raise' : prim_raise }
