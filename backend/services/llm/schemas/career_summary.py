from typing import List

from pydantic import BaseModel


class CareerSummary(BaseModel):
    """The four sections the career-summary prompt has always asked for.

    They used to come back as one prose blob that the UI rendered verbatim, so the
    sections existed only as a suggestion to the model. Making them fields means the
    frontend can label and lay them out, and a missing section is now visible rather
    than silently absorbed into the paragraph.
    """

    why_it_fits: str
    strengths: List[str]
    skill_gaps: List[str]
    outlook: str
