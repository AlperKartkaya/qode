from __future__ import annotations

import json
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from ..analysis import AnalysisSessionRequest, run_analysis_session
from ..evaluation import run_scenario_suite
from ..export import export_scenario_report_markdown
from ..integration import MockNumberVerificationGateway, MockQualityOnDemandGateway
from ..orchestration import MockSessionRequest, MockTelecomOrchestrator
from ..policy import QodPolicy, load_default_qod_policy


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, indent=2).encode("utf-8")


def _read_json(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    content_length = int(handler.headers.get("Content-Length", "0"))
    raw_body = handler.rfile.read(content_length) if content_length > 0 else b"{}"
    return json.loads(raw_body.decode("utf-8"))


def _load_policy(policy_path: str | None) -> QodPolicy:
    if policy_path is None:
        return load_default_qod_policy()
    return QodPolicy.from_path(policy_path)


def _build_handler() -> type[BaseHTTPRequestHandler]:
    class LocalApiHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path != "/health":
                self._send_json(
                    HTTPStatus.NOT_FOUND,
                    {"error": "NOT_FOUND", "message": "Unknown endpoint."},
                )
                return

            self._send_json(
                HTTPStatus.OK,
                {"status": "ok", "service": "smart-road-safety-local-api"},
            )

        def do_POST(self) -> None:
            try:
                payload = _read_json(self)
                if self.path == "/orchestration/run":
                    self._handle_orchestration(payload)
                    return
                if self.path == "/analysis-session/run":
                    self._handle_analysis_session(payload)
                    return
                if self.path == "/evaluation/run-scenarios":
                    self._handle_scenarios(payload)
                    return
                if self.path == "/export/report-markdown":
                    self._handle_export(payload)
                    return
                self._send_json(
                    HTTPStatus.NOT_FOUND,
                    {"error": "NOT_FOUND", "message": "Unknown endpoint."},
                )
            except ValueError as error:
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": "INVALID_REQUEST", "message": str(error)},
                )

        def log_message(self, format: str, *args: object) -> None:
            return

        def _handle_orchestration(self, payload: dict[str, Any]) -> None:
            request = MockSessionRequest.from_dict(payload["request"])
            gateway_payload = payload.get("gateway_setup", {})
            policy = _load_policy(payload.get("policy_path"))
            orchestrator = MockTelecomOrchestrator(
                number_verification_gateway=MockNumberVerificationGateway(
                    verified_numbers=tuple(
                        str(value)
                        for value in gateway_payload.get(
                            "verified_numbers", [request.phone_number]
                        )
                    )
                ),
                quality_on_demand_gateway=MockQualityOnDemandGateway(
                    available_profiles=tuple(
                        str(value)
                        for value in gateway_payload.get(
                            "available_profiles", ["standard", "boosted"]
                        )
                    ),
                    denied_session_ids=tuple(
                        str(value)
                        for value in gateway_payload.get("denied_session_ids", [])
                    ),
                ),
                policy=policy,
            )
            result = orchestrator.run(request)
            self._send_json(HTTPStatus.OK, asdict(result))

        def _handle_analysis_session(self, payload: dict[str, Any]) -> None:
            request = AnalysisSessionRequest.from_dict(payload["request"])
            policy = _load_policy(payload.get("policy_path"))
            result = run_analysis_session(request=request, policy=policy)
            self._send_json(HTTPStatus.OK, asdict(result))

        def _handle_scenarios(self, payload: dict[str, Any]) -> None:
            scenario_path = payload["scenario_path"]
            output_path = payload.get("output_path")
            policy = _load_policy(payload.get("policy_path"))
            report = run_scenario_suite(
                scenario_path=scenario_path,
                output_path=output_path,
                policy=policy,
            )
            response = {
                "report": asdict(report),
                "report_path": None if output_path is None else str(Path(output_path)),
            }
            self._send_json(HTTPStatus.OK, response)

        def _handle_export(self, payload: dict[str, Any]) -> None:
            target = export_scenario_report_markdown(
                report_path=payload["report_path"],
                output_path=payload["output_path"],
            )
            self._send_json(
                HTTPStatus.OK,
                {"output_path": str(target)},
            )

        def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
            body = _json_bytes(payload)
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return LocalApiHandler


def create_local_api_server(
    host: str = "127.0.0.1", port: int = 8000
) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), _build_handler())


def run_local_api_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = create_local_api_server(host=host, port=port)
    try:
        server.serve_forever()
    finally:
        server.server_close()
