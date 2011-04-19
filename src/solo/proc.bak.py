# -*- coding: utf-8 -*-

import lisp
import pycode
import context

# _S for Symbol construction, same with generated code

_S = lisp.Symbol

class MatchException(Exception): pass
_ME = MatchException
class UncatchedMatchException(Exception): pass
_UME = UncatchedMatchException

def is_proc(node):
    return lisp.getop(node) in ('#', '=>')

class Compiler(object):
    EXTS = {}

    def __init__(self, lisp_compiler):
        self.lisp_compiler = lisp_compiler
        self.compile_lisp = self.lisp_compiler.compile

    @staticmethod
    def construct_chain(src):
        if not is_proc(src):
            src = (_S('#'), src)
	chain = []
	for element in src:
	    if type(element) is _S:
		op = element.name
	    else:
		op = None

	    if op == '#':
		chain.append({})
		curr_stat = '#'
	    elif op == '=>':
		if curr_stat != '#':
		    chain.append({})
		curr_stat = '=>'
	    else:
		chain[-1].setdefault(curr_stat, []).append(element)
	return [(x.get('#'), x.get('=>')) for x in chain]

    @staticmethod
    def get_binding(item):
	"""
	Detect whether the item can be left side of assignment statement in Python
	Return (bind_python_expr, may_raise)
	"""
	if type(item) is _S:
	    if item.name in ('_', '.'):
		# Reserved name used in pattern matching
		return None, False
	    return item.name, False

	if type(item) is list:
	    # May be a Python structual matching if all it's element is legal binding
	    output = []
	    for el in item:
		bind_expr, unused = Compiler.get_binding(el)
		if bind_expr is None:
		    return None, False
		output.append(bind_expr)
	    # Return python structual matching
	    return '(' + ','.join(output) + ',)', True
	# Other cases, not binding
	return None, False

    def compile_test(self, *exprs):
	proc_var = lisp.env_curr()
	tpl = 'if not ($#):\n  raise _ME()\n%s' % (proc_var,) 
	source = (_S('and'),) + tuple(exprs)
	test_code = self.compile_lisp(source)
	return pycode.create(
		tpl, test_code, shortcut_guards = list(exprs))

    def compile_equal(self, value):
	return self.compile_test((_S('=='), value, _S('_'))).add_meta(
		shortcut_equal = value)
   

    def compile_pattern_struct(self, source):
	proc_var = lisp.env_curr()

	if type(source) is not list or len(source) < 1:
	    return self.compile_equal(source)

	if len(source) >= 2 and source[-2] == _S('.'):
	    car_part = source[:-2]
	    cdr_part = source[-1]
	else:
	    car_part = source
	    cdr_part = _S('_')
	if not car_part:
	    return self.compile(cdr_part)

	# Compile each element, do special handling with equal and bind shortcuts
	equal_elements = []
	bind_elements = []
	custom_elements = []
	is_need_wrap = [False]

	def handle_element_code(idx_expr, src_var, element_code):
	    is_need_wrap[0] = is_need_wrap[0] or \
		    element_code.meta.get('raise_random', False)
	    if 'shortcut_nop' in element_code.meta:
		pass
	    elif 'shortcut_equal' in element_code.meta:
		equal_elements.append((idx_expr, element_code))
	    elif 'shortcut_bind' in element_code.meta:
		bind_elements.append((idx_expr, element_code))
	    else:
		custom_elements.append((idx_expr, src_var, element_code))

	for element_idx in xrange(len(car_part)):
	    idx_expr = '%s[%d]' % (proc_var, element_idx,)
	    src_var = '%s_%d' % (proc_var, element_idx)
	    element_code = self.compile(src_var, car_part[element_idx])
	    handle_element_code(idx_expr, src_var, element_code)
	# Handle cdr_expr as the same
	if len(car_part) < len(source):
	    cdr_expr = '%s[%d:]' % (proc_var, len(car_part),)
	    src_var = proc_var + '_cdr'
	    cdr_code = self.compile(src_var, cdr_part)
	    handle_element_code(cdr_expr, src_var, cdr_code)

	# Shortcut: if all element is equal check
	# Treat as a equal check of whole
	if len(equal_elements) == len(source):
	    return self.compile_equal(source)

	code = pycode.create(proc_var).add_meta(shortcut_nop = True)
	# Compile equal_elemens and length check
	if equal_elements:
	    fetch_part = '(' + ','.join([x[0] for x in equal_elements]) + ',)'
	    equal_data = tuple(x[1].meta['shortcut_equal'] for x in equal_elements)
	    if len(car_part) == len(source):
		tpl = 'if len(%s) != %d or $# != $#:\n  raise _ME(%s)\n%s' % (
			proc_var, len(car_part), proc_var, proc_var)
	    else:
		tpl = 'if $# != $#:\n  raise _ME(%s)\n%s' % (proc_var, proc_var)
	    code += pycode.create(tpl, equal_data, pycode.create(fetch_part))
	elif len(car_part) == len(source):
	    code += pycode.create('if len(%s) != %d:\n  raise _ME(%s)\n%s' % (
		proc_var, len(car_part), proc_var, proc_var))
	else:
	    code += pycode.create('if len(%s) < %d:\n  raise _ME(%s)\n%s' % (
		proc_var, len(car_part), proc_var, proc_var))
	    
	for bind_idx, bind_code in bind_elements:
	    code += pycode.create('%s=%s\n%s' %
		    ('='.join(bind_code.meta['shortcut_bind']), bind_idx, proc_var))

	if custom_elements:
	    for source_idx, src_var, element_code in custom_elements:
		code += pycode.create('%s = %s\n%s' % (src_var, source_idx, src_var))
		code += element_code
	return code.add_meta(raise_random = is_need_wrap[0])


    def compile_pattern_element(self, element):
	proc_var = lisp.env_curr()

	# '_' is a blank space holder that do nothing
	if element == _S('_'):
	    return pycode.create(proc_var, shortcut_nop = True)

	# Name binding
	bind_to, may_raise = Compiler.get_binding(element)
	if bind_to is not None:
	    return pycode.create(
		    '%s=%s\n%s' % (bind_to, proc_var, proc_var),
		    shortcut_bind = [bind_to],
		    raise_random = may_raise)

	opname = lisp.getop(element)
	# Force equal testing
	if opname == '\'':
	    return self.compile_equal(element[1])

	# Type checking
	if opname == ':':
	    # NOTE: infact, type checking expression could throw exception
	    return self.compile_test((_S('isinstance'), _S('_'), element[1]))

	if opname == '?':
	    return self.compile_test(*element[1:]).add_meta(raise_random = True)

	# Expanded matchings
	if opname in self.EXTS:
	    return self.EXTS[opname](self, element)

	# Extractor
	if type(element) is tuple and len(element) > 0:
	    return self.compile_call(element[1], (element[0], _S('_'))).add_meta(
