"""Servidor local da demonstração web Escudo d'Água."""
# pyright: reportMissingImports=false
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from src.main import compile_source
from src.monitoramento import MonitoramentoStore

ROOT = Path(__file__).parent.resolve()
WEB = ROOT / "web"
EXEMPLOS = ROOT / "exemplos"
RESUMO = ROOT / "dados" / "resumo_respostas.json"
STORE = MonitoramentoStore(ROOT / "dados" / "monitoramento.json")
MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
}


class handler(BaseHTTPRequestHandler):
    server_version = "EscudoDAguaDev/1.0"

    def send_bytes(self, payload: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def send_json(self, payload: object, status: int = 200) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_bytes(encoded, "application/json; charset=utf-8", status)

    def read_json(self) -> dict:
        size = int(self.headers.get("Content-Length", "0"))
        if size > 1_000_000:
            raise ValueError("A requisição excede o limite de 1 MB.")
        payload = json.loads(self.rfile.read(size).decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("O corpo da requisição deve ser um objeto JSON.")
        return payload

    @staticmethod
    def dashboard_data() -> dict:
        monitoring = STORE.snapshot()
        research = json.loads(RESUMO.read_text(encoding="utf-8"))
        return {"research": research, "monitoring": monitoring}

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/insights":
            self.send_bytes(RESUMO.read_bytes(), "application/json; charset=utf-8")
            return
        if parsed.path in {"/api/dashboard", "/api/reports"}:
            self.send_json(self.dashboard_data())
            return
        if parsed.path == "/api/monitoring":
            self.send_json(STORE.snapshot())
            return
        if parsed.path == "/api/rules":
            self.send_json(STORE.snapshot()["rules"])
            return
        if parsed.path == "/api/risk/check":
            from src.monitoramento import classify_risk

            query = parse_qs(parsed.query)
            try:
                water = float(query.get("water_cm", ["0"])[0])
                rain = float(query.get("rain_mm", ["0"])[0])
                risk = classify_risk(water, rain, STORE.snapshot()["rules"])
            except (ValueError, TypeError):
                self.send_json({"error": "Nível e chuva devem ser números válidos."}, 400)
                return
            self.send_json({"risk": risk})
            return
        if parsed.path == "/api/examples":
            examples = []
            for path in sorted(EXEMPLOS.glob("T*.min")):
                examples.append({"id": path.name[:3], "name": path.name, "source": path.read_text(encoding="utf-8")})
            self.send_json(examples)
            return
        if parsed.path.startswith("/api/"):
            self.send_json({"error": "Endpoint não encontrado."}, 404)
            return

        relative = "index.html" if parsed.path in {"", "/"} else parsed.path.lstrip("/")
        candidate = (WEB / relative).resolve()
        if WEB not in candidate.parents and candidate != WEB:
            self.send_error(403, "Acesso negado")
            return
        if not candidate.is_file():
            self.send_error(404, "Arquivo não encontrado")
            return
        self.send_bytes(candidate.read_bytes(), MIME.get(candidate.suffix, "application/octet-stream"))

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path not in {"/api/compile", "/api/points", "/api/measurements", "/api/simulate", "/api/rules"}:
            self.send_json({"error": "Endpoint não encontrado."}, 404)
            return
        try:
            payload = self.read_json()
            if path == "/api/compile":
                source = payload.get("source", "")
                execute = payload.get("execute", True)
                if not isinstance(source, str) or len(source) > 100_000:
                    raise ValueError("O campo source deve ser texto com até 100.000 caracteres.")
                if not isinstance(execute, bool):
                    raise ValueError("O campo execute deve ser booleano.")
                result = compile_source(source, execute=execute)
                if execute:
                    STORE.add_program(source, result["accepted"], result["output"], result["message"])
                self.send_json(result)
                return
            if path == "/api/points":
                point = STORE.create_point(payload)
                self.send_json(point, 201)
                return
            if path == "/api/measurements":
                measurement = STORE.add_measurement(payload)
                self.send_json(measurement, 201)
                return
            if path == "/api/simulate":
                point_id = payload.get("point_id")
                if not isinstance(point_id, str):
                    raise ValueError("Selecione um ponto para simular a enchente.")
                measurement = STORE.simulate_flood(point_id)
                self.send_json(measurement, 201)
                return
            self.send_json(STORE.update_rules(payload.get("rules")))
        except KeyError as error:
            self.send_json({"error": str(error.args[0])}, 404)
        except (ValueError, json.JSONDecodeError) as error:
            self.send_json({"error": str(error)}, 400)

    def do_DELETE(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if not path.startswith("/api/points/"):
            self.send_json({"error": "Endpoint não encontrado."}, 404)
            return
        point_id = unquote(path.removeprefix("/api/points/")).strip()
        try:
            STORE.delete_point(point_id)
            self.send_json({"deleted": point_id})
        except KeyError as error:
            self.send_json({"error": str(error.args[0])}, 404)

    def log_message(self, format: str, *args: object) -> None:
        print(f"[web] {self.address_string()} - {format % args}")

EscudoDAguaHandler = handler

def run() -> None:
    port = 3000
    print(f"Escudo d'Água disponível em http://localhost:{port}")
    ThreadingHTTPServer(("0.0.0.0", port), EscudoDAguaHandler).serve_forever()


if __name__ == "__main__":
    run()
