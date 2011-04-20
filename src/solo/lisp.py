# -*- coding: utf-8 -*-

"""
Compiler, LISP model
"""

####################################
# Customizing parser
####################################
import sexpr
import pycode
import context

class Symbol(object):
    def __init__(self, name):
        self.name = name

    def __eq__(self, other):
	return type(self) == type(other) and self.name == other.name

    def __ne__(self, other):
	return not (self == other)

    def __repr__(self):
        return '_S(%s)' % (repr(self.name),)

    @staticmethod
    def parse_sexpr(src):
	if src in ('True', 'False', 'None'):
	    return eval(src)
	else:
	    return Symbol(src)

class KVStream(list):
    @classmethod
    def from_source(cls, src):
        if len(src) % 2 != 0:
            raise ValueError, 'Invalid KVStream %s' % (src,)

        output = cls()
        for idx in xrange(0, len(src), 2):
            output.append((src[idx], src[idx + 1]))
        return output

    def __repr__(self):
        return repr(dict(self))


parser_types = {
        'num' : eval,
	'str' : lambda x: eval('u' + x),
        'sym' : Symbol.parse_sexpr,
        'tuple' : tuple,
        'list' : list,
        'dict' : KVStream.from_source,
        '' : lambda x: x}

def prefix_rewrite(prefixes):
    output = {}
    def make_rewrite(c):
        return lambda x: (Symbol(c), x)
    
    for ch in prefixes:
        output[ch] = make_rewrite(ch)
    return output

PARSER = sexpr.Parser(prefix_rewrite('\'`:?#$'), parser_types)

# Util functions to easily handling sexpr
def getop(src):
    if type(src) is tuple and len(src) > 0 and type(src[0]) is Symbol:
        return src[0].name
    return None

class MacroExpander(object):
    def __init__(self, macros = {}):
        self.macros = dict(macros)

    def extend(self, macros):
	new_macros = dict(self.macros)
	new_macros.update(macros)
	return type(self)(new_macros)

    def expand_node(self, src):
        while getop(src) in self.macros:
            src = self.macros[src[0].name](src)
        return src

    def compile(self, src):
        src = self.expand_node(src)
        if type(src) in (tuple, list):
            return type(src)(map(self.compile, src))
        elif type(src) is KVStream:
            output = KVStream()
            for k, v in src:
                output.append((self.compile(k), self.compile(v)))
            return output
        else:
            return src

def env_curr():
    return context.curr()['ENV_STACK'][-1]

def env_push(name):
    context.curr().setdefault('ENV_STACK', []).append(name)

def env_pop():
    context.curr()['ENV_STACK'].pop()


"""
Default behaviour of the compiler
"""
def compile_struct(compiler, data):
    if type(data) in (tuple, list):
        elements = map(compiler.compile, data)
        if type(data) is tuple:
            tpl = '(' + '$#,' * len(elements) + ')'
        else:
            tpl = '[' + '$#,' * len(elements) + ']'
        return pycode.create(tpl, *elements)
    elif type(data) is KVStream:
        element_codes = [
                pycode.create(
                        '$#:$#', compiler.compile(x[0]), compiler.compile(x[1]))
                for x in data]
        tpl = '{' + '$#,' * len(element_codes) + '}'
        return pycode.create(tpl, *element_codes)
    else:
        return pycode.create('$#', data)


def parse_call(src):
    subject = src[0]
    sections = []
    if len(src) >= 2 and src[1] == Symbol('|'):
	src = src[2:]
	sections.append(['|'])
    elif len(src) >= 2 and src[1] == Symbol('=>'):
	sections.append(['=>'])
	src = src[2:]
    else:
	src = src[1:]
	sections.append(['=>'])

    for item in src:
	if item in (Symbol('|'), Symbol('=>')):
	    sections.append([item.name])
	else:
	    sections[-1].append(item)
    return subject, sections

