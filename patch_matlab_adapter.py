from pathlib import Path
import ast

path = Path("app/services/matlab_adapter.py")
source = path.read_text(encoding="utf-8-sig")

backup = path.with_suffix(".py.before_dataset_integration.bak")
if not backup.exists():
    backup.write_text(source, encoding="utf-8")

# Confirm this is the expected adapter before patching.
ast.parse(source)

if "from app.services.infant_dataset import select_infant_profile" in source:
    raise SystemExit(
        "Dataset import already exists. Stop and inspect the adapter before patching."
    )

source = source.replace(
    "from app.core.config import settings",
    "from app.core.config import settings\n"
    "from app.services.infant_dataset import select_infant_profile",
    1,
)

source = source.replace(
    "        seed: Optional[int] = None,\n"
    "    ) -> Dict[str, Any]:\n"
    '        """Execute the saved Simulink model and return generated data."""',
    "        seed: Optional[int] = None,\n"
    "        age_days: int = 30,\n"
    "    ) -> Dict[str, Any]:\n"
    '        """Execute Simulink using a dataset-informed infant profile."""',
    1,
)

source = source.replace(
    "        self._validate_inputs(scenario, duration, sample_rate, seed)\n\n"
    "        temp_dir = Path(tempfile.mkdtemp(prefix=\"pvg_matlab_\"))",
    "        self._validate_inputs(scenario, duration, sample_rate, seed)\n"
    "        profile = select_infant_profile(age_days=age_days, seed=seed)\n\n"
    "        temp_dir = Path(tempfile.mkdtemp(prefix=\"pvg_matlab_\"))",
    1,
)

source = source.replace(
    "                seed=seed,\n"
    "                output_dir=temp_dir,",
    "                seed=seed,\n"
    "                output_dir=temp_dir,\n"
    "                profile=profile,",
    1,
)

source = source.replace(
    '                    "spo2_percent",\n'
    "                }",
    '                    "spo2_percent",\n'
    '                    "respiratory_rate_bpm",\n'
    '                    "systolic_bp_mmhg",\n'
    '                    "diastolic_bp_mmhg",\n'
    '                    "mean_bp_mmhg",\n'
    "                }",
    1,
)

source = source.replace(
    '                        "timestamp, pulse_bpm, spo2_percent"',
    '                        "timestamp, pulse_bpm, spo2_percent, "\n'
    '                        "respiratory_rate_bpm, systolic_bp_mmhg, "\n'
    '                        "diastolic_bp_mmhg, mean_bp_mmhg"',
    1,
)

source = source.replace(
    "        output_dir: Path,\n"
    "    ) -> str:\n"
    '        """Generate a MATLAB script that executes PediatricVitalGuard.slx."""',
    "        output_dir: Path,\n"
    "        profile: Optional[Dict[str, Any]] = None,\n"
    "    ) -> str:\n"
    '        """Generate a MATLAB script for the saved model and vital profile."""',
    1,
)

# Build default profile values for legacy direct calls to the private helper.
source = source.replace(
    "        seed_expression = (\n"
    '            str(seed) if seed is not None else "randi(10000)"\n'
    "        )\n\n"
    "        return f\"\"\"",
    "        seed_expression = (\n"
    '            str(seed) if seed is not None else "randi(10000)"\n'
    "        )\n"
    "        profile = profile or {\n"
    '            "pulse_bpm": 140.0,\n'
    '            "spo2_percent": 98.0,\n'
    '            "respiratory_rate_bpm": 44.0,\n'
    '            "systolic_bp_mmhg": 82.0,\n'
    '            "diastolic_bp_mmhg": 50.0,\n'
    '            "mean_bp_mmhg": 60.0,\n'
    "        }\n"
    "        baseline_values = {\n"
    '            key: float(profile[key])\n'
    '            for key in ("pulse_bpm", "spo2_percent", '
    '"respiratory_rate_bpm", "systolic_bp_mmhg", '
    '"diastolic_bp_mmhg", "mean_bp_mmhg")\n'
    "        }\n\n"
    "        return f\"\"\"",
    1,
)

# Add reference profile baselines and generate six output signals.
old_signal_block = """% Generate synthetic input samples.
n_samples = floor(duration * sample_rate);
t = (0:n_samples-1)' / sample_rate;

pulse = 120 + 10*randn(n_samples, 1);
spo2 = 98 + randn(n_samples, 1);

% Apply scenario-specific changes to the synthetic pulse signal."""
new_signal_block = """% Generate synthetic, dataset-informed signals.
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

% Apply scenario-specific signal changes."""
if old_signal_block not in source:
    raise SystemExit("Could not find expected signal block; no adapter changes saved.")

