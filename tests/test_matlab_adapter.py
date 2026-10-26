
import csv
import json
import subprocess
from pathlib import Path

import pytest

import app.services.matlab_adapter as adapter_module
from app.services.matlab_adapter import MATLABAdapter


@pytest.fixture
def adapter():
    """Create an adapter without requiring MATLAB to be installed."""
    instance = MATLABAdapter()
    instance.matlab_available = True
    instance.matlab_path = "fake-matlab"
    instance.timeout = 30
    return instance


@pytest.fixture
def fake_temp_directory(tmp_path, monkeypatch):
    """Provide a controlled temporary directory for simulations."""
    directory = tmp_path / "pvg_matlab_test"

    def fake_mkdtemp(prefix=""):
        directory.mkdir(parents=True, exist_ok=True)
        return str(directory)

    monkeypatch.setattr(
        adapter_module.tempfile,
        "mkdtemp",
        fake_mkdtemp,
    )

    return directory


def successful_process_result(stdout="MATLAB R2025a", stderr=""):
    """Build a successful subprocess result."""
    return subprocess.CompletedProcess(
        args=["fake-matlab"],
        returncode=0,
        stdout=stdout,
        stderr=stderr,
    )


def failed_process_result(stderr="MATLAB execution error"):
    """Build a failed subprocess result."""
    return subprocess.CompletedProcess(
        args=["fake-matlab"],
        returncode=1,
        stdout="",
        stderr=stderr,
    )


def write_csv_output(directory, rows=None):
    """Write simulated MATLAB CSV output."""
    if rows is None:
        rows = [
            {
                "timestamp": 0.0,
                "pulse_bpm": 120.0,
                "spo2_percent": 98.0,
            },
            {
                "timestamp": 0.1,
                "pulse_bpm": 121.0,
                "spo2_percent": 97.5,
            },
        ]

    with (directory / "simulation_data.csv").open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "timestamp",
                "pulse_bpm",
                "spo2_percent",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def write_metadata(directory, metadata=None):
    """Write simulated MATLAB JSON metadata."""
    if metadata is None:
        metadata = {
            "scenario": "clean",
            "generation_method": "matlab_script",
            "synthetic_data": True,
        }

    (directory / "simulation_metadata.json").write_text(
        json.dumps(metadata),
        encoding="utf-8",
    )


# ---------------------------------------------------------
# Initialization and MATLAB availability tests
# ---------------------------------------------------------


def test_adapter_initializes_from_settings():
    instance = MATLABAdapter()

    assert instance.matlab_available is not None
    assert hasattr(instance, "matlab_path")
    assert hasattr(instance, "timeout")


def test_check_availability_when_matlab_is_disabled(adapter):
    adapter.matlab_available = False

    result = adapter.check_availability()

    assert result["available"] is False
    assert result["reason"] == "MATLAB path not configured"
    assert result["matlab_path"] is None


def test_check_availability_success(adapter, monkeypatch):
    monkeypatch.setattr(
        adapter_module.subprocess,
        "run",
        lambda *args, **kwargs: successful_process_result(
            stdout="MATLAB Version 25.1"
        ),
    )

    result = adapter.check_availability()

    assert result["available"] is True
    assert result["version"] == "MATLAB Version 25.1"
    assert result["matlab_path"] == "fake-matlab"


def test_check_availability_execution_failure(adapter, monkeypatch):
    monkeypatch.setattr(
        adapter_module.subprocess,
        "run",
        lambda *args, **kwargs: failed_process_result(
            stderr="MATLAB license unavailable"
        ),
    )

    result = adapter.check_availability()

    assert result["available"] is False
    assert "MATLAB execution failed" in result["reason"]
    assert "MATLAB license unavailable" in result["reason"]
    assert result["matlab_path"] == "fake-matlab"


