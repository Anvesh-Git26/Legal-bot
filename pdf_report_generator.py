# pdf_report_generator.py

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any


class PDFReportGenerator:
    """
    FINAL – Legal review PDF generator with watermark
    Indian SME focused, judge-friendly
    """

    def __init__(self, output_dir: str = "reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.styles = getSampleStyleSheet()
        self.styles.add(
            ParagraphStyle(
                name="SectionHeader",
                fontSize=14,
                leading=18,
                spaceAfter=10,
                textColor=colors.darkblue,
                bold=True
            )
        )

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------

    def generate(
        self,
        filename: str,
        contract_type: str,
        risk_summary: Dict[str, Any],
        clause_analyses: List[Dict[str, Any]],
        entities: Dict[str, Any]
    ) -> Path:
        """
        Generate final legal review PDF
        """

        pdf_path = self.output_dir / f"{filename}_legal_report.pdf"

        doc = SimpleDocTemplate(
            str(pdf_path),
            pagesize=A4,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40
        )

        story = []

        # ------------------------------------------------------------------
        # COVER
        # ------------------------------------------------------------------

        story.append(Paragraph("Legal Risk Assessment Report", self.styles["Title"]))
        story.append(Spacer(1, 0.2 * inch))

        meta = f"""
        <b>Contract Type:</b> {contract_type}<br/>
        <b>Generated On:</b> {datetime.now().strftime('%d %B %Y')}<br/>
        <b>Purpose:</b> SME Contract Review (India)
        """
        story.append(Paragraph(meta, self.styles["Normal"]))
        story.append(Spacer(1, 0.3 * inch))

        # ------------------------------------------------------------------
        # EXECUTIVE SUMMARY
        # ------------------------------------------------------------------

        story.append(Paragraph("Executive Summary", self.styles["SectionHeader"]))

        summary_table = [
            ["Overall Risk Level", risk_summary["overall_risk"]["level"]],
            ["Risk Score", str(risk_summary["overall_risk"]["score"])],
            ["High Risk Clauses", str(risk_summary["risk_distribution"]["high_risk_clauses"])],
            ["Medium Risk Clauses", str(risk_summary["risk_distribution"]["medium_risk_clauses"])],
        ]

        table = Table(summary_table, colWidths=[3 * inch, 3 * inch])
        table.setStyle(self._table_style())
        story.append(table)
        story.append(Spacer(1, 0.3 * inch))

        # ------------------------------------------------------------------
        # KEY RISK AREAS
        # ------------------------------------------------------------------

        story.append(Paragraph("Key Risk Areas", self.styles["SectionHeader"]))

        for area in risk_summary.get("key_risk_areas", []):
            story.append(
                Paragraph(
                    f"- <b>{area['risk_area']}</b>: {area['description']}",
                    self.styles["Normal"]
                )
            )

        story.append(Spacer(1, 0.2 * inch))

        # ------------------------------------------------------------------
        # CLAUSE-BY-CLAUSE ANALYSIS
        # ------------------------------------------------------------------

        story.append(PageBreak())
        story.append(Paragraph("Clause-by-Clause Analysis", self.styles["SectionHeader"]))

        for clause in clause_analyses:
            story.append(
                Paragraph(
                    f"<b>Clause {clause.get('clause_id', '')} "
                    f"({clause.get('clause_type', 'general')})</b>",
                    self.styles["Normal"]
                )
            )

            analysis = clause.get("analysis", {})

            story.append(
                Paragraph(
                    f"<b>Explanation:</b> {analysis.get('plain_language_explanation', '')}",
                    self.styles["Normal"]
                )
            )

            if analysis.get("key_risks"):
                story.append(
                    Paragraph(
                        "<b>Key Risks:</b> " + ", ".join(analysis["key_risks"]),
                        self.styles["Normal"]
                    )
                )

            if analysis.get("renegotiation_points"):
                story.append(
                    Paragraph(
                        "<b>Renegotiation Points:</b> " +
                        ", ".join(analysis["renegotiation_points"]),
                        self.styles["Normal"]
                    )
                )

            story.append(Spacer(1, 0.2 * inch))

        # ------------------------------------------------------------------
        # ENTITIES SUMMARY
        # ------------------------------------------------------------------

        story.append(PageBreak())
        story.append(Paragraph("Extracted Key Information", self.styles["SectionHeader"]))

        self._add_entity_section(story, "Parties", entities.get("parties", []))
        self._add_entity_section(story, "Dates", entities.get("dates", []))
        self._add_entity_section(story, "Amounts", entities.get("amounts", []))
        self._add_entity_section(story, "Jurisdiction", entities.get("jurisdictions", []))

        # ------------------------------------------------------------------
        # DISCLAIMER
        # ------------------------------------------------------------------

        story.append(PageBreak())
        story.append(Paragraph("Disclaimer", self.styles["SectionHeader"]))

        disclaimer = """
        This report is generated by an AI-assisted legal analysis system
        for informational purposes only. It does not constitute legal advice.
        Users are strongly advised to consult a qualified legal professional
        before signing or acting upon any contract.
        """

        story.append(Paragraph(disclaimer, self.styles["Normal"]))

        # ------------------------------------------------------------------
        # BUILD PDF
        # ------------------------------------------------------------------

        doc.build(
            story,
            onFirstPage=self._watermark,
            onLaterPages=self._watermark
        )

        return pdf_path

    # ------------------------------------------------------------------
    # INTERNAL HELPERS
    # ------------------------------------------------------------------

    def _table_style(self):
        return TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 1, colors.grey),
            ("FONT", (0, 0), (-1, -1), "Helvetica"),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ])

    def _add_entity_section(self, story, title, items):
        if not items:
            return

        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph(title, self.styles["SectionHeader"]))

        for item in items[:5]:
            story.append(Paragraph(str(item), self.styles["Normal"]))

    def _watermark(self, canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(colors.grey)
        canvas.drawString(
            40,
            20,
            "CONFIDENTIAL – Generated by SME Legal Assistant"
        )
        canvas.restoreState()
