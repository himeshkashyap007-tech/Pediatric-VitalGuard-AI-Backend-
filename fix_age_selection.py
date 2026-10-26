from pathlib import Path

path = Path("app/services/infant_dataset.py")
source = path.read_text(encoding="utf-8-sig")

start = source.find("def select_infant_profile(")
if start == -1:
    raise SystemExit("ERROR: select_infant_profile was not found. No changes made.")

replacement = '''def select_infant_profile(
    age_days: int,
    seed: int | None = None,
    path: str | Path | None = None,
) -> dict:
    """Select a reproducible reference profile within the requested age group."""
    if isinstance(age_days, bool) or not isinstance(age_days, int):
        raise ValueError("age_days must be an integer")
    if not 0 <= age_days <= 180:
        raise ValueError("age_days must be between 0 and 180")
    if seed is not None and (
        isinstance(seed, bool) or not isinstance(seed, int) or seed < 0
    ):
        raise ValueError("seed must be a non-negative integer or None")

    if age_days <= 7:
        requested_group = "0-7 days"
    elif age_days <= 28:
        requested_group = "8-28 days"
    elif age_days <= 90:
        requested_group = "1-3 months"
    else:
        requested_group = "3-6 months"

    frame = load_infant_dataset(path)
    candidates = frame.loc[frame["Age group"] == requested_group].copy()

    if candidates.empty:
        raise ValueError(
            f"No reference profiles found for age group {requested_group!r}"
        )

    candidates["_age_distance"] = (
        candidates["Age (days)"] - age_days
    ).abs()
    nearest_distance = candidates["_age_distance"].min()
    nearest = candidates.loc[
        candidates["_age_distance"] == nearest_distance
    ]

    rng = random.Random(seed)
    selected_index = rng.choice(list(nearest.index))
    row = frame.loc[selected_index]

    profile = {
        "age_days_requested": age_days,
        "profile_age_days": int(row["Age (days)"]),
        "profile_id": str(row["Patient ID"]),
        "sex": str(row["Sex"]),
        "age_group": str(row["Age group"]),
        "requested_age_group": requested_group,
        "selection_method": (
            "exact_age"
            if int(row["Age (days)"]) == age_days
            else "nearest_age_within_group"
        ),
        "dataset_filename": DATASET_FILENAME,
        "synthetic_data": True,
        "profile_seed": seed,
    }

    for output_name, source_column in VITAL_COLUMN_MAP.items():
        profile[output_name] = float(row[source_column])

    return profile
'''

backup = path.with_suffix(".py.before_age_fix.bak")
if not backup.exists():
    backup.write_text(source, encoding="utf-8")

path.write_text(source[:start] + replacement, encoding="utf-8")
print("SUCCESS: Replaced select_infant_profile without regex.")
print("Backup:", backup)
