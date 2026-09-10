from __future__ import annotations
import os,time,uuid
import streamlit as st
from core import FAULT_LABELS,NODES,ROLE_DEFAULTS,access_allowed,build_blueprint,deterministic_brief,execute_langgraph,role_config,run_workflow,workflow_map
from llm_service import PROVIDER_MODELS,call_llm,manager_prompt,test_connection

st.set_page_config(page_title="Aster Agentic Workflow Control Room",page_icon="✦",layout="wide",initial_sidebar_state="expanded")
st.markdown("""<style>
:root{--ink:#071A2B;--teal:#007C78;--blue:#075EA8;--gold:#9B6400;--red:#B42318;--muted:#40566B;--line:#CBD7E1}
.stApp{background:linear-gradient(180deg,#EDF4F7 0,#F8FAFB 460px);color:var(--ink)}[data-testid="stSidebar"]{background:#071A2B;border-right:1px solid #153B55}[data-testid="stSidebar"] *{color:#F7FBFC!important}p,li,label,.stMarkdown{color:var(--ink)}
.hero{padding:2.7rem 3rem;border-radius:24px;background:radial-gradient(circle at 92% 12%,#0E7490 0,transparent 28%),linear-gradient(130deg,#061827,#0A3146 72%);color:#FFF;margin-bottom:1.2rem;box-shadow:0 18px 45px #071a2b33;border:1px solid #29556A}.hero h1{font-size:clamp(2.5rem,4.5vw,4.5rem);line-height:.98;margin:.55rem 0 1rem;color:#FFF;letter-spacing:-.045em}.hero p{font-size:1.08rem;color:#E8F5F5!important;max-width:820px;line-height:1.6}.eyebrow{letter-spacing:.15em;text-transform:uppercase;color:#7DE2D1!important;font-weight:800;font-size:.76rem}
.card{background:#FFF;border:1px solid #C9D6DF;border-radius:17px;padding:1.25rem 1.35rem;height:100%;box-shadow:0 5px 22px #071a2b12}.card p{color:#31495D!important}.card h3{margin:.2rem 0;color:#071A2B}.kpi{font-size:2.15rem;font-weight:850;color:#071A2B;letter-spacing:-.04em}.label{font-size:.7rem;letter-spacing:.11em;text-transform:uppercase;font-weight:850;color:#075EA8!important}
.node{padding:.9rem 1rem;border-radius:13px;border:1px solid #C9D6DF;border-left:7px solid #8194A3;background:#FFF;margin:.5rem 0;box-shadow:0 2px 8px #071a2b0d}.node.passed,.node.approved{border-left-color:#007C78}.node.blocked{border-left-color:#B42318;background:#FFF4F2}.node.escalated,.node.waiting{border-left-color:#9B6400;background:#FFFAEB}.status{font-size:.68rem;letter-spacing:.1em;text-transform:uppercase;font-weight:900}.fine{font-size:.84rem;color:#40566B!important}.mapstep{background:#FFF;border:1px solid #C9D6DF;border-left:5px solid #075EA8;border-radius:13px;padding:.9rem 1rem;margin:.55rem 0}.notice{padding:.85rem 1rem;background:#E3F4F2;color:#083D3B;border:1px solid #87CAC4;border-radius:11px;font-weight:650}.danger{padding:.85rem 1rem;background:#FFF0ED;color:#7A271A;border:1px solid #FDA29B;border-radius:11px}.brief{background:#FFF;border:1px solid #B7C7D3;border-radius:18px;padding:1.4rem 1.6rem;box-shadow:0 5px 20px #071a2b10}.stack{font-family:ui-monospace,monospace;background:#071A2B;color:#E7F6F4;padding:1rem;border-radius:12px;line-height:1.8}.stButton>button,.stDownloadButton>button{border-radius:10px;font-weight:750;min-height:2.8rem}.stMetric{background:white;border:1px solid #CBD7E1;padding:1rem;border-radius:13px}
</style>""",unsafe_allow_html=True)

def secret(name):
    try:return st.secrets.get(name,"")
    except Exception:return ""
def init():
    defaults={"access":False,"page":"Situation Room","state":None,"fault":"none","scenario":{"demand":72,"slots":48,"prior":54,"roster_age":0,"claimed_confidence":86,"priority":"Fastest operational relief","control_mode":"Strict fail-closed"},"profile":{"name":"","department":"Clinic Operations","role":"Clinic / Operations","success_kpi":"≥95% evidence completeness and 100% safe-stop compliance","next_action":"Confirm source owners and rehearse one fault test with the accountable leader."},"config":role_config("Clinic / Operations"),"api_key":"","provider":"OpenAI","model":"gpt-5.5","connection":None,"live_brief":"","last_active":time.time(),"thread_id":str(uuid.uuid4())}
    for k,v in defaults.items():st.session_state.setdefault(k,v)
