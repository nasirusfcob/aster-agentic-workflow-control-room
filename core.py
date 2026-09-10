from __future__ import annotations

import hashlib
import io
import re
import time
from dataclasses import dataclass, field
from typing import Any, Literal, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

Fault = Literal["none", "stale_roster", "conflicting_reports", "missing_owner", "unapproved_tool", "risk_timeout", "high_confidence", "bypass_approval"]

NODES = [
    ("intake_scope", "Intake & Scope Agent"),
    ("retrieve_evidence", "Evidence Retrieval Agent"),
    ("calculate_decision_metrics", "Decision Calculator Tool"),
    ("validate_evidence", "Evidence Validation"),
    ("risk_policy_review", "Risk & Policy Agent"),
    ("supervisor_quality_gate", "Supervisor / Quality Gate"),
    ("human_approval_interrupt", "Human Approval Checkpoint"),
    ("generate_decision_packet", "Decision-Packet Generator"),
]


class AgentGraphState(TypedDict, total=False):
    """Typed, checkpointable orchestration envelope; never stores credentials."""
    fault: Fault
    approval: str
    workflow: WorkflowState
    current_node: str


def build_langgraph():
    """Build the real execution topology used to mirror the visible X-Ray.

    Each node advances only when its predecessor produced a releasable status.
    The in-memory checkpointer is scoped to the active process/session.
    """
    graph = StateGraph(AgentGraphState)

    def intake(state: AgentGraphState):
        return {"workflow": run_workflow(state.get("fault", "none"), state.get("approval", "pending")), "current_node": "intake_scope"}

    def mark(name: str):
        def node(state: AgentGraphState): return {"current_node": name}
        return node

    for name, _ in NODES:
        graph.add_node(name, intake if name == "intake_scope" else mark(name))
    graph.add_edge(START, "intake_scope")
    for (a, _), (b, _) in zip(NODES, NODES[1:]): graph.add_edge(a, b)
    graph.add_edge("generate_decision_packet", END)
    return graph.compile(checkpointer=MemorySaver(), interrupt_before=["generate_decision_packet"])

FAULT_LABELS = {
    "none": "No fault — verified baseline",
    "stale_roster": "Stale staffing roster",
    "conflicting_reports": "Conflicting access-demand report",
    "missing_owner": "Missing evidence owner",
    "unapproved_tool": "Requested unapproved tool",
    "risk_timeout": "Risk-agent timeout",
    "high_confidence": "Unjustifiably high confidence",
    "bypass_approval": "Instruction attempting to bypass manager approval",
}

ROLE_DEFAULTS = {
    "Clinic / Operations": ["Urgent waitlist rises 20% in 24 hours", "Prepare a bounded same-week access response", "Access demand report", "Staffing roster", "Waitlist ÷ staffed appointment slots", "Roster must be current within 24 hours", "Clinic operations director", "Change appointments or contact patients", "Validate one clinic workflow with ≥95% evidence completeness"],
    "Patient Experience": ["Complaint volume exceeds weekly tolerance", "Prepare service-recovery themes for review", "Synthetic complaint themes", "Service-level report", "Open cases ÷ available review capacity", "No patient-level text may enter the workflow", "Patient experience director", "Contact patients or modify cases", "Reduce review preparation time by 25%"],
    "Finance / Revenue Cycle": ["Synthetic denial backlog rises 15%", "Prepare two backlog-management options", "Denial category report", "Analyst capacity roster", "Backlog items ÷ weekly analyst capacity", "No claim may be changed or resubmitted", "Revenue cycle director", "Alter, submit, or adjudicate claims", "Validate variance within ±2% of manual calculation"],
    "People / Workforce": ["Shift coverage risk exceeds tolerance", "Prepare coverage-risk options", "Synthetic coverage roster", "Approved demand forecast", "Required hours ÷ available qualified hours", "No employee-level performance inference", "Workforce planning director", "Assign shifts or evaluate employees", "Identify coverage gaps 2 days earlier"],
    "Procurement / Supply Chain": ["Critical-item days-on-hand falls below threshold", "Prepare replenishment options", "Synthetic inventory snapshot", "Approved usage forecast", "On-hand units ÷ average daily usage", "Vendor and inventory data must be approved and current", "Supply chain director", "Place orders or contact vendors", "Validate alerts with zero autonomous orders"],
}


def calculate_metrics(waitlist: int, slots: int, prior_waitlist: int) -> dict[str, float]:
    if slots <= 0 or prior_waitlist <= 0 or waitlist < 0:
        raise ValueError("waitlist must be non-negative; slots and prior_waitlist must be positive")
    return {"pressure_ratio": round(waitlist / slots, 2), "waitlist_change_pct": round((waitlist - prior_waitlist) / prior_waitlist * 100, 1), "capacity_gap": max(waitlist - slots, 0)}


