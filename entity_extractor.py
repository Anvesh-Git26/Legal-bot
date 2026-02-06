# entity_extractor.py

import re
import spacy
from typing import Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime
import dateparser


# ------------------------------------------------------------------
# DATA CONTAINER
# ------------------------------------------------------------------

@dataclass
class ExtractedEntities:
    parties: List[Dict] = field(default_factory=list)
    dates: List[Dict] = field(default_factory=list)
    amounts: List[Dict] = field(default_factory=list)
    jurisdictions: List[Dict] = field(default_factory=list)

    obligations: List[Dict] = field(default_factory=list)
    rights: List[Dict] = field(default_factory=list)
    prohibitions: List[Dict] = field(default_factory=list)

    termination_conditions: List[Dict] = field(default_factory=list)
    liabilities: List[Dict] = field(default_factory=list)
    indemnities: List[Dict] = field(default_factory=list)
    penalties: List[Dict] = field(default_factory=list)

    confidentiality: List[Dict] = field(default_factory=list)
    intellectual_property: List[Dict] = field(default_factory=list)
    dispute_resolution: List[Dict] = field(default_factory=list)
    governing_law: List[Dict] = field(default_factory=list)


# ------------------------------------------------------------------
# ENTITY EXTRACTOR
# ------------------------------------------------------------------

class ProductionEntityExtractor:
    """
    FINAL – Entity extractor for Indian legal contracts
    Regex-first + NLP assist (no hallucination)
    """

    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")
        self.patterns = self._build_patterns()

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------

    def extract(self, text: str) -> Dict[str, Any]:
        entities = ExtractedEntities()

        text = self._clean_text(text)

        self._extract_parties(text, entities)
        self._extract_dates(text, entities)
        self._extract_amounts(text, entities)
        self._extract_jurisdiction(text, entities)

        self._extract_semantic_clauses(text, entities)

        return self._to_dict(entities)

    # ------------------------------------------------------------------
    # REGEX EXTRACTION
    # ------------------------------------------------------------------

    def _build_patterns(self) -> Dict[str, List[str]]:
        return {
            "party": [
                r'between\s+(.*?)\s+and\s+(.*?)(?=,|\n|hereinafter)',
            ],
            "date": [
                r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}',
                r'\d{1,2}\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}',
            ],
            "amount": [
                r'(₹|Rs\.?|INR)\s*\d[\d,]*(?:\.\d+)?',
            ],
            "jurisdiction": [
                r'courts?\s+(?:at|in)\s+([A-Za-z ]+)',
                r'jurisdiction\s+of\s+([A-Za-z ]+)',
            ],
        }

    def _extract_parties(self, text: str, entities: ExtractedEntities):
        for pattern in self.patterns["party"]:
            for match in re.findall(pattern, text, re.IGNORECASE):
                for party in match:
                    party = party.strip()
                    if len(party) > 3:
                        entities.parties.append({
                            "name": party,
                            "type": self._classify_party(party)
                        })

    def _extract_dates(self, text: str, entities: ExtractedEntities):
        for pattern in self.patterns["date"]:
            for match in re.findall(pattern, text):
                parsed = dateparser.parse(str(match))
                if parsed:
                    entities.dates.append({
                        "date": parsed.date().isoformat(),
                        "raw": match
                    })

    def _extract_amounts(self, text: str, entities: ExtractedEntities):
        for pattern in self.patterns["amount"]:
            for match in re.findall(pattern, text):
                entities.amounts.append({
                    "amount": match,
                    "currency": "INR"
                })

    def _extract_jurisdiction(self, text: str, entities: ExtractedEntities):
        for pattern in self.patterns["jurisdiction"]:
            for match in re.findall(pattern, text, re.IGNORECASE):
                entities.jurisdictions.append({
                    "location": match.strip(),
                    "country": "India"
                })

    # ------------------------------------------------------------------
    # SEMANTIC EXTRACTION (LOW RISK NLP)
    # ------------------------------------------------------------------

    def _extract_semantic_clauses(self, text: str, entities: ExtractedEntities):
        doc = self.nlp(text[:800000])

        for sent in doc.sents:
            s = sent.text.lower()

            if "shall" in s or "must" in s:
                entities.obligations.append({"text": sent.text})

            if "may" in s or "entitled" in s:
                entities.rights.append({"text": sent.text})

            if "shall not" in s or "prohibited" in s:
                entities.prohibitions.append({"text": sent.text})

            if "terminate" in s:
                entities.termination_conditions.append({"text": sent.text})

            if "liability" in s:
                entities.liabilities.append({"text": sent.text})

            if "indemnify" in s:
                entities.indemnities.append({"text": sent.text})

            if "penalty" in s or "liquidated damages" in s:
                entities.penalties.append({"text": sent.text})

            if "confidential" in s:
                entities.confidentiality.append({"text": sent.text})

            if "intellectual property" in s or "ip" in s:
                entities.intellectual_property.append({"text": sent.text})

            if "arbitration" in s or "dispute" in s:
                entities.dispute_resolution.append({"text": sent.text})

            if "governing law" in s:
                entities.governing_law.append({"text": sent.text})

    # ------------------------------------------------------------------
    # UTILITIES
    # ------------------------------------------------------------------

    def _classify_party(self, name: str) -> str:
        n = name.lower()
        if any(x in n for x in ["pvt", "ltd", "llp", "inc"]):
            return "company"
        if any(x in n for x in ["government", "ministry", "authority"]):
            return "government"
        return "individual"

    def _clean_text(self, text: str) -> str:
        return re.sub(r'\s+', ' ', text).strip()

    def _to_dict(self, entities: ExtractedEntities) -> Dict[str, Any]:
        return entities.__dict__
