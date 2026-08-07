from pathlib import Path
from unittest.mock import MagicMock, patch

from container_runner import ContainerInferenceRunner


def test_runner_requires_immutable_digest(tmp_path):
    runner = ContainerInferenceRunner(
        image="teknofest-2026/qode-final:mutable",
        use_gpu=False,
        timeout_seconds=570,
    )
    input_path = tmp_path / "input" / "video.mp4"
    input_path.parent.mkdir()
    input_path.write_bytes(b"video")

    result = runner.run(input_path, tmp_path / "output")

    assert result.exit_code == 2
    assert result.message == "IMAGE_NOT_DIGEST_PINNED"


@patch("container_runner.docker.from_env")
def test_runner_uses_offline_fixed_mounts_gpu_and_timeout(mock_from_env, tmp_path):
    input_path = tmp_path / "input" / "video.mp4"
    input_path.parent.mkdir()
    input_path.write_bytes(b"video")
    output_dir = tmp_path / "output"
    container = MagicMock()
    container.wait.return_value = {"StatusCode": 0}
    mock_from_env.return_value.containers.run.return_value = container
    image = "teknofest-2026/qode-final:frozen@sha256:" + "a" * 64
    runner = ContainerInferenceRunner(image=image, use_gpu=True, timeout_seconds=570)

    result = runner.run(input_path, output_dir)

    assert result.exit_code == 0
    kwargs = mock_from_env.return_value.containers.run.call_args.kwargs
    assert kwargs["network_disabled"] is True
    assert kwargs["detach"] is True
    assert kwargs["volumes"][str(input_path.parent.resolve())]["mode"] == "ro"
    assert kwargs["volumes"][str(output_dir.resolve())]["mode"] == "rw"
    assert kwargs["device_requests"][0].capabilities == [["gpu"]]
    container.wait.assert_called_once_with(timeout=570)
    container.remove.assert_called_once_with(force=True)
