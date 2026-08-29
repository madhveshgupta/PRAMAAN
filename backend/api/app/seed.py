"""Seed demo users and reference data:  python -m api.app.seed

Three users deliberately, not two. The third is a ministry account with can_sanction=False,
so the separation-of-duties gate is exercised by the demo rather than merely described.
"""
import sys
from pathlib import Path

import yaml
from sqlalchemy import select

from api.app.db import SessionLocal
from api.app.models import Organisation, Sector, Setting, User
from api.app.security import hash_password

DEMO_PASSWORD = "pramaan"  # demo only

ORGS = [
    ("Ministry of Road Transport & Highways", "ministry", None),
    ("Assam Public Works Department", "state_dept", "Assam"),
    ("Meghalaya Urban Development Authority", "implementing_agency", "Meghalaya"),
]

SECTORS = [
    ("Roads & Highways", "Transport & Logistics"),
    ("Water Resources", "Water & Sanitation"),
    ("Urban Public Transport", "Transport & Logistics"),
    ("Electricity Generation", "Energy"),
]

USERS = [
    ("applicant@demo.gov.in", "R. Sharma (Executive Engineer)", "applicant", False,
     "Assam Public Works Department"),
    ("ministry@demo.gov.in", "K. Nair (Joint Secretary)", "ministry", True,
     "Ministry of Road Transport & Highways"),
    # Appraises and recommends, cannot sanction. Proves the gate is real.
    ("officer@demo.gov.in", "S. Bose (Desk Officer)", "ministry", False,
     "Ministry of Road Transport & Highways"),
]


def seed() -> int:
    db = SessionLocal()
    created = {"orgs": 0, "sectors": 0, "users": 0, "settings": 0}
    try:
        org_by_name: dict[str, Organisation] = {}
        for name, otype, state in ORGS:
            org = db.scalar(select(Organisation).where(Organisation.name == name))
            if org is None:
                org = Organisation(name=name, type=otype, state=state)
                db.add(org)
                db.flush()
                created["orgs"] += 1
            org_by_name[name] = org

        for name, hml in SECTORS:
            if db.scalar(select(Sector).where(Sector.name == name)) is None:
                db.add(Sector(name=name, hml_category=hml))
                created["sectors"] += 1

        for email, full_name, role, can_sanction, org_name in USERS:
            if db.scalar(select(User).where(User.email == email)) is None:
                db.add(User(email=email, full_name=full_name, role=role,
                            can_sanction=can_sanction,
                            password_hash=hash_password(DEMO_PASSWORD),
                            organisation_id=org_by_name[org_name].id))
                created["users"] += 1

        defaults = yaml.safe_load(
            (Path(__file__).resolve().parents[2] / "config" / "settings_defaults.yaml").read_text())
        for key, spec in defaults.items():
            if db.get(Setting, key) is None:
                db.add(Setting(key=key, value={"v": spec["value"]},
                               description=spec.get("description")))
                created["settings"] += 1

        db.commit()
    finally:
        db.close()

    print(f"seeded: {created['orgs']} orgs, {created['sectors']} sectors, "
          f"{created['users']} users, {created['settings']} settings")
    print(f"\ndemo logins (password: {DEMO_PASSWORD})")
    for email, name, role, can_sanction, _ in USERS:
        gate = "can sanction" if can_sanction else "APPRAISE ONLY - cannot sanction"
        print(f"  {email:26} {role:10} {gate:32} {name}")
    return 0


if __name__ == "__main__":
    sys.exit(seed())
