from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass
class Occupation:
    occupation_id: UUID
    occupation_name: str
    description: str | None
    average_salary: Decimal | None
    growth_outlook: str | None
    created_at: datetime