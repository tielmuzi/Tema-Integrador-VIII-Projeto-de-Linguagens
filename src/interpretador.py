"""Interpretador da AST da DSL Escudo d'Água."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.parser import Node


@dataclass
class EstadoMonitoramento:
    areas: dict[str, list[str]] = field(default_factory=dict)
    sensores: set[str] = field(default_factory=set)
    niveis: dict[str, int] = field(default_factory=dict)
    alarmes: list[str] = field(default_factory=list)


class Interpretador:
    def __init__(self):
        self.estado = EstadoMonitoramento()
        self.saidas: list[str] = []

    def executar(self, programa: Node) -> list[str]:
        for statement in programa.children:
            self.executar_statement(statement)
        if not self.saidas:
            self.saidas.append("[ESCUDO D'ÁGUA] Programa aceito: nenhum comando de monitoramento foi solicitado.")
        return self.saidas

    def executar_statement(self, statement: Node) -> None:
        kind = statement.kind
        if kind == "DeclaracaoArea":
            params = [child.value for child in statement.children]
            self.estado.areas[statement.value] = params
            self.saidas.append(
                f"[ÁREA] {statement.value} cadastrada com {len(params)} configuração(ões): "
                f"{', '.join(params) if params else 'sem parâmetros'}."
            )
        elif kind == "DeclaracaoSensor":
            self.estado.sensores.add(statement.value)
            self.saidas.append(f"[SENSOR] {statement.value} conectado ao centro de monitoramento.")
        elif kind == "AtribuicaoNivel":
            area = statement.value["area"]
            level = statement.value["nivel"]
            self.estado.niveis[area] = level
            self.saidas.append(f"[NÍVEL] {area}: {level}% de risco pluviométrico registrado.")
        elif kind == "Atribuicao":
            self.saidas.append(
                f"[DADO] {statement.value['nome']} recebeu o valor {statement.value['valor']}."
            )
        elif kind == "ComandoMonitore":
            self.monitorar(statement.value)
        elif kind == "ComandoAlarme":
            alvo = statement.value or "sistema"
            self.estado.alarmes.append(alvo)
            self.saidas.append(f"[ALARME] Alerta preventivo acionado para {alvo}.")

    def monitorar(self, area: str) -> None:
        if area not in self.estado.areas:
            self.saidas.append(f"[AVISO] Área {area} ainda não foi declarada; monitoramento iniciado mesmo assim.")
        nivel = self.estado.niveis.get(area, 0)
        if nivel >= 80:
            status = "RISCO ALTO — alarme recomendado"
        elif nivel >= 50:
            status = "ATENÇÃO — acompanhar evolução"
        else:
            status = "NORMAL — sem risco imediato"
        self.saidas.append(f"[MONITORAMENTO] {area}: nível {nivel}%. {status}.")


def interpretar(programa: Node) -> list[str]:
    return Interpretador().executar(programa)
