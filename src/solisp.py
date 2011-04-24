#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Command-line tools to compile SoLISP code
"""

import os
from solo import lisp, pycode, context

###############################
# Dealing with file system
###############################

def search_compile_files(packages, compile_all = False):
    """Find files to compile"""
    def get_mtime(path):
	try:
	    return os.stat(path).st_mtime
	except OSError, e:
	    return 0

    compile_queue = []
    for package_path in packages:
	for basedir, dirs, files in os.walk(package_path):
	    for filename in files:
		# FIXME: better extension name?
		if not filename.endswith('.lisp'):
		    continue
		source_filename = os.path.normpath(os.path.join(basedir, filename))
		dest_filename = source_filename[:-5] + '.py'		
		if compile_all or get_mtime(source_filename) > get_mtime(dest_filename):
		    compile_queue.append((source_filename, dest_filename))
    return compile_queue

def dump_code(filename, code):
    f = open(filename, 'w')
    f.write(code.stat)
    if not pycode.Code.is_expr_pure(code.value):
	f.write('\n' + code.value)
    f.write('\n')
    f.close()


#############################################
# Extensible prims and macros infrastructure
#############################################

def load_module(name):
    sections = name.split('.')
    curr = __import__(name)
    for section in sections[1:]:
	curr = getattr(curr, section)
    return curr

def load_prims(*modules):
    prims = {}
    for module in modules:
	prims.update(getattr(load_module(module), 'PRIMS', {}))
    return prims

def load_macros(*modules):
    macros = {}
    for module in modules:
	macros.update(getattr(load_module(module), 'MACROS', {}))
    return macros



######################################################
# Compiler
######################################################

FILE_TPL = """\
# -*- coding: utf-8 -*-
from solo import _S, _ME, _UME
from solo.builtin_lib import *

$#
"""

def compile_packages(macro_expander, compiler, packages, compile_all = False):
    for src_filename, dst_filename in search_compile_files(packages, compile_all):
	source = lisp.PARSER.parseall(open(src_filename).read().decode('utf-8'))
	source = macro_expander.compile(source)
	with context.Context():
	   code = pycode.create(FILE_TPL, compiler.compile_block(source))
	dump_code(dst_filename, code)


def init_compiler(prim_modules, macro_dir):
    prims = load_prims(*prim_modules)
    compiler = lisp.Compiler(prims)

    macros = {}
    expander = lisp.MacroExpander({})
    compile_packages(expander, compiler, [macro_dir], True)
    # Load Macros
    for basedir, dirs, files in os.walk(macro_dir):
	for filename in files:
	    if not filename.endswith('.py'):
		continue
	    module = os.path.normpath(os.path.join(macro_dir, filename[:-3])).replace('/', '.')
	    macros.update(load_macros(module))
    return lisp.MacroExpander(macros), compiler

def interpreter(expander, compiler, debug = False):
    import readline
   
    env = {}
    exec """\
from solo import _S, _ME, _UME
from solo.builtin_lib import *
""" in env
    with context.Context():
        while True:
	    source = raw_input('> ')

	    try:
		source = lisp.PARSER.parseall(source.strip() + '\n')
		if not source:
		    continue
		source = expander.compile(source)
		if debug:
		    print ';; Expand:', lisp.repr_data(source)
		code = compiler.compile_block(source)
		if debug:
		    lines = []
		    if code.stat:
			lines.extend(code.stat.split('\n'))
		    lines.append(code.value)
		    print ';; Compiled:'
		    for line in lines:
			print ';;', line
	    except BaseException, e:
		print 'Compile error, %s' % (repr(e),)
		continue
	    try:
		run_code = code.stat + '\nprint \'=>\', repr(%s)' % (code.value,)
		exec run_code in env
	    except BaseException, e:
		print 'Runtime error, %s' % (repr(e),)
		continue

PRIM_MODULES = [
    'solo.lisp_prims', 'solo.lisp_for', 'solo.lisp_loop',
    'solo.lisp_if', 'solo.lisp_fn', 'solo.lisp_try', 'solo.lisp_class' ]

if __name__ == '__main__':
    import sys
    expander, compiler = init_compiler(PRIM_MODULES, 'macros')
    if len(sys.argv) == 1:
	interpreter(expander, compiler, True)
    else:
        compile_packages(expander, compiler, sys.argv[1:], True)


