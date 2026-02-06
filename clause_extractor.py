# clause_extractor.py

import re
import hashlib
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class Clause:
    id: str
    number: str
    title: str
    type: str
    full_text: str


class ProductionClauseExtractor:
    """
    FINAL – Robust Clause Extractor
    Handles:
    - Numbered clauses (1., 1.1, Clause 3, Section IV)
    - Unnumbered paragraph-based contracts
    - Indian drafting styles
    """

    def __init__(self):
        self.clause_type_patterns = self._build_clause_type_patterns()

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------

    def extract_clauses(self, text: str) -> List[Dict[str, Any]]:
        text = self._clean_text(text)

        clauses = self._extract_numbered_clauses(text)

        if not clauses or len(clauses) < 3:
            clauses = self._extract_paragraph_clauses(text)

        return [self._to_dict(c) for c in clauses]

    # ------------------------------------------------------------------
    # NUMBERED CLAUSE EXTRACTION
    # ------------------------------------------------------------------

    def _extract_numbered_clauses(self, text: str) -> List[Clause]:
        pattern = re.compile(
            r'(?:^|\n)'
            r'(?P<number>(?:Clause|Section)?\s*\d+(?:\.\d+)*|\d+\.)'
            r'\s*(?P<title>[A-Z][^\n]{0,80})?'
            r'\n(?P<body>.*?)(?=\n(?:Clause|Section)?\s*\d+(?:\.\d+)*|\Z)',
            re.IGNORECASE | re.DOTALL
        )

        clauses = []

        for match in pattern.finditer(text):
            number = match.group("number").strip()
            title = (match.group("title") or "").strip()
            body = match.group("body").strip()

            full_text = f"{number} {title}\n{body}".strip()
            clause_type = self._infer_clause_type(full_text)

            clauses.append(
                Clause(
                    id=self._generate_id(full_text),
                    number=number,
                    title=title,
                    type=clause_type,
                    full_text=full_text
                )
            )

        return clauses

    # ------------------------------------------------------------------
    # PARAGRAPH-BASED FALLBACK
    # ------------------------------------------------------------------

    def _extract_paragraph_clauses(self, text: str) -> List[Clause]:
        paragraphs = [
            p.strip() for p in re.split(r'\n{2,}', text)
            if len(p.strip()) > 200
        ]

        clauses = []

        for idx, para in enumerate(paragraphs, start=1):
            clause_type = self._infer_clause_type(para)

            clauses.append(
                Clause(
                    id=self._generate_id(para),
                    number=f"P{idx}",
                    title=clause_type.replace("_", " ").title(),
                    type=clause_type,
                    full_text=para
                )
            )

        return clauses

    # ------------------------------------------------------------------
    # CLAUSE TYPE INFERENCE
    # ------------------------------------------------------------------

    def _build_clause_type_patterns(self) -> Dict[str, List[str]]:
        return {
            "termination": [
                "terminate", "termination", "notice period"
            ],
            "payment": [
                "payment", "fees", "salary", "consideration", "invoice"
            ],
            "confidentiality": [
                "confidential", "non-disclosure", "nda"
            ],
            "indemnification": [
                "indemnify", "hold harmless"
            ],
            "limitation_of_liability": [
                "liability", "damages", "cap on liability"
            ],
            "governing_law": [
                "governing law", "jurisdiction", "courts"
            ],
            "intellectual_property": [
                "intellectual property", "ip rights", "ownership"
            ],
            "non_compete": [
                "non-compete", "restraint of trade"
            ],
            "arbitration": [
                "arbitration", "arbitral tribunal"
            ]
        }

    def _infer_clause_type(self, text: str) -> str:
        text_l = text.lower()

        for clause_type, keywords in self.clause_type_patterns.items():
            if any(k in text_l for k in keywords):
                return clause_type

        return "general"

    # ------------------------------------------------------------------
    # UTILITIES
    # ------------------------------------------------------------------

    def _clean_text(self, text: str) -> str:
        text = text.replace("\r", "")
        text = re.sub(r'[ \t]+', ' ', text)
        return text.strip()

    def _generate_id(self, text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()[:12]

    def _to_dict(self, clause: Clause) -> Dict[str, Any]:
        return {
            "id": clause.id,
            "number": clause.number,
            "title": clause.title,
            "type": clause.type,
            "full_text": clause.full_text
        }
