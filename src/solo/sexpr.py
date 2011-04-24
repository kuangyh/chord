# -*- coding: utf-8 -*-

"""
S-expr parser, a LISP front-end for Python
"""

import re

class Parser(object):
    RE_NUM      = re.compile(r'^[+-]?[0-9]+(\.[0-9]+)?')
    RE_STR      = re.compile(r'^\"(\\\\|\\\"|[^"])*\"', re.DOTALL)
    RE_SYM      = re.compile(r'^[^0-9\s\(\)\[\]{}\",][^\s\(\)\[\]{}\",]*')
    RE_LITERAL  = re.compile(r'^<!\[([a-zA-Z0-9-_]*)\[(.*)\]\]>?', re.DOTALL)
    RE_BLANK    = re.compile(r'^[\s,]*(;[^\r\n]*[\r\n\s,]+)*', re.DOTALL)

    PARN        = {
            '(' : ('tuple', ')'),
            '[' : ('list', ']'),
            '{' : ('dict', '}')}

    def __init__(self, prefixes, types):
        self.prefixes = prefixes
        self.types = types

    @staticmethod
    def next(src, pattern):
        if isinstance(pattern, basestring):
            if src.startswith(pattern):
                return (pattern,), src[len(pattern):]
            else:
                return None, src
        else:
            m = pattern.search(src)
            if m is not None and m.start() == 0:
                return (src[:m.end()],) + m.groups(), src[m.end():]
            else:
                return None, src

    def parse(self, src):
        # Clear blank and comment
        unused_match, src = Parser.next(src, Parser.RE_BLANK) 
        if not src:
            raise StopIteration

        if src[0] in Parser.PARN:
            typename, endch = Parser.PARN[src[0]]

            unused, src = Parser.next(src[1:], Parser.RE_BLANK)
            output = []
            while src and src[0] != endch:
                elim, src = self.parse(src)
                output.append(elim)
                unused, src = Parser.next(src, Parser.RE_BLANK)                
            if not src:                
                raise SyntaxError, src            
            return self.types[typename](output), src[1:]

        # prefixes char (quote etc)
        if src[0] in self.prefixes and (
                len(src) > 1 and src[1] not in ' \t\r\n'):
            prefix_func = self.prefixes[src[0]]
            ret, src = self.parse(src[1:])
            return prefix_func(ret), src

        m, src = Parser.next(src, Parser.RE_LITERAL)
        if m is not None:
            unused, typename, content = m
            return self.types[typename](content), src

        m, src = Parser.next(src, Parser.RE_STR)
        if m is not None:
            return self.types['str'](m[0]), src

        m, src = Parser.next(src, Parser.RE_NUM)
        if m is not None:
            return self.types['num'](m[0]), src

        # OK, it will be symbol hah?
        m, src= Parser.next(src, Parser.RE_SYM)
        if m is not None:
            return self.types['sym'](m[0]), src

        raise SyntaxError, src[:80]

    def parseall(self, src):
        output = []
        while True:
            try:
                obj, src = self.parse(src)
                output.append(obj)
            except StopIteration:
                break
        return output

if __name__ == '__main__':
    import sys
    parser = Parser(
            prefixes = {'\'' : lambda x: ('QUOTE', x)},
            types = {
                    'num' : eval,
                    'str' : eval,
                    'sym' : lambda x: '<SYM %s>' % (x,),
                    ''    : lambda x: x,
                    'py'  : lambda x: '<PY %s>' % (x,),
                    'tuple' : tuple,
                    'list' : lambda x: ('list',) + tuple(x),
                    'dict' :  lambda x: ('dict',) + tuple(x)}
            )
    print parser.parseall(sys.stdin.read())
