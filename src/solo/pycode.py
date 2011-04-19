# -*- coding: utf-8 -*-

import re
import context

TAB     = '  '

def name(prefix = 'tmp'):
    """Assign name in current context"""
    nameidx = context.curr().setdefault('NAME_INDEX', {})
    idx = nameidx.setdefault(prefix, 0)
    name = '_%s_%d' % (prefix, idx)
    nameidx[prefix] = idx + 1
    return name

class Code(object):
    def __init__(self, stat, value, **meta):
        # rstrip to delete trailing newlines
        self.stat = stat.rstrip()
        # Expr should be one line and no indent
        self.value = value.strip()
	self.meta = meta

    def add_meta(self, **info):
	"""Add meta information to code block for further optimization"""
	new_meta = dict(self.meta)
	new_meta.update(info)
	return type(self)(self.stat, self.value, **new_meta)

    def is_expr(self):
        return not self.stat

    def asname(self, name):
        if self.value == name:
            return self
        return type(self)(self.stat + '\n%s=%s' % (name, self.value), name)

    @staticmethod
    def is_expr_pure(expr):
        return bool(re.match(r'[0-9a-zA-Z_]*$', expr))

    def __add__(self, other):
        stat = self.stat
        if not Code.is_expr_pure(self.value):
            if stat:
                stat += '\n'
            stat += self.value
        if stat:
            stat += '\n'
        stat += other.stat
        return type(self)(stat, other.value)
    
    SLOT	= '$#'
    
    @classmethod
    def from_tpl(cls, tpl, *args, **meta):
        tpl_lines = tpl.strip().split('\n')
        arg_idx = 0
        output_lines = []
        
        for tpl_line in tpl_lines:
            tpl_line = tpl_line.rstrip()
            if not tpl_line:
                # skip blank line
                continue

            if cls.SLOT not in tpl_line:
                # constant line
                output_lines.append(tpl_line)
                continue

            # count indent level of this line
            idx = 0
            while tpl_line[idx] in ' \t':
                idx += 1
            line_indent = tpl_line[:idx]

            if tpl_line.strip() == cls.SLOT:
                # Insert code block here
                ins_code = args[arg_idx]
                arg_idx += 1
                if not isinstance(ins_code, cls):
                    output_lines.append(line_indent + repr(ins_code))
                else:
                    # Insert the code block, handling code indent
                    output_lines.extend(
                        [line_indent + x for x
                         in ins_code.stat.split('\n') if x])
                    if not Code.is_expr_pure(ins_code.value):
                        output_lines.append(line_indent + ins_code.value)
                continue

            # Apply argument as expr argument, always from left to right
            # As far as I know, this is consistent with Python runtime behavior

            # Find number of slots to fill
            num_slots = len(re.findall(r'\$#', tpl_line))
            # Determine if we should assign tmp var to deal with
            # stat->expr problem
            need_arg_assign = False
            if num_slots > 1:
                for idx in xrange(num_slots):
                    arg = args[arg_idx + idx]
                    if isinstance(arg, Code) and not arg.is_expr():
                        need_arg_assign = True
                        break
            fill_exprs = []
            name_prefix = name('arg')
            for idx in xrange(num_slots):
                arg = args[arg_idx + idx]
                if isinstance(arg, Code):
                    if need_arg_assign and not Code.is_expr_pure(arg.value):
                        # In this case, we should assign the arg into tmp var
                        # 1. convert stat into expr,
                        # 2. preserve computation order
                        arg = arg.asname('%s_%d' % (name_prefix, idx))
                    # append any prefix statments to output_lines
                    output_lines.extend([line_indent + x for x in arg.stat.split('\n') if x])
                    fill_exprs.append(arg.value)
                else:
                    fill_exprs.append(repr(arg))
            arg_idx += num_slots

            # fill in slots
            sects = tpl_line.split(cls.SLOT)
            line = sects[0] + ''.join(
                    [fill_exprs[i] + sects[i + 1] for i in xrange(num_slots)])
            output_lines.append(line)

        # Join output lines and return final Code object
        if not output_lines:
            return cls('', 'None', **meta)
        if output_lines[-1][0] in ' \t':
            # The last line of output line is indented
            # it cannot treated as output value
            return cls('\n'.join(output_lines), 'None', **meta)
        else:
            return cls('\n'.join(output_lines[:-1]), output_lines[-1], **meta)
        
create = Code.from_tpl
