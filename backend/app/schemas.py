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


class FounderCredentials(_SafeModel):
    """Hard evidence of what a founder has actually produced, with a judgement on
    how *significant* it is — a single granted utility patent central to the product
    counts very differently from a trivial design patent."""
    years_experience: Optional[int] = Field(
        default=None, description="Approx. years of relevant professional experience"
    )
    papers_count: Optional[int] = Field(default=None, description="Number of research papers/publications found")
    patents_count: Optional[int] = Field(default=None, description="Number of patents found")
    patent_quality: str = Field(
        default="",
        description='Significance of the patents: "substantive" | "mixed" | "trivial" | "unknown" '
        "(e.g. granted utility patent central to the product vs. a basic design patent).",
    )
    research_quality: str = Field(
        default="",
        description="Significance of the papers/research: highly-cited / venue quality vs. obscure.",
    )
    notable_achievements: List[Claim] = Field(
        default_factory=list,
        description="Specific, sourced achievements: a key paper, a granted patent, a notable "
        "role/exit — each with a note on why it matters (or doesn't).",
    )
    assessment: str = Field(
        default="",
        description="One-line overall read of credential depth: substantive track record vs. thin.",
    )


class TeamMemberAnalysis(_SafeModel):
    name: str = ""
    title: Optional[str] = None
    linkedin_url: Optional[str] = None
    deck_claims: List[Claim] = Field(default_factory=list)
    credentials: FounderCredentials = Field(default_factory=FounderCredentials)
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


class GraphNode(_SafeModel):
    id: str = ""
    label: str = ""
    type: str = Field(default="", description="company|founder|market|competitor|valuation|traction|legitimacy|delivery|risk")
    detail: str = ""
    score: Optional[int] = Field(default=None, description="0-100 score for this node (None = unscored/structural)")
    weight: float = Field(default=0.0, description="Importance of this node in the overall score")
    rationale: str = ""


class GraphEdge(_SafeModel):
    source: str = ""
    target: str = ""
    relation: str = ""
    polarity: str = Field(default="neutral", description='"support" | "pressure" | "neutral" — how source affects target')
    weight: float = Field(default=1.0, description="Strength of the link (0-1)")


class KnowledgeGraph(_SafeModel):
    """Entities linked to each other; the visual backbone of the final judgement."""
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)


class ScoreFactor(_SafeModel):
    key: str = ""
    name: str = ""
    score: int = Field(default=0, description="0-100 for this dimension")
    weight: float = Field(default=0.0, description="0-1 weight in the overall score")
    rationale: str = ""


class RiskBreakdown(_SafeModel):
    """Why the risk rating is what it is, decomposed along the axes that matter."""
    legitimacy: str = Field(default="", description="How verifiable/real the company, team and claims are")
    valuation: str = Field(default="", description="Is the ask/valuation justified by evidence?")
    revenue: str = Field(default="", description="Revenue/traction reality and durability")
    future_plan: str = Field(default="", description="Credibility of the roadmap and use of funds")
    impact: str = Field(default="", description="How these combine into the overall risk and what would change it")


class InvestmentScore(_SafeModel):
    """A transparent 0-100 score: a weighted blend of factor scores, plus the risk
    decomposition and the entity knowledge graph that supports the call."""
    overall: int = Field(default=0, description="0-100 weighted investment score")
    verdict: str = Field(default="", description="Short label derived from the score")
    factors: List[ScoreFactor] = Field(default_factory=list)
    risk: RiskBreakdown = Field(default_factory=RiskBreakdown)
    rationale: str = Field(default="", description="2-3 sentence justification of the overall score")
    graph: KnowledgeGraph = Field(default_factory=KnowledgeGraph)
    scored: bool = Field(default=False, description="False when scoring did not run (mock/degraded)")


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
    score: InvestmentScore = Field(default_factory=InvestmentScore)
    recommendation: FinalRecommendation
    analyst_note: str = Field(
        default="Directional analyst support. Augments, not replaces, partner judgment.",
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Non-fatal data-quality / pipeline notes (e.g. image-only deck, research degraded).",
    )
    mock_mode: bool = False