def test_check_availability_executable_not_found(adapter, monkeypatch):
    def raise_not_found(*args, **kwargs):
        raise FileNotFoundError("Executable not found")

    monkeypatch.setattr(
        adapter_module.subprocess,
        "run",
        raise_not_found,
    )

    result = adapter.check_availability()

    assert result["available"] is False
    assert result["reason"] == "MATLAB executable not found"
    assert result["matlab_path"] == "fake-matlab"


def test_check_availability_timeout(adapter, monkeypatch):
    def raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(
            cmd="fake-matlab",
            timeout=10,
        )

    monkeypatch.setattr(
        adapter_module.subprocess,
        "run",
        raise_timeout,
    )

    result = adapter.check_availability()

    assert result["available"] is False
    assert result["reason"] == "MATLAB check timed out"
    assert result["matlab_path"] == "fake-matlab"


def test_check_availability_unexpected_exception(adapter, monkeypatch):
    def raise_error(*args, **kwargs):
        raise OSError("Unexpected operating system error")

    monkeypatch.setattr(
        adapter_module.subprocess,
        "run",
        raise_error,
    )

    result = adapter.check_availability()

    assert result["available"] is False
    assert "Error checking MATLAB" in result["reason"]
    assert "Unexpected operating system error" in result["reason"]


# ---------------------------------------------------------
# MATLAB script generation tests
# ---------------------------------------------------------


def test_generate_script_with_fixed_seed(adapter, tmp_path):
    script = adapter._generate_matlab_script(
        scenario="clean",
        duration=10,
        sample_rate=100,
        seed=42,
        output_dir=tmp_path,
    )

    assert "scenario = 'clean';" in script
    assert "duration = 10" in script
    assert "sample_rate = 100" in script
    assert "seed = 42;" in script
    assert "rng(seed);" in script
    assert "writetable" in script
    assert "jsonencode(metadata)" in script
    assert "synthetic_data = true" in script


def test_generate_script_without_seed_uses_random_seed(adapter, tmp_path):
    script = adapter._generate_matlab_script(
        scenario="movement",
        duration=5,
        sample_rate=50,
        seed=None,
        output_dir=tmp_path,
    )

    assert "scenario = 'movement';" in script
    assert "seed = randi(10000);" in script


# ---------------------------------------------------------
# Simulation tests
# ---------------------------------------------------------


def test_simulation_rejected_when_matlab_disabled(adapter):
    adapter.matlab_available = False

    with pytest.raises(
        RuntimeError,
        match="MATLAB is not available",
    ):
        adapter.run_simulation(
            scenario="clean",
            duration=1,
            sample_rate=10,
        )


def test_simulation_success_with_csv_and_metadata(
    adapter,
    fake_temp_directory,
    monkeypatch,
):
    directory = fake_temp_directory

    def fake_run(*args, **kwargs):
        write_csv_output(directory)
        write_metadata(directory)
        return successful_process_result(stdout="Simulation complete")

    monkeypatch.setattr(
        adapter_module.subprocess,
        "run",
        fake_run,
    )

    result = adapter.run_simulation(
        scenario="clean",
        duration=1,
        sample_rate=10,
        seed=123,
    )

    assert result["success"] is True
    assert result["source"] == "matlab"
    assert len(result["data"]) == 2
    assert result["data"][0]["timestamp"] == 0.0
    assert result["data"][0]["pulse_bpm"] == 120.0
    assert result["data"][0]["spo2_percent"] == 98.0
    assert result["metadata"]["scenario"] == "clean"
    assert result["metadata"]["synthetic_data"] is True

    # The adapter attempts to clean its temporary directory.
    assert not directory.exists()


def test_simulation_uses_fallback_metadata_when_json_missing(
    adapter,
    fake_temp_directory,
    monkeypatch,
):
    directory = fake_temp_directory

    def fake_run(*args, **kwargs):
        write_csv_output(directory)
        return successful_process_result()

    monkeypatch.setattr(
        adapter_module.subprocess,
        "run",
        fake_run,
    )

    result = adapter.run_simulation(
        scenario="movement",
        duration=1,
        sample_rate=10,
    )

    assert result["success"] is True
    assert result["metadata"] == {
        "scenario": "movement",
        "generation_method": "matlab",
        "synthetic_data": True,
    }

    assert not directory.exists()