def compile_call(compiler, src):
    subject, sections = parse_call(src)

    tpl_lines = ['$#']
    sum_codes = [compiler.compile(subject)]

    op_sects = []
    for section in sections:
	section_type, section_content = section[0], section[1:]
	if section_type == '|':
	    # For Props
	    for item in section_content:
		if type(item) == Symbol:
		    op_sects.append(('.' + item.name,))
		elif getop(item) == ':':
		    op_sects.append(
			    ('[' + ':'.join(['$#'] * (len(item) -1)) + ']',) \
			     + tuple(map(compiler.compile, item[1:])))                
		else:
		    op_sects.append(('[$#]', compiler.compile(item)))
	else:
	    args = []
	    kwargs = []
	    vargs = []
	    vkwargs = []

	    section_idx = 0
	    while section_idx < len(section_content):
		item = section_content[section_idx]
		if item == Symbol('.'):
		    vargs.append(section_content[section_idx + 1])
		    section_idx += 1
		elif item == Symbol('..'):
		    vkwargs.append(section_content[section_idx + 1])
		    section_idx += 1
		elif getop(item) == ':' and len(item) == 2 and type(item[1]) == Symbol:
		    kwargs.append((item[1].name, section_content[section_idx + 1]))
		    section_idx += 1
		else:
		    args.append(section_content[section_idx])
		section_idx += 1

	    tpl = ['$#'] * len(args)
	    codes = list(args)
	    if vargs:
		tpl.append('*$#')
		codes.append(vargs[0])
	    tpl.extend([x[0] + '=$#' for x in kwargs])
	    codes.extend([x[1] for x in kwargs])
	    if vkwargs:
		tpl.append('**$#')
		codes.append(vkwargs[0])
	    codes = tuple(map(compiler.compile, codes))
	    op_sects.append(
		    ('(' + ','.join(tpl) + ')',) + codes)

    # Create tpl
    tmp_name = None
    for item in op_sects:
	sect_tpl, sect_codes = item[0], item[1:]
        if len([x for x in sect_codes if x.is_expr()]) == len(sect_codes):
            # All section code is expr, save to directly join
	    tpl_lines[-1] += sect_tpl
        else:
            if tmp_name is None:
                tmp_name = pycode.name()
	    tpl_lines[-1] = '%s = %s' % (tmp_name, tpl_lines[-1])
	    tpl_lines.append(tmp_name + sect_tpl)
        sum_codes.extend(sect_codes)
    return pycode.create('\n'.join(tpl_lines), *sum_codes)

def compile_sym(compiler, src):
    if src.name == '_':
        return pycode.create(env_curr())
    else:
	return pycode.create(src.name)

class Compiler(object):
    """Compiler engine with default behaviour"""
    DEFAULT_PRIMS = {
	    '.struct' : compile_struct,
	    '.sym' : compile_sym,
	    '.call' : compile_call }

    def __init__(self, prims = {}):
	self.prims = dict(self.DEFAULT_PRIMS)
	self.prims.update(prims)

    def extend(self, prims):
	new_prims = dict(self.prims)
	new_prims.update(prims)
	return type(self)(new_prims)

    def compile_call_args(self, arglist):
        args = []
        kwargs = []
        kwarg_keys = []
	vargs = []
	vkwargs = []

        idx = 0
        # Parse argument list, compile each value argument
        while idx < len(arglist):
            curr = arglist[idx]
	    if isinstance(curr, Symbol) and curr.name in ('.', '..'):
		idx += 1
		if curr.name == '.':
		    vargs.append(self.compile(arglist[idx]))
		else:
		    vkwargs.append(self.compile(arglist[idx]))
            elif getop(curr) == ':':
                if len(curr) < 2 or type(curr[1]) is not Symbol:
                    raise SyntaxError('Invalid key argument syntax', arglist)
                kwarg_keys.append(curr[1].name)
                idx += 1
                kwargs.append(self.compile(arglist[idx]))
            else:
                args.append(self.compile(arglist[idx]))
            idx += 1

	arg_tpls = ['$#'] * len(args) + \
		['*($#)'] * len(vargs) + \
		[x+'=$#' for x in kwarg_keys] + \
		['**($#)'] * len(vkwargs)
        tpl = ','.join(arg_tpls)
	return tpl, (args + vargs + kwargs + vkwargs)

    def compile(self, src):
	if type(src) == pycode.Code:
	    return src

	if type(src) is tuple and len(src) > 0:
	    if getop(src) in self.prims:
		prim_name = getop(src)
	    else:
		prim_name = '.call'
	elif type(src) == Symbol:
	    prim_name = '.sym'
	else:
	    prim_name = '.struct'
	# Simply dispatch it
	return self.prims[prim_name](self, src)

    def compile_block(self, src, init_value = 'None'):
        # Start with blank block
        code = pycode.create(init_value)
        for item in src:
            code += self.compile(item)
        return code

if __name__ == '__main__':
    import sys
    import context

    with context.Context():
        src = PARSER.parseall(sys.stdin.read())
        test_compiler = Compiler()
        code = test_compiler.compile_block(src)
        print code.stat
        print '=>', code.value
