from dataclasses import dataclass, field, asdict
from typing import Literal
import json

Status = Literal['CONFIRMED', 'REFUTED', 'PARTIAL', 'UNVERIFIED', 'SKIPPED_RESOURCE']
STATUSES = ('CONFIRMED', 'REFUTED', 'PARTIAL', 'UNVERIFIED', 'SKIPPED_RESOURCE')

@dataclass
class Result:
    claim: str
    status: Status
    summary: str
    evidence: list[dict] = field(default_factory=list)
    logs: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    duration: float = 0
    versions: dict = field(default_factory=dict)
    execution: str = 'NOT_RUN'
    comparisons: list[dict] = field(default_factory=list)

    def to_dict(self):
        if self.status not in STATUSES:
            raise ValueError(self.status)
        if self.status != 'UNVERIFIED' and not self.evidence:
            raise ValueError('A verdict requires evidence')
        return asdict(self)
