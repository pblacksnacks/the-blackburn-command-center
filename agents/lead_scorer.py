from __future__ import annotations

import json
import os
import random
import time
from dataclasses import dataclass, field
from typing import Any, Literal

from anthropic import Anthropic
from pydantic import BaseModel, Field, model_validator

CLAUDE_MODEL = "claude-sonnet-4-20250514"
IntentLabel = Literal["new_business", "support", "partnership", "spam", "other"]
UseCaseLabel = Literal[
    "internal_productivity", "product_integration", "dual_motion",
    "platform_consolidation", "devsecops", "ci_cd_modernization", "compliance_automation",
    "unknown",
]
BuyingStageLabel = Literal["researching", "evaluating", "ready_to_buy", "unknown"]
ProductLineFit = Literal[
    "api", "claude_ai_seats", "claude_enterprise",
    "gitlab_ultimate", "gitlab_premium", "gitlab_self_managed", "gitlab_dedicated",
    "multiple", "unknown",
]
DealSizeTier = Literal["enterprise", "mid_market", "smb", "unknown"]
MeddpiccStatus = Literal["known", "partial", "unknown"]


@dataclass(frozen=True, slots=True)
class MeddpiccDimension:
    status: MeddpiccStatus
    evidence: str          # what we know (empty string if unknown)
    gap: str               # what's still missing
    question: str          # suggested discovery question for this dimension


@dataclass(frozen=True, slots=True)
class MeddpiccScore:
    metrics: MeddpiccDimension
    economic_buyer: MeddpiccDimension
    decision_criteria: MeddpiccDimension
    decision_process: MeddpiccDimension
    paper_process: MeddpiccDimension
    implicate_pain: MeddpiccDimension
    champion: MeddpiccDimension
    competition: MeddpiccDimension


@dataclass(frozen=True, slots=True)
class ScoringResult:
    email_id: str
    sender_email: str
    sender_name: str | None
    sender_title: str | None
    company_name: str | None
    company_domain: str | None

    # Core scoring
    intent: IntentLabel
    intent_score: int
    domain_quality_score: int
    urgency_score: int
    content_depth_score: int
    authority_score: int
    total_score: int
    grade: Literal["A", "B", "C", "D"]
    urgency_signals: list[str]
    summary: str
    reasoning: str

    # Anthropic-specific
    use_case: UseCaseLabel
    product_line_fit: ProductLineFit

    # Market position
    buying_stage: BuyingStageLabel
    current_ai_provider: str | None
    competitive_signals: list[str]

    # Revenue
    estimated_acv: int | None
    deal_size_tier: DealSizeTier
    tam_estimate: str | None
    expansion_potential: str | None

    # MEDDPICC
    meddpicc: MeddpiccScore
    discovery_questions: list[str]
    next_best_action: str

    # Partnership
    partnership_synergies: list[str]
    partnership_detractors: list[str]

    model_name: str = CLAUDE_MODEL


class RawEmail(BaseModel):
    email_id: str
    sender_email: str
    sender_name: str | None = None
    subject: str
    body: str
    received_at: str


class MeddpiccDimensionModel(BaseModel):
    status: MeddpiccStatus = "unknown"
    evidence: str = ""
    gap: str = ""
    question: str = ""


class MeddpiccModel(BaseModel):
    metrics: MeddpiccDimensionModel = Field(default_factory=MeddpiccDimensionModel)
    economic_buyer: MeddpiccDimensionModel = Field(default_factory=MeddpiccDimensionModel)
    decision_criteria: MeddpiccDimensionModel = Field(default_factory=MeddpiccDimensionModel)
    decision_process: MeddpiccDimensionModel = Field(default_factory=MeddpiccDimensionModel)
    paper_process: MeddpiccDimensionModel = Field(default_factory=MeddpiccDimensionModel)
    implicate_pain: MeddpiccDimensionModel = Field(default_factory=MeddpiccDimensionModel)
    champion: MeddpiccDimensionModel = Field(default_factory=MeddpiccDimensionModel)
    competition: MeddpiccDimensionModel = Field(default_factory=MeddpiccDimensionModel)


