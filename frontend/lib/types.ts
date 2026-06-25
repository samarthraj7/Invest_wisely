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

export interface TeamMember {
  name: string;
  title?: string | null;
  linkedin_url?: string | null;
  deck_claims: Claim[];
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

export interface InvestmentReport {
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