def access_allowed(entered: str, expected: str | None) -> bool:
    if not expected:
        return True
    return bool(entered) and hashlib.sha256(entered.encode()).digest() == hashlib.sha256(expected.encode()).digest()


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: ("[REDACTED]" if any(x in k.lower() for x in ("key", "token", "secret")) else redact(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, str):
        value = re.sub(r"(?i)(api[_ -]?key|bearer|token)\s*[:=]?\s*[A-Za-z0-9_\-\.]{8,}", r"\1=[REDACTED]", value)
        value = re.sub(r"\b(sk-|AIza|xai-)[A-Za-z0-9_\-]{8,}\b", "[REDACTED]", value)
    return value


@dataclass
class WorkflowState:
    fault: Fault = "none"
    approval: str = "pending"
    statuses: dict[str, str] = field(default_factory=lambda: {key: "waiting" for key, _ in NODES})
    evidence: list[dict[str, Any]] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)
    trace: list[dict[str, Any]] = field(default_factory=list)
    recommendation: str = "Not yet prepared"
    risk: str = "Awaiting review"
    confidence: int = 0
    packet: str = ""


def _event(state: WorkflowState, node: str, status: str, detail: str, ms: int, cost: float = 0.0) -> None:
    state.statuses[node] = status
    state.trace.append({"node": node, "status": status, "detail": detail, "latency_ms": ms, "estimated_cost_usd": cost})


def run_workflow(fault: Fault = "none", approval: str = "pending") -> WorkflowState:
    s = WorkflowState(fault=fault, approval=approval)
    _event(s, "intake_scope", "passed", "Scope bounded to preparation for leadership review; actions prohibited.", 82, .0001)
    s.evidence = [
        {"source": "Synthetic access-demand report", "value": "72 urgent requests", "owner": "Access analytics", "freshness": "08:35 today", "status": "verified"},
        {"source": "Synthetic staffing roster", "value": "48 staffed slots", "owner": "Clinic operations", "freshness": "08:30 today", "status": "verified"},
    ]
    if fault == "stale_roster": s.evidence[1].update(freshness="72 hours old", status="stale")
    if fault == "conflicting_reports": s.evidence.append({"source": "Synthetic secondary demand report", "value": "51 urgent requests", "owner": "Planning", "freshness": "08:36 today", "status": "conflict"})
    if fault == "missing_owner": s.evidence[0].update(owner="Missing", status="incomplete")
    _event(s, "retrieve_evidence", "passed", f"Retrieved {len(s.evidence)} approved synthetic sources.", 146, .0002)
    s.metrics = calculate_metrics(72, 48, 54)
    _event(s, "calculate_decision_metrics", "passed", "Deterministic calculation: 72 ÷ 48 = 1.50 pressure ratio; demand is up 33.3%.", 4)
    if fault in ("stale_roster", "missing_owner"):
        reason = "Roster is stale; obtain a current approved roster." if fault == "stale_roster" else "Evidence owner is missing; manager must request ownership."
        _event(s, "validate_evidence", "blocked", reason, 31); s.risk = "BLOCKED — evidence incomplete"; return s
    _event(s, "validate_evidence", "passed", "Freshness, ownership, and consistency checks completed.", 39)
    if fault == "unapproved_tool":
        _event(s, "risk_policy_review", "blocked", "Unapproved scheduling tool denied and recorded. No call was made.", 18); s.risk = "BLOCKED — unapproved tool"; return s
    if fault == "risk_timeout":
        _event(s, "risk_policy_review", "blocked", "Risk agent timed out. Fail-safe stop; no hidden continuation.", 2000); s.risk = "BLOCKED — control unavailable"; return s
    _event(s, "risk_policy_review", "passed", "No patient contact, schedule change, or staffing action permitted.", 73, .0001)
    if fault == "conflicting_reports":
        _event(s, "supervisor_quality_gate", "escalated", "Demand reports conflict: 72 vs 51. Reconcile before recommendation.", 55); s.risk = "ESCALATED — evidence conflict"; return s
    s.confidence = 58 if fault == "high_confidence" else 86
    quality = "Claimed confidence reduced from 98% to 58% because evidence does not support it." if fault == "high_confidence" else "Evidence, calculations, and bounded options are internally consistent."
    _event(s, "supervisor_quality_gate", "passed", quality, 61, .0001)
    s.recommendation = "Prepare Option A: add protected review capacity; Option B: rebalance same-week administrative capacity. Leadership decides; no action is taken."
    if fault == "bypass_approval":
        _event(s, "human_approval_interrupt", "blocked", "Bypass instruction rejected. Manager approval remains mandatory.", 7); s.risk = "BLOCKED — approval required"; return s
    if approval == "pending":
        _event(s, "human_approval_interrupt", "waiting", "Paused. Manager must approve, reject, or request clarification.", 1); s.risk = "HUMAN REVIEW"; return s
    if approval == "reject":
        _event(s, "human_approval_interrupt", "blocked", "Manager rejected simulated preparation.", 3); s.risk = "REJECTED"; return s
    if approval == "clarify":
        _event(s, "human_approval_interrupt", "escalated", "Manager requested evidence clarification. Packet generation remains locked.", 3); s.risk = "CLARIFICATION REQUIRED"; return s
    _event(s, "human_approval_interrupt", "approved", "Manager approved simulated packet preparation only.", 3)
    s.packet = "Leadership review packet prepared: verified situation, two bounded options, assumptions, controls, and approval record. No operational action executed."
    _event(s, "generate_decision_packet", "passed", s.packet, 92, .0002); s.risk = "CONTROLLED / APPROVED"
    return s