class ScoringResultModel(BaseModel):
    email_id: str
    sender_email: str
    sender_name: str | None = None
    sender_title: str | None = None
    company_name: str | None = None
    company_domain: str | None = None

    # Core scoring
    intent: IntentLabel
    intent_score: int = Field(ge=0, le=30)
    domain_quality_score: int = Field(ge=0, le=25)
    urgency_score: int = Field(ge=0, le=20)
    content_depth_score: int = Field(ge=0, le=15)
    authority_score: int = Field(ge=0, le=10)
    total_score: int = Field(ge=0, le=100)
    grade: Literal["A", "B", "C", "D"]
    urgency_signals: list[str] = Field(default_factory=list)
    summary: str
    reasoning: str

    # Anthropic-specific
    use_case: UseCaseLabel = "unknown"
    product_line_fit: ProductLineFit = "unknown"

    # Market position
    buying_stage: BuyingStageLabel = "unknown"
    current_ai_provider: str | None = None
    competitive_signals: list[str] = Field(default_factory=list)

    # Revenue
    estimated_acv: int | None = None
    deal_size_tier: DealSizeTier = "unknown"
    tam_estimate: str | None = None
    expansion_potential: str | None = None

    # MEDDPICC
    meddpicc: MeddpiccModel = Field(default_factory=MeddpiccModel)
    discovery_questions: list[str] = Field(default_factory=list)
    next_best_action: str = ""

    # Partnership
    partnership_synergies: list[str] = Field(default_factory=list)
    partnership_detractors: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_total_and_grade(self) -> "ScoringResultModel":
        expected_total = (
            self.intent_score
            + self.domain_quality_score
            + self.urgency_score
            + self.content_depth_score
            + self.authority_score
        )
        if expected_total != self.total_score:
            raise ValueError(
                f"score total mismatch: expected {expected_total}, got {self.total_score}"
            )
        expected_grade = grade_from_score(self.total_score)
        if expected_grade != self.grade:
            raise ValueError(
                f"grade mismatch: expected {expected_grade}, got {self.grade}"
            )
        return self

    def to_dataclass(self) -> ScoringResult:
        data = self.model_dump()
        meddpicc_data = data.pop("meddpicc")
        data["meddpicc"] = MeddpiccScore(
            **{k: MeddpiccDimension(**v) for k, v in meddpicc_data.items()}
        )
        return ScoringResult(**data)


def grade_from_score(score: int) -> Literal["A", "B", "C", "D"]:
    if score >= 80:
        return "A"
    if score >= 60:
        return "B"
    if score >= 40:
        return "C"
    return "D"


