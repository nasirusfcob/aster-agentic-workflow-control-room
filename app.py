from __future__ import annotations

import os
import time
import streamlit as st
from core import FAULT_LABELS, NODES, ROLE_DEFAULTS, access_allowed, build_blueprint, role_config, run_workflow, workflow_map

st.set_page_config(page_title="Aster Agentic Workflow Control Room", page_icon="◎", layout="wide", initial_sidebar_state="expanded")
st.markdown("""<style>
:root{--navy:#102A43;--teal:#087F8C;--blue:#276FBF;--amber:#D99000;--coral:#D1495B;--paper:#F7F3EA}
.stApp{background:var(--paper);color:var(--navy)} [data-testid="stSidebar"]{background:#102A43;color:white}
[data-testid="stSidebar"] *{color:white}.hero{padding:2.2rem;border-radius:22px;background:linear-gradient(125deg,#102A43,#174D5E);color:white;margin-bottom:1rem;box-shadow:0 12px 35px #102a4322}.eyebrow{letter-spacing:.14em;text-transform:uppercase;color:#84DCC6;font-weight:700;font-size:.75rem}.hero h1{font-size:3rem;line-height:1.02;margin:.5rem 0}.hero p{font-size:1.05rem;color:#E5EEF2;max-width:760px}.card{background:white;border:1px solid #DDE7EB;border-radius:16px;padding:1rem 1.1rem;height:100%;box-shadow:0 4px 18px #102a430d}.node{padding:.75rem;border-radius:12px;border-left:6px solid #A8B8C2;background:white;margin:.38rem 0}.passed,.approved{border-color:#087F8C}.blocked{border-color:#D1495B}.escalated,.waiting{border-color:#D99000}.tag{font-size:.72rem;letter-spacing:.08em;text-transform:uppercase;font-weight:800}.fine{font-size:.78rem;color:#526D82}.bigmetric{font-size:2rem;font-weight:800;color:#102A43}.mapstep{background:white;border-top:4px solid #276FBF;border-radius:12px;padding:.8rem;min-height:125px}.stButton>button,.stDownloadButton>button{border-radius:10px;font-weight:700}.notice{padding:.8rem 1rem;background:#E8F3F4;border-radius:10px;border-left:4px solid #087F8C}
</style>""", unsafe_allow_html=True)

def init():
    defaults={"access":False,"page":"Mission Control","state":None,"fault":"none","profile":{"name":"","department":"Clinic Operations","role":"Clinic / Operations","success_kpi":"≥95% evidence completeness and 100% safe-stop compliance","next_action":"Confirm source owners and rehearse one fault test with the accountable leader."},"config":role_config("Clinic / Operations"),"api_key":"","last_active":time.time()}
    for k,v in defaults.items(): st.session_state.setdefault(k,v)
init()
if time.time()-st.session_state.last_active>1800: st.session_state.api_key=""
st.session_state.last_active=time.time()

def secret(name):
    try: return st.secrets.get(name, "")
    except FileNotFoundError: return ""
    except Exception: return ""

expected=os.getenv("WORKSHOP_ACCESS_CODE","") or secret("WORKSHOP_ACCESS_CODE")
if not st.session_state.access:
    st.markdown('<div class="hero"><div class="eyebrow">Aster Healthcare • Manager Lab</div><h1>Agentic Workflow<br/>Control Room</h1><p>Configure → Run → Inspect → Challenge → Adapt</p></div>',unsafe_allow_html=True)
    code=st.text_input("Workshop access code",type="password")
    if st.button("Enter control room",type="primary"):
        if access_allowed(code,expected): st.session_state.access=True; st.rerun()
        else: st.error("That workshop code is not valid. Check the code shown by your facilitator.")
    st.caption("Workshop-entry gate only. This environment contains synthetic training data and no operational systems.")
    st.stop()

pages=["Mission Control","Run the Workflow","Inspect the Evidence","Challenge the Workflow","Make This Your Workflow","Download Your Blueprint"]
with st.sidebar:
    st.markdown("## ASTER / CONTROL ROOM")
    st.caption("SYNTHETIC TRAINING ENVIRONMENT")
    page=st.radio("Navigate",pages,index=pages.index(st.session_state.page),label_visibility="collapsed")
    st.session_state.page=page
    st.divider(); mode=st.selectbox("Experience mode",["Demo Mode","Participant BYOK Live Mode"])
    if mode.startswith("Participant"):
        st.selectbox("Provider",["OpenAI","Gemini","Anthropic","Grok"]); st.selectbox("Model",["Provider default","Fast","Balanced"])
        st.markdown('<div class="notice">Your API key is used only for this active training session and is never saved.</div>',unsafe_allow_html=True)
        st.session_state.api_key=st.text_input("API key",type="password",value=st.session_state.api_key)
        if st.button("Reset and Remove My Key"): st.session_state.api_key=""; st.success("Key removed from this session.")
    st.divider(); st.caption("Designed and facilitated by\nDr. Nasir Uddin, PhD | Duke MBA")

