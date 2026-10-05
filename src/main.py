"""Entrada principal do compilador Escudo d'Água: Scanner → Parser → Interpretador."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

from src.interpretador import interpretar
from src.parser import format_parse_errors, parse_tokens
from src.scanner import format_lexical_errors, scan_source


def _add_error_context(errors: list[dict[str, Any]], source: str) -> None:
    lines = source.splitlines()
    for error in errors:
        line = error.get("line", 0)
        column = error.get("column", 0)
        if not isinstance(line, int) or not isinstance(column, int) or not 1 <= line <= len(lines):
            continue
        source_line = lines[line - 1]
        caret_column = len(source_line[: max(0, column - 1)].expandtabs(4))
        error["context"] = f"{source_line.expandtabs(4)}\n{' ' * caret_column}^"


def compile_source(source: str, execute: bool = True) -> dict[str, Any]:
    tokens, lexical_errors = scan_source(source)
    result: dict[str, Any] = {
        "accepted": False,
        "tokens": [token.to_dict() for token in tokens if token.type.value != "EOF"],
        "lexical_errors": [error.to_dict() for error in lexical_errors],
        "syntax_errors": [],
        "ast": None,
        "output": [],
    }
    if lexical_errors:
        _add_error_context(result["lexical_errors"], source)
        result["message"] = format_lexical_errors(lexical_errors)
        return result

    ast, parse_errors = parse_tokens(tokens)
    if parse_errors or ast is None:
        result["syntax_errors"] = [error.to_dict() for error in parse_errors]
        _add_error_context(result["syntax_errors"], source)
        result["message"] = format_parse_errors(parse_errors)
        return result

    result["accepted"] = True
    result["ast"] = ast.to_dict()
    if execute:
        result["output"] = interpretar(ast)
    result["message"] = "Programa aceito pelo Scanner, Parser e Interpretador."
    return result


def run_file(path: str | Path, execute: bool = True) -> dict[str, Any]:
    source_path = Path(path)
    return compile_source(source_path.read_text(encoding="utf-8"), execute=execute)


def main() -> int:
    cli = argparse.ArgumentParser(description="Compilador Escudo d'Água para monitoramento de chuvas")
    cli.add_argument("arquivo", help="arquivo .min de entrada")
    cli.add_argument("--tokens", action="store_true", help="exibe os tokens")
    cli.add_argument("--ast", action="store_true", help="exibe a árvore sintática")
    cli.add_argument("--sem-execucao", action="store_true", help="não executa o interpretador")
    cli.add_argument("--json", action="store_true", help="imprime o resultado em JSON")
    args = cli.parse_args()

    result = run_file(args.arquivo, execute=not args.sem_execucao)
    if args.json or (not args.tokens and not args.ast):
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if args.tokens:
            print("TOKENS")
            print(json.dumps(result["tokens"], ensure_ascii=False, indent=2))
        if args.ast:
            print("ÁRVORE")
            print(json.dumps(result["ast"], ensure_ascii=False, indent=2))
        if result["message"]:
            print(result["message"])
        for line in result["output"]:
            print(line)
    return 0 if result["accepted"] else 1


if __name__ == "__main__":
    main()
