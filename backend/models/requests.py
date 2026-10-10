from enum import Enum
from pydantic import BaseModel, Field


class InvestigationDepth(str, Enum):
    QUICK = "quick"
    STANDARD = "standard"
    DEEP = "deep"


class InvestigationRequest(BaseModel):
    question: str = Field(min_length=5, max_length=1000)
    depth: InvestigationDepth = InvestigationDepth.STANDARD
    # Optional: regions to compare, e.g. ["Global", "India", "United States"]. Empty = let the agent decide.
    regions: list[str] = Field(default_factory=list, max_length=4)
