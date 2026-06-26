"""Pydantic schemas for the structured investment report.

The central design constraint: every atomic claim carries provenance
(`source_type` + `source_ref`) and a `confidence` level. The analysis LLM is
only allowed to cite deck pages or research sources it was given.
"""
from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator
from pydantic_core import PydanticUndefined


class _SafeModel(BaseModel):
    """Base model that tolerates a sloppy LLM.

    LLMs occasionally emit ``null`` (or omit a value) for a field we declared as
    required. Rather than letting one missing field blow up the entire report
    (and surface as an opaque deck error), we repair ``None`` values:
      * plain ``str`` fields  -> ``""``
      * any field that has a non-``None`` default -> that default (e.g. enums)
    Optional fields legitimately keep their ``None``.
    """

    @field_validator("*", mode="before")
    @classmethod
    def _repair_none(cls, v, info):
        if v is not None:
            return v
        field = cls.model_fields.get(info.field_name)
        if field is None:
            return v
        if field.annotation is str:
            return ""
        if field.default is not PydanticUndefined and field.default is not None:
            return field.default
        return v


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


class Claim(_SafeModel):
    """An atomic, sourced statement. The backbone of the whole report."""
    claim: str
    source_type: SourceType = SourceType.inference
    source_ref: str = Field(default="", description='"deck p.7" or a URL')
    confidence: Confidence = Confidence.medium


class CompanySnapshot(_SafeModel):
    name: str = ""
    one_liner: str = ""
    sector: Optional[str] = None
    stage: Optional[str] = None
    location: Optional[str] = None
    ask: Optional[str] = Field(None, description="What the deck is raising")
    deck_claims: List[Claim] = Field(default_factory=list)


class TeamMemberAnalysis(_SafeModel):
    name: str = ""
    title: Optional[str] = None
    linkedin_url: Optional[str] = None
    deck_claims: List[Claim] = Field(default_factory=list)
    researched_background: List[Claim] = Field(
        default_factory=list,
        description="What the person has actually done: prior roles, companies, years of "
        "experience, education, notable achievements/exits — sourced from research.",
    )
    strengths: List[Claim] = Field(
        default_factory=list,
        description="Concrete positive signals for executing THIS venture: relevant domain "
        "depth, scaling/operating experience, prior wins, technical credibility.",
    )
    founder_market_fit: List[Claim] = Field(
        default_factory=list,
        description="Assessment of how well this person's track record positions them to "
        "deliver the specific plan in the deck (the future they're proposing).",
    )
    gaps_vs_venture: List[Claim] = Field(
        default_factory=list,
        description="Specific gaps between this person's background and what THIS venture needs",
    )
    research_confidence: Confidence = Confidence.inconclusive


class Competitor(_SafeModel):
    name: str = ""
    relationship: str = Field(default="", description="e.g. direct, adjacent, incumbent")
    note: Claim


class CompetitiveLandscape(_SafeModel):
    named_in_deck: List[Competitor] = Field(default_factory=list)
    discovered: List[Competitor] = Field(default_factory=list)
    differentiation_assessment: List[Claim] = Field(default_factory=list)


class RedFlag(_SafeModel):
    title: str = ""
    severity: Severity = Severity.medium
    reasoning: Claim


class DiligenceQuestion(_SafeModel):
    question: str = ""
    targets_gap: str = Field(default="", description="Which ambiguity/gap this closes")


class ValuationComp(_SafeModel):
    company: str = ""
    detail: str = Field(default="", description="stage / round size / valuation / multiple")
    source: Claim


class ValuationAnalysis(_SafeModel):
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


class QAExchange(_SafeModel):
    """A cross-question from the audience and how the presenter handled it."""
    question: str = ""
    answer: str = Field(default="", description="What the presenter actually answered")
    assessment: str = Field(
        default="", description="How well the answer addressed the question (direct? evasive? data-backed?)"
    )
    confidence: Confidence = Confidence.medium


class PitchDelivery(_SafeModel):
    """Analysis of how the pitch was delivered, derived from a transcript and/or
    video. `tone` is only populated when a video was provided."""
    available: bool = False
    source: str = Field(default="", description='"transcript" | "video" | "video+transcript"')
    clarity: str = Field(default="", description="How clearly the presenter communicated the idea")
    structure: str = Field(default="", description="How well-organized / coherent the narrative was")
    handling_of_questions: str = Field(
        default="", description="How well the presenter handled cross-questions overall"
    )
    tone: str = Field(
        default="",
        description="Delivery tone/confidence/energy — populated ONLY when a video was uploaded.",
    )
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    qa: List[QAExchange] = Field(default_factory=list)
    notes: List[Claim] = Field(default_factory=list)


class FinalRecommendation(_SafeModel):
    recommendation: Recommendation = Recommendation.more_diligence
    suggested_check_size: Optional[str] = None
    risk_rating: str = Field(default="Medium", description="e.g. 'High' / 'Medium' / 'Low'")
    risk_factors: List[Claim] = Field(default_factory=list)
    rationale: str = ""


class InvestmentReport(_SafeModel):
    """The full report. Mirrors the target structure in the brief."""
    executive_summary: str = Field(
        default="",
        description="Consolidated 3-6 sentence partner-facing take synthesizing team, "
        "market/differentiation, traction, valuation, and the bottom-line call.",
    )
    company_snapshot: CompanySnapshot
    team_analysis: List[TeamMemberAnalysis] = Field(default_factory=list)
    competitive_landscape: CompetitiveLandscape
    red_flags: List[RedFlag] = Field(default_factory=list)
    diligence_questions: List[DiligenceQuestion] = Field(default_factory=list)
    valuation: ValuationAnalysis
    delivery: PitchDelivery = Field(default_factory=PitchDelivery)
    recommendation: FinalRecommendation
    analyst_note: str = Field(
        default="Directional analyst support. Augments, not replaces, partner judgment.",
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Non-fatal data-quality / pipeline notes (e.g. image-only deck, research degraded).",
    )
    mock_mode: bool = False
