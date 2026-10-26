from pathlib import Path
import pandas as pd

path = Path("data/reference/normal_neonate_infant_vitals_0-6mo.xlsx")

if not path.is_file():
    raise FileNotFoundError(f"Dataset not found: {path.resolve()}")

df = pd.read_excel(path, sheet_name="Data")

print("=" * 65)
print("PEDIATRIC VITALGUARD - DATASET INSPECTION")
print("=" * 65)

print(f"\nTotal records: {len(df)}")
print("\nColumns:")
for column in df.columns:
    print(f"  - {column}")

print("\nAge range:")
print(f"  Minimum: {df['Age (days)'].min()} days")
print(f"  Maximum: {df['Age (days)'].max()} days")

print("\nRecords by age group:")
print(df["Age group"].value_counts(dropna=False).to_string())

columns = [
    "Heart rate (beats/min)",
    "SpO2 (%)",
    "Respiratory rate (breaths/min)",
    "Systolic BP (mmHg)",
    "Diastolic BP (mmHg)",
    "Mean BP (mmHg)",
]

print("\nVital-sign statistics:")
print(df[columns].describe().round(2).to_string())

print("\nMissing values:")
print(df[columns + ["Age (days)"]].isna().sum().to_string())

print("\nDataset inspection completed.")
