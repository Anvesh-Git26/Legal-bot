# language_handler.py

from transformers import MarianMTModel, MarianTokenizer
import torch
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate
import re
from typing import Dict, List, Tuple, Optional, Any
import hashlib
import json
from pathlib import Path
from langdetect import detect_langs
import logging


class ProductionLanguageHandler:
    """
    FINAL – Production-grade language detection & Hindi→English normalization
    - Supports English, Hindi, Hinglish (mixed)
    - Preserves legal terminology
    - Safe fallbacks if translation model unavailable
    """

    def __init__(self):
        self.translation_cache_dir = Path("cache/translations")
        self.translation_cache_dir.mkdir(parents=True, exist_ok=True)

        self.logger = self._setup_logging()

        # Load translation model (best-effort)
        self.hi_en_model, self.hi_en_tokenizer = self._load_translation_model()

        # Legal terminology dictionary (Hindi → English)
        self.legal_terms = self._load_legal_terminology()

    # ------------------------------------------------------------------
    # PUBLIC ENTRY POINT
    # ------------------------------------------------------------------

    def detect_and_normalize(self, text: str) -> Dict[str, Any]:
        """
        Detect language and normalize text to English for NLP
        """
        if not text or not text.strip():
            return {
                "primary_language": "unknown",
                "confidence": 0.0,
                "requires_translation": False,
                "english_text": "",
                "is_translated": False,
                "translation_confidence": 0.0
            }

        text_hash = hashlib.md5(text.encode("utf-8")).hexdigest()
        cache_file = self.translation_cache_dir / f"{text_hash}.json"

        # Cache check
        if cache_file.exists():
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)

        try:
            lang_info = self._detect_language(text)

            if lang_info["requires_translation"]:
                translation = self._translate_hindi_text(text)
                result = {**lang_info, **translation}
            else:
                result = {
                    **lang_info,
                    "english_text": text,
                    "is_translated": False,
                    "translation_confidence": 1.0
                }

            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, default=str)

            return result

        except Exception as e:
            self.logger.error(f"Language handling failed: {e}")
            return self._fallback_normalization(text)

    # ------------------------------------------------------------------
    # LANGUAGE DETECTION
    # ------------------------------------------------------------------

    def _detect_language(self, text: str) -> Dict[str, Any]:
        """
        Detect language using langdetect + Unicode heuristics
        """
        try:
            langs = detect_langs(text)
            primary = langs[0]

            hindi_chars = len(re.findall(r"[\u0900-\u097F]", text))
            total_chars = len(re.sub(r"\s", "", text))

            if total_chars == 0:
                return {
                    "primary_language": "unknown",
                    "confidence": 0.0,
                    "requires_translation": False
                }

            hindi_ratio = hindi_chars / total_chars

            if hindi_ratio > 0.3:
                return {
                    "primary_language": "hindi",
                    "confidence": max(primary.prob, hindi_ratio),
                    "hindi_ratio": hindi_ratio,
                    "is_mixed": hindi_ratio < 0.85,
                    "requires_translation": True
                }

            return {
                "primary_language": "english",
                "confidence": primary.prob,
                "requires_translation": False
            }

        except Exception:
            return self._character_based_detection(text)

    def _character_based_detection(self, text: str) -> Dict[str, Any]:
        hindi_chars = len(re.findall(r"[\u0900-\u097F]", text))
        english_chars = len(re.findall(r"[a-zA-Z]", text))
        total_chars = len(re.sub(r"\s", "", text))

        if total_chars == 0:
            return {
                "primary_language": "unknown",
                "confidence": 0.0,
                "requires_translation": False
            }

        hindi_ratio = hindi_chars / total_chars
        english_ratio = english_chars / total_chars

        if hindi_ratio > 0.5:
            return {
                "primary_language": "hindi",
                "confidence": hindi_ratio,
                "requires_translation": True,
                "is_mixed": hindi_ratio < 0.9
            }

        if english_ratio > 0.5:
            return {
                "primary_language": "english",
                "confidence": english_ratio,
                "requires_translation": False
            }

        return {
            "primary_language": "mixed",
            "confidence": (hindi_ratio + english_ratio) / 2,
            "requires_translation": True
        }

    # ------------------------------------------------------------------
    # TRANSLATION
    # ------------------------------------------------------------------

    def _translate_hindi_text(self, text: str) -> Dict[str, Any]:
        """
        Translate Hindi / mixed text to English with legal term preservation
        """
        entities = self._extract_legal_entities(text)
        placeholder_text = self._replace_entities(text, entities)

        chunks = self._split_into_chunks(placeholder_text, max_tokens=400)

        translated_chunks = []
        method = "model"

        for chunk in chunks:
            if self.hi_en_model and self.hi_en_tokenizer:
                translated = self._translate_with_model(chunk)
            else:
                translated = self._fallback_transliteration(chunk)
                method = "transliteration"

            translated_chunks.append(translated)

        english_text = " ".join(translated_chunks)
        english_text = self._restore_entities(english_text, entities)
        english_text = self._post_process_translation(english_text)

        return {
            "english_text": english_text,
            "hindi_original": text,
            "entities_preserved": entities,
            "is_translated": True,
            "translation_method": method,
            "translation_confidence": self._calculate_translation_confidence(
                english_text
            )
        }

    def _translate_with_model(self, text: str) -> str:
        try:
            inputs = self.hi_en_tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=512
            )
            with torch.no_grad():
                output = self.hi_en_model.generate(**inputs)
            return self.hi_en_tokenizer.decode(
                output[0], skip_special_tokens=True
            )
        except Exception:
            return self._fallback_transliteration(text)

    def _fallback_transliteration(self, text: str) -> str:
        try:
            translit = transliterate(
                text, sanscript.DEVANAGARI, sanscript.ITRANS
            )
            for hi, en in self.legal_terms.items():
                translit = translit.replace(
                    transliterate(hi, sanscript.DEVANAGARI, sanscript.ITRANS),
                    en
                )
            return translit
        except Exception:
            return text

    # ------------------------------------------------------------------
    # LEGAL TERM HANDLING
    # ------------------------------------------------------------------

    def _extract_legal_entities(self, text: str) -> List[Dict[str, str]]:
        entities = []
        for hi, en in self.legal_terms.items():
            for match in re.finditer(re.escape(hi), text):
                entities.append({
                    "hindi": hi,
                    "english": en,
                    "placeholder": f"__LEGAL_{len(entities)}__",
                    "start": match.start(),
                    "length": len(hi)
                })
        entities.sort(key=lambda x: x["start"], reverse=True)
        return entities

    def _replace_entities(self, text: str, entities: List[Dict]) -> str:
        for e in entities:
            text = (
                text[:e["start"]] +
                e["placeholder"] +
                text[e["start"] + e["length"]:]
            )
        return text

    def _restore_entities(self, text: str, entities: List[Dict]) -> str:
        for e in entities:
            text = text.replace(e["placeholder"], e["english"])
        return text

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    def _split_into_chunks(self, text: str, max_tokens: int) -> List[str]:
        sentences = re.split(r"[।.!?]+", text)
        chunks, current = [], []
        length = 0

        for s in sentences:
            words = s.split()
            if length + len(words) > max_tokens and current:
                chunks.append(" ".join(current))
                current, length = [s], len(words)
            else:
                current.append(s)
                length += len(words)

        if current:
            chunks.append(" ".join(current))
        return chunks

    def _post_process_translation(self, text: str) -> str:
        fixes = {
            "rs.": "₹",
            "inr": "₹",
            "section ": "Section ",
            "clause ": "Clause ",
            "article ": "Article "
        }
        for k, v in fixes.items():
            text = re.sub(rf"\b{k}\b", v, text, flags=re.IGNORECASE)
        return text

    def _calculate_translation_confidence(self, text: str) -> float:
        hindi_left = len(re.findall(r"[\u0900-\u097F]", text))
        return 0.9 if hindi_left == 0 else 0.7

    def _fallback_normalization(self, text: str) -> Dict[str, Any]:
        return {
            "primary_language": "unknown",
            "confidence": 0.0,
            "requires_translation": False,
            "english_text": text,
            "is_translated": False,
            "translation_confidence": 0.5,
            "error": "Fallback normalization used"
        }

    def _load_translation_model(self):
        try:
            model_name = "Helsinki-NLP/opus-mt-hi-en"
            tokenizer = MarianTokenizer.from_pretrained(model_name)
            model = MarianMTModel.from_pretrained(model_name)
            model.eval()
            self.logger.info("Hindi→English translation model loaded")
            return model, tokenizer
        except Exception as e:
            self.logger.warning(f"Translation model unavailable: {e}")
            return None, None

    def _load_legal_terminology(self) -> Dict[str, str]:
        return {
            "अनुबंध": "Contract",
            "समझौता": "Agreement",
            "पक्ष": "Party",
            "भुगतान": "Payment",
            "जुर्माना": "Penalty",
            "दायित्व": "Obligation",
            "जिम्मेदारी": "Liability",
            "गोपनीयता": "Confidentiality",
            "बौद्धिक संपदा": "Intellectual Property",
            "अधिकार": "Right",
            "न्यायालय": "Court"
        }

    def _setup_logging(self):
        logger = logging.getLogger("LanguageHandler")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
