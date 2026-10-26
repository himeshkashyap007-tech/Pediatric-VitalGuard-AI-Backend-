from pathlib import Path
import ast

path = Path("app/services/matlab_adapter.py")
source = path.read_text(encoding="utf-8-sig")

old = '''                expected_columns = {
                    "timestamp",
                    "pulse_bpm",
                    "spo2_percent",
                    "respiratory_rate_bpm",
                    "systolic_bp_mmhg",
                    "diastolic_bp_mmhg",
                    "mean_bp_mmhg",
                }

                if not reader.fieldnames or not expected_columns.issubset(
                    set(reader.fieldnames)
                ):
                    raise RuntimeError(
                        "Simulation CSV is missing required columns: "
                        "timestamp, pulse_bpm, spo2_percent, "
                        "respiratory_rate_bpm, systolic_bp_mmhg, "
                        "diastolic_bp_mmhg, mean_bp_mmhg"
                    )
'''

new = '''                # Preserve compatibility with legacy CSV files.
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
'''

if old not in source:
    raise SystemExit(
        "Expected validation block not found. No changes made."
    )

backup = path.with_suffix(".py.before_csv_compat_fix.bak")
if not backup.exists():
    backup.write_text(source, encoding="utf-8")

updated = source.replace(old, new, 1)
ast.parse(updated)
path.write_text(updated, encoding="utf-8")

print("SUCCESS: Legacy CSV compatibility restored.")
print("Backup:", backup)
