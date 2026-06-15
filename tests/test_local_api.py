from __future__ import annotations

import json
import sys
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from smart_road_safety.local_api import create_local_api_server


class LocalApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.server = create_local_api_server(host="127.0.0.1", port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.host = str(self.server.server_address[0])
        self.port = int(self.server.server_address[1])

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def test_health_endpoint_returns_ok(self) -> None:
        connection = HTTPConnection(self.host, self.port)
        connection.request("GET", "/health")
        response = connection.getresponse()
        payload = json.loads(response.read().decode("utf-8"))
        connection.close()

        self.assertEqual(response.status, 200)
        self.assertEqual(payload["status"], "ok")

    def test_orchestration_endpoint_returns_success_payload(self) -> None:
        request_payload = {
            "request": json.loads(
                (ROOT / "examples" / "mock_orchestration_request.json").read_text(
                    encoding="utf-8"
                )
            )
        }
        connection = HTTPConnection(self.host, self.port)
        connection.request(
            "POST",
            "/orchestration/run",
            body=json.dumps(request_payload),
            headers={"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        payload = json.loads(response.read().decode("utf-8"))
        connection.close()

        self.assertEqual(response.status, 200)
        self.assertEqual(payload["status"], "SUCCESS")

    def test_analysis_session_endpoint_returns_combined_result(self) -> None:
        request_payload = {
            "request": json.loads(
                (ROOT / "examples" / "analysis_session_request.json").read_text(
                    encoding="utf-8"
                )
            )
        }
        connection = HTTPConnection(self.host, self.port)
        connection.request(
            "POST",
            "/analysis-session/run",
            body=json.dumps(request_payload),
            headers={"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        payload = json.loads(response.read().decode("utf-8"))
        connection.close()

        self.assertEqual(response.status, 200)
        self.assertTrue(payload["analysis_result"]["target_vehicle_detected"])
        self.assertEqual(
            payload["analysis_result"]["driver_risk_label"],
            "smoking_and_unsafe_scanning",
        )
        self.assertEqual(payload["workflow_result"]["status"], "SUCCESS")

    @unittest.skipUnless((ROOT / "data" / "datasets" / "state-farm-distracted-driver" / "driver_imgs_list.csv").exists(), "Requires real dataset")
    def test_analysis_session_endpoint_returns_state_farm_result(self) -> None:
        request_payload = {
            "request": json.loads(
                (ROOT / "examples" / "analysis_session_state_farm.json").read_text(
                    encoding="utf-8"
                )
            )
        }
        connection = HTTPConnection(self.host, self.port)
        connection.request(
            "POST",
            "/analysis-session/run",
            body=json.dumps(request_payload),
            headers={"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        payload = json.loads(response.read().decode("utf-8"))
        connection.close()

        self.assertEqual(response.status, 200)
        self.assertEqual(payload["analysis_result"]["driver_risk_label"], "texting_right")
        self.assertFalse(payload["analysis_result"]["target_vehicle_detected"])

    def test_competition_ftr_output_endpoint_returns_source_of_truth_schema(self) -> None:
        request_payload = {
            "request": json.loads(
                (ROOT / "examples" / "analysis_session_request.json").read_text(
                    encoding="utf-8"
                )
            ),
            "vehicle_info": json.loads(
                (ROOT / "examples" / "ftr_vehicle_info.json").read_text(
                    encoding="utf-8"
                )
            ),
            "video_id": "video_1.mp4",
            "event_time_seconds": 1.5,
        }
        connection = HTTPConnection(self.host, self.port)
        connection.request(
            "POST",
            "/competition/ftr-output",
            body=json.dumps(request_payload),
            headers={"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        payload = json.loads(response.read().decode("utf-8"))
        connection.close()

        self.assertEqual(response.status, 200)
        self.assertEqual(payload["result"]["video_id"], "video_1.mp4")
        self.assertEqual(payload["result"]["arac_bilgisi"]["plaka"], "34ABC123")
        self.assertEqual(
            {event["etiket"] for event in payload["result"]["tespitler"]},
            {"sigara_icme", "etrafa_bakinma"},
        )

    def test_dataset_inventory_endpoint_returns_real_inventory(self) -> None:
        request_payload = {
            "manifest_path": str(ROOT / "data" / "real_dataset_manifest.json"),
            "dataset_root": str(ROOT / "data"),
        }
        connection = HTTPConnection(self.host, self.port)
        connection.request(
            "POST",
            "/dataset/inventory",
            body=json.dumps(request_payload),
            headers={"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        payload = json.loads(response.read().decode("utf-8"))
        connection.close()

        self.assertEqual(response.status, 200)
        self.assertEqual(payload["sample_count"], 3)

    def test_scenario_endpoint_returns_report_summary(self) -> None:
        request_payload = {
            "scenario_path": str(ROOT / "examples" / "dataset_scenarios"),
        }
        connection = HTTPConnection(self.host, self.port)
        connection.request(
            "POST",
            "/evaluation/run-scenarios",
            body=json.dumps(request_payload),
            headers={"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        payload = json.loads(response.read().decode("utf-8"))
        connection.close()

        self.assertEqual(response.status, 200)
        self.assertEqual(payload["report"]["summary"]["scenario_count"], 3)

    def test_export_endpoint_writes_markdown_file(self) -> None:
        evaluation_payload = {
            "scenario_path": str(ROOT / "examples" / "dataset_scenarios"),
            "output_path": str(ROOT / "out" / "scenario_report.json"),
        }
        evaluation_connection = HTTPConnection(self.host, self.port)
        evaluation_connection.request(
            "POST",
            "/evaluation/run-scenarios",
            body=json.dumps(evaluation_payload),
            headers={"Content-Type": "application/json"},
        )
        evaluation_response = evaluation_connection.getresponse()
        evaluation_response.read()
        evaluation_connection.close()

        output_path = ROOT / "out" / "scenario_report_api.md"
        request_payload = {
            "report_path": str(ROOT / "out" / "scenario_report.json"),
            "output_path": str(output_path),
        }
        connection = HTTPConnection(self.host, self.port)
        connection.request(
            "POST",
            "/export/report-markdown",
            body=json.dumps(request_payload),
            headers={"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        payload = json.loads(response.read().decode("utf-8"))
        connection.close()

        self.assertEqual(response.status, 200)
        self.assertEqual(payload["output_path"], str(output_path))
        self.assertTrue(output_path.exists())


if __name__ == "__main__":
    unittest.main()
