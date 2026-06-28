from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID


@dataclass
class Occupation:
    occupation_id: UUID
    occupation_name: str
    description: Optional[str]
    average_salary: Optional[Decimal]
    growth_outlook: Optional[str]
    created_at: datetime