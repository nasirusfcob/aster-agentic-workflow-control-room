from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

import httpx

PROVIDER_MODELS = {
    "OpenAI": ["gpt-5.5", "gpt-5.2", "gpt-5.1", "gpt-5-mini", "gpt-4.1"],
    "Google Gemini": ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.1-pro-preview", "gemini-2.5-pro", "gemini-2.5-flash"],
    "Anthropic": ["claude-sonnet-5", "claude-opus-5", "claude-fable-5", "claude-sonnet-4-6", "claude-haiku-4-5-20251001"],
    "xAI Grok": ["grok-4.6", "grok-4.5", "grok-4.3", "grok-4.20-reasoning-latest", "grok-4.20-non-reasoning-latest"],
}

@dataclass
class LLMResult:
    ok: bool
    text: str
    latency_ms: int
    provider: str
    model: str
    error: str = ""

SYSTEM = """You are the managerial-language layer inside a healthcare operations training simulation. All data is synthetic. Use only facts supplied in the prompt. Never invent patients, causes, forecasts, policies, staffing availability, or operational actions. Do not reveal chain-of-thought. Produce a decision-grade brief with exactly these headings: Executive signal; Verified facts; Two bounded options; Trade-offs; Decision requested; Assumptions to validate; Controls and stop conditions. State clearly that leadership review is required and no action was taken."""

def _extract_openai(data: dict[str, Any]) -> str:
    if data.get("output_text"): return data["output_text"]
    texts=[]
    for item in data.get("output",[]):
        for part in item.get("content",[]):
            if part.get("type") in ("output_text","text"): texts.append(part.get("text", ""))
    return "\n".join(texts).strip()

def call_llm(provider: str, model: str, api_key: str, prompt: str, max_tokens: int = 800) -> LLMResult:
    started=time.perf_counter()
    try:
        timeout=httpx.Timeout(30.0, connect=10.0)
        with httpx.Client(timeout=timeout) as client:
            if provider=="OpenAI":
                r=client.post("https://api.openai.com/v1/responses",headers={"Authorization":f"Bearer {api_key}","Content-Type":"application/json"},json={"model":model,"instructions":SYSTEM,"input":prompt,"max_output_tokens":max_tokens})
                r.raise_for_status(); text=_extract_openai(r.json())
            elif provider=="Google Gemini":
                r=client.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",params={"key":api_key},json={"system_instruction":{"parts":[{"text":SYSTEM}]},"contents":[{"parts":[{"text":prompt}]}],"generationConfig":{"maxOutputTokens":max_tokens,"temperature":0.2}})
                r.raise_for_status(); text=r.json()["candidates"][0]["content"]["parts"][0]["text"]
            elif provider=="Anthropic":
                r=client.post("https://api.anthropic.com/v1/messages",headers={"x-api-key":api_key,"anthropic-version":"2023-06-01","Content-Type":"application/json"},json={"model":model,"system":SYSTEM,"messages":[{"role":"user","content":prompt}],"max_tokens":max_tokens,"temperature":0.2})
                r.raise_for_status(); text="\n".join(x.get("text","") for x in r.json().get("content",[]) if x.get("type")=="text")
            elif provider=="xAI Grok":
                r=client.post("https://api.x.ai/v1/chat/completions",headers={"Authorization":f"Bearer {api_key}","Content-Type":"application/json"},json={"model":model,"messages":[{"role":"system","content":SYSTEM},{"role":"user","content":prompt}],"max_tokens":max_tokens,"temperature":0.2})
                r.raise_for_status(); text=r.json()["choices"][0]["message"]["content"]
            else: raise ValueError("Unsupported provider")
        if not text.strip(): raise ValueError("Provider returned an empty response")
        return LLMResult(True,text.strip(),round((time.perf_counter()-started)*1000),provider,model)
    except Exception as exc:
        safe=str(exc).replace(api_key,"[REDACTED]") if api_key else str(exc)
        return LLMResult(False,"",round((time.perf_counter()-started)*1000),provider,model,safe[:280])

def test_connection(provider: str, model: str, api_key: str) -> LLMResult:
    return call_llm(provider,model,api_key,"Connection check. Reply with exactly: CONNECTED",32)

def manager_prompt(workflow: Any) -> str:
    evidence=json.dumps(workflow.evidence,ensure_ascii=False)
    return f"""Prepare the simulated leadership brief from this verified workflow state.
Evidence: {evidence}
Deterministic metrics: {json.dumps(workflow.metrics)}
Risk state: {workflow.risk}
Confidence: {workflow.confidence}%
Bounded recommendation: {workflow.recommendation}
Approval status: {workflow.approval}
Policy boundary: Do not change appointments, contact patients, alter staffing, or call external tools."""
