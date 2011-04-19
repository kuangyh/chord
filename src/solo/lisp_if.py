# -*- coding: utf-8 -*-

import lisp
import proc
import pycode
import context

def _parse_if(source):
    """Parse if chain into sections"""
    chain = []
    source_idx = 0
    while source_idx < len(source):
	node = source[source_idx]
	if node == lisp.Symbol('if'):
	    chain.append((source[source_idx + 1], []))
	    source_idx += 1
	elif node == lisp.Symbol('else'):
	    chain.append((None, []))
	else:
	    chain[-1][1].append(node)
	source_idx += 1
    return chain

def prim_if(compiler, source):
    chain = _parse_if(source)

    if_var = pycode.name('if_var')
    tpl = 'if $#:\n  %s = $#\n' % (if_var,)
    codes = [compiler.compile(chain[0][0]), compiler.compile_block(chain[0][1])]

    indent = ''
    for idx in xrange(1, len(chain)):
	curr_test, curr_body = chain[idx]
	if curr_test is None:
	    tpl += indent + 'else:\n'
	    tpl += indent + '  %s = $#\n' % (if_var,)
	    codes.append(compiler.compile_block(curr_body))
	    break
	else:
	    tpl += indent + 'else:\n'
	    tpl += indent + '  if $#:\n'
	    tpl += indent + '    %s = $#\n' % (if_var,)
	    indent += pycode.TAB
	    codes.extend([compiler.compile(curr_test), compiler.compile_block(curr_body)])
    tpl += if_var
    return pycode.create(tpl, *codes)

PRIMS = { 'if' : prim_if }
