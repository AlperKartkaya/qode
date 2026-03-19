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
        self.assertEqual(payload["workflow_result"]["status"], "SUCCESS")

    def test_scenario_endpoint_returns_report_summary(self) -> None:
        request_payload = {
            "scenario_path": str(ROOT / "examples" / "scenarios"),
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
