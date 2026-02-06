# llm_reasoner.py

import json
import time
import hashlib
import re
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import anthropic
except ImportError:
    anthropic = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


class ProductionLLMReasoner:
    """
    FINAL – LLM-based legal reasoning engine
    LLM is used ONLY for explanation, never extraction or scoring
    """

    def __init__(
        self,
        provider: str = "claude",
        api_key: Optional[str] = None,
        cache_ttl: int = 86400
    ):
        self.provider = provider
        self.api_key = api_key
        self.cache_ttl = cache_ttl

        self.cache_dir = Path("cache/llm")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.last_call_time = 0
        self.min_interval = 1.0  # rate limiting

        self.claude_client = None
        self.openai_client = None

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------

    def analyze_clause(
        self,
        clause_text: str,
        clause_type: str,
        contract_type: str,
        risk_summary: Dict[str, Any]
    ) -> Dict[str, Any]:

        cache_key = hashlib.md5(
            f"{clause_text}{clause_type}{contract_type}".encode()
        ).hexdigest()

        cache_file = self.cache_dir / f"{cache_key}.json"

        if cache_file.exists():
            cached = json.loads(cache_file.read_text())
            if self._cache_valid(cached):
                return cached

        # Try LLM first
        if self.api_key:
            result = self._call_llm(
                clause_text, clause_type, contract_type, risk_summary
            )
            if result:
                cache_file.write_text(json.dumps(result, indent=2))
                return result

        # Fallback (always safe)
        fallback = self._fallback_reasoning(
            clause_text, clause_type, contract_type, risk_summary
        )
        cache_file.write_text(json.dumps(fallback, indent=2))
        return fallback

    # ------------------------------------------------------------------
    # LLM CALLS
    # ------------------------------------------------------------------

    def _call_llm(
        self,
        clause_text: str,
        clause_type: str,
        contract_type: str,
        risk_summary: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:

        self._rate_limit()

        prompt = self._build_prompt(
            clause_text, clause_type, contract_type, risk_summary
        )

        try:
            if self.provider == "claude" and anthropic:
                return self._call_claude(prompt)

            if self.provider == "openai" and OpenAI:
                return self._call_openai(prompt)

        except Exception:
            return None

        return None

    def _call_claude(self, prompt: Dict[str, str]) -> Optional[Dict[str, Any]]:
        if not anthropic:
            return None

        if self.claude_client is None:
            self.claude_client = anthropic.Anthropic(api_key=self.api_key)

        response = self.claude_client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=900,
            temperature=0.1,
            system=prompt["system"],
            messages=[{"role": "user", "content": prompt["user"]}],
        )

        return self._parse_json(response.content[0].text)

    def _call_openai(self, prompt: Dict[str, str]) -> Optional[Dict[str, Any]]:
        if not OpenAI:
            return None

        if self.openai_client is None:
            self.openai_client = OpenAI(api_key=self.api_key)

        response = self.openai_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": prompt["system"]},
                {"role": "user", "content": prompt["user"]},
            ],
            temperature=0.1,
            max_tokens=800,
            response_format={"type": "json_object"},
        )

        return json.loads(response.choices[0].message.content)

    # ------------------------------------------------------------------
    # PROMPTING
    # ------------------------------------------------------------------

    def _build_prompt(
        self,
        clause_text: str,
        clause_type: str,
        contract_type: str,
        risk_summary: Dict[str, Any]
    ) -> Dict[str, str]:

        clause_text = clause_text[:3000]

        system = (
            "You are an Indian contract law expert helping SMEs.\n"
            "Explain legal clauses in SIMPLE business English.\n"
            "Do NOT invent facts. Do NOT cite cases.\n"
            "Output VALID JSON only."
        )

        user = f"""
Clause Type: {clause_type}
Contract Type: {contract_type}

Clause Text:
{clause_text}

Detected Risk Summary:
{json.dumps(risk_summary, indent=2)}

Respond ONLY in this JSON format:
{{
  "plain_language_explanation": "",
  "business_impact": "",
  "key_risks": [],
  "renegotiation_points": [],
  "alternative_wording": "",
  "indian_law_notes": "",
  "confidence": 0.0
}}
"""

        return {"system": system, "user": user}

    # ------------------------------------------------------------------
    # FALLBACK (CRITICAL FOR HACKATHON)
    # ------------------------------------------------------------------

    def _fallback_reasoning(
        self,
        clause_text: str,
        clause_type: str,
        contract_type: str,
        risk_summary: Dict[str, Any]
    ) -> Dict[str, Any]:

        risks = [f["risk"] for f in risk_summary.get("risk_factors", [])]

        return {
            "plain_language_explanation": (
                f"This {clause_type} clause sets obligations or rights "
                f"that affect your business under this {contract_type}."
            ),
            "business_impact": (
                "This clause may increase legal or financial exposure "
                "if not carefully negotiated."
            ),
            "key_risks": risks[:3],
            "renegotiation_points": [
                "Limit liability where possible",
                "Ensure mutual rights and obligations",
                "Clarify ambiguous terms"
            ],
            "alternative_wording": (
                "Consider revising this clause to balance rights "
                "and cap liabilities."
            ),
            "indian_law_notes": (
                "Under Indian Contract Act, unreasonable or one-sided "
                "clauses may be challenged."
            ),
            "confidence": 0.55,
            "fallback_used": True
        }

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    def _rate_limit(self):
        now = time.time()
        if now - self.last_call_time < self.min_interval:
            time.sleep(self.min_interval - (now - self.last_call_time))
        self.last_call_time = time.time()

    def _parse_json(self, text: str) -> Optional[Dict[str, Any]]:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            return None

    def _cache_valid(self, data: Dict[str, Any]) -> bool:
        ts = data.get("_cached_at")
        if not ts:
            return False
        return time.time() - ts < self.cache_ttl
