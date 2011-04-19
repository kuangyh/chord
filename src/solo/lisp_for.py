# -*- coding: utf-8 -*-

import lisp
import proc
import pycode
import context

def prim_for(compiler, src):
    if lisp.Symbol('<-') != src[2]:
	raise SyntaxError(src[:3])

    matcher = src[1]
    datasource = src[3]
    body = src[4:]

    queue_name = pycode.name('for_queue')
    context.curr().setdefault('FOR_STACK', []).append(queue_name)

    if type(matcher) is lisp.Symbol:
	tpl = '%s = []\nfor %s in $#:\n  %s.append($#)\n%s' % (
		queue_name, matcher.name, queue_name, queue_name)
	datasource_code = compiler.compile(datasource)
	if body:
	    body_code = compiler.compile((lisp.Symbol('env'), matcher) + body)
	else:
	    body_code = pycode.create(matcher.name)
	output_code = pycode.create(tpl, datasource_code, body_code)
    else:
	datasource_code = compiler.compile(datasource)
	if datasource_code.value == '_':
	    datasource_code = datasource.asname(pycode.name())
	
	for_var = pycode.name('for_var')
	proc_compiler = proc.Compiler(compiler)
	matcher_code = proc_compiler.compile(for_var, matcher)

	tpl = \
		'%s = []\n' % (queue_name,) + \
		'for %s in $#:\n' % (for_var,) + \
		'  try:\n' + \
		'    $#\n' + \
		'  except _ME, e:\n' + \
		'    continue\n' + \
		'  %s.append($#)\n' % (queue_name,) + \
		queue_name

	if body:
	    body_code = compiler.compile(
		    (lisp.Symbol('env'), lisp.Symbol(matcher_code.value)) + body)
	else:
	    body_code = pycode.create(matcher_code.value)
	output_code = pycode.create(tpl, datasource_code, matcher_code, body_code)
    context.curr()['FOR_STACK'].pop()
    return output_code

def prim_emit(compiler, src):
    queue_name = context.curr()['FOR_STACK'][-1]
    return pycode.create('%s.extend($#)\nNone' % (queue_name,), compiler.compile(list(src[1:])))

def prim_emit_many(compiler, src):
    queue_name = context.curr()['FOR_STACK'][-1]
    return pycode.create('%s.extend($#)\nNone' % (queue_name,), compiler.compile(src[1]))

PRIMS = {
    'for' : prim_for,
    'emit' : prim_emit,
    'emit*' : prim_emit_many }
