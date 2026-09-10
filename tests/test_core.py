import io
import pytest
from pypdf import PdfReader
from core import ROLE_DEFAULTS, access_allowed, build_blueprint, calculate_metrics, redact, role_config, run_workflow, workflow_map

def test_calculations():
    assert calculate_metrics(72,48,54)=={"pressure_ratio":1.5,"waitlist_change_pct":33.3,"capacity_gap":24}
    with pytest.raises(ValueError): calculate_metrics(2,0,1)

@pytest.mark.parametrize("fault,last,status",[
 ("stale_roster","validate_evidence","blocked"),("conflicting_reports","supervisor_quality_gate","escalated"),("missing_owner","validate_evidence","blocked"),("unapproved_tool","risk_policy_review","blocked"),("risk_timeout","risk_policy_review","blocked"),("bypass_approval","human_approval_interrupt","blocked")])
def test_fault_paths(fault,last,status):
    s=run_workflow(fault); assert s.trace[-1]["node"]==last and s.trace[-1]["status"]==status and not s.packet

def test_high_confidence_is_reduced(): assert run_workflow("high_confidence").confidence==58
def test_approval_gate_blocks_and_resumes():
    assert run_workflow().statuses["generate_decision_packet"]=="waiting"
    assert run_workflow(approval="approve").packet
    assert not run_workflow(approval="reject").packet
    assert not run_workflow(approval="clarify").packet
def test_access_code(): assert access_allowed("aster","aster") and not access_allowed("wrong","aster") and access_allowed("",None)
def test_redaction():
    x=redact({"api_key":"sk-secret123456", "message":"Bearer abcdefghijklmnop"}); assert "secret" not in str(x) and "abcdefghijklmnop" not in str(x)
def test_role_changes_map(): assert workflow_map(role_config("Clinic / Operations")) != workflow_map(role_config("Finance / Revenue Cycle"))
def test_pdf_changes_with_inputs():
    c=role_config("Clinic / Operations"); p={"name":"Alex Example","department":"Ops","role":"Clinic / Operations","success_kpi":"95 percent","next_action":"Meet owner"}
    a=build_blueprint(p,c,"stale_roster","Blocked for stale evidence")
    p["name"]="Jordan Example"; b=build_blueprint(p,c,"none","Ready")
    assert a!=b
    text="".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(b)).pages)
    assert "Jordan Example" in text and "Training artifact based on synthetic data" in text and "Ready" in text