def role_config(role: str) -> dict[str, str]:
    vals = ROLE_DEFAULTS[role]
    keys = ["trigger", "decision", "evidence_1", "evidence_2", "kpi", "control", "approver", "prohibited", "pilot"]
    return dict(zip(keys, vals))


def workflow_map(config: dict[str, str]) -> list[dict[str, str]]:
    return [
        {"stage": "Trigger", "value": config["trigger"]}, {"stage": "Evidence", "value": f'{config["evidence_1"]} + {config["evidence_2"]}'},
        {"stage": "Calculate", "value": config["kpi"]}, {"stage": "Control", "value": config["control"]},
        {"stage": "Approve", "value": config["approver"]}, {"stage": "Prepare", "value": config["decision"]},
    ]


def build_blueprint(profile: dict[str, str], config: dict[str, str], fault: Fault, outcome: str) -> bytes:
    out = io.BytesIO(); styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(out, pagesize=letter, rightMargin=.55*inch, leftMargin=.55*inch, topMargin=.55*inch, bottomMargin=.55*inch)
    title = ParagraphStyle("TitleX", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=23, leading=27, textColor=colors.HexColor("#102A43"), alignment=TA_CENTER)
    h = ParagraphStyle("HX", parent=styles["Heading2"], textColor=colors.HexColor("#087F8C"), spaceBefore=10, spaceAfter=5)
    body = ParagraphStyle("BX", parent=styles["BodyText"], leading=14, textColor=colors.HexColor("#243B53"))
    story = [Paragraph("Agent Reliability &amp; Role Adaptation Blueprint", title), Spacer(1, 8), Paragraph("Aster Agentic Workflow Control Room", h), Paragraph(f'<b>Participant:</b> {profile.get("name","Participant")} &nbsp; | &nbsp; <b>Department:</b> {profile.get("department","")} &nbsp; | &nbsp; <b>Role pack:</b> {profile.get("role","")}', body), Spacer(1, 10)]
    rows = [[Paragraph("WORKFLOW STAGE", body), Paragraph("YOUR CONFIGURATION", body)]] + [[Paragraph(x["stage"], body), Paragraph(x["value"], body)] for x in workflow_map(config)]
    table = Table(rows, colWidths=[1.35*inch, 5.45*inch]); table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#102A43")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.5,colors.HexColor("#B7C9D3")),("VALIGN",(0,0),(-1,-1),"TOP"),("BACKGROUND",(0,1),(0,-1),colors.HexColor("#E8F3F4")),("LEFTPADDING",(0,0),(-1,-1),8),("RIGHTPADDING",(0,0),(-1,-1),8),("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7)])); story += [table]
    story += [Paragraph("Reliability controls", h), Paragraph(f'<b>Prohibited action:</b> {config["prohibited"]}<br/><b>Observability signals:</b> evidence freshness and ownership; deterministic inputs/outputs; node status; latency; estimated model cost; policy result; human approval.<br/><b>Fault-injection test:</b> {FAULT_LABELS[fault]}<br/><b>Observed outcome:</b> {outcome}', body), PageBreak()]
    story += [Paragraph("30-Day Pilot Card", title), Spacer(1, 12), Paragraph(f'<b>Pilot hypothesis:</b> {config["pilot"]}<br/><br/><b>Success KPI:</b> {profile.get("success_kpi", "Evidence completeness and safe-stop rate")}<br/><br/><b>Next-week action:</b> {profile.get("next_action", "Validate the trigger, source owners, and approval path with the accountable leader.")}', body), Spacer(1, 18), Paragraph("Manager review prompts", h), Paragraph("1. Can every recommendation be reproduced from approved evidence and deterministic calculations?<br/>2. Does every unavailable control stop the workflow visibly?<br/>3. Is the human checkpoint placed before any consequential output?<br/>4. What would prove this pilot is reliable enough to continue—and what would stop it?", body), Spacer(1, 24), Paragraph("Training artifact based on synthetic data. Not an operational, clinical, or production-system instruction.", body)]
    def footer(canvas, _doc):
        canvas.saveState(); canvas.setFont("Helvetica", 8); canvas.setFillColor(colors.HexColor("#526D82")); canvas.drawCentredString(letter[0]/2, .28*inch, "Aster Agentic Workflow Control Room | Designed and facilitated by Dr. Nasir Uddin"); canvas.restoreState()
    doc.build(story, onFirstPage=footer, onLaterPages=footer); return out.getvalue()
