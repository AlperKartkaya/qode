from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import docker


@dataclass(frozen=True)
class RunnerResult:
    exit_code: int
    message: str


class ContainerInferenceRunner:
    def __init__(self, *, image: str, use_gpu: bool, timeout_seconds: int) -> None:
        self.image = image
        self.use_gpu = use_gpu
        self.timeout_seconds = timeout_seconds

    def run(self, input_path: Path, output_dir: Path) -> RunnerResult:
        if not input_path.is_file():
            return RunnerResult(2, "INPUT_MISSING")
        if not self.image.startswith("teknofest-2026/"):
            return RunnerResult(2, "INVALID_IMAGE_NAME")
        output_dir.mkdir(parents=True, exist_ok=True)
        device_requests = (
            [docker.types.DeviceRequest(count=-1, capabilities=[["gpu"]])]
            if self.use_gpu
            else []
        )
        container = None
        try:
            client = docker.from_env()
            container = client.containers.run(
                self.image,
                detach=True,
                network_disabled=True,
                device_requests=device_requests,
                volumes={
                    str(input_path.parent.resolve()): {
                        "bind": "/app/data/input",
                        "mode": "ro",
                    },
                    str(output_dir.resolve()): {
                        "bind": "/app/data/output",
                        "mode": "rw",
                    },
                },
            )
            result = container.wait(timeout=self.timeout_seconds)
            exit_code = int(result.get("StatusCode", 1))
            if exit_code != 0:
                print(f"Container failed with exit code {exit_code}. Logs:")
                logs_text = ""
                try:
                    logs_text = container.logs().decode('utf-8', errors='replace')
                    print(logs_text)
                    log_file = output_dir / "container_error.log"
                    log_file.write_text(logs_text, encoding="utf-8")
                except Exception as log_exc:
                    print(f"Failed to fetch logs: {log_exc}")
                
                error_msg = "NONZERO_EXIT"
                if logs_text:
                    last_lines = " | ".join(logs_text.strip().splitlines()[-3:])
                    error_msg = f"Crash: {last_lines}"[:250]
                
                return RunnerResult(exit_code, error_msg)
            return RunnerResult(0, "COMPLETED")
        except Exception as exc:
            return RunnerResult(1, f"CONTAINER_ERROR_{type(exc).__name__.upper()}")
        finally:
            if container is not None:
                try:
                    container.remove(force=True)
                except Exception:
                    pass
