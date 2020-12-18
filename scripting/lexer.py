from sly import Lexer


class LeLexer(Lexer):
    tokens = { NAME, NUMBER, STRING }
    ignore = '\t '
    literals = { '=', '+', '-', '/',
                 '*', '(', ')', ',', ';'}

    NAME = r'[a-zA-Z_][a-zA-Z0-9_]*'
    STRING = r'\".*?\"'

    # Number Token
    @_(r'\d+')
    def NUMBER(self, t):
        t.value = int(t.value)
        return t