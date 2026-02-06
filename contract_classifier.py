# contract_classifier.py

import re
import pickle
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier


class ProductionContractClassifier:
    """
    FINAL – Hybrid (Rule + ML) Contract Type Classifier
    Supported:
    - employment_agreement
    - vendor_contract
    - lease_agreement
    - partnership_deed
    - service_contract
    """

    def __init__(self, model_dir: str = "models"):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)

        self.logger = self._setup_logging()

        # Contract types (ORDER IS IMPORTANT – DO NOT CHANGE)
        self.contract_types = [
            "employment_agreement",
            "vendor_contract",
            "lease_agreement",
            "partnership_deed",
            "service_contract"
        ]

        self.vectorizer, self.classifier = self._load_or_train_models()
        self.keyword_patterns = self._build_keyword_patterns()

    # ------------------------------------------------------------------
    # MODEL LOADING / TRAINING
    # ------------------------------------------------------------------

    def _load_or_train_models(self) -> Tuple[TfidfVectorizer, RandomForestClassifier]:
        vec_path = self.model_dir / "tfidf_vectorizer.pkl"
        clf_path = self.model_dir / "random_forest_classifier.pkl"

        if vec_path.exists() and clf_path.exists():
            try:
                with open(vec_path, "rb") as f:
                    vectorizer = pickle.load(f)
                with open(clf_path, "rb") as f:
                    classifier = pickle.load(f)

                self.logger.info("Loaded trained contract classifier models")
                return vectorizer, classifier

            except Exception as e:
                self.logger.warning(f"Model load failed, retraining: {e}")

        return self._train_models()

    def _train_models(self) -> Tuple[TfidfVectorizer, RandomForestClassifier]:
        data = self._generate_training_data()

        vectorizer = TfidfVectorizer(
            max_features=1500,
            ngram_range=(1, 2),
            stop_words="english"
        )

        X = vectorizer.fit_transform(data["texts"])
        y = data["labels"]

        classifier = RandomForestClassifier(
            n_estimators=200,
            random_state=42,
            class_weight="balanced",
            min_samples_leaf=1
        )
        classifier.fit(X, y)

        with open(self.model_dir / "tfidf_vectorizer.pkl", "wb") as f:
            pickle.dump(vectorizer, f)
        with open(self.model_dir / "random_forest_classifier.pkl", "wb") as f:
            pickle.dump(classifier, f)

        self.logger.info("Trained and saved new contract classification models")
        return vectorizer, classifier

    # ------------------------------------------------------------------
    # SYNTHETIC TRAINING DATA
    # ------------------------------------------------------------------

    def _generate_training_data(self) -> Dict[str, List]:
        texts, labels = [], []

        def add(samples: List[str], label: int):
            texts.extend(samples)
            labels.extend([label] * len(samples))

        add([
            "employment agreement salary benefits termination notice probation",
            "employee shall receive salary provident fund gratuity",
            "appointment letter duties compensation non compete",
            "terms of employment working hours leave policy",
            "confidentiality intellectual property employment"
        ], 0)

        add([
            "vendor agreement supply of goods payment delivery",
            "supplier shall deliver products as per purchase order",
            "payment terms invoices quality inspection",
            "vendor liability warranty indemnity",
            "procurement contract supply chain"
        ], 1)

        add([
            "lease agreement rent landlord tenant security deposit",
            "rental property maintenance utilities",
            "lease term possession eviction notice",
            "lessor lessee rent escalation",
            "commercial lease premises"
        ], 2)

        add([
            "partnership deed profit sharing capital contribution",
            "partners rights duties dissolution",
            "partnership firm business management",
            "joint venture partnership agreement",
            "partners admission retirement"
        ], 3)

        add([
            "service agreement scope of work deliverables fees",
            "consulting services payment milestones",
            "professional services contract",
            "statement of work timelines",
            "service provider client agreement"
        ], 4)

        return {"texts": texts, "labels": labels}

    # ------------------------------------------------------------------
    # RULE-BASED KEYWORDS
    # ------------------------------------------------------------------

    def _build_keyword_patterns(self) -> Dict[str, Dict]:
        return {
            "employment_agreement": {
                "keywords": [
                    "employee", "employer", "salary", "wages", "probation",
                    "termination", "leave", "benefits", "appointment"
                ],
                "patterns": [
                    r"employment\s+agreement",
                    r"appointment\s+letter"
                ]
            },
            "vendor_contract": {
                "keywords": [
                    "vendor", "supplier", "purchase", "delivery",
                    "goods", "invoice", "procurement"
                ],
                "patterns": [
                    r"vendor\s+agreement",
                    r"supply\s+contract"
                ]
            },
            "lease_agreement": {
                "keywords": [
                    "lease", "rent", "tenant", "landlord",
                    "premises", "security deposit"
                ],
                "patterns": [
                    r"lease\s+agreement",
                    r"rental\s+agreement"
                ]
            },
            "partnership_deed": {
                "keywords": [
                    "partner", "partnership", "profit", "capital",
                    "dissolution", "firm"
                ],
                "patterns": [
                    r"partnership\s+deed",
                    r"partnership\s+agreement"
                ]
            },
            "service_contract": {
                "keywords": [
                    "service", "consulting", "deliverables",
                    "scope of work", "milestones"
                ],
                "patterns": [
                    r"service\s+agreement",
                    r"consulting\s+contract"
                ]
            }
        }

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------

    def classify_contract(self, text: str) -> Dict[str, Any]:
        rule_result = self._rule_based(text)
        ml_result = self._ml_based(text)

        combined = self._combine(rule_result, ml_result)
        combined["method"] = "hybrid"

        return combined

    # ------------------------------------------------------------------
    # RULE-BASED
    # ------------------------------------------------------------------

    def _rule_based(self, text: str) -> Dict[str, Any]:
        text_l = text.lower()
        scores = {}

        for ctype, cfg in self.keyword_patterns.items():
            score = 0
            for kw in cfg["keywords"]:
                if kw in text_l:
                    score += 1
            for pat in cfg["patterns"]:
                score += len(re.findall(pat, text_l)) * 2
            scores[ctype] = score

        total = sum(scores.values()) or 1
        probs = {k: v / total for k, v in scores.items()}
        pred = max(probs, key=probs.get)

        return {
            "predicted_type": pred,
            "confidence": round(probs[pred], 3),
            "probabilities": probs,
            "raw_scores": scores
        }

    # ------------------------------------------------------------------
    # ML-BASED
    # ------------------------------------------------------------------

    def _ml_based(self, text: str) -> Dict[str, Any]:
        try:
            X = self.vectorizer.transform([text])
            probs = self.classifier.predict_proba(X)[0]

            prob_map = {
                self.contract_types[i]: float(probs[i])
                for i in range(len(self.contract_types))
            }

            pred = max(prob_map, key=prob_map.get)

            return {
                "predicted_type": pred,
                "confidence": round(prob_map[pred], 3),
                "probabilities": prob_map
            }

        except Exception as e:
            self.logger.error(f"ML classification failed: {e}")
            return {}

    # ------------------------------------------------------------------
    # COMBINATION
    # ------------------------------------------------------------------

    def _combine(self, rule: Dict, ml: Dict) -> Dict[str, Any]:
        if not ml:
            return rule

        combined_probs = {}
        for ct in self.contract_types:
            combined_probs[ct] = (
                0.7 * ml["probabilities"].get(ct, 0) +
                0.3 * rule["probabilities"].get(ct, 0)
            )

        pred = max(combined_probs, key=combined_probs.get)

        return {
            "predicted_type": pred,
            "confidence": round(combined_probs[pred], 3),
            "probabilities": combined_probs,
            "rule_based": rule,
            "ml_based": ml
        }

    # ------------------------------------------------------------------
    # LOGGING
    # ------------------------------------------------------------------

    def _setup_logging(self):
        logger = logging.getLogger("ContractClassifier")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
