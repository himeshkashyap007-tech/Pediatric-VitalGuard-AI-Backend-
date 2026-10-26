import json
from app.services.matlab_adapter import MATLABAdapter

adapter = MATLABAdapter()

scenarios = [
    "clean",
    "movement",
    "poor_contact",
    "excessive_noise",
    "baseline_drift",
    "signal_dropout",
]

all_passed = True

for scenario in scenarios:
    print("\n" + "=" * 65)
    print(f"SCENARIO: {scenario.upper()}")
    print("=" * 65)

    try:
        result = adapter.run_simulation(
            scenario=scenario,
            duration=2,
            sample_rate=100,
            seed=42,
        )

        data = result["data"]
        metadata = result["metadata"]

        assert result["success"] is True
        assert result["source"] == "matlab"
        assert len(data) == 200
        assert metadata.get("simulink_executed") is True
        assert metadata.get("synthetic_data") is True

        for row in data:
            assert {"timestamp", "pulse_bpm", "spo2_percent"} <= row.keys()

        print("STATUS       : PASS")
        print("SAMPLES      :", len(data))
        print("SIMULINK     :", metadata["simulink_executed"])
        print("SYNTHETIC    :", metadata["synthetic_data"])
        print("FIRST SAMPLE :", json.dumps(data[0], indent=2))

    except Exception as exc:
        all_passed = False
        print("STATUS       : FAIL")
        print("ERROR        :", repr(exc))

print("\n" + "=" * 65)
print("OVERALL RESULT:", "ALL SCENARIOS PASSED" if all_passed else "FAILURES FOUND")
print("=" * 65)

if not all_passed:
    raise SystemExit(1)
