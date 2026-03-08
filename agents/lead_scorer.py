from __future__ import annotations

import json
import random
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from anthropic import Anthropic
from pydantic import BaseModel, Field, ValidationError, model_validator

CLAUDE_MODEL = "claude-sonnet-4-20250514"
IntentLabel = Literal["new_business", "support", "partnership", "spam", "other"]
UseCaseLabel = Literal["internal_productivity", "product_integration", "dual_motion", "unknown"]
BuyingStageLabel = Literal["researching", "evaluating", "ready_to_buy", "unknown"]
ProductLineFit = Literal["api", "claude_ai_seats", "claude_enterprise", "multiple", "unknown"]
DealSizeTier = Literal["enterprise", "mid_market", "smb", "unknown"]
MeddpiccStatus = Literal["known", "partial", "unknown"]


@dataclass(frozen=True, slots=True)
class MeddpiccScore:
    metrics: str
    economic_buyer: str
    decision_criteria: str
    decision_process: str
    paper_process: str
    implicate_pain: str
    champion: str
    competition: str


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


class MeddpiccModel(BaseModel):
    metrics: MeddpiccStatus = "unknown"
    economic_buyer: MeddpiccStatus = "unknown"
    decision_criteria: MeddpiccStatus = "unknown"
    decision_process: MeddpiccStatus = "unknown"
    paper_process: MeddpiccStatus = "unknown"
    implicate_pain: MeddpiccStatus = "unknown"
    champion: MeddpiccStatus = "unknown"
    competition: MeddpiccStatus = "unknown"


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
        data["meddpicc"] = MeddpiccScore(**meddpicc_data)
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
    def __init__(self, api_key: str, model: str = CLAUDE_MODEL) -> None:
        self.client = Anthropic(api_key=api_key)
        self.model = model

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
        meddpicc_status = {"type": "string", "enum": ["known", "partial", "unknown"]}
        return {
            "name": "record_scoring_result",
            "description": (
                "Return the fully scored and qualified lead object. "
                "Include MEDDPICC assessment, use case classification, revenue estimation, "
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

                    # Anthropic-specific
                    "use_case": {
                        "type": "string",
                        "enum": ["internal_productivity", "product_integration", "dual_motion", "unknown"],
                    },
                    "product_line_fit": {
                        "type": "string",
                        "enum": ["api", "claude_ai_seats", "claude_enterprise", "multiple", "unknown"],
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
                            "metrics": meddpicc_status,
                            "economic_buyer": meddpicc_status,
                            "decision_criteria": meddpicc_status,
                            "decision_process": meddpicc_status,
                            "paper_process": meddpicc_status,
                            "implicate_pain": meddpicc_status,
                            "champion": meddpicc_status,
                            "competition": meddpicc_status,
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

For each letter, assess what the email tells us:
- M (Metrics): Do they mention measurable goals, KPIs, ROI expectations?
- E (Economic Buyer): Is the sender the budget holder? Did they reference one?
- D (Decision Criteria): What are they evaluating on? Performance, price, security?
- D (Decision Process): Timeline, committee, stages, procurement steps?
- P (Paper Process): Legal, security review, contract, MSA, BAA?
- I (Implicate Pain): Is there a stated business problem driving this?
- C (Champion): Does the sender seem like an internal advocate for Claude?
- C (Competition): Are other vendors being evaluated?

Values: "known" (clearly stated), "partial" (hinted at), "unknown" (not mentioned)

DISCOVERY QUESTIONS: 3-5 questions the rep should ask to fill MEDDPICC gaps.
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

    def _user_prompt(self, email: RawEmail) -> str:
        return f"""
Score and qualify this inbound email to Anthropic.

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
- Identify company name and domain when inferable
- Classify use case, product line fit, and buying stage
- Estimate ACV and TAM based on available signals
- Complete MEDDPICC assessment with known/partial/unknown for each letter
- Generate 3-5 specific discovery questions tied to MEDDPICC gaps
- Provide one concrete next best action for the rep
- Identify partnership synergies and detractors
- Summary must be 1-2 sentences, usable in a sales dashboard
""".strip()
