"""
Generates a synthetic dataset of 20 patients for the Mini Healthcare Assistant.
Run once: python data/generate_data.py
Writes data/patients.csv with columns:
    user_id, first_name, last_name, city, dietary_preference, medical_condition, cgm_reading
All data is fake (Faker) — no real patient information is used.
"""
import csv
import random
from pathlib import Path

from faker import Faker

fake = Faker()
Faker.seed(42)
random.seed(42)

DIETARY_PREFERENCES = ["veg", "non-veg", "vegan"]
MEDICAL_CONDITIONS = [
    "Type 2 Diabetes",
    "Hypertension",
    "Pre-diabetes",
    "High Cholesterol",
    "Obesity",
    "None",
]

OUT_PATH = Path(__file__).parent / "patients.csv"


def generate_patients(n: int = 20):
    rows = []
    for i in range(1, n + 1):
        rows.append(
            {
                "user_id": i,
                "first_name": fake.first_name(),
                "last_name": fake.last_name(),
                "city": fake.city(),
                "dietary_preference": random.choice(DIETARY_PREFERENCES),
                "medical_condition": random.choice(MEDICAL_CONDITIONS),
                # Deliberately include some readings outside the 80-300 "normal" band
                # so the CGM agent's out-of-range branch is exercised.
                "cgm_reading": random.choice(
                    [random.randint(80, 300)] * 4 + [random.randint(50, 79)] + [random.randint(301, 400)]
                ),
            }
        )
    return rows


def main():
    rows = generate_patients(20)
    with open(OUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} synthetic patients to {OUT_PATH}")


if __name__ == "__main__":
    main()
