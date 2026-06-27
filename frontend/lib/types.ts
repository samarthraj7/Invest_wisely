export type Confidence = "high" | "medium" | "low" | "inconclusive";
export type SourceType = "deck" | "web" | "enrichment" | "inference";
export type Severity = "critical" | "high" | "medium" | "low";

export interface Claim {
  claim: string;
  source_type: SourceType;
  source_ref: string;
  confidence: Confidence;
}

export interface CompanySnapshot {
  name: string;
  one_liner: string;
  sector?: string | null;
  stage?: string | null;
  location?: string | null;
  ask?: string | null;
  deck_claims: Claim[];
}

export interface FounderCredentials {
  years_experience?: number | null;
  papers_count?: number | null;
  patents_count?: number | null;
  patent_quality: string;
  research_quality: string;
  notable_achievements: Claim[];
  assessment: string;
}

export interface TeamMember {
  name: string;
  title?: string | null;
  linkedin_url?: string | null;
  deck_claims: Claim[];
  credentials?: FounderCredentials;
  researched_background: Claim[];
  strengths: Claim[];
  founder_market_fit: Claim[];
  gaps_vs_venture: Claim[];
  research_confidence: Confidence;
}

export interface Competitor {
  name: string;
  relationship: string;
  note: Claim;
}

export interface RedFlag {
  title: string;
  severity: Severity;
  reasoning: Claim;
}

export interface DiligenceQuestion {
  question: string;
  targets_gap: string;
}

export interface ValuationComp {
  company: string;
  detail: string;
  source: Claim;
}

export interface Valuation {
  comps: ValuationComp[];
  assumptions: string[];
  multiples_used?: string | null;
  range_low?: string | null;
  range_high?: string | null;
  deck_ask?: string | null;
  ask_vs_comps: Claim[];
}

export interface Recommendation {
  recommendation: "invest" | "pass" | "more_diligence";
  suggested_check_size?: string | null;
  risk_rating: string;
  risk_factors: Claim[];
  rationale: string;
}

export interface QAExchange {
  question: string;
  answer: string;
  assessment: string;
  confidence: Confidence;
}

export interface PitchDelivery {
  available: boolean;
  source: string;
  clarity: string;
  structure: string;
  handling_of_questions: string;
  tone: string;
  strengths: string[];
  weaknesses: string[];
  qa: QAExchange[];
  notes: Claim[];
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  detail: string;
  score?: number | null;
  weight?: number;
  rationale?: string;
}

export interface GraphEdge {
  source: string;
  target: string;
  relation: string;
  polarity?: string;
  weight?: number;
}

export interface KnowledgeGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface ScoreFactor {
  key: string;
  name: string;
  score: number;
  weight: number;
  rationale: string;
}

export interface RiskBreakdown {
  legitimacy: string;
  valuation: string;
  revenue: string;
  future_plan: string;
  impact: string;
}

export interface InvestmentScore {
  overall: number;
  verdict: string;
  factors: ScoreFactor[];
  risk: RiskBreakdown;
  rationale: string;
  graph: KnowledgeGraph;
  scored: boolean;
}

export interface Icebreaker {
  founder: string;
  common_ground: string[];
  shared_interests: string[];
  openers: string[];
  note: string;
}

export interface IcebreakerSet {
  founders: Icebreaker[];
  overall: string;
  available: boolean;
}

export interface InvestmentReport {
  executive_summary?: string;
  company_snapshot: CompanySnapshot;
  team_analysis: TeamMember[];
  competitive_landscape: {
    named_in_deck: Competitor[];
    discovered: Competitor[];
    differentiation_assessment: Claim[];
  };
  red_flags: RedFlag[];
  diligence_questions: DiligenceQuestion[];
  valuation: Valuation;
  delivery?: PitchDelivery;
  score?: InvestmentScore;
  recommendation: Recommendation;
  analyst_note: string;
  warnings: string[];
  mock_mode: boolean;
}

export interface DeckListItem {
  id: string;
  filename: string;
  company_name: string;
  status: string;
  error?: string;
  recommendation: string;
  risk_rating: string;
  has_transcript?: boolean;
  has_video?: boolean;
  created_at: string;
}

export interface DeckDetail {
  id: string;
  filename: string;
  company_name: string;
  status: string;
  error: string;
  report: InvestmentReport | null;
  created_at: string;
}