init()
if time.time()-st.session_state.last_active>1800:st.session_state.api_key="";st.session_state.connection=None
st.session_state.last_active=time.time()
expected=os.getenv("WORKSHOP_ACCESS_CODE","") or secret("WORKSHOP_ACCESS_CODE")
if not st.session_state.access:
    st.markdown('<div class="hero"><div class="eyebrow">Aster Healthcare • Applied AI Leadership Lab</div><h1>Agentic Workflow<br/>Control Room</h1><p>Operate a transparent healthcare workflow. Stress it. Stop it safely. Then redesign the pattern for a real managerial decision—without touching a patient, schedule, workforce action, or production system.</p></div>',unsafe_allow_html=True)
    code=st.text_input("Workshop access code",type="password")
    if st.button("Enter the control room",type="primary",use_container_width=True):
        if access_allowed(code,expected):st.session_state.access=True;st.rerun()
        else:st.error("Access denied. Use the rotating code shown by your facilitator.")
    st.caption("Synthetic training environment • Workshop gate, not a security boundary");st.stop()

pages=["Situation Room","Live Agent Run","Evidence & Math","Red-Team Lab","Role Design Studio","Blueprint"]
with st.sidebar:
    st.markdown("## ✦ ASTER CONTROL ROOM");st.caption("OBSERVE • CHALLENGE • ADAPT")
    page=st.radio("Workshop navigation",pages,index=pages.index(st.session_state.page),label_visibility="collapsed");st.session_state.page=page
    st.divider();st.markdown("### Intelligence layer");mode=st.radio("Mode",["Deterministic Demo","Live BYOK"],horizontal=True)
    if mode=="Live BYOK":
        st.session_state.provider=st.selectbox("Provider",list(PROVIDER_MODELS),index=list(PROVIDER_MODELS).index(st.session_state.provider));models=PROVIDER_MODELS[st.session_state.provider]
        if st.session_state.model not in models:st.session_state.model=models[0]
        st.session_state.model=st.selectbox("Model",models,index=models.index(st.session_state.model));st.session_state.api_key=st.text_input("API key",type="password",value=st.session_state.api_key)
        st.markdown('<div class="notice">Your API key is used only for this active training session and is never saved.</div>',unsafe_allow_html=True)
        c1,c2=st.columns(2)
        if c1.button("Test connection",use_container_width=True,disabled=not bool(st.session_state.api_key)):
            with st.spinner("Calling selected model…"):st.session_state.connection=test_connection(st.session_state.provider,st.session_state.model,st.session_state.api_key)
        if c2.button("Remove key",use_container_width=True):st.session_state.api_key="";st.session_state.connection=None;st.session_state.live_brief="";st.rerun()
        if st.session_state.connection:
            r=st.session_state.connection;(st.success if r.ok else st.error)(f'{"Connected" if r.ok else "Connection failed"} • {r.model} • {r.latency_ms} ms'+(f" • {r.error}" if r.error else ""))
    st.divider();st.caption("Designed and facilitated by\nDr. Nasir Uddin, PhD | Duke MBA")

def hero(k,t,c):st.markdown(f'<div class="hero"><div class="eyebrow">{k}</div><h1>{t}</h1><p>{c}</p></div>',unsafe_allow_html=True)
def go(p):st.session_state.page=p;st.rerun()

