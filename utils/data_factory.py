"""Builders for synthetic, PHI-free test data."""
import random
import string
from datetime import date, timedelta

FIRST = ["Olivia", "Liam", "Ava", "Noah", "Mia", "Ethan", "Grace", "Lucas"]
LAST = ["Brooks", "Hayes", "Patel", "Reed", "Foster", "Kim", "Lopez", "Shah"]


def patient(**overrides) -> dict:
    data = {
        "first_name": random.choice(FIRST),
        "last_name": random.choice(LAST) + "".join(random.choices(string.ascii_lowercase, k=3)),
        "dob": (date.today() - timedelta(days=random.randint(20, 80) * 365)).isoformat(),
        "gender": random.choice("MF"),
        "phone": "512555" + "".join(random.choices(string.digits, k=4)),
        "email": "test.patient@example.com",
        "zip": "78704",
        "payer": "Cigna",
        "member_id": "CIG" + "".join(random.choices(string.digits, k=7)),
    }
    data.update(overrides)
    return data


def days_ago(n: int) -> str:
    return (date.today() - timedelta(days=n)).isoformat()


def days_ahead(n: int) -> str:
    return (date.today() + timedelta(days=n)).isoformat()
