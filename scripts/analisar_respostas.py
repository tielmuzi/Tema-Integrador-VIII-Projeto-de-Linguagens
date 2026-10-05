"""Analisa as respostas do formulário Escudo d'Água e gera um resumo para a aplicação."""
from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Iterable


ALIASES = {
    "regiao": ("estado ou regiao", "estado/regiao", "regiao"),
    "suscetibilidade": ("suscetivel", "suscetibilidade"),
    "frequencia": ("frequencia ocorrem", "frequencia"),
    "locais": ("locais da sua regiao", "locais"),
    "impactos": ("principais problemas", "problemas causados"),
    "canais": ("meios voce gostaria", "meios"),
    "informacoes": ("informacoes voce considera", "informacoes"),
    "adocao": ("sistema digital", "utilizaria um sistema"),
    "sensores": ("instalacao de sensores", "importante a instalacao"),
    "orientacoes": ("gostaria de receber orientacoes", "receber orientacoes"),
    "melhorias": ("reduzir os alagamentos", "poderia ser feito"),
    "sugestoes": ("sugestao para melhorar", "melhorar o monitoramento"),
}


def remover_acentos(value: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFD", value) if unicodedata.category(ch) != "Mn")


def normalizar(value: str) -> str:
    return re.sub(r"\s+", " ", remover_acentos(value or "").strip().lower())


def ler_csv(path: Path) -> list[dict[str, str]]:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "cp1252", "latin1"):
        try:
            text = raw.decode(encoding)
            rows = list(csv.DictReader(text.splitlines(), delimiter=";"))
            if rows and len(rows[0]) >= 10:
                return rows
        except UnicodeDecodeError:
            continue
    raise ValueError("Não foi possível ler o CSV em UTF-8, CP1252 ou Latin-1.")


def localizar_coluna(fieldnames: Iterable[str], aliases: tuple[str, ...]) -> str:
    for field in fieldnames:
        compact = normalizar(field)
        if any(alias in compact for alias in aliases):
            return field
    raise ValueError(f"Coluna não encontrada; aliases esperados: {aliases}")


def colunas(rows: list[dict[str, str]]) -> dict[str, str]:
    fields = list(rows[0])
    return {key: localizar_coluna(fields, aliases) for key, aliases in ALIASES.items()}


def itens(value: str) -> list[str]:
    return [part.strip() for part in (value or "").split(",") if part.strip()]


def regiao_canonica(value: str) -> str:
    text = " ".join((value or "").strip().split())
    low = normalizar(text)
    if "itaperuna" in low:
        return "Itaperuna"
    if "itaberaba" in low:
        return "Itaberaba - Bahia"
    if "mato grosso" in low:
        return "Mato Grosso"
    if "pará" in text.lower() or "para," in low:
        return "Pará"
    if "sudeste" in low or low.endswith("rj"):
        return "Sudeste - RJ"
    return text.title()


def risco_score(row: dict[str, str], cols: dict[str, str]) -> int:
    susc = normalizar(row[cols["suscetibilidade"]])
    freq = normalizar(row[cols["frequencia"]])
    susc_score = 90 if "sim, frequentemente" in susc else 70 if "sim, ocasionalmente" in susc else 45 if "raramente" in susc else 15
    freq_score = 95 if "toda vez" in freq else 80 if "frequentemente" in freq else 60 if "algumas" in freq else 35 if "raramente" in freq else 10
    impact_bonus = min(10, len(itens(row[cols["impactos"]])) * 2)
    return max(0, min(100, round((susc_score * 0.55) + (freq_score * 0.35) + impact_bonus)))


def faixa(score: int) -> str:
    return "alto" if score >= 70 else "moderado" if score >= 45 else "baixo"


def top_multi(rows: list[dict[str, str]], column: str, limit: int = 6) -> list[dict[str, object]]:
    counter: Counter[str] = Counter()
    for row in rows:
        counter.update(normalizar(item) for item in itens(row[column]))
    return [{"label": label, "count": count} for label, count in counter.most_common(limit)]


def analisar(path: Path) -> dict[str, object]:
    rows = ler_csv(path)
    cols = colunas(rows)
    scores = [risco_score(row, cols) for row in rows]
    region_counter = Counter(regiao_canonica(row[cols["regiao"]]) for row in rows)
    risk_counter = Counter(faixa(score) for score in scores)
    adoption = Counter(normalizar(row[cols["adocao"]]) for row in rows)
    sensor = Counter(normalizar(row[cols["sensores"]]) for row in rows)
    orient = Counter(normalizar(row[cols["orientacoes"]]) for row in rows)
    profiles = []
    for row, score in zip(rows, scores):
        profiles.append({
            "regiao": regiao_canonica(row[cols["regiao"]]),
            "risco": score,
            "faixa": faixa(score),
            "frequencia": row[cols["frequencia"]].strip(),
            "locais": itens(row[cols["locais"]]),
            "canais": itens(row[cols["canais"]]),
        })
    high_risk = sum(1 for score in scores if score >= 70)
    return {
        "fonte": path.name,
        "total_respostas": len(rows),
        "campos": len(cols),
        "regioes": [{"label": label, "count": count} for label, count in region_counter.most_common()],
        "risco": {
            "medio": round(sum(scores) / len(scores), 1) if scores else 0,
            "distribuicao": [{"label": label, "count": risk_counter.get(label, 0)} for label in ("alto", "moderado", "baixo")],
            "alto_percentual": round((high_risk / len(scores)) * 100) if scores else 0,
        },
        "adocao_sistema": [{"label": label, "count": count} for label, count in adoption.most_common()],
        "sensores": [{"label": label, "count": count} for label, count in sensor.most_common()],
        "orientacoes": [{"label": label, "count": count} for label, count in orient.most_common()],
        "impactos": top_multi(rows, cols["impactos"]),
        "canais": top_multi(rows, cols["canais"]),
        "informacoes_alerta": top_multi(rows, cols["informacoes"]),
        "perfis": profiles,
        "evidencias": [
            f"{region_counter.most_common(1)[0][0]} concentra {region_counter.most_common(1)[0][1]} respostas e deve ser priorizada na simulação.",
            f"{high_risk} de {len(rows)} respostas foram classificadas como risco alto pelo cruzamento entre suscetibilidade e frequência.",
            f"{adoption.get('sim', 0)} respondentes disseram que usariam um sistema digital de monitoramento.",
            f"{sensor.get('muito importante', 0) + sensor.get('importante', 0)} respondentes consideram sensores importantes ou muito importantes.",
        ],
    }


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Gera o resumo da pesquisa Escudo d'Água")
    parser.add_argument("entrada", type=Path)
    parser.add_argument("saida", type=Path)
    args = parser.parse_args()
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text(json.dumps(analisar(args.entrada), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Resumo gerado em {args.saida}")
    return 0


if __name__ == "__main__":
    main()