if page=="Situation Room":
    hero("08:40 AM • SYNTHETIC ACCESS SIGNAL","The pressure is real. The authority is bounded.","Urgent seven-day demand has moved from 54 to 72 requests while verified staffed capacity is 48 slots. Your task is not to ‘let AI decide.’ Your task is to determine whether a leadership option packet is reliable enough to prepare.")
    a,b,c,d=st.columns(4)
    for col,label,value,copy in [(a,"DEMAND","72","urgent requests"),(b,"VERIFIED CAPACITY","48","staffed slots"),(c,"PRESSURE","1.50×","requests per slot"),(d,"AUTHORITY","PREPARE","never execute")]:col.markdown(f'<div class="card"><div class="label">{label}</div><div class="kpi">{value}</div><p>{copy}</p></div>',unsafe_allow_html=True)
    st.write("");st.markdown("### Configure the operating reality")
    x1,x2,x3=st.columns(3);st.session_state.scenario["demand"]=x1.slider("Urgent requests",30,110,st.session_state.scenario["demand"]);st.session_state.scenario["slots"]=x2.slider("Verified staffed slots",24,90,st.session_state.scenario["slots"]);st.session_state.scenario["prior"]=x3.slider("Prior-period requests",25,100,st.session_state.scenario["prior"])
    x4,x5=st.columns(2);st.session_state.scenario["roster_age"]=x4.slider("Roster age (hours)",0,72,st.session_state.scenario["roster_age"]);st.session_state.scenario["claimed_confidence"]=x5.slider("Agent's claimed confidence",40,99,st.session_state.scenario["claimed_confidence"])
    x6,x7=st.columns(2);st.session_state.scenario["priority"]=x6.selectbox("Leadership priority",["Fastest operational relief","Least disruption","Equity across clinics"],index=["Fastest operational relief","Least disruption","Equity across clinics"].index(st.session_state.scenario["priority"]));st.session_state.scenario["control_mode"]=x7.selectbox("Control posture",["Strict fail-closed","Allow best-effort continuation"],index=["Strict fail-closed","Allow best-effort continuation"].index(st.session_state.scenario["control_mode"]))
    preview=run_workflow(scenario=st.session_state.scenario);p1,p2,p3=st.columns(3);p1.metric("Calculated pressure",f'{preview.metrics["pressure_ratio"]:.2f}×');p2.metric("Expected graph state",preview.risk);p3.metric("Calibrated confidence",f"{preview.confidence}%")
    st.markdown("A conventional assistant can draft plausible prose. This workflow must prove **what it saw, what it calculated, what control it applied, why it stopped, and who authorized continuation**.")
    if st.button("Run this configuration through LangGraph →",type="primary",use_container_width=True):st.session_state.state=execute_langgraph(scenario=st.session_state.scenario,thread_id=st.session_state.thread_id);st.session_state.live_brief="";go("Live Agent Run")
elif page=="Live Agent Run":
    hero("LANGGRAPH EXECUTION • CHECKPOINTED SESSION","Follow the evidence—not the theater.","Each node owns a different contract. Inspect its input, operation, release condition, latency, and downstream consequence. The graph pauses at human approval.")
    if st.session_state.state is None:st.session_state.state=execute_langgraph(scenario=st.session_state.scenario,thread_id=st.session_state.thread_id)
    s=st.session_state.state;left,right=st.columns([1.05,1.25])
    with left:
        selected=st.radio("Inspect node",[k for k,_ in NODES],format_func=lambda k:dict(NODES)[k],label_visibility="collapsed")
        for idx,(k,label) in enumerate(NODES):
            status=s.statuses[k];detail=next((e["detail"] for e in s.trace if e["node"]==k),"Waiting for released state");connector="↓" if idx<len(NODES)-1 else ""
            st.markdown(f'<div class="node {status}"><span class="status">{status}</span><br/><b>{label}</b><br/><span class="fine">{detail}</span></div><div style="text-align:center;color:#547184">{connector}</div>',unsafe_allow_html=True)
    with right:
        event=next((e for e in s.trace if e["node"]==selected),None);st.subheader(dict(NODES)[selected]);responsibilities={"intake_scope":"Bounds the decision-support contract and denies operational actions.","retrieve_evidence":"Retrieves allowlisted synthetic sources with owner, scope, and freshness.","calculate_decision_metrics":"Runs reproducible Python math; the LLM never calculates KPIs.","validate_evidence":"Tests ownership, freshness, scope alignment, and consistency.","risk_policy_review":"Evaluates prohibited actions, approved tools, and control availability.","supervisor_quality_gate":"Challenges confidence, conflicts, and option-to-evidence alignment.","human_approval_interrupt":"Persists state and blocks packet generation until a manager decides.","generate_decision_packet":"Turns verified state into managerial language without adding facts or acting."}
        st.markdown(f'<div class="card"><div class="label">NODE CONTRACT</div><h3>{responsibilities[selected]}</h3></div>',unsafe_allow_html=True)
        if event:
            m1,m2,m3=st.columns(3);m1.metric("State",event["status"].upper());m2.metric("Latency",f'{event["latency_ms"]} ms');m3.metric("Est. cost",f'${event["estimated_cost_usd"]:.4f}');st.markdown("**Released output**");st.info(event["detail"]);st.markdown("**Release rule**");st.write("Advance only after pass or accountable approval." if event["status"] in ("passed","approved") else "Downstream state is locked; no silent continuation.")
        else:st.warning("No state arrived because an upstream control stopped the graph.")
        st.markdown('<div class="stack">StateGraph → typed shared state<br/>MemorySaver → session checkpoint<br/>Python tools → KPI + evidence + policy<br/>LangSmith → safe traces when configured<br/>Human gate → required before packet</div>',unsafe_allow_html=True)
    st.divider();c1,c2=st.columns([1,2]);c1.metric("Current risk",s.risk);c2.markdown(f"**Bounded recommendation**  \n{s.recommendation}")
    if s.statuses["human_approval_interrupt"]=="waiting":
        st.warning("DECISION CHECKPOINT — authorize packet preparation only, never an intervention.");x,y,z=st.columns(3)
        if x.button("Approve packet preparation",type="primary",use_container_width=True):st.session_state.state=execute_langgraph(s.fault,"approve",st.session_state.scenario,st.session_state.thread_id);st.session_state.live_brief="";st.rerun()
        if y.button("Request evidence clarification",use_container_width=True):st.session_state.state=execute_langgraph(s.fault,"clarify",st.session_state.scenario,st.session_state.thread_id);st.rerun()
        if z.button("Reject and close",use_container_width=True):st.session_state.state=execute_langgraph(s.fault,"reject",st.session_state.scenario,st.session_state.thread_id);st.rerun()
    if s.packet:
        st.subheader("Decision-grade leadership brief")
        if mode=="Live BYOK" and st.session_state.connection and st.session_state.connection.ok:
            if st.button(f"Generate with {st.session_state.model}",type="primary"):
                with st.spinner("Grounding language in verified state…"):result=call_llm(st.session_state.provider,st.session_state.model,st.session_state.api_key,manager_prompt(s));st.session_state.live_brief=result.text if result.ok else "";st.session_state.connection=result
                if not result.ok:st.error(f"Live call failed safely: {result.error}. Deterministic brief preserved.")
        st.markdown(st.session_state.live_brief or deterministic_brief(s))
