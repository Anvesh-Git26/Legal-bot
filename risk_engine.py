# risk_engine.py

import re
from typing import Dict, List, Any
from dataclasses import dataclass
from pathlib import Path
import json
import hashlib


# ------------------------------------------------------------------
# DATA MODELS
# ------------------------------------------------------------------

@dataclass
class RiskScore:
    clause_level: str
    clause_score: float
    contract_level: str
    contract_score: float
    high_risk_clauses: List[Dict]
    medium_risk_clauses: List[Dict]
    risk_factors: Dict[str, Dict]


# ------------------------------------------------------------------
# RISK ENGINE
# ------------------------------------------------------------------

class ProductionRiskEngine:
    """
    FINAL – Rule-based + weighted risk engine for Indian SME contracts
    No external legal data, no hallucination
    """

    def __init__(self):
        self.config = self._load_config()
        self.patterns = self._build_patterns()
        self.weights = self._build_contract_weights()

        self.cache_dir = Path("cache/risk")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------

    def evaluate_clause(self, clause: Dict, contract_type: str) -> Dict[str, Any]:
        text = clause.get("full_text", "").lower()
        clause_type = clause.get("type", "general")

        cache_key = hashlib.md5(f"{text}{contract_type}".encode()).hexdigest()
        cache_file = self.cache_dir / f"{cache_key}.json"

        if cache_file.exists():
            return json.loads(cache_file.read_text())

        score = 0
        triggered = []

        for risk_name, rule in self.patterns.items():
            if self._match(text, rule):
                base = rule["base_score"]
                weight = self.weights.get(contract_type, {}).get(risk_name, 1.0)
                score += base * weight

                triggered.append({
                    "risk": risk_name,
                    "description": rule["description"],
                    "mitigation": rule["mitigation"]
                })

        normalized = min(score, 100)
        level = self._risk_level(normalized, "clause")

        result = {
            "clause_id": clause.get("id"),
            "clause_type": clause_type,
            "risk_score": round(normalized, 2),
            "risk_level": level,
            "risk_factors": triggered
        }

        cache_file.write_text(json.dumps(result, indent=2))
        return result

    def evaluate_contract(self, clauses: List[Dict], contract_type: str) -> RiskScore:
        clause_results = []
        highs, mediums = [], []
        total_score = 0
        factor_map = {}

        for clause in clauses:
            r = self.evaluate_clause(clause, contract_type)
            clause_results.append(r)
            total_score += r["risk_score"]

            if r["risk_level"] == "High":
                highs.append(r)
            elif r["risk_level"] == "Medium":
                mediums.append(r)

            for f in r["risk_factors"]:
                name = f["risk"]
                factor_map.setdefault(name, {
                    "count": 0,
                    "description": f["description"]
                })
                factor_map[name]["count"] += 1

        avg = total_score / max(len(clauses), 1)

        # Penalize many high-risk clauses
        if len(highs) >= 3:
            avg *= 1.3

        avg = min(avg, 100)
        contract_level = self._risk_level(avg, "contract")

        return RiskScore(
            clause_level=self._risk_level(avg, "clause"),
            clause_score=round(avg, 2),
            contract_level=contract_level,
            contract_score=round(avg, 2),
            high_risk_clauses=highs[:3],
            medium_risk_clauses=mediums[:5],
            risk_factors=factor_map
        )

    # ------------------------------------------------------------------
    # RULE DEFINITIONS
    # ------------------------------------------------------------------

    def _build_patterns(self) -> Dict[str, Dict]:
        return {
            "penalty": {
                "keywords": ["penalty", "liquidated damages", "fine", "forfeit"],
                "base_score": 18,
                "description": "Financial penalties imposed on breach",
                "mitigation": "Cap penalties to actual damages"
            },
            "indemnity": {
                "keywords": ["indemnify", "hold harmless"],
                "base_score": 20,
                "description": "Indemnity obligation for losses",
                "mitigation": "Limit indemnity to direct damages only"
            },
            "unilateral_termination": {
                "keywords": ["terminate without cause", "sole discretion"],
                "base_score": 22,
                "description": "One-sided termination rights",
                "mitigation": "Seek mutual termination rights"
            },
            "jurisdiction": {
                "keywords": ["foreign jurisdiction", "outside india"],
                "base_score": 15,
                "description": "Non-Indian jurisdiction",
                "mitigation": "Insist on Indian courts / arbitration"
            },
            "auto_renewal": {
                "keywords": ["auto renew", "deemed renewed", "lock-in"],
                "base_score": 12,
                "description": "Automatic renewal or lock-in",
                "mitigation": "Add explicit renewal consent"
            },
            "non_compete_ip": {
                "keywords": ["non compete", "ip assignment", "restraint of trade"],
                "base_score": 25,
                "description": "Restrictive non-compete or IP transfer",
                "mitigation": "Limit duration and preserve background IP"
            },
            "unlimited_liability": {
                "keywords": ["unlimited liability", "all damages"],
                "base_score": 30,
                "description": "Unlimited financial exposure",
                "mitigation": "Add liability cap"
            }
        }

    def _build_contract_weights(self) -> Dict[str, Dict]:
        return {
            "employment_agreement": {
                "non_compete_ip": 2.0,
                "unilateral_termination": 1.8
            },
            "vendor_contract": {
                "unlimited_liability": 2.2,
                "penalty": 1.8,
                "indemnity": 2.0
            },
            "lease_agreement": {
                "auto_renewal": 1.7
            },
            "partnership_deed": {
                "jurisdiction": 1.5
            },
            "service_contract": {
                "unlimited_liability": 2.0,
                "indemnity": 1.9
            }
        }

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    def _match(self, text: str, rule: Dict) -> bool:
        return any(k in text for k in rule["keywords"])

    def _risk_level(self, score: float, level: str) -> str:
        if level == "clause":
            return "High" if score >= 70 else "Medium" if score >= 40 else "Low"
        return "High" if score >= 60 else "Medium" if score >= 30 else "Low"

    def _load_config(self):
        return {}
