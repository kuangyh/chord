# -*- coding: utf-8 -*-

"""
Fundermantal prims for a lisp compiler
"""
import lisp
import proc
import pycode

def prim_quote(compiler, src):
    return pycode.create('$#', src[1])

def prim_struct_quote(compiler, src):
    return compiler.prims['.struct'](compiler, src[1])



def is_prop_fetch(src):
    if type(src) is not tuple:
	return False
    if proc.is_proc(src):
	return False
    for idx in xrange(len(src) - 1, 0, -1):
	if src[idx] == Symbol('=>'):
	    return False
	if src[idx] == Symbol('|'):
	    return True
    return False


def prim_assign(compiler, src):
    if type(src[1]) is lisp.Symbol:
	value_code = compiler.compile(src[2])
        return pycode.create('%s=$#\n%s' % (src[1].name, src[1].name), value_code)
    elif is_prop_fetch(src[1]):
	value_code = compiler.compile(src[2])
	if not pycode.Code.is_expr_pure(value_code.value):
	    value_code = value_code.asname(pycode.name())
	sym_code = compiler.compile(src[1])
	# NOTE: Note that pycode tempalte dosen't work here
	# Because theres to code is not arguments to one expression
	stat_lines = (sym_code.stat, value_code.stat,
		      '%s = %s' % (sym_code.value, value_code.value))
	stat = '\n'.join([x for x in stat_lines if x])
	return pycode.Code(stat, value_code.value)
    else:    
        pattern_compiler = proc.Compiler(compiler)
	return pattern_compiler.compile_call(src[1], src[2])

def prim_begin(compiler, src):
    return compiler.compile_block(src[1:])

def prim_print(compiler, src):
    return pycode.create('print $#\nNone', compiler.compile(src[1]))

def prim_global(compiler, src):
    return pycode.create('global ' + ','.join([x.name for x in src[1:]]) + '\nNone')

def prim_env(compiler, src):
    env_name = pycode.name('env')
    env_code = compiler.compile(src[1]).asname(env_name)
    lisp.env_push(env_name)
    body_code = compiler.compile_block((lisp.Symbol('_'),) + src[2:])
    lisp.env_pop()
    return env_code + body_code

def prim_import(compiler, src):
    if isinstance(src[1], lisp.Symbol):
	import_expr = src[1].name
    else:
	import_expr = str(src[1])
    return pycode.create('import %s\nNone' % (import_expr,))

PRIMS = {
    '\'' : prim_quote,
    '`' : prim_struct_quote,
    '=' : prim_assign,
    'begin' : prim_begin,
    'print' : prim_print,
    'global' : prim_global,
    'env' : prim_env,
    'import' : prim_import }

##########################################
# Math OPS
# FIXME: ops is not 1st class in solisp
##########################################
OP_MAPPING = {}

def prim_infix(compiler, src):
    op_name = src[0].name
    if op_name != '-':
	op_name = op_name.replace('-', ' ')
    op_name = OP_MAPPING.get(op_name, op_name)

    tpl = '(' + (') %s (' % (op_name,)).join(['$#'] * (len(src) - 1)) + ')'
    codes = map(compiler.compile, src[1:])
    return pycode.create(tpl, *codes)

def prim_prefix(compiler, src):
    op_name = OP_MAPPING.get(src[0].name, src[0].name.replace('-', ' '))
    return pycode.create('%s($#)' % (op_name,), compiler.compile(src[1]))

def update_infix(*ls):
    for item in ls:
        PRIMS[item] = prim_infix
def update_prefix(*ls):
    for item in ls:
        PRIMS[item] = prim_prefix

# Math
update_infix('+', '-', '*', '/', '%', '//', '**')
# Compare
update_infix('==', '>', '<', '>=', '<=', '!=')
# Bit wise
update_infix('<<', '>>', '&', '^', '|')
# Logic
update_infix('and', 'or', 'in', 'not-in', 'is', 'is-not')
update_prefix('not', '~')
    