elif page=="Evidence & Math":
    hero("EVIDENCE LEDGER • REPRODUCIBLE TOOLS","Every number has a lineage.","Challenge the source, reproduce the math, and inspect the policy result without asking a model for private reasoning.")
    s=st.session_state.state or execute_langgraph(scenario=st.session_state.scenario,thread_id=st.session_state.thread_id);sc=s.scenario or st.session_state.scenario;st.dataframe(s.evidence,use_container_width=True,hide_index=True);a,b,c=st.columns(3);a.metric("Access pressure",f'{s.metrics["pressure_ratio"]:.2f}×',f'{sc["demand"]} ÷ {sc["slots"]}');b.metric("Demand movement",f'{s.metrics["waitlist_change_pct"]:.1f}%',f'vs {sc["prior"]} prior');c.metric("Capacity gap",s.metrics["capacity_gap"],f'max({sc["demand"]} − {sc["slots"]}, 0)')
    t1,t2=st.tabs(["Execution trace","Exact LLM context"]);t1.dataframe(s.trace,use_container_width=True,hide_index=True);t2.code(manager_prompt(s),language="text");t2.caption("Keys, identity, and hidden reasoning are excluded. Only verified synthetic state is released.")
elif page=="Red-Team Lab":
    hero("CONTROLLED FAILURE • SEVEN DISTINCT PATHS","Reliability becomes visible when something breaks.","Predict the stop point, inject a fault, and compare your expectation with the actual control response.")
    outcomes={"stale_roster":"Evidence Validation blocks → request current roster","conflicting_reports":"Supervisor escalates → reconcile 72 vs 51","missing_owner":"Evidence Validation blocks → assign owner","unapproved_tool":"Policy Agent denies tool → record attempt","risk_timeout":"Policy Agent fails closed → no continuation","high_confidence":"Supervisor recalibrates 98% → 58%","bypass_approval":"Human gate rejects bypass → approval stays mandatory","none":"Baseline pauses at human review"}
    fault=st.selectbox("Fault to inject",list(FAULT_LABELS),format_func=lambda x:FAULT_LABELS[x],index=list(FAULT_LABELS).index(st.session_state.fault));st.markdown(f'<div class="card"><div class="label">EXPECTED CONTROL RESPONSE</div><h3>{outcomes[fault]}</h3></div>',unsafe_allow_html=True)
    if st.button("Run adversarial test",type="primary",use_container_width=True):st.session_state.fault=fault;st.session_state.state=execute_langgraph(fault,"pending",st.session_state.scenario,st.session_state.thread_id);st.session_state.live_brief="";st.rerun()
    s=st.session_state.state or execute_langgraph(fault,"pending",st.session_state.scenario,st.session_state.thread_id);st.markdown(f"## Result: `{s.risk}`")
    for e in s.trace:st.markdown(f'<div class="node {e["status"]}"><span class="status">{e["status"]}</span> · <b>{dict(NODES)[e["node"]]}</b><br/><span class="fine">{e["detail"]}</span></div>',unsafe_allow_html=True)
    if not s.packet:st.markdown('<div class="danger"><b>No packet. No tool call. No hidden continuation.</b><br/>The absence of output is correct when a required control fails.</div>',unsafe_allow_html=True)
