# streamlit_app.py

import streamlit as st
from pathlib import Path
import tempfile
import json

from orchestrator import LegalAnalysisOrchestrator


# ------------------------------------------------------------------
# PAGE CONFIG
# ------------------------------------------------------------------

st.set_page_config(
    page_title="SME Legal Assistant",
    page_icon="⚖️",
    layout="wide"
)

st.title("⚖️ SME Legal Assistant – Contract Risk Analyzer")
st.caption(
    "Analyze contracts, detect risks, and get plain-language legal insights "
    "for Indian SMEs."
)


# ------------------------------------------------------------------
# SIDEBAR
# ------------------------------------------------------------------

st.sidebar.header("⚙️ Configuration")

llm_provider = st.sidebar.selectbox(
    "LLM Provider (optional)",
    ["None (Rule-based only)", "Claude", "OpenAI"]
)

api_key = None
if llm_provider != "None (Rule-based only)":
    api_key = st.sidebar.text_input(
        "API Key",
        type="password",
        help="Optional – system works without LLM as well"
    )

st.sidebar.markdown("---")
st.sidebar.info(
    "🔐 All processing is done locally.\n\n"
    "📄 No documents are stored externally.\n\n"
    "🧪 Hackathon + Production Safe"
)


# ------------------------------------------------------------------
# ORCHESTRATOR INIT
# ------------------------------------------------------------------

provider_map = {
    "None (Rule-based only)": None,
    "Claude": "claude",
    "OpenAI": "openai"
}

orchestrator = LegalAnalysisOrchestrator(
    llm_provider=provider_map[llm_provider],
    llm_api_key=api_key
)


# ------------------------------------------------------------------
# FILE UPLOAD
# ------------------------------------------------------------------

st.header("📄 Upload Contract")

uploaded_file = st.file_uploader(
    "Upload a contract document",
    type=["pdf", "docx", "txt"]
)

if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=uploaded_file.name) as tmp:
        tmp.write(uploaded_file.read())
        temp_path = tmp.name

    st.success(f"Uploaded: {uploaded_file.name}")

    if st.button("🔍 Analyze Contract"):
        with st.spinner("Analyzing contract… this may take a moment"):
            result = orchestrator.analyze_document(temp_path)

        if not result.get("success"):
            st.error("❌ Analysis failed")
            st.code(result.get("error"))
        else:
            st.success("✅ Analysis completed")

            # ------------------------------------------------------
            # OVERVIEW
            # ------------------------------------------------------

            st.subheader("📊 Overview")

            col1, col2, col3 = st.columns(3)

            col1.metric(
                "Contract Type",
                result["contract_type"].replace("_", " ").title()
            )

            col2.metric(
                "Overall Risk",
                result["risk_summary"]["overall_risk"]["level"]
            )

            col3.metric(
                "Risk Score",
                result["risk_summary"]["overall_risk"]["score"]
            )

            # ------------------------------------------------------
            # KEY RISKS
            # ------------------------------------------------------

            st.subheader("⚠️ Key Risk Areas")

            for area in result["risk_summary"].get("key_risk_areas", []):
                st.warning(
                    f"**{area['risk_area']}** – {area['description']} "
                    f"(Appears {area['frequency']} times)"
                )

            # ------------------------------------------------------
            # CLAUSE ANALYSIS
            # ------------------------------------------------------

            st.subheader("📑 Clause-by-Clause Analysis")

            for clause in result["clause_analyses"]:
                with st.expander(
                    f"Clause {clause['clause_id']} – "
                    f"{clause['clause_type'].replace('_', ' ').title()}"
                ):
                    analysis = clause["analysis"]

                    st.markdown("**Explanation**")
                    st.write(analysis.get("plain_language_explanation", ""))

                    if analysis.get("key_risks"):
                        st.markdown("**Key Risks**")
                        st.write(", ".join(analysis["key_risks"]))

                    if analysis.get("renegotiation_points"):
                        st.markdown("**Renegotiation Points**")
                        for p in analysis["renegotiation_points"]:
                            st.write(f"- {p}")

                    if analysis.get("alternative_wording"):
                        st.markdown("**Suggested Alternative**")
                        st.info(analysis["alternative_wording"])

            # ------------------------------------------------------
            # ENTITIES
            # ------------------------------------------------------

            st.subheader("🔎 Extracted Key Information")

            with st.expander("Parties"):
                st.json(result["entities"].get("parties", []))

            with st.expander("Dates"):
                st.json(result["entities"].get("dates", []))

            with st.expander("Amounts"):
                st.json(result["entities"].get("amounts", []))

            with st.expander("Jurisdiction"):
                st.json(result["entities"].get("jurisdictions", []))

            # ------------------------------------------------------
            # PDF DOWNLOAD
            # ------------------------------------------------------

            st.subheader("📥 Legal Review Report")

            pdf_path = Path(result["pdf_report"])
            if pdf_path.exists():
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        "Download PDF Report",
                        f,
                        file_name=pdf_path.name,
                        mime="application/pdf"
                    )

            # ------------------------------------------------------
            # RAW JSON (FOR JUDGES)
            # ------------------------------------------------------

            with st.expander("🧾 Full JSON Output (Audit-Friendly)"):
                st.json(result)

else:
    st.info("Upload a contract to begin analysis.")