def hero(kicker,title,copy): st.markdown(f'<div class="hero"><div class="eyebrow">{kicker}</div><h1>{title}</h1><p>{copy}</p></div>',unsafe_allow_html=True)
def go(name): st.session_state.page=name; st.rerun()

if page=="Mission Control":
    hero("08:40 AM • ACCESS-PRESSURE INCIDENT","Your agent is standing by.","The next-seven-day urgent access waitlist has increased sharply. Determine whether a same-week operational intervention should be prepared for leadership review.")
    a,b,c=st.columns(3)
    a.markdown('<div class="card"><div class="tag">Your authority</div><div class="bigmetric">Prepare</div><p>A simulated leadership packet—not an operational action.</p></div>',unsafe_allow_html=True)
    b.markdown('<div class="card"><div class="tag">Hard boundary</div><div class="bigmetric">No action</div><p>No appointments, patient contact, staffing changes, or production connections.</p></div>',unsafe_allow_html=True)
    c.markdown('<div class="card"><div class="tag">Your mission</div><div class="bigmetric">See control</div><p>Operate, challenge, inspect, and adapt an observable workflow.</p></div>',unsafe_allow_html=True)
    st.write("");
    if st.button("Launch the Workflow X-Ray →",type="primary",use_container_width=True): st.session_state.state=run_workflow(); go("Run the Workflow")

elif page=="Run the Workflow":
    hero("LIVE WORKFLOW X-RAY","Watch the work. Inspect the proof.","Every node has one accountable responsibility. Select a node to inspect what it received, produced, and why the workflow may proceed.")
    if st.session_state.state is None: st.session_state.state=run_workflow()
    s=st.session_state.state; left,right=st.columns([1.15,1])
    with left:
        selected=st.radio("Workflow nodes",[k for k,_ in NODES],format_func=lambda k:dict(NODES)[k],label_visibility="collapsed")
        for k,label in NODES:
            status=s.statuses[k]; st.markdown(f'<div class="node {status}"><span class="tag">{status}</span><br/><b>{label}</b></div>',unsafe_allow_html=True)
    with right:
        event=next((x for x in s.trace if x["node"]==selected),None)
        label=dict(NODES)[selected]; st.subheader(label)
        if event:
            st.status(event["detail"],state="error" if event["status"]=="blocked" else "complete" if event["status"] in ("passed","approved") else "running")
            m1,m2=st.columns(2); m1.metric("Elapsed",f'{event["latency_ms"]} ms'); m2.metric("Est. model cost",f'${event["estimated_cost_usd"]:.4f}')
            st.markdown(f'**Verified output**  \n{event["detail"]}'); st.markdown(f'**Why next may proceed**  \n{"Control passed; next node may receive the verified output." if event["status"] in ("passed","approved") else "The workflow cannot advance until this state is resolved."}')
        else: st.info("Waiting. No input has been released to this node.")
    st.divider(); st.markdown(f'**Current recommendation:** {s.recommendation}'); st.markdown(f'**Risk state:** `{s.risk}`')
    if s.statuses["human_approval_interrupt"]=="waiting":
        c1,c2,c3=st.columns(3)
        if c1.button("Approve simulated preparation",type="primary",use_container_width=True): st.session_state.state=run_workflow(s.fault,"approve");st.rerun()
        if c2.button("Request clarification",use_container_width=True): st.session_state.state=run_workflow(s.fault,"clarify");st.rerun()
        if c3.button("Reject",use_container_width=True): st.session_state.state=run_workflow(s.fault,"reject");st.rerun()

