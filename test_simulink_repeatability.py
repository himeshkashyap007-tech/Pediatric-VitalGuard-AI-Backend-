from app.services.matlab_adapter import MATLABAdapter

adapter = MATLABAdapter()

a = adapter.run_simulation(
    scenario="clean", duration=2, sample_rate=100, seed=42
)
b = adapter.run_simulation(
    scenario="clean", duration=2, sample_rate=100, seed=42
)

assert a["data"] == b["data"], "FAIL: Identical seeds produced different data"

print("PASS: Identical seeds produced identical data.")
print("Samples checked:", len(a["data"]))
