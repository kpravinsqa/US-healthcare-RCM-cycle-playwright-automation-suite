"""Central configuration. Override with environment variables (see README)."""
import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    username: str = os.getenv("TEST_USERNAME", "billing_admin")
    password: str = os.getenv("TEST_PASSWORD", "Health@123")
    front_desk: tuple = ("front_desk", "Health@123")
    provider: tuple = ("dr_smith", "Health@123")
    timely_filing_days: int = 365
    default_credentials: dict = field(default_factory=dict)

    def __post_init__(self):
        object.__setattr__(self, "default_credentials", {"username": self.username, "password": self.password})


settings = Settings()