def test_simulation_fails_when_csv_output_is_missing(
    adapter,
    fake_temp_directory,
    monkeypatch,
):
    directory = fake_temp_directory

    monkeypatch.setattr(
        adapter_module.subprocess,
        "run",
        lambda *args, **kwargs: successful_process_result(),
    )

    with pytest.raises(
        RuntimeError,
        match="MATLAB did not generate CSV output",
    ):
        adapter.run_simulation(
            scenario="clean",
            duration=1,
            sample_rate=10,
        )

    assert not directory.exists()


def test_simulation_fails_when_matlab_returns_nonzero(
    adapter,
    fake_temp_directory,
    monkeypatch,
):
    directory = fake_temp_directory

    monkeypatch.setattr(
        adapter_module.subprocess,
        "run",
        lambda *args, **kwargs: failed_process_result(
            stderr="Simulation crashed"
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="MATLAB execution failed",
    ):
        adapter.run_simulation(
            scenario="clean",
            duration=1,
            sample_rate=10,
        )

    assert not directory.exists()


def test_simulation_timeout_raises_runtime_error(
    adapter,
    fake_temp_directory,
    monkeypatch,
):
    directory = fake_temp_directory

    def raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(
            cmd="fake-matlab",
            timeout=adapter.timeout,
        )

    monkeypatch.setattr(
        adapter_module.subprocess,
        "run",
        raise_timeout,
    )

    with pytest.raises(
        RuntimeError,
        match="MATLAB simulation timed out after 30s",
    ):
        adapter.run_simulation(
            scenario="clean",
            duration=1,
            sample_rate=10,
        )

    assert not directory.exists()


def test_simulation_propagates_unexpected_exception(
    adapter,
    fake_temp_directory,
    monkeypatch,
):
    directory = fake_temp_directory

    def raise_error(*args, **kwargs):
        raise OSError("Unexpected simulation error")

    monkeypatch.setattr(
        adapter_module.subprocess,
        "run",
        raise_error,
    )

    with pytest.raises(
        OSError,
        match="Unexpected simulation error",
    ):
        adapter.run_simulation(
            scenario="clean",
            duration=1,
            sample_rate=10,
        )

    assert not directory.exists()


def test_simulation_handles_empty_csv_values(
    adapter,
    fake_temp_directory,
    monkeypatch,
):
    directory = fake_temp_directory

    def fake_run(*args, **kwargs):
        write_csv_output(
            directory,
            rows=[
                {
                    "timestamp": 0.0,
                    "pulse_bpm": "",
                    "spo2_percent": 98.0,
                }
            ],
        )
        write_metadata(directory)
        return successful_process_result()

    monkeypatch.setattr(
        adapter_module.subprocess,
        "run",
        fake_run,
    )

    result = adapter.run_simulation(
        scenario="clean",
        duration=1,
        sample_rate=10,
    )

    assert result["success"] is True
    assert result["data"][0]["pulse_bpm"] is None
    assert result["data"][0]["spo2_percent"] == 98.0
    assert not directory.exists()


def test_simulation_invalid_metadata_raises_error(
    adapter,
    fake_temp_directory,
    monkeypatch,
):
    directory = fake_temp_directory

    def fake_run(*args, **kwargs):
        write_csv_output(directory)
        (
            directory / "simulation_metadata.json"
        ).write_text(
            "{invalid json",
            encoding="utf-8",
        )
        return successful_process_result()

    monkeypatch.setattr(
        adapter_module.subprocess,
        "run",
        fake_run,
    )

    with pytest.raises(json.JSONDecodeError):
        adapter.run_simulation(
            scenario="clean",
            duration=1,
            sample_rate=10,
        )

    assert not directory.exists()
