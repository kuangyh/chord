# -*- coding: utf-8 -*-

import lisp
import proc
import pycode
import context

"""
Prims for defining function
"""

def _parse_arglist(arglist):
    args = []
    kwargs = []
    kwargs_source = []
    idx = 0
    while idx < len(arglist):
        curr = arglist[idx]
	if type(curr) is lisp.Symbol and curr.name in ('.', '..'):
	    args.append(curr.name.replace('.', '*') + arglist[idx + 1].name)
	    idx += 1
        elif type(curr) is lisp.Symbol:
            args.append(curr.name)
        elif lisp.getop(curr) == ':':
            if type(curr[1]) is not lisp.Symbol:
                raise SyntaxError, arglist
            kwargs.append(curr[1].name)
            kwargs_source.append(arglist[idx + 1])
            idx += 1
        else:
            raise SyntaxError, arglist
        idx += 1
    return args, kwargs, kwargs_source

def compile_fn(compiler, fn_name, arglist, body):
    if fn_name is None:
        fn_name = pycode.name('fn')
    args, kwargs, kwargs_source = _parse_arglist(arglist)
    kwargs_codes = map(compiler.compile, kwargs_source)
    arglist_tpl = ','.join(list(args) + [x + '=$#' for x in kwargs])
    tpl = 'def %s(%s):\n  return $#\n%s' % (fn_name, arglist_tpl, fn_name)
    with context.Context():
        body_code = compiler.compile_block(body)
    return pycode.create(tpl, *(kwargs_codes + [body_code]))

def prim_fn(compiler, source):
    return compile_fn(compiler, None, source[1], source[2:])

def prim_def(compiler, source):
    fn_name = lisp.getop(source[1])
    if fn_name is not None:
        return compile_fn(compiler, fn_name, source[1][1:], source[2:])
    else:
        return compiler.compile((lisp.Symbol('='),) + source[1:])

def prim_return(compiler, source):
    return pycode.create('return $#\nNone', compiler.compile(source))

def prim_proc(compiler, source):
    proc_name = pycode.name('proc')
    tpl = 'def %s(%s_in):\n  return $#\n%s' % (proc_name, proc_name, proc_name)
    with context.Context():
        proc_compiler = proc.Compiler(compiler)
        return pycode.create(tpl, proc_compiler.compile(proc_name + '_in', source))

PRIMS = {
    'fn' : prim_fn,
    'def' : prim_def,
    'return' : prim_return,
    '#' : prim_proc,
    '=>' : prim_proc }