source = source.replace(old_signal_block, new_signal_block, 1)

source = source.replace(
    "    case 'movement'\n"
    "        pulse = pulse + 8*sin(2*pi*2*t);\n"
    "    case 'poor_contact'\n"
    "        pulse = pulse + 15*randn(n_samples, 1);\n"
    "    case 'excessive_noise'\n"
    "        pulse = pulse + 20*randn(n_samples, 1);\n"
    "    case 'baseline_drift'\n"
    "        pulse = pulse + 10*(t / max(duration, eps));\n"
    "    case 'signal_dropout'\n"
    "        dropout_count = max(1, floor(0.05*n_samples));\n"
    "        pulse(1:dropout_count) = 0;\n"
    "end",
    "    case 'movement'\n"
    "        disturbance = sin(2*pi*2*t);\n"
    "        pulse = pulse + 8*disturbance;\n"
    "        spo2 = spo2 - 0.5*abs(disturbance);\n"
    "        respiratory_rate = respiratory_rate + 3*disturbance;\n"
    "    case 'poor_contact'\n"
    "        pulse = pulse + 15*randn(n_samples, 1);\n"
    "        spo2 = spo2 + 2*randn(n_samples, 1);\n"
    "    case 'excessive_noise'\n"
    "        pulse = pulse + 20*randn(n_samples, 1);\n"
    "        spo2 = spo2 + 2*randn(n_samples, 1);\n"
    "        respiratory_rate = respiratory_rate + 5*randn(n_samples, 1);\n"
    "        systolic_bp = systolic_bp + 3*randn(n_samples, 1);\n"
    "        diastolic_bp = diastolic_bp + 2*randn(n_samples, 1);\n"
    "        mean_bp = mean_bp + 2*randn(n_samples, 1);\n"
    "    case 'baseline_drift'\n"
    "        drift = t / max(duration, eps);\n"
    "        pulse = pulse + 10*drift;\n"
    "        spo2 = spo2 - 0.5*drift;\n"
    "        respiratory_rate = respiratory_rate + 2*drift;\n"
    "    case 'signal_dropout'\n"
    "        dropout_count = max(1, floor(0.05*n_samples));\n"
    "        pulse(1:dropout_count) = 0;\n"
    "        spo2(1:dropout_count) = NaN;\n"
    "end",
    1,
)

source = source.replace(
    "data_table = table(t, pulse_bpm, spo2, ...\n"
    "    'VariableNames', {{'timestamp', 'pulse_bpm', 'spo2_percent'}});",
    "data_table = table(t, pulse_bpm, spo2, respiratory_rate, ...\n"
    "    systolic_bp, diastolic_bp, mean_bp, ...\n"
    "    'VariableNames', {{'timestamp', 'pulse_bpm', 'spo2_percent', ...\n"
    "    'respiratory_rate_bpm', 'systolic_bp_mmhg', ...\n"
    "    'diastolic_bp_mmhg', 'mean_bp_mmhg'}});",
    1,
)

source = source.replace(
    "metadata.spo2_source = 'Synthetic MATLAB signal';\n"
    "metadata.sample_count = height(data_table);",
    "metadata.spo2_source = 'Synthetic MATLAB signal using dataset baseline';\n"
    "metadata.reference_dataset = 'normal_neonate_infant_vitals_0-6mo.xlsx';\n"
    "metadata.profile_age_days = {int(profile.get('profile_age_days', 30))};\n"
    "metadata.requested_age_days = {int(profile.get('age_days_requested', 30))};\n"
    "metadata.profile_id = '{str(profile.get('profile_id', 'default'))}';\n"
    "metadata.vital_signs = {{'pulse_bpm', 'spo2_percent', ...\n"
    "    'respiratory_rate_bpm', 'systolic_bp_mmhg', ...\n"
    "    'diastolic_bp_mmhg', 'mean_bp_mmhg'}};\n"
    "metadata.sample_count = height(data_table);",
    1,
)

# Ensure expected blocks were actually patched.
for marker in (
    "profile=profile,",
    "respiratory_rate_bpm",
    "reference_dataset",
    "age_days: int = 30",
):
    if marker not in source:
        raise SystemExit(f"Patch validation failed: missing {marker!r}")

ast.parse(source)
path.write_text(source, encoding="utf-8")
print("Adapter integration patch applied.")
print("Backup:", backup)
