"""Analisador léxico da DSL Escudo d'Água.

O scanner transforma o texto fonte em tokens e informa erros com linha, coluna
 e contexto. A especificação de IDs e números segue o Projeto Escudo d'Água.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Iterable


class TokenType(str, Enum):
    KEYWORD = "PALAVRA_RESERVADA"
    ID = "ID"
    NUM = "NUM"
    SYMBOL = "SIMBOLO"
    EOF = "EOF"


KEYWORDS = {"INICIO", "FIM", "AREA", "SENSOR", "MONITORE", "ALARME", "NIVEL"}
SYMBOLS = {"(", ")", ";", ",", "="}


@dataclass(frozen=True)
class Token:
    type: TokenType
    lexeme: str
    line: int
    column: int

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "lexeme": self.lexeme,
            "line": self.line,
            "column": self.column,
        }


@dataclass(frozen=True)
class LexicalError:
    message: str
    line: int
    column: int
    lexeme: str

    def to_dict(self) -> dict:
        return {
            "kind": "léxico",
            "message": self.message,
            "line": self.line,
            "column": self.column,
            "lexeme": self.lexeme,
        }


class Scanner:
    """Scanner baseado em uma expressão regular com grupos nomeados."""

    _token_re = re.compile(
        r"(?P<NEWLINE>\n)|(?P<SKIP>[ \t\r]+)|(?P<COMMENT>#[^\n]*)|"
        r"(?P<NUM>[0-9]+)|(?P<ID>[A-Z][a-zA-Z0-9_]*)|(?P<SYMBOL>[();,=])"
    )

    def __init__(self, source: str):
        self.source = source
        self.tokens: list[Token] = []
        self.errors: list[LexicalError] = []

    def scan(self) -> tuple[list[Token], list[LexicalError]]:
        line = 1
        column = 1
        position = 0
        length = len(self.source)

        while position < length:
            match = self._token_re.match(self.source, position)
            if match is None:
                bad = self.source[position]
                self.errors.append(
                    LexicalError(
                        message=f"Caractere ou comando desconhecido: '{bad}'",
                        line=line,
                        column=column,
                        lexeme=bad,
                    )
                )
                position += 1
                column += 1
                continue

            lexeme = match.group(0)
            kind = match.lastgroup
            if kind == "NEWLINE":
                line += 1
                column = 1
            elif kind in {"SKIP", "COMMENT"}:
                column += len(lexeme)
            elif kind == "NUM":
                self.tokens.append(Token(TokenType.NUM, lexeme, line, column))
                column += len(lexeme)
            elif kind == "ID":
                # Uma palavra em caixa alta que não pertence ao vocabulário
                # é reportada como comando desconhecido, mantendo a distinção
                # entre ID (ex.: Centro) e erro léxico (ex.: CHUVA).
                if lexeme.isupper() and lexeme not in KEYWORDS:
                    self.errors.append(
                        LexicalError(
                            message=f"Palavra reservada ou comando desconhecido: '{lexeme}'",
                            line=line,
                            column=column,
                            lexeme=lexeme,
                        )
                    )
                else:
                    token_type = TokenType.KEYWORD if lexeme in KEYWORDS else TokenType.ID
                    self.tokens.append(Token(token_type, lexeme, line, column))
                column += len(lexeme)
            elif kind == "SYMBOL":
                self.tokens.append(Token(TokenType.SYMBOL, lexeme, line, column))
                column += len(lexeme)
            position = match.end()

        self.tokens.append(Token(TokenType.EOF, "", line, column))
        return self.tokens, self.errors


def scan_source(source: str) -> tuple[list[Token], list[LexicalError]]:
    return Scanner(source).scan()


def format_lexical_errors(errors: Iterable[LexicalError]) -> str:
    return "\n".join(
        f"Erro léxico na linha {error.line}, coluna {error.column}: {error.message}"
        for error in errors
    )