elif page=="Inspect the Evidence":
    hero("EVIDENCE ROOM","Trust is inspectable.","Review source ownership, freshness, deterministic math, and the exact trace—not hidden reasoning.")
    s=st.session_state.state or run_workflow(); st.dataframe(s.evidence,use_container_width=True,hide_index=True)
    cols=st.columns(3)
    cols[0].metric("Access pressure",f'{s.metrics["pressure_ratio"]:.2f}×',"72 requests / 48 slots")
    cols[1].metric("Demand change",f'{s.metrics["waitlist_change_pct"]:.1f}%','vs. prior 54')
    cols[2].metric("Capacity gap",f'{s.metrics["capacity_gap"]} requests')
    st.subheader("Observable execution trace"); st.dataframe(s.trace,use_container_width=True,hide_index=True)

elif page=="Challenge the Workflow":
    hero("FAULT-INJECTION LAB","Make it fail—safely.","A reliable agent does not improvise around missing controls. Inject one fault and observe where the path changes.")
    fault=st.selectbox("Select a controlled fault",list(FAULT_LABELS),format_func=lambda x:FAULT_LABELS[x],index=list(FAULT_LABELS).index(st.session_state.fault))
    if st.button("Inject fault & run",type="primary"):
        st.session_state.fault=fault; st.session_state.state=run_workflow(fault); st.rerun()
    s=st.session_state.state or run_workflow(fault); st.markdown(f'### Outcome: `{s.risk}`')
    for e in s.trace: st.markdown(f'<div class="node {e["status"]}"><b>{dict(NODES)[e["node"]]}</b> · {e["status"]}<br/><span class="fine">{e["detail"]}</span></div>',unsafe_allow_html=True)
    st.info("Safe stop means no packet and no hidden continuation. Resolve the evidence or control issue, then run again.")

elif page=="Make This Your Workflow":
    hero("ROLE ADAPTATION STUDIO","Turn the pattern into your pilot.","Configure a safe business workflow in plain language. Your map and blueprint update as you type.")
    role=st.selectbox("Role pack",list(ROLE_DEFAULTS),index=list(ROLE_DEFAULTS).index(st.session_state.profile["role"]))
    if role!=st.session_state.profile["role"]: st.session_state.profile["role"]=role;st.session_state.profile["department"]=role;st.session_state.config=role_config(role);st.rerun()
    labels=[("trigger","1. My operational trigger"),("decision","2. My decision to support"),("evidence_1","3a. Approved evidence source one"),("evidence_2","3b. Approved evidence source two"),("kpi","4. Deterministic KPI / calculation"),("control","5. Non-negotiable control or policy rule"),("approver","6. Human approver"),("prohibited","7. Prohibited action"),("pilot","8. First 30-day pilot outcome")]
    left,right=st.columns([1,1.15])
    with left:
        for k,label in labels: st.session_state.config[k]=st.text_input(label,value=st.session_state.config[k],key=f"cfg_{role}_{k}")
    with right:
        st.subheader("Your live workflow map")
        for i,x in enumerate(workflow_map(st.session_state.config)): st.markdown(f'<div class="mapstep"><div class="tag">0{i+1} · {x["stage"]}</div><p>{x["value"]}</p></div>',unsafe_allow_html=True)

elif page=="Download Your Blueprint":
    hero("TAKE-HOME BLUEPRINT","Leave with a testable pilot—not a promise.","Capture ownership, controls, observability, fault testing, and a next-week action in a personalized two-page artifact.")
    p=st.session_state.profile
    a,b=st.columns(2); p["name"]=a.text_input("Participant name",p["name"]);p["department"]=b.text_input("Department",p["department"])
    p["success_kpi"]=st.text_input("Pilot success KPI",p["success_kpi"]);p["next_action"]=st.text_input("Next-week action",p["next_action"])
    s=st.session_state.state or run_workflow(st.session_state.fault); outcome=s.trace[-1]["detail"] if s.trace else "Not yet tested"
    pdf=build_blueprint(p,st.session_state.config,st.session_state.fault,outcome)
    st.download_button("Download my Agent Reliability Blueprint (PDF)",pdf,"aster-agent-reliability-blueprint.pdf","application/pdf",type="primary",use_container_width=True)
    st.success("Generated in memory for this browser session. The app does not retain your inputs or PDF.")

# Hidden instructor entry
with st.sidebar.expander("Facilitator access"):
    pin=st.text_input("Instructor PIN",type="password")
    expected_pin=os.getenv("INSTRUCTOR_PIN","") or secret("INSTRUCTOR_PIN")
    if expected_pin and access_allowed(pin,expected_pin):
        st.toggle("Disable Live AI",value=True,key="disable_live");st.caption("Reliability console: session-local only")
        if st.button("Return session to Demo"): st.session_state.api_key="";st.success("Demo Mode restored.")
