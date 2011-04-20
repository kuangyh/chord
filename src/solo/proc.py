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
	curr_stat = ''

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
		tpl = 'if len(%s) < %d or $# != $#:\n  raise _ME(%s)\n%s' % (
			proc_var, len(car_part), proc_var, proc_var)
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
	    return self.compile_call(
		    (_S('#'),) + element[1:],
		    (element[0], _S('_'))).add_meta(raise_random = True)
	# Now all come to the structual matching
	return self.compile_pattern_struct(element)

    def compile_pattern(self, pattern):
	proc_var = lisp.env_curr()

	# Combine effect of each pattern element
	# Count metadata for caller
	shortcuts = []
	is_raise_random = False

	output = pycode.create(proc_var)
	for element in pattern:
	    code = self.compile_pattern_element(element)
	    if code.meta.get('shortcut_nop', False):
		continue
	    output += code

	    is_raise_random = is_raise_random or code.meta.get('raise_random', False)
	    if 'shortcut_equal' in code.meta:
		shortcut = ('equal', code.meta['shortcut_equal'])
	    elif 'shortcut_bind' in code.meta:
		shortcut = ('bind', code.meta['shortcut_bind'])
	    else:
		shortcut = (None, None)
	    shortcuts.append(shortcut)

	if len(shortcuts) == 0:
	    return output.add_meta(shortcut_nop = True)
 
	equals = [x[1] for x in shortcuts if x[0] == 'equal']
	if len(equals) == len(shortcuts):
	    return output.add_meta(shortcut_equal = equals[0])

	binds = [x[1] for x in shortcuts if x[0] == 'bind']
	if len(binds) == len(shortcuts):
	    join_binds = []
	    for item in binds:
		join_binds.extend(item)
	    return output.add_meta(shortcut_bind = join_binds, raise_random = is_raise_random)
	return output.add_meta(raise_random = is_raise_random) 

    def compile_section(self, proc_var, section, is_last):
	pattern_part, body_part = section
	proc_stack = context.curr().setdefault('PROC_STACK', [])
	lisp.env_push(proc_var)
    
	if pattern_part:
	    proc_stack.append('#')
	    pattern_code = self.compile_pattern(pattern_part)
            
	    if pattern_code.meta.get('raise_random', False) and (
                (not is_last) or (len(proc_stack) < 2 or proc_stack[-2] != '#')):
                # When compiled pattern code may raise random exception
                # And it's not the last one of matching chain or
                # The caller is call directely in a LISP environment (not in pattern matching)
                # It's the pattern matching code's responsibility to catch all exception
                # and turn it to _ME
		wrap_tpl = 'try:\n  $#\nexcept:\n  raise _ME(%s)\n%s' % (proc_var, proc_var)
		pattern_code = pycode.create(wrap_tpl, pattern_code)
	    proc_stack.pop()
	else:
	    pattern_code = pycode.create(proc_var, shortcut_nop = True)

	if body_part is None:
	    return pattern_code

	proc_stack.append('=>')
	body_tpl = 'try:\n  %s = $#\nexcept _ME, e:\n  raise _UME(%s)\n%s' % (
		proc_var, proc_var, proc_var)
	body_code = pycode.create(
		body_tpl, self.lisp_compiler.compile_block(body_part))
	proc_stack.pop()
	lisp.env_pop()
	return pattern_code + body_code

    def compile(self, proc_var, src):
        chain = Compiler.construct_chain(src)
        if not chain:
            return pycode.create(proc_var)
	if len(chain) == 1:
	    return self.compile_section(proc_var, chain[0], True)

        tpl = 'try:\n  $#\n'
	indent = ''
        for i in xrange(len(chain) - 2):
	    tpl += indent + 'except _ME:\n'
	    tpl += indent + '  try:\n'
	    tpl += indent + '    $#\n'
	    indent += pycode.TAB
	tpl += indent + 'except _ME:\n'
	tpl += indent + '  $#\n'
	tpl += proc_var
	section_codes = [self.compile_section(proc_var,  chain[0], False)]
	section_codes.extend([
	    self.compile_section(proc_var, x, False)
	    for x in chain[1:-1]])
	section_codes.append(self.compile_section(proc_var, chain[-1], True))
	return pycode.create(tpl, *section_codes)

    def compile_call(self, proc_src, argument):
	if type(argument) is not pycode.Code:
	    argument = self.compile_lisp(argument)
	proc_var = pycode.name('proc_var')
	return pycode.create(
		'%s = $#\n$#\n%s' % (proc_var, proc_var),
		argument,
		self.compile(proc_var, proc_src))


def pattern_ext_not(compiler, element):
    proc_var = lisp.env_curr()
    matched_var = pycode.name('switch')
    tpl = """\
try:
  $#
  %s = False
except _ME:
  %s = True
if not %s:
  raise _ME, %s
%s""" % (matched_var, matched_var, matched_var, proc_var, proc_var)
    return pycode.create(tpl, compiler.compile(proc_var, element[1]))

def pattern_ext_all(compiler, element):
    proc_var = lisp.env_curr()
    element_var = pycode.name('pattern_all')
    tpl = 'for %s in %s:\n  $#\n%s' % (element_var, proc_var, proc_var)
    return pycode.create(tpl, compiler.compile(element_var, element[1]))

def pattern_ext_some(compiler, element):
    proc_var = lisp.env_curr()
    element_var = pycode.name('pattern_some')
    matched_var = pycode.name('switch')
    tpl = \
	    '%s = False\n' % (matched_var,) + \
	    'for %s in %s\n' % (element_var, proc_var) + \
	    '  try:\n' + \
	    '    $#\n' + \
	    '    %s = True\n' % (matched_var,) + \
	    '    break\n' + \
	    '  except _ME:\n' + \
	    '    continue\n' + \
	    'if not %s:\n' % (matched_var,) + \
	    '  raise _ME, %s\n' % (proc_var,) + \
	    proc_var
    return pycode.create(tpl, compiler.compile(element_var, element[1]))

Compiler.EXTS.update({
    'not' : pattern_ext_not,
    'all' : pattern_ext_all,
    'some' : pattern_ext_some })
