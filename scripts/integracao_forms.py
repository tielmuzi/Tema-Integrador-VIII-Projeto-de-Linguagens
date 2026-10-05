"""Converte respostas do Google Forms para um programa executável da DSL Escudo d'Água."""
# pyright: reportMissingImports=false
from __future__ import annotations

import argparse
import re
import unicodedata
from pathlib import Path

try:
    from scripts.analisar_respostas import colunas, ler_csv, regiao_canonica, risco_score
except ModuleNotFoundError:  # execução como `python scripts/integracao_forms.py`
    from analisar_respostas import colunas, ler_csv, regiao_canonica, risco_score


def id_seguro(valor: str, fallback: str) -> str:
    sem_acentos = "".join(
        char for char in unicodedata.normalize("NFD", valor) if unicodedata.category(char) != "Mn"
    )
    palavras = re.findall(r"[A-Za-z0-9]+", sem_acentos.title())
    nome = "".join(palavras) or fallback
    return nome if nome[0].isupper() else fallback + nome


def converter(csv_path: Path, output_path: Path) -> Path:
    rows = ler_csv(csv_path)
    cols = colunas(rows)
    lines = [
        "# Programa gerado a partir das respostas do Google Forms",
        "# O nível é estimado cruzando suscetibilidade, frequência e impactos relatados.",
        "INICIO",
    ]
    registros: list[tuple[str, int]] = []
    usados: set[str] = set()
    for index, row in enumerate(rows, start=1):
        area = id_seguro(regiao_canonica(row[cols["regiao"]]), f"Area{index}")
        if area in usados:
            area = f"{area}{index}"
        usados.add(area)
        nivel = risco_score(row, cols)
        registros.append((area, nivel))
        lines.append(f"AREA {area} (SENSOR, NIVEL);")
        lines.append(f"NIVEL {area} = {nivel};")
    for area, _ in registros:
        lines.append(f"MONITORE {area};")
    if any(nivel >= 70 for _, nivel in registros):
        lines.append("ALARME;")
    lines.append("FIM")
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Google Forms CSV para programa Escudo d'Água")
    parser.add_argument("csv", nargs="?", default="dados/respostas_google_forms.csv")
    parser.add_argument("saida", nargs="?", default="programa_valido.min")
    args = parser.parse_args()
    destino = converter(Path(args.csv), Path(args.saida))
    print(f"Programa gerado em {destino}")
    return 0


if __name__ == "__main__":
    main()
