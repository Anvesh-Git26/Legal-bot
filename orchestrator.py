# orchestrator.py

from pathlib import Path
from typing import Dict, Any, List

from document_processor import ProductionDocumentProcessor
from language_handler import ProductionLanguageHandler
from contract_classifier import ProductionContractClassifier
from clause_extractor import ProductionClauseExtractor
from entity_extractor import ProductionEntityExtractor
from risk_engine import ProductionRiskEngine
from llm_reasoner import ProductionLLMReasoner
from template_engine import ProductionTemplateEngine
from audit_system import AuditLogger
from pdf_report_generator import PDFReportGenerator


class LegalAnalysisOrchestrator:
    """
    FINAL – End-to-end orchestrator for GenAI Legal Assistant
    Hackathon + production safe
    """

    def __init__(self, llm_provider: str = "claude", llm_api_key: str = None):
        # Core engines
        self.doc_processor = ProductionDocumentProcessor()
        self.language_handler = ProductionLanguageHandler()
        self.classifier = ProductionContractClassifier()
        self.clause_extractor = ProductionClauseExtractor()
        self.entity_extractor = ProductionEntityExtractor()
        self.risk_engine = ProductionRiskEngine()
        self.llm_reasoner = ProductionLLMReasoner(
            provider=llm_provider,
            api_key=llm_api_key
        )
        self.template_engine = ProductionTemplateEngine()
        self.pdf_generator = PDFReportGenerator()
        self.audit_logger = AuditLogger()

    # ------------------------------------------------------------------
    # MAIN PIPELINE
    # ------------------------------------------------------------------

    def analyze_document(self, file_path: str) -> Dict[str, Any]:
        """
        Run full contract analysis pipeline
        """

        file_path = Path(file_path)

        # ---------------- AUDIT START ----------------
        session_id = self.audit_logger.start_session(file_path.name)

        try:
            # ---------------- DOCUMENT PROCESSING ----------------
            doc_data = self.doc_processor.process_document(file_path)
            self.audit_logger.log_event(session_id, "document_processed")

            raw_text = doc_data.get("full_text", "")

            # ---------------- LANGUAGE NORMALIZATION ----------------
            lang_data = self.language_handler.detect_and_normalize(raw_text)
            normalized_text = lang_data.get("english_text", raw_text)
            self.audit_logger.log_event(session_id, "language_normalized", {
                "primary_language": lang_data.get("primary_language"),
                "translated": lang_data.get("is_translated")
            })

            # ---------------- CONTRACT CLASSIFICATION ----------------
            contract_classification = self.classifier.classify_contract(normalized_text)
            contract_type = contract_classification["predicted_type"]
            self.audit_logger.log_event(session_id, "contract_classified", {
                "contract_type": contract_type,
                "confidence": contract_classification["confidence"]
            })

            # ---------------- CLAUSE EXTRACTION ----------------
            clauses = self.clause_extractor.extract_clauses(normalized_text)
            self.audit_logger.log_event(session_id, "clauses_extracted", {
                "total_clauses": len(clauses)
            })

            # ---------------- ENTITY EXTRACTION ----------------
            entities = self.entity_extractor.extract(normalized_text)
            self.audit_logger.log_event(session_id, "entities_extracted")

            # ---------------- RISK SCORING ----------------
            contract_risk = self.risk_engine.evaluate_contract(
                clauses, contract_type
            )
            risk_report = self.risk_engine.generate_risk_report(
                contract_risk, contract_type
            )
            self.audit_logger.log_event(session_id, "risk_scored", {
                "overall_risk": contract_risk.contract_level
            })

            # ---------------- LLM CLAUSE REASONING ----------------
            clause_analyses = []
            for clause in clauses:
                clause_risk = self.risk_engine.evaluate_clause(
                    clause, contract_type
                )

                analysis = self.llm_reasoner.analyze_clause(
                    clause_text=clause["full_text"],
                    clause_type=clause["type"],
                    contract_type=contract_type,
                    risk_summary=clause_risk
                )

                clause_analyses.append({
                    "clause_id": clause["id"],
                    "clause_type": clause["type"],
                    "analysis": analysis
                })

            self.audit_logger.log_event(session_id, "llm_reasoned")

            # ---------------- PDF GENERATION ----------------
            pdf_path = self.pdf_generator.generate(
                filename=file_path.stem,
                contract_type=contract_type,
                risk_summary=risk_report,
                clause_analyses=clause_analyses,
                entities=entities
            )

            self.audit_logger.log_event(session_id, "report_generated", {
                "pdf_path": str(pdf_path)
            })

            # ---------------- AUDIT CLOSE ----------------
            self.audit_logger.close_session(session_id, status="completed")

            # ---------------- FINAL RESPONSE ----------------
            return {
                "success": True,
                "session_id": session_id,
                "contract_type": contract_type,
                "risk_summary": risk_report,
                "entities": entities,
                "clauses": clauses,
                "clause_analyses": clause_analyses,
                "pdf_report": str(pdf_path)
            }

        except Exception as e:
            self.audit_logger.log_event(
                session_id, "error", {"message": str(e)}
            )
            self.audit_logger.close_session(session_id, status="failed")

            return {
                "success": False,
                "session_id": session_id,
                "error": str(e)
            }
