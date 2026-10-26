
"""MATLAB/Simulink adapter for Pediatric VitalGuard."""

import csv
import json
import logging
import math
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.config import settings
from app.services.infant_dataset import select_infant_profile

logger = logging.getLogger(__name__)


class MATLABAdapter:
    """Adapter for MATLAB/Simulink integration."""

    ALLOWED_SCENARIOS = {
        "clean",
        "movement",
        "poor_contact",
        "excessive_noise",
        "baseline_drift",
        "signal_dropout",
    }

    def __init__(self):
        self.matlab_available = settings.MATLAB_AVAILABLE
        self.matlab_path = settings.MATLAB_PATH
        self.timeout = settings.MATLAB_TIMEOUT

    def check_availability(self) -> Dict[str, Any]:
        """Check whether MATLAB can be launched."""

        if not self.matlab_available:
            return {
                "available": False,
                "reason": "MATLAB path not configured",
                "matlab_path": None,
            }

        try:
            result = subprocess.run(
                [self.matlab_path, "-batch", "version"],
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )

            if result.returncode == 0:
                return {
                    "available": True,
                    "version": result.stdout.strip(),
                    "matlab_path": self.matlab_path,
                }

            return {
                "available": False,
                "reason": f"MATLAB execution failed: {result.stderr.strip()}",
                "matlab_path": self.matlab_path,
            }

        except FileNotFoundError:
            return {
                "available": False,
                "reason": "MATLAB executable not found",
                "matlab_path": self.matlab_path,
            }

        except subprocess.TimeoutExpired:
            return {
                "available": False,
                "reason": "MATLAB check timed out",
                "matlab_path": self.matlab_path,
            }

        except Exception as exc:
            logger.exception("MATLAB availability check failed")
            return {
                "available": False,
                "reason": f"Error checking MATLAB: {exc}",
                "matlab_path": self.matlab_path,
            }

    def run_simulation(
        self,
        scenario: str,
        duration: float,
        sample_rate: float,
        seed: Optional[int] = None,
        age_days: int = 30,
    ) -> Dict[str, Any]:
        """Execute Simulink using a dataset-informed infant profile."""

        if not self.matlab_available:
            raise RuntimeError("MATLAB is not available")

        self._validate_inputs(scenario, duration, sample_rate, seed)
        profile = select_infant_profile(age_days=age_days, seed=seed)

        temp_dir = Path(tempfile.mkdtemp(prefix="pvg_matlab_"))

        try:
            script_content = self._generate_matlab_script(
                scenario=scenario,
                duration=duration,
                sample_rate=sample_rate,
                seed=seed,
                output_dir=temp_dir,
                profile=profile,
            )

            script_path = temp_dir / "run_simulation.m"
            script_path.write_text(script_content, encoding="utf-8")

            logger.info(
                "Running MATLAB/Simulink: scenario=%s, duration=%s, "
                "sample_rate=%s",
                scenario,
                duration,
                sample_rate,
            )

            matlab_command = (
                f"run('{self._matlab_quote(script_path.resolve().as_posix())}')"
            )

            result = subprocess.run(
                [self.matlab_path, "-batch", matlab_command],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=str(temp_dir),
            )

            if result.returncode != 0:
                details = (result.stderr or result.stdout or "").strip()
                raise RuntimeError(f"MATLAB execution failed: {details}")

            csv_path = temp_dir / "simulation_data.csv"
            metadata_path = temp_dir / "simulation_metadata.json"

            if not csv_path.is_file():
                raise RuntimeError("MATLAB did not generate CSV output")

            with csv_path.open(
                "r",
                newline="",
                encoding="utf-8-sig",
            ) as csv_file:
                reader = csv.DictReader(csv_file)
                # Preserve compatibility with legacy CSV files.
                # Updated MATLAB output includes all six vital signs, but
                # older integrations may only contain pulse and SpO2.
                required_columns = {
                    "timestamp",
                    "pulse_bpm",
                    "spo2_percent",
                }

                if not reader.fieldnames or not required_columns.issubset(
                    set(reader.fieldnames)
                ):
                    raise RuntimeError(
                        "Simulation CSV is missing required columns: "
                        "timestamp, pulse_bpm, spo2_percent"
                    )

                data = []
                for row in reader:
                    parsed_row = {}

                    for key in reader.fieldnames:
                        value = row.get(key)

                        if value is None or value == "":
                            parsed_row[key] = None
                        else:
                            try:
                                parsed_row[key] = float(value)
                            except (ValueError, TypeError) as exc:
                                raise RuntimeError(
                                    f"Invalid numeric value in CSV column "
                                    f"{key!r}: {value!r}"
                                ) from exc

                    data.append(parsed_row)

            if not data:
                raise RuntimeError("MATLAB generated an empty simulation CSV")

            if metadata_path.is_file():
                with metadata_path.open("r", encoding="utf-8") as metadata_file:
                    metadata = json.load(metadata_file)
            else:
                # Preserve the existing fallback metadata contract.
                metadata = {
                    "scenario": scenario,
                    "generation_method": "matlab",
                    "synthetic_data": True,
                }

            logger.info(
                "MATLAB/Simulink simulation completed: %d samples",
                len(data),
            )

            return {
                "success": True,
                "data": data,
                "metadata": metadata,
                "source": "matlab",
            }

        except subprocess.TimeoutExpired as exc:
            logger.error(
                "MATLAB simulation timed out after %s seconds",
                self.timeout,
            )
            raise RuntimeError(
                f"MATLAB simulation timed out after {self.timeout}s"
            ) from exc

        except Exception:
            logger.exception("MATLAB simulation failed")
            raise

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    @staticmethod
    def _validate_inputs(
        scenario: str,
        duration: float,
        sample_rate: float,
        seed: Optional[int],
    ) -> None:
        """Validate simulation parameters."""

        if not isinstance(scenario, str):
            raise ValueError("scenario must be a string")

        if scenario not in MATLABAdapter.ALLOWED_SCENARIOS:
            raise ValueError(
                f"Unsupported scenario {scenario!r}. Allowed scenarios: "
                f"{', '.join(sorted(MATLABAdapter.ALLOWED_SCENARIOS))}"
            )

        if isinstance(duration, bool) or not isinstance(duration, (int, float)):
            raise ValueError("duration must be numeric")

        if not math.isfinite(duration) or duration <= 0:
            raise ValueError("duration must be a positive finite number")

        if isinstance(sample_rate, bool) or not isinstance(
            sample_rate, (int, float)
        ):
            raise ValueError("sample_rate must be numeric")

        if not math.isfinite(sample_rate) or sample_rate <= 0:
            raise ValueError("sample_rate must be a positive finite number")

        sample_count = duration * sample_rate

        if sample_count < 2 or sample_count > 10_000_000:
            raise ValueError(
                "Requested simulation sample count is outside "
                "supported limits"
            )

        if seed is not None and (
            isinstance(seed, bool)
            or not isinstance(seed, int)
            or seed < 0
        ):
            raise ValueError("seed must be a non-negative integer or None")

    @staticmethod
    def _matlab_quote(value: str) -> str:
        """Escape a string for a MATLAB single-quoted string literal."""

        return value.replace("'", "''")

    def _generate_matlab_script(
        self,
        scenario: str,
        duration: float,
        sample_rate: float,
        seed: Optional[int],
        output_dir: Path,
        profile: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate a MATLAB script for the saved model and vital profile."""

        self._validate_inputs(scenario, duration, sample_rate, seed)

        model_path = (
            Path(__file__).resolve().parents[2]
            / "matlab_simulation"
            / "PediatricVitalGuard.slx"
        )

        if not model_path.is_file():
            raise FileNotFoundError(
                f"Simulink model not found: {model_path}"
            )

        model_file = self._matlab_quote(model_path.as_posix())
        output_csv = self._matlab_quote(
            (output_dir / "simulation_data.csv").resolve().as_posix()
        )
        output_json = self._matlab_quote(
            (output_dir / "simulation_metadata.json").resolve().as_posix()
        )

        seed_expression = (
            str(seed) if seed is not None else "randi(10000)"
        )
        profile = profile or {
            "pulse_bpm": 140.0,
            "spo2_percent": 98.0,
            "respiratory_rate_bpm": 44.0,
            "systolic_bp_mmhg": 82.0,
            "diastolic_bp_mmhg": 50.0,
            "mean_bp_mmhg": 60.0,
        }
        baseline_values = {
            key: float(profile[key])
            for key in ("pulse_bpm", "spo2_percent", "respiratory_rate_bpm", "systolic_bp_mmhg", "diastolic_bp_mmhg", "mean_bp_mmhg")
        }

        return f"""
% Auto-generated Pediatric VitalGuard Simulink simulation.
scenario = '{scenario}';
duration = {duration};
sample_rate = {sample_rate};
seed = {seed_expression};

rng(seed);
synthetic_data = true;

fprintf('Running scenario: %s\\n', scenario);

model_file = '{model_file}';
output_csv = '{output_csv}';
output_json = '{output_json}';
model = 'PediatricVitalGuard';

if ~isfile(model_file)
    error('Simulink model file not found: %s', model_file);
end

load_system(model_file);

% Generate synthetic, dataset-informed signals.
n_samples = floor(duration * sample_rate);
t = (0:n_samples-1)' / sample_rate;

pulse_baseline = {baseline_values["pulse_bpm"]};
spo2_baseline = {baseline_values["spo2_percent"]};
resp_baseline = {baseline_values["respiratory_rate_bpm"]};
sbp_baseline = {baseline_values["systolic_bp_mmhg"]};
dbp_baseline = {baseline_values["diastolic_bp_mmhg"]};
mbp_baseline = {baseline_values["mean_bp_mmhg"]};

pulse = pulse_baseline + 2*randn(n_samples, 1);
spo2 = spo2_baseline + 0.3*randn(n_samples, 1);
respiratory_rate = resp_baseline + 1.5*randn(n_samples, 1);
systolic_bp = sbp_baseline + 1.5*randn(n_samples, 1);
diastolic_bp = dbp_baseline + randn(n_samples, 1);
mean_bp = mbp_baseline + randn(n_samples, 1);

% Apply scenario-specific signal changes.
switch scenario
    case 'clean'
        % Baseline synthetic signal.
    case 'movement'
        disturbance = sin(2*pi*2*t);
        pulse = pulse + 8*disturbance;
        spo2 = spo2 - 0.5*abs(disturbance);
        respiratory_rate = respiratory_rate + 3*disturbance;
    case 'poor_contact'
        pulse = pulse + 15*randn(n_samples, 1);
        spo2 = spo2 + 2*randn(n_samples, 1);
    case 'excessive_noise'
        pulse = pulse + 20*randn(n_samples, 1);
        spo2 = spo2 + 2*randn(n_samples, 1);
        respiratory_rate = respiratory_rate + 5*randn(n_samples, 1);
        systolic_bp = systolic_bp + 3*randn(n_samples, 1);
        diastolic_bp = diastolic_bp + 2*randn(n_samples, 1);
        mean_bp = mean_bp + 2*randn(n_samples, 1);
    case 'baseline_drift'
        drift = t / max(duration, eps);
        pulse = pulse + 10*drift;
        spo2 = spo2 - 0.5*drift;
        respiratory_rate = respiratory_rate + 2*drift;
    case 'signal_dropout'
        dropout_count = max(1, floor(0.05*n_samples));
        pulse(1:dropout_count) = 0;
        spo2(1:dropout_count) = NaN;
end

% Provide the From Workspace block's input variable.
inputSignal = [t, pulse];

% Run the actual saved Simulink model.
set_param(model, 'StopTime', num2str(t(end), 17));
simOut = sim(model, 'ReturnWorkspaceOutputs', 'on');

% Retrieve the Timeseries from the To Workspace block.
simulatedSignal = simOut.get('simulatedSignal');

if isempty(simulatedSignal)
    error('Simulink did not return simulatedSignal.');
end

sim_time = simulatedSignal.Time(:);
sim_values = squeeze(simulatedSignal.Data);
sim_values = sim_values(:);

if isempty(sim_time) || numel(sim_time) ~= numel(sim_values)
    error('Simulink output has an invalid time or data vector.');
end

% Resample the Simulink output onto the requested timestamps.
pulse_bpm = interp1(sim_time, sim_values, t, 'linear', 'extrap');

data_table = table(t, pulse_bpm, spo2, respiratory_rate, ...
    systolic_bp, diastolic_bp, mean_bp, ...
    'VariableNames', {{'timestamp', 'pulse_bpm', 'spo2_percent', ...
    'respiratory_rate_bpm', 'systolic_bp_mmhg', ...
    'diastolic_bp_mmhg', 'mean_bp_mmhg'}});

writetable(data_table, output_csv);

metadata = struct();
metadata.scenario = scenario;
metadata.duration = duration;
metadata.sample_rate = sample_rate;
metadata.seed = seed;
metadata.generation_method = 'matlab_simulink';
metadata.simulink_model = 'PediatricVitalGuard.slx';
metadata.simulink_executed = true;
metadata.synthetic_data = true;
metadata.pulse_source = 'Simulink pass-through of synthetic input';
metadata.spo2_source = 'Synthetic MATLAB signal using dataset baseline';
metadata.reference_dataset = 'normal_neonate_infant_vitals_0-6mo.xlsx';
metadata.profile_age_days = {int(profile.get('profile_age_days', 30))};
metadata.requested_age_days = {int(profile.get('age_days_requested', 30))};
metadata.profile_id = '{str(profile.get('profile_id', 'default'))}';
metadata.vital_signs = {{'pulse_bpm', 'spo2_percent', ...
    'respiratory_rate_bpm', 'systolic_bp_mmhg', ...
    'diastolic_bp_mmhg', 'mean_bp_mmhg'}};
metadata.sample_count = height(data_table);

fid = fopen(output_json, 'w');
if fid < 0
    error('Could not create simulation metadata JSON.');
end

cleanupFile = onCleanup(@() fclose(fid));
fprintf(fid, '%s', jsonencode(metadata));
clear cleanupFile;

close_system(model, 0);
fprintf('SIMULINK_SIMULATION_PASSED\\n');
"""