elif page=="Role Design Studio":
    hero("NO-CODE WORKFLOW DESIGN","Convert a management problem into an auditable graph.","Define the decision boundary before choosing a model. Every edit becomes part of your pilot specification.")
    role=st.selectbox("Start from a role pack",list(ROLE_DEFAULTS),index=list(ROLE_DEFAULTS).index(st.session_state.profile["role"]))
    if role!=st.session_state.profile["role"]:st.session_state.profile["role"]=role;st.session_state.profile["department"]=role;st.session_state.config=role_config(role);st.rerun()
    labels=[("trigger","1 · Trigger"),("decision","2 · Decision support"),("evidence_1","3 · Approved evidence A"),("evidence_2","4 · Approved evidence B"),("kpi","5 · Deterministic calculation"),("control","6 · Non-negotiable control"),("approver","7 · Human approver"),("prohibited","8 · Prohibited action"),("pilot","9 · 30-day learning outcome")];left,right=st.columns([1.05,1])
    with left:
        for k,label in labels:st.session_state.config[k]=st.text_area(label,value=st.session_state.config[k],height=72,key=f"cfg_{role}_{k}")
    with right:
        st.subheader("Live workflow specification")
        for i,x in enumerate(workflow_map(st.session_state.config)):st.markdown(f'<div class="mapstep"><span class="label">NODE {i+1} · {x["stage"]}</span><br/><b>{x["value"]}</b></div>',unsafe_allow_html=True)
        completeness=sum(bool(v.strip()) for v in st.session_state.config.values())/len(st.session_state.config);st.progress(completeness,text=f"Control design completeness: {completeness:.0%}");st.markdown(f'<div class="danger"><b>Never:</b> {st.session_state.config["prohibited"]}</div>',unsafe_allow_html=True)
elif page=="Blueprint":
    hero("AGENT RELIABILITY BLUEPRINT","Leave with an operating hypothesis.","Capture the decision contract, evidence, tool, control, authority, adversarial test, success measure, and next move.")
    p=st.session_state.profile;a,b=st.columns(2);p["name"]=a.text_input("Participant name",p["name"]);p["department"]=b.text_input("Department",p["department"]);p["success_kpi"]=st.text_input("Pilot success KPI",p["success_kpi"]);p["next_action"]=st.text_input("Next-week action",p["next_action"])
    s=st.session_state.state or run_workflow(st.session_state.fault);outcome=s.trace[-1]["detail"] if s.trace else "Not tested";pdf=build_blueprint(p,st.session_state.config,st.session_state.fault,outcome);c1,c2,c3=st.columns(3);c1.metric("Role pack",p["role"]);c2.metric("Fault tested",FAULT_LABELS[st.session_state.fault]);c3.metric("Graph state",s.risk)
    st.download_button("Download my 2-page reliability blueprint",pdf,"aster-agent-reliability-blueprint.pdf","application/pdf",type="primary",use_container_width=True);st.caption("Generated in memory. Inputs and PDFs are not retained after the session.")

with st.sidebar.expander("Instructor reliability console"):
    pin=st.text_input("Instructor PIN",type="password");expected_pin=os.getenv("INSTRUCTOR_PIN","") or secret("INSTRUCTOR_PIN")
    if expected_pin and access_allowed(pin,expected_pin):
        st.success("Instructor controls unlocked");st.toggle("Disable live AI",value=False,key="disable_live");st.code(f"thread={st.session_state.thread_id}\nprovider={st.session_state.provider}\nmodel={st.session_state.model}\nkey=NEVER TRACED")
        if st.button("Reset participant session"):st.session_state.api_key="";st.session_state.connection=None;st.session_state.live_brief="";st.session_state.state=None;st.session_state.fault="none";st.rerun()
