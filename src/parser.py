"""Parser descendente recursivo da DSL Escudo d'Água."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from src.scanner import Token, TokenType


class ParseError(Exception):
    def __init__(self, message: str, token: Token):
        self.message = message
        self.token = token
        super().__init__(message)

    def to_dict(self) -> dict:
        return {
            "kind": "sintático",
            "message": self.message,
            "line": self.token.line,
            "column": self.token.column,
            "lexeme": self.token.lexeme,
        }


@dataclass
class Node:
    kind: str
    value: Any = None
    children: list["Node"] = field(default_factory=list)

    def to_dict(self) -> dict:
        result: dict[str, Any] = {"kind": self.kind}
        if self.value is not None:
            result["value"] = self.value
        if self.children:
            result["children"] = [child.to_dict() for child in self.children]
        return result


class Parser:
    """Implementa a forma operacional da BNF do projeto.

    programa ::= INICIO comando* FIM
    comando ::= AREA ID '(' lista ');'
              | SENSOR ID ';'
              | MONITORE ID ';'
              | ALARME [ID] ';'
              | NIVEL ID '=' NUM ';'
              | ID '=' NUM ';'
    lista   ::= ID|SENSOR|NIVEL (',' ID|SENSOR|NIVEL)*
    """

    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.current = 0
        self.errors: list[ParseError] = []

    def parse(self) -> Node:
        try:
            self.consume_lexeme("INICIO", "O programa deve começar com INICIO.")
            statements: list[Node] = []
            while not self.check_lexeme("FIM") and not self.check_type(TokenType.EOF):
                statements.append(self.statement())
            self.consume_lexeme("FIM", "Esperado FIM para encerrar o programa.")
            self.consume_type(TokenType.EOF, "Não deve haver conteúdo depois de FIM.")
            return Node("Programa", children=statements)
        except ParseError as error:
            self.errors.append(error)
            raise

    def statement(self) -> Node:
        token = self.peek()
        if token.lexeme == "AREA":
            return self.area_declaration()
        if token.lexeme == "SENSOR":
            return self.sensor_declaration()
        if token.lexeme == "MONITORE":
            return self.monitor_command()
        if token.lexeme == "ALARME":
            return self.alarm_command()
        if token.lexeme == "NIVEL":
            return self.level_command()
        if token.type == TokenType.ID:
            return self.assignment()
        raise ParseError(
            f"Comando inesperado '{token.lexeme or 'fim do arquivo'}'.",
            token,
        )

    def area_declaration(self) -> Node:
        self.consume_lexeme("AREA", "Esperado AREA.")
        name = self.consume_type(TokenType.ID, "Esperado um ID para nomear a área.")
        self.consume_lexeme("(", "Esperado '(' após o nome da área.")
        parameters: list[Node] = []
        if not self.check_lexeme(")"):
            parameters.append(self.parameter())
            while self.match_lexeme(","):
                parameters.append(self.parameter())
        self.consume_lexeme(")", "Esperado ')' para fechar a declaração da área.")
        self.consume_lexeme(";", "Esperado ';' ao final da declaração da área.")
        return Node(
            "DeclaracaoArea",
            value=name.lexeme,
            children=parameters,
        )

    def parameter(self) -> Node:
        token = self.peek()
        if token.type not in {TokenType.ID, TokenType.KEYWORD}:
            raise ParseError("Esperado um ID ou palavra reservada na lista da área.", token)
        self.advance()
        return Node("Parametro", value=token.lexeme)

    def sensor_declaration(self) -> Node:
        self.consume_lexeme("SENSOR", "Esperado SENSOR.")
        name = self.consume_type(TokenType.ID, "Esperado um ID para nomear o sensor.")
        self.consume_lexeme(";", "Esperado ';' ao final da declaração do sensor.")
        return Node("DeclaracaoSensor", value=name.lexeme)

    def monitor_command(self) -> Node:
        self.consume_lexeme("MONITORE", "Esperado MONITORE.")
        area = self.consume_type(TokenType.ID, "Esperado o ID da área a monitorar.")
        self.consume_lexeme(";", "Esperado ';' após o comando MONITORE.")
        return Node("ComandoMonitore", value=area.lexeme)

    def alarm_command(self) -> Node:
        self.consume_lexeme("ALARME", "Esperado ALARME.")
        target = None
        if self.check_type(TokenType.ID):
            target = self.advance().lexeme
        self.consume_lexeme(";", "Esperado ';' após o comando ALARME.")
        return Node("ComandoAlarme", value=target)

    def level_command(self) -> Node:
        self.consume_lexeme("NIVEL", "Esperado NIVEL.")
        area = self.consume_type(TokenType.ID, "Esperado o ID da área no comando NIVEL.")
        self.consume_lexeme("=", "Esperado '=' no comando NIVEL.")
        number = self.consume_type(TokenType.NUM, "Esperado NUM para o nível.")
        self.consume_lexeme(";", "Esperado ';' após o nível.")
        return Node("AtribuicaoNivel", value={"area": area.lexeme, "nivel": int(number.lexeme)})

    def assignment(self) -> Node:
        name = self.consume_type(TokenType.ID, "Esperado um ID.")
        self.consume_lexeme("=", "Esperado '=' na atribuição.")
        number = self.consume_type(TokenType.NUM, "Esperado NUM na atribuição.")
        self.consume_lexeme(";", "Esperado ';' ao final da atribuição.")
        return Node("Atribuicao", value={"nome": name.lexeme, "valor": int(number.lexeme)})

    def match_lexeme(self, lexeme: str) -> bool:
        if self.check_lexeme(lexeme):
            self.advance()
            return True
        return False

    def check_lexeme(self, lexeme: str) -> bool:
        return self.peek().lexeme == lexeme

    def check_type(self, token_type: TokenType) -> bool:
        return self.peek().type == token_type

    def consume_lexeme(self, lexeme: str, message: str) -> Token:
        if self.check_lexeme(lexeme):
            return self.advance()
        raise ParseError(message, self.peek())

    def consume_type(self, token_type: TokenType, message: str) -> Token:
        if self.check_type(token_type):
            return self.advance()
        raise ParseError(message, self.peek())

    def advance(self) -> Token:
        token = self.peek()
        if self.current < len(self.tokens) - 1:
            self.current += 1
        return token

    def peek(self) -> Token:
        return self.tokens[self.current]


def parse_tokens(tokens: list[Token]) -> tuple[Node | None, list[ParseError]]:
    parser = Parser(tokens)
    try:
        return parser.parse(), []
    except ParseError as error:
        return None, [error]


def format_parse_errors(errors: Iterable[ParseError]) -> str:
    return "\n".join(
        f"Erro sintático na linha {error.token.line}, coluna {error.token.column}: {error.message}"
        for error in errors
    )
