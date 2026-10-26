from app.services.infant_dataset import (
    load_infant_dataset,
    select_infant_profile,
    VITAL_COLUMN_MAP,
)

df = load_infant_dataset()

assert len(df) == 100, f"Expected 100 records; got {len(df)}"
assert df["Age (days)"].min() == 0
assert df["Age (days)"].max() == 178

print("=" * 65)
print("INFANT DATASET LOADER TEST")
print("=" * 65)
print("Dataset records:", len(df))
print("Dataset age range:", df["Age (days)"].min(), "-", df["Age (days)"].max())

for age in [0, 7, 28, 60, 90, 150, 178, 180]:
    first = select_infant_profile(age, seed=42)
    second = select_infant_profile(age, seed=42)

    assert first == second, f"Reproducibility failed at age {age}"
    assert abs(first["profile_age_days"] - age) <= 14
    assert all(key in first for key in VITAL_COLUMN_MAP)

    print(
        f"\nAge requested: {age} days"
        f"\n  Selected profile age: {first['profile_age_days']} days"
        f"\n  Age group: {first['age_group']}"
        f"\n  Heart rate: {first['pulse_bpm']}"
        f"\n  SpO2: {first['spo2_percent']}"
        f"\n  Respiratory rate: {first['respiratory_rate_bpm']}"
        f"\n  Systolic BP: {first['systolic_bp_mmhg']}"
        f"\n  Diastolic BP: {first['diastolic_bp_mmhg']}"
        f"\n  Mean BP: {first['mean_bp_mmhg']}"
    )

print("\nPASS: Dataset loading, age selection, six vital signs, and reproducibility.")
