"""Pydantic schemas for the structured investment report.

The central design constraint: every atomic claim carries provenance
(`source_type` + `source_ref`) and a `confidence` level. The analysis LLM is
only allowed to cite deck pages or research sources it was given.
"""
from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    deck = "deck"          # stated in the deck (source_ref = "deck p.X")
    web = "web"            # from web research (source_ref = URL)
    enrichment = "enrichment"  # from people-enrichment API (source_ref = profile URL)
    inference = "inference"    # analyst inference from the above (must reference inputs)


class Confidence(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"
    inconclusive = "inconclusive"


class Severity(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class Recommendation(str, Enum):
    invest = "invest"
    pass_ = "pass"
    more_diligence = "more_diligence"


class Claim(BaseModel):
    """An atomic, sourced statement. The backbone of the whole report."""
    claim: str
    source_type: SourceType
    source_ref: str = Field(..., description='"deck p.7" or a URL')
    confidence: Confidence = Confidence.medium


class CompanySnapshot(BaseModel):
    name: str
    one_liner: str
    sector: Optional[str] = None
    stage: Optional[str] = None
    location: Optional[str] = None
    ask: Optional[str] = Field(None, description="What the deck is raising")
    deck_claims: List[Claim] = Field(default_factory=list)


class TeamMemberAnalysis(BaseModel):
    name: str
    title: Optional[str] = None
    linkedin_url: Optional[str] = None
    deck_claims: List[Claim] = Field(default_factory=list)
    researched_background: List[Claim] = Field(default_factory=list)
    gaps_vs_venture: List[Claim] = Field(
        default_factory=list,
        description="Specific gaps between this person's background and what THIS venture needs",
    )
    research_confidence: Confidence = Confidence.inconclusive


class Competitor(BaseModel):
    name: str
    relationship: str = Field(..., description="e.g. direct, adjacent, incumbent")
    note: Claim


class CompetitiveLandscape(BaseModel):
    named_in_deck: List[Competitor] = Field(default_factory=list)
    discovered: List[Competitor] = Field(default_factory=list)
    differentiation_assessment: List[Claim] = Field(default_factory=list)


class RedFlag(BaseModel):
    title: str
    severity: Severity
    reasoning: Claim


class DiligenceQuestion(BaseModel):
    question: str
    targets_gap: str = Field(..., description="Which ambiguity/gap this closes")


class ValuationComp(BaseModel):
    company: str
    detail: str = Field(..., description="stage / round size / valuation / multiple")
    source: Claim


class ValuationAnalysis(BaseModel):
    comps: List[ValuationComp] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    multiples_used: Optional[str] = None
    range_low: Optional[str] = None
    range_high: Optional[str] = None
    deck_ask: Optional[str] = None
    ask_vs_comps: List[Claim] = Field(
        default_factory=list,
        description="Is the deck's ask in line with comps? Explain.",
    )


class FinalRecommendation(BaseModel):
    recommendation: Recommendation
    suggested_check_size: Optional[str] = None
    risk_rating: str = Field(..., description="e.g. 'High' / 'Medium' / 'Low'")
    risk_factors: List[Claim] = Field(default_factory=list)
    rationale: str


class InvestmentReport(BaseModel):
    """The full report. Mirrors the target structure in the brief."""
    company_snapshot: CompanySnapshot
    team_analysis: List[TeamMemberAnalysis] = Field(default_factory=list)
    competitive_landscape: CompetitiveLandscape
    red_flags: List[RedFlag] = Field(default_factory=list)
    diligence_questions: List[DiligenceQuestion] = Field(default_factory=list)
    valuation: ValuationAnalysis
    recommendation: FinalRecommendation
    analyst_note: str = Field(
        default="Directional analyst support. Augments, not replaces, partner judgment.",
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Non-fatal data-quality / pipeline notes (e.g. image-only deck, research degraded).",
    )
    mock_mode: bool = False
