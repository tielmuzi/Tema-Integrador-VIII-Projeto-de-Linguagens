"""Persistência local para telemetria e regras simuladas do Escudo d'Água."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta
import json
import math
from pathlib import Path
from threading import RLock
from typing import Any


DEFAULT_RULES = [
    {"level": "CRÍTICO", "water_min": 150, "rain_min": 80, "color": "#df5262"},
    {"level": "ALERTA", "water_min": 100, "rain_min": 50, "color": "#ed813d"},
    {"level": "ATENÇÃO", "water_min": 50, "rain_min": 25, "color": "#e8bd4a"},
    {"level": "NORMAL", "water_min": 0, "rain_min": 0, "color": "#29a887"},
]
DEFAULT_POINTS = [
    {"id": "P01", "name": "Baixada do Rio", "neighborhood": "Baixada do Rio", "channel": "Córrego Central", "simulated": True},
    {"id": "P02", "name": "Vila dos Pescadores", "neighborhood": "Vila dos Pescadores", "channel": "Canal Sul", "simulated": True},
    {"id": "P03", "name": "Centro", "neighborhood": "Centro", "channel": "Rio Principal", "simulated": True},
    {"id": "P04", "name": "Alto da Serra", "neighborhood": "Alto da Serra", "channel": "Córrego da Serra", "simulated": True},
    {"id": "P05", "name": "Jardim Esperança", "neighborhood": "Jardim Esperança", "channel": "Canal Leste", "simulated": True},
    {"id": "P06", "name": "Vila Nova", "neighborhood": "Vila Nova", "channel": "Córrego Novo", "simulated": True},
    {"id": "P07", "name": "Zona Sul", "neighborhood": "Zona Sul", "channel": "Canal Sul", "simulated": True},
]
SEED_READINGS = [
    ("P01", 18, 32),
    ("P02", 34, 70),
    ("P01", 55, 108),
    ("P02", 82, 153),
    ("P03", 8, 25),
    ("P04", 52, 118),
    ("P05", 31, 62),
    ("P06", 12, 40),
    ("P07", 86, 166),
]


def _now() -> datetime:
    return datetime.now().astimezone()


def _initial_state() -> dict[str, Any]:
    now = _now()
    points = deepcopy(DEFAULT_POINTS)
    measurements = []
    for index, (point_id, rain, water) in enumerate(SEED_READINGS):
        measurements.append({
            "id": f"M{index + 1:04d}",
            "point_id": point_id,
            "rain_mm": rain,
            "water_cm": water,
            "risk": classify_risk(water, rain, DEFAULT_RULES),
            "measured_at": (now - timedelta(minutes=(len(SEED_READINGS) - index - 1) * 12)).isoformat(timespec="microseconds"),
            "simulated": True,
        })
    alerts = [
        _alert_from_measurement(measurement, points)
        for measurement in measurements
        if measurement["risk"] in {"ALERTA", "CRÍTICO"}
    ]
    return {"points": points, "measurements": measurements, "alerts": alerts, "rules": deepcopy(DEFAULT_RULES), "programs": [], "demo_points_version": 1}


def classify_risk(water_cm: float, rain_mm: float, rules: list[dict[str, Any]]) -> str:
    for rule in sorted(rules, key=lambda item: ["NORMAL", "ATENÇÃO", "ALERTA", "CRÍTICO"].index(item["level"]), reverse=True):
        if rule["level"] == "NORMAL":
            continue
        if water_cm >= rule["water_min"] or rain_mm >= rule["rain_min"]:
            return rule["level"]
    return "NORMAL"


def _alert_from_measurement(measurement: dict[str, Any], points: list[dict[str, Any]]) -> dict[str, Any]:
    point = next((item for item in points if item["id"] == measurement["point_id"]), None)
    return {
        "id": f"A{measurement['id'][1:]}",
        "point_id": measurement["point_id"],
        "point_name": point["name"] if point else measurement["point_id"],
        "risk": measurement["risk"],
        "message": f"{measurement['risk']}: nível {measurement['water_cm']} cm e chuva {measurement['rain_mm']} mm.",
        "created_at": measurement["measured_at"],
        "simulated": True,
    }


class MonitoramentoStore:
    """Armazena o estado em JSON e oferece operações seguras por thread."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._lock = RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write(_initial_state())
        else:
            with self._lock:
                state = self._read()
                if self._add_demo_points(state):
                    self._write(state)

    def _read(self) -> dict[str, Any]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, state: dict[str, Any]) -> None:
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(self.path)

    @staticmethod
    def _add_demo_points(state: dict[str, Any]) -> bool:
        if state.get("demo_points_version", 0) >= 1:
            return False
        existing_ids = {point["id"] for point in state["points"]}
        new_points = [deepcopy(point) for point in DEFAULT_POINTS if point["id"] not in existing_ids]
        if new_points:
            state["points"].extend(new_points)
        new_ids = {point["id"] for point in new_points}
        existing_measurement_ids = {item["id"] for item in state["measurements"]}
        next_measurement = max((int(item["id"][1:]) for item in state["measurements"] if item["id"].startswith("M") and item["id"][1:].isdigit()), default=0) + 1
        now = _now()
        for point_id, rain, water in SEED_READINGS:
            if point_id not in new_ids:
                continue
            measurement_id = f"M{next_measurement:04d}"
            while measurement_id in existing_measurement_ids:
                next_measurement += 1
                measurement_id = f"M{next_measurement:04d}"
            measurement = {
                "id": measurement_id,
                "point_id": point_id,
                "rain_mm": rain,
                "water_cm": water,
                "risk": classify_risk(water, rain, state["rules"]),
                "measured_at": now.isoformat(timespec="microseconds"),
                "simulated": True,
            }
            state["measurements"].append(measurement)
            existing_measurement_ids.add(measurement_id)
            next_measurement += 1
            if measurement["risk"] in {"ALERTA", "CRÍTICO"}:
                state["alerts"].append(_alert_from_measurement(measurement, state["points"]))
        state["demo_points_version"] = 1
        return True

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            state = self._read()
        result = deepcopy(state)
        last_by_point = {}
        for measurement in sorted(result["measurements"], key=lambda item: item["measured_at"], reverse=True):
            last_by_point.setdefault(measurement["point_id"], measurement)
        for point in result["points"]:
            point["latest"] = last_by_point.get(point["id"])
        result["measurements"].sort(key=lambda item: (item["measured_at"], item["id"]), reverse=True)
        result["alerts"].sort(key=lambda item: (item["created_at"], item["id"]), reverse=True)
        result["programs"].sort(key=lambda item: (item["executed_at"], item["id"]), reverse=True)
        result["counts"] = {
            "points": len(result["points"]),
            "measurements": len(result["measurements"]),
            "alerts": len(result["alerts"]),
            "programs": len(result["programs"]),
        }
        return result

    def create_point(self, data: dict[str, Any]) -> dict[str, Any]:
        name = self._required_text(data, "name", "Nome")
        neighborhood = self._required_text(data, "neighborhood", "Bairro")
        channel = self._required_text(data, "channel", "Canal")
        with self._lock:
            state = self._read()
            next_number = max((int(point["id"][1:]) for point in state["points"] if point["id"].startswith("P") and point["id"][1:].isdigit()), default=0) + 1
            point = {"id": f"P{next_number:02d}", "name": name, "neighborhood": neighborhood, "channel": channel, "simulated": True}
            state["points"].append(point)
            self._write(state)
            return deepcopy(point)

    def delete_point(self, point_id: str) -> None:
        with self._lock:
            state = self._read()
            if not any(point["id"] == point_id for point in state["points"]):
                raise KeyError("Ponto não encontrado.")
            state["points"] = [point for point in state["points"] if point["id"] != point_id]
            state["measurements"] = [item for item in state["measurements"] if item["point_id"] != point_id]
            state["alerts"] = [item for item in state["alerts"] if item["point_id"] != point_id]
            self._write(state)

    def add_measurement(self, data: dict[str, Any]) -> dict[str, Any]:
        point_id = self._required_text(data, "point_id", "Ponto")
        water_cm = self._number(data, "water_cm", "Nível da água")
        rain_mm = self._number(data, "rain_mm", "Precipitação")
        with self._lock:
            state = self._read()
            if not any(point["id"] == point_id for point in state["points"]):
                raise ValueError("Selecione um ponto de monitoramento existente.")
            number = max((int(item["id"][1:]) for item in state["measurements"] if item["id"].startswith("M") and item["id"][1:].isdigit()), default=0) + 1
            measurement = {
                "id": f"M{number:04d}",
                "point_id": point_id,
                "rain_mm": rain_mm,
                "water_cm": water_cm,
                "risk": classify_risk(water_cm, rain_mm, state["rules"]),
                "measured_at": _now().isoformat(timespec="microseconds"),
                "simulated": True,
            }
            state["measurements"].append(measurement)
            if measurement["risk"] in {"ALERTA", "CRÍTICO"}:
                state["alerts"].append(_alert_from_measurement(measurement, state["points"]))
            self._write(state)
            return deepcopy(measurement)

    def simulate_flood(self, point_id: str) -> dict[str, Any]:
        return self.add_measurement({"point_id": point_id, "water_cm": 180, "rain_mm": 98})

    def update_rules(self, rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
        required = {"CRÍTICO", "ALERTA", "ATENÇÃO", "NORMAL"}
        if not isinstance(rules, list) or {rule.get("level") for rule in rules if isinstance(rule, dict)} != required:
            raise ValueError("Informe exatamente as quatro faixas: CRÍTICO, ALERTA, ATENÇÃO e NORMAL.")
        normalized = []
        for rule in rules:
            if not isinstance(rule, dict):
                raise ValueError("Cada regra deve ser um objeto.")
            water = self._number(rule, "water_min", f"Nível mínimo de {rule.get('level', 'risco')}")
            rain = self._number(rule, "rain_min", f"Chuva mínima de {rule.get('level', 'risco')}")
            normalized.append({"level": rule["level"], "water_min": water, "rain_min": rain, "color": str(rule.get("color", "#607d8b"))})
        normalized.sort(key=lambda item: ["NORMAL", "ATENÇÃO", "ALERTA", "CRÍTICO"].index(item["level"]), reverse=True)
        with self._lock:
            state = self._read()
            state["rules"] = normalized
            self._write(state)
        return deepcopy(normalized)

    def add_program(self, source: str, accepted: bool, output: list[str], message: str) -> dict[str, Any]:
        with self._lock:
            state = self._read()
            number = len(state["programs"]) + 1
            program = {
                "id": f"R{number:04d}",
                "source": source[:2000],
                "accepted": accepted,
                "output": output[:20],
                "message": message[:300],
                "executed_at": _now().isoformat(timespec="seconds"),
                "simulated": True,
            }
            state["programs"].append(program)
            self._write(state)
            return deepcopy(program)

    @staticmethod
    def _required_text(data: dict[str, Any], key: str, label: str) -> str:
        value = data.get(key)
        if not isinstance(value, str) or not value.strip() or len(value.strip()) > 120:
            raise ValueError(f"{label} é obrigatório e deve ter até 120 caracteres.")
        return value.strip()

    @staticmethod
    def _number(data: dict[str, Any], key: str, label: str) -> int:
        value = data.get(key)
        if isinstance(value, bool):
            raise ValueError(f"{label} deve ser um número entre 0 e 1000.")
        try:
            number = float(value) # type: ignore
        except (TypeError, ValueError):
            raise ValueError(f"{label} deve ser um número entre 0 e 1000.") from None
        if not math.isfinite(number) or not 0 <= number <= 1000:
            raise ValueError(f"{label} deve ser um número entre 0 e 1000.")
        return int(number) if number.is_integer() else round(number, 2) # type: ignore
