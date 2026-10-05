import unittest
# pyright: reportMissingImports=false
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from src.main import compile_source, run_file
from src.monitoramento import DEFAULT_RULES, MonitoramentoStore
from scripts.analisar_respostas import analisar
from scripts.integracao_forms import converter


ROOT = Path(__file__).parents[1]


class TestEscudoDAgua(unittest.TestCase):
    def test_monitoramento_persiste_pontos_medicoes_e_alertas(self):
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "monitoramento.json"
            store = MonitoramentoStore(path)
            point = store.create_point({"name": "Centro", "neighborhood": "Centro", "channel": "Rio"})
            measurement = store.add_measurement({"point_id": point["id"], "water_cm": 180, "rain_mm": 20})

            self.assertEqual(measurement["risk"], "CRÍTICO")
            reopened = MonitoramentoStore(path).snapshot()
            self.assertEqual(reopened["counts"]["points"], 8)
            self.assertEqual(reopened["measurements"][0]["id"], measurement["id"])
            self.assertEqual(reopened["alerts"][0]["point_id"], point["id"])

    def test_monitoramento_rejeita_medicao_invalida(self):
        with TemporaryDirectory() as temporary_directory:
            store = MonitoramentoStore(Path(temporary_directory) / "monitoramento.json")
            with self.assertRaisesRegex(ValueError, "entre 0 e 1000"):
                store.add_measurement({"point_id": "P01", "water_cm": -1, "rain_mm": 10})

    def test_migracao_adiciona_pontos_sem_apagar_estado_existente(self):
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "monitoramento.json"
            old_state = {
                "points": [
                    {"id": "P01", "name": "Baixada do Rio", "neighborhood": "Baixada do Rio", "channel": "Córrego Central", "simulated": True},
                    {"id": "P02", "name": "Vila dos Pescadores", "neighborhood": "Vila dos Pescadores", "channel": "Canal Sul", "simulated": True},
                    {"id": "P10", "name": "Ponto manual", "neighborhood": "Centro", "channel": "Rio", "simulated": True},
                ],
                "measurements": [{"id": "M0001", "point_id": "P01", "rain_mm": 5, "water_cm": 10, "risk": "NORMAL", "measured_at": "2026-01-01T00:00:00+00:00", "simulated": True}],
                "alerts": [],
                "rules": DEFAULT_RULES,
                "programs": [{"id": "R0001", "source": "preservar", "executed_at": "2026-01-01T00:00:00+00:00"}],
            }
            path.write_text(json.dumps(old_state), encoding="utf-8")

            migrated = MonitoramentoStore(path).snapshot()
            reopened = MonitoramentoStore(path).snapshot()

            self.assertEqual(migrated["counts"]["points"], 8)
            self.assertEqual(migrated["counts"]["measurements"], 6)
            self.assertTrue(any(point["id"] == "P10" for point in migrated["points"]))
            self.assertEqual(migrated["programs"][0]["source"], "preservar")
            self.assertEqual(reopened["counts"], migrated["counts"])

    def test_erros_incluem_trecho_e_coluna(self):
        lexical = compile_source("INICIO\n?FIM")
        self.assertEqual(lexical["lexical_errors"][0]["context"], "?FIM\n^")

        syntax = compile_source("INICIO\nAREA Centro (SENSOR, NIVEL)\nFIM")
        self.assertEqual(syntax["syntax_errors"][0]["context"], "FIM\n^")

    def test_t01_e_t02_aceitos(self):
        for name in ("T01_valido_simples.min", "T02_valido_varias_instrucoes.min"):
            with self.subTest(name=name):
                result = run_file(ROOT / "exemplos" / name)
                self.assertTrue(result["accepted"])
                self.assertEqual(result["lexical_errors"], [])
                self.assertEqual(result["syntax_errors"], [])

    def test_t03_e_t06_lexicos(self):
        for name in ("T03_comando_desconhecido.min", "T06_id_invalido.min"):
            with self.subTest(name=name):
                result = run_file(ROOT / "exemplos" / name)
                self.assertFalse(result["accepted"])
                self.assertGreater(len(result["lexical_errors"]), 0)

    def test_t04_e_t05_sintaticos(self):
        for name in ("T04_sem_ponto_virgula.min", "T05_parenteses_incorretos.min"):
            with self.subTest(name=name):
                result = run_file(ROOT / "exemplos" / name)
                self.assertFalse(result["accepted"])
                self.assertGreater(len(result["syntax_errors"]), 0)

    def test_planilha_real_gera_resumo_e_programa(self):
        csv_path = ROOT / "dados" / "respostas_google_forms.csv"
        summary = analisar(csv_path)
        self.assertEqual(summary["total_respostas"], 13)
        self.assertEqual(summary["risco"]["alto_percentual"], 62)
        output = ROOT / "dados" / "_teste_programa.min"
        try:
            converter(csv_path, output)
            result = run_file(output)
            self.assertTrue(result["accepted"])
            self.assertGreaterEqual(len(result["output"]), 13)
        finally:
            output.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