class LeadScorer:
    def __init__(self, api_key: str, model: str = CLAUDE_MODEL, gitlab_mode: bool = False) -> None:
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.gitlab_mode = gitlab_mode

    def score_email(self, email: RawEmail) -> ScoringResult:
        response = self._call_with_retry(
            lambda: self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                system=self._system_prompt(),
                messages=[
                    {
                        "role": "user",
                        "content": self._user_prompt(email),
                    }
                ],
                tools=[self._result_tool()],
                tool_choice={"type": "tool", "name": "record_scoring_result"},
            )
        )

        tool_block = next(
            (
                block
                for block in response.content
                if getattr(block, "type", None) == "tool_use"
                and getattr(block, "name", None) == "record_scoring_result"
            ),
            None,
        )
        if tool_block is None:
            raise RuntimeError("Claude did not emit record_scoring_result")

        payload = dict(tool_block.input)
        payload["email_id"] = email.email_id
        payload["sender_email"] = email.sender_email
        payload.setdefault("sender_name", email.sender_name)

        validated = ScoringResultModel.model_validate(payload)
        return validated.to_dataclass()

    def _call_with_retry(self, fn, attempts: int = 3):
        for attempt in range(1, attempts + 1):
            try:
                return fn()
            except Exception as exc:
                status_code = getattr(exc, "status_code", None)
                retryable = status_code in {408, 409, 429, 500, 502, 503, 504} or (
                    exc.__class__.__name__
                    in {
                        "RateLimitError",
                        "APIConnectionError",
                        "APITimeoutError",
                        "InternalServerError",
                    }
                )
                if not retryable or attempt == attempts:
                    raise
                sleep_seconds = (0.75 * (2 ** (attempt - 1))) + random.uniform(0, 0.35)
                time.sleep(sleep_seconds)

    def _result_tool(self) -> dict[str, Any]:
        meddpicc_dimension = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "status": {"type": "string", "enum": ["known", "partial", "unknown"]},
                "evidence": {
                    "type": "string",
                    "description": "What we know from the email — specific facts, quotes, or signals. Empty string if unknown.",
                },
                "gap": {
                    "type": "string",
                    "description": "What is still missing or unclear for this dimension.",
                },
                "question": {
                    "type": "string",
                    "description": "A specific discovery question the rep should ask to fill this gap.",
                },
            },
            "required": ["status", "evidence", "gap", "question"],
        }
        return {
            "name": "record_scoring_result",
            "description": (
                "Return the fully scored and qualified lead object. "
                "Include MEDDPICC assessment with per-dimension detail (evidence, gap, question), "
                "use case classification, revenue estimation, "
                "competitive analysis, and next best action for the rep. "
                "The total_score must equal the sum of the five dimension scores."
            ),
            "input_schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    # Identity
                    "sender_name": {"type": ["string", "null"]},
                    "sender_title": {"type": ["string", "null"]},
                    "company_name": {"type": ["string", "null"]},
                    "company_domain": {"type": ["string", "null"]},

                    # Core scoring
                    "intent": {
                        "type": "string",
                        "enum": ["new_business", "support", "partnership", "spam", "other"],
                    },
                    "intent_score": {"type": "integer", "minimum": 0, "maximum": 30},
                    "domain_quality_score": {"type": "integer", "minimum": 0, "maximum": 25},
                    "urgency_score": {"type": "integer", "minimum": 0, "maximum": 20},
                    "content_depth_score": {"type": "integer", "minimum": 0, "maximum": 15},
                    "authority_score": {"type": "integer", "minimum": 0, "maximum": 10},
                    "total_score": {"type": "integer", "minimum": 0, "maximum": 100},
                    "grade": {"type": "string", "enum": ["A", "B", "C", "D"]},
                    "urgency_signals": {"type": "array", "items": {"type": "string"}},
                    "summary": {"type": "string"},
                    "reasoning": {"type": "string"},

                    # Product-specific
                    "use_case": {
                        "type": "string",
                        "enum": (
                            ["platform_consolidation", "devsecops", "ci_cd_modernization", "compliance_automation", "dual_motion", "unknown"]
                            if self.gitlab_mode else
                            ["internal_productivity", "product_integration", "dual_motion", "unknown"]
                        ),
                    },
                    "product_line_fit": {
                        "type": "string",
                        "enum": (
                            ["gitlab_ultimate", "gitlab_premium", "gitlab_self_managed", "gitlab_dedicated", "multiple", "unknown"]
                            if self.gitlab_mode else
                            ["api", "claude_ai_seats", "claude_enterprise", "multiple", "unknown"]
                        ),
                    },

                    # Market position
                    "buying_stage": {
                        "type": "string",
                        "enum": ["researching", "evaluating", "ready_to_buy", "unknown"],
                    },
                    "current_ai_provider": {"type": ["string", "null"]},
                    "competitive_signals": {"type": "array", "items": {"type": "string"}},

                    # Revenue
                    "estimated_acv": {"type": ["integer", "null"]},
                    "deal_size_tier": {
                        "type": "string",
                        "enum": ["enterprise", "mid_market", "smb", "unknown"],
                    },
                    "tam_estimate": {"type": ["string", "null"]},
                    "expansion_potential": {"type": ["string", "null"]},

                    # MEDDPICC
                    "meddpicc": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "metrics": meddpicc_dimension,
                            "economic_buyer": meddpicc_dimension,
                            "decision_criteria": meddpicc_dimension,
                            "decision_process": meddpicc_dimension,
                            "paper_process": meddpicc_dimension,
                            "implicate_pain": meddpicc_dimension,
                            "champion": meddpicc_dimension,
                            "competition": meddpicc_dimension,
                        },
                        "required": [
                            "metrics", "economic_buyer", "decision_criteria",
                            "decision_process", "paper_process", "implicate_pain",
                            "champion", "competition",
                        ],
                    },
                    "discovery_questions": {"type": "array", "items": {"type": "string"}},
                    "next_best_action": {"type": "string"},

                    # Partnership
                    "partnership_synergies": {"type": "array", "items": {"type": "string"}},
                    "partnership_detractors": {"type": "array", "items": {"type": "string"}},
                },
                "required": [
                    "intent", "intent_score", "domain_quality_score",
                    "urgency_score", "content_depth_score", "authority_score",
                    "total_score", "grade", "urgency_signals", "summary", "reasoning",
                    "use_case", "product_line_fit", "buying_stage",
                    "competitive_signals", "deal_size_tier", "meddpicc",
                    "discovery_questions", "next_best_action",
                    "partnership_synergies", "partnership_detractors",
                ],
            },
        }

    def _system_prompt(self) -> str:
        if self.gitlab_mode:
            return self._system_prompt_gitlab()
        return self._system_prompt_anthropic()

    def _system_prompt_anthropic(self) -> str:
        return """
You are a B2B inbound lead qualification agent for Anthropic's mid-market sales team.
You are scoring emails from high-tech companies (500-3000 employees) in the San Francisco Bay Area.

Anthropic sells:
- Claude API: usage-based, for companies embedding AI into their products
- Claude.ai seats: per-seat, for internal team productivity
- Claude Enterprise: org-wide deployment with admin controls, SSO, higher limits

YOUR JOB HAS FIVE PARTS:

═══════════════════════════════════════════════════
PART 1: SCORE THE LEAD (0-100)
═══════════════════════════════════════════════════

INTENT SCORE (0-30)
- 25-30: explicit demo, pricing, RFP, vendor evaluation, contract request
- 15-24: clear product interest, softer call to action
- 5-14: ambiguous interest, general inquiry
- 0-4: not a buying conversation

DOMAIN QUALITY (0-25)
- 20-25: large enterprise or well-known tech company
- 10-19: legitimate mid-market or funded startup
- 3-9: personal domain or weak signal
- 0-2: disposable, scammy, or junk domain

URGENCY SIGNALS (0-20)
- 15-20: explicit timeline, budget, deadline, competitor bake-off
- 8-14: implied urgency
- 1-7: weak urgency
- 0: none

CONTENT DEPTH (0-15)
- 12-15: specific use case, environment details, team size, rollout plan
- 6-11: moderate specificity
- 1-5: thin but understandable
- 0: low information

SENDER AUTHORITY (0-10)
- 8-10: VP, C-level, founder, head of function
- 4-7: director, manager, team lead with ownership
- 1-3: unclear or junior
- 0: generic alias (info@, support@, admin@)

Grade: A=80-100, B=60-79, C=40-59, D=0-39
Total MUST equal the sum of the five dimensions.

═══════════════════════════════════════════════════
PART 2: CLASSIFY THE OPPORTUNITY
═══════════════════════════════════════════════════

USE CASE — what would they use Claude for?
- internal_productivity: internal docs, support, summarization, team productivity
- product_integration: embedding Claude API into their product for end users
- dual_motion: both internal use AND product integration
- unknown: not enough signal

PRODUCT LINE FIT — which Anthropic product?
- api: they want to build on Claude programmatically
- claude_ai_seats: team seats for daily use
- claude_enterprise: org-wide with admin/SSO needs
- multiple: they need more than one product
- unknown: not enough signal

BUYING STAGE:
- researching: early exploration, gathering info
- evaluating: actively comparing vendors, running pilots
- ready_to_buy: has budget, timeline, and decision authority
- unknown: can't determine

CURRENT AI PROVIDER: if mentioned or inferable (e.g. "switching from OpenAI", "replacing our GPT integration"), state it. Otherwise null.

COMPETITIVE SIGNALS: list any mentions of competitors, bake-offs, or vendor comparisons.

═══════════════════════════════════════════════════
PART 3: ESTIMATE REVENUE
═══════════════════════════════════════════════════

ESTIMATED ACV (annual contract value in USD):
- API product_integration: estimate based on likely token volume and company size
- Claude.ai seats: $20-30/seat/month × estimated seat count × 12
- Enterprise: $50-100/seat/month × estimated seat count × 12
- For mid-market (500-3000 employees), typical ACV range: $50K-$500K

DEAL SIZE TIER:
- enterprise: ACV > $200K
- mid_market: ACV $50K-$200K
- smb: ACV < $50K
- unknown: not enough signal

TAM ESTIMATE: total addressable value at this account if fully deployed.
Format: "$X based on Y employees × Z use case"

EXPANSION POTENTIAL: how could a pilot grow? Think land-and-expand.

═══════════════════════════════════════════════════
PART 4: MEDDPICC QUALIFICATION
═══════════════════════════════════════════════════

For each letter, provide a structured assessment with FOUR fields:
  status: "known" (clearly stated), "partial" (hinted at), "unknown" (not mentioned)
  evidence: what the email tells us — cite specifics (quotes, facts, signals). Empty string if nothing.
  gap: what is still missing or unclear for this dimension.
  question: one specific discovery question the rep should ask to fill this gap.

- M (Metrics): Do they mention measurable goals, KPIs, ROI expectations?
- E (Economic Buyer): Is the sender the budget holder? Did they reference one?
- D (Decision Criteria): What are they evaluating on? Performance, price, security?
- D (Decision Process): Timeline, committee, stages, procurement steps?
- P (Paper Process): Legal, security review, contract, MSA, BAA?
- I (Implicate Pain): Is there a stated business problem driving this?
- C (Champion): Does the sender seem like an internal advocate for Claude?
- C (Competition): Are other vendors being evaluated?

DISCOVERY QUESTIONS: 3-5 additional general questions the rep should ask.
These should be specific, not generic. Reference what we know and what's missing.

NEXT BEST ACTION: one concrete sentence. What should the rep do RIGHT NOW?
Examples: "Call within 2 hours — active bake-off with timeline pressure"
          "Send enterprise security whitepaper, then schedule technical deep-dive"
          "Deprioritize — route to support team"

═══════════════════════════════════════════════════
PART 5: PARTNERSHIP & STRATEGIC FIT
═══════════════════════════════════════════════════

PARTNERSHIP SYNERGIES: ways Anthropic and this company could mutually benefit.
Think: shared customer base, co-sell potential, integration ecosystem, market positioning.

PARTNERSHIP DETRACTORS: risks or friction points.
Think: existing competitor contracts, competing product, regulatory concerns.

═══════════════════════════════════════════════════
RULES
═══════════════════════════════════════════════════
- Be conservative on scores. Do not inflate vague emails.
- Do not invent titles, companies, or budget figures not supported by the email.
- Support and partnership emails are visible but not new pipeline.
- Spam should score near zero.
- Return the final answer ONLY by calling record_scoring_result.
""".strip()

    def _system_prompt_gitlab(self) -> str:
        return """
You are a B2B inbound lead qualification agent for GitLab's mid-market and enterprise sales team.
You are scoring emails from companies interested in GitLab's DevSecOps platform.

GitLab sells:
- GitLab Premium: advanced CI/CD, project management, and compliance features
- GitLab Ultimate: full DevSecOps platform with security scanning, compliance, and advanced analytics
- GitLab Self-Managed: on-premise or private cloud deployment for data sovereignty
- GitLab Dedicated: single-tenant SaaS with isolation and compliance guarantees

YOUR JOB HAS FIVE PARTS:

═══════════════════════════════════════════════════
PART 1: SCORE THE LEAD (0-100)
═══════════════════════════════════════════════════

INTENT SCORE (0-30)
- 25-30: explicit demo request, pricing inquiry, RFP, vendor evaluation, migration planning, contract request
- 15-24: clear interest in GitLab platform, mentions specific products (Ultimate, Premium), requests technical discussion
- 5-14: general DevOps inquiry, mentions CI/CD or SCM needs without specifics
- 0-4: not a buying conversation

DOMAIN QUALITY (0-25)
- 20-25: large enterprise or well-known company (Fortune 500, major tech, defense/gov)
- 10-19: legitimate mid-market company, funded startup, or recognized brand
- 3-9: personal domain or weak signal
- 0-2: disposable, scammy, or junk domain

URGENCY SIGNALS (0-20)
- 15-20: audit pressure, compliance deadline, tool contract expiring, migration timeline set, budget approved, security incident driving change
- 8-14: tool sprawl causing pain, team growth requiring platform, implied urgency
- 1-7: weak urgency signals
- 0: none

CONTENT DEPTH (0-15)
- 12-15: specific seat counts, named tools being replaced, migration requirements, compliance frameworks mentioned (SOC2, FedRAMP, HIPAA), ACV ranges stated
- 6-11: moderate specificity — mentions team size, general requirements
- 1-5: thin but understandable
- 0: low information

SENDER AUTHORITY (0-10)
- 8-10: CTO, VP Engineering, CISO, SVP, Head of Platform/DevOps, founder
- 4-7: Director of Engineering, DevOps Manager, Security Lead, team lead with ownership
- 1-3: unclear or junior role
- 0: generic alias (info@, support@, admin@)

Grade: A=80-100, B=60-79, C=40-59, D=0-39
Total MUST equal the sum of the five dimensions.

═══════════════════════════════════════════════════
PART 2: CLASSIFY THE OPPORTUNITY
═══════════════════════════════════════════════════

USE CASE — what would they use GitLab for?
- platform_consolidation: replacing multiple tools (Jenkins + GitHub + Snyk, etc.) with unified GitLab platform
- devsecops: security scanning, vulnerability management, compliance pipelines, software supply chain security
- ci_cd_modernization: replacing legacy CI/CD (Jenkins, CircleCI, TeamCity) with GitLab CI
- compliance_automation: audit trails, separation of duties, compliance frameworks, regulated industry needs
- dual_motion: both platform consolidation AND security/compliance needs
- unknown: not enough signal

PRODUCT LINE FIT — which GitLab product?
- gitlab_ultimate: needs security scanning, compliance, advanced analytics, or full DevSecOps
- gitlab_premium: needs advanced CI/CD, project management, but not full security suite
- gitlab_self_managed: requires on-premise or private cloud deployment
- gitlab_dedicated: wants SaaS but needs single-tenant isolation
- multiple: needs more than one deployment model or tier
- unknown: not enough signal

BUYING STAGE:
- researching: early exploration, gathering info
- evaluating: actively comparing vendors, running pilots or POCs
- ready_to_buy: has budget, timeline, and decision authority
- unknown: can't determine

CURRENT TOOLCHAIN: identify the tools they currently use or are replacing.
Look for mentions of: GitHub, Jenkins, CircleCI, Travis CI, Bamboo, Azure DevOps, Bitbucket, Harness, JFrog, Snyk, SonarQube, Checkmarx, Veracode, TeamCity. State what's mentioned or inferable. Null if unknown.

COMPETITIVE SIGNALS: list any mentions of competing platforms, bake-offs, or vendor comparisons.
Key competitors: GitHub Enterprise, Harness, CircleCI, JFrog, Azure DevOps, Bitbucket, Snyk.

═══════════════════════════════════════════════════
PART 3: ESTIMATE REVENUE
═══════════════════════════════════════════════════

ESTIMATED ACV (annual contract value in USD):
- GitLab Premium: ~$29/user/month × seat count × 12
- GitLab Ultimate: ~$99/user/month × seat count × 12
- GitLab Dedicated: premium on top of Ultimate pricing
- Self-Managed: similar per-seat pricing with support tiers
- For mid-market (200-2000 dev seats), typical ACV range: $100K-$2M+

DEAL SIZE TIER:
- enterprise: ACV > $200K
- mid_market: ACV $50K-$200K
- smb: ACV < $50K
- unknown: not enough signal

TAM ESTIMATE: total addressable value at this account if fully deployed.
Format: "$X based on Y developers × Z tier"

EXPANSION POTENTIAL: how could a pilot grow? Think land-and-expand across teams, tiers (Premium → Ultimate), and deployment models.

═══════════════════════════════════════════════════
PART 4: MEDDPICC QUALIFICATION
═══════════════════════════════════════════════════

For each letter, provide a structured assessment with FOUR fields:
  status: "known" (clearly stated), "partial" (hinted at), "unknown" (not mentioned)
  evidence: what the email tells us — cite specifics (quotes, facts, signals). Empty string if nothing.
  gap: what is still missing or unclear for this dimension.
  question: one specific discovery question the rep should ask to fill this gap.

- M (Metrics): Do they mention measurable goals — deployment frequency, MTTR, vulnerability reduction, tool cost savings?
- E (Economic Buyer): Is the sender the budget holder? Did they reference CTO/VP approval?
- D (Decision Criteria): What are they evaluating on? Security features, CI/CD speed, platform consolidation ROI, compliance?
- D (Decision Process): Timeline, committee, POC stages, procurement steps?
- P (Paper Process): Legal, security review, contract, MSA, SOC2/FedRAMP requirements?
- I (Implicate Pain): Is there a stated business problem — tool sprawl, security gaps, audit failures, slow pipelines?
- C (Champion): Does the sender seem like an internal advocate for GitLab adoption?
- C (Competition): Are other vendors being evaluated? GitHub, Harness, etc.?

DISCOVERY QUESTIONS: 3-5 additional general questions the rep should ask.
These should be specific, not generic. Reference what we know and what's missing.

NEXT BEST ACTION: one concrete sentence. What should the rep do RIGHT NOW?
Examples: "Call within 2 hours — active bake-off with GitHub Enterprise, timeline pressure"
          "Send GitLab Ultimate security scanning demo, then schedule POC planning call"
          "Schedule migration assessment — they have 500+ Jenkins pipelines to convert"

═══════════════════════════════════════════════════
PART 5: PARTNERSHIP & STRATEGIC FIT
═══════════════════════════════════════════════════

PARTNERSHIP SYNERGIES: ways GitLab and this company could mutually benefit.
Think: case study potential, industry vertical reference, co-sell with cloud partners, integration ecosystem.

PARTNERSHIP DETRACTORS: risks or friction points.
Think: existing GitHub Enterprise contract, competing vendor lock-in, migration complexity, regulatory constraints.

═══════════════════════════════════════════════════
RULES
═══════════════════════════════════════════════════
- These are INBOUND emails TO GitLab expressing interest in GitLab products. Score them as GitLab prospects.
- Be generous with scores for emails that show clear GitLab product interest, specific requirements, and buying signals.
- Do not penalize emails for mentioning GitLab — that IS the product they should be asking about.
- Do not invent titles, companies, or budget figures not supported by the email.
- Support and partnership emails are visible but not new pipeline.
- Spam should score near zero.
- Return the final answer ONLY by calling record_scoring_result.
""".strip()

    def _user_prompt(self, email: RawEmail) -> str:
        company = "GitLab" if self.gitlab_mode else "Anthropic"
        extra = (
            "\n- Classify use case (platform_consolidation, devsecops, ci_cd_modernization, compliance_automation, dual_motion)"
            "\n- Identify current toolchain being replaced (GitHub, Jenkins, CircleCI, etc.)"
            if self.gitlab_mode else
            "\n- Classify use case, product line fit, and buying stage"
        )
        return f"""
Score and qualify this inbound email to {company}.

Email metadata:
- email_id: {email.email_id}
- sender_email: {email.sender_email}
- sender_name: {email.sender_name or "unknown"}
- received_at: {email.received_at}

Subject:
{email.subject}

Body:
{email.body}

Output requirements:
- Identify company name and domain when inferable{extra}
- Estimate ACV and TAM based on available signals
- Complete MEDDPICC assessment with known/partial/unknown for each letter
- Generate 3-5 specific discovery questions tied to MEDDPICC gaps
- Provide one concrete next best action for the rep
- Identify partnership synergies and detractors
- Summary must be 1-2 sentences, usable in a sales dashboard
""".strip()
