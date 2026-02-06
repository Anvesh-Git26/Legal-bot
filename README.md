🧠 GenAI-Powered Legal Contract Analysis Assistant (India)

A production-grade GenAI legal assistant designed to help Indian Small and Medium Enterprises (SMEs) understand complex contracts, identify legal risks, and receive actionable, plain-language advice — with privacy-first, offline-safe architecture.

Built for hackathons + real-world deployment
No external legal APIs • Full audit trail • Hindi + English support

🚀 Key Features
📄 Contract Understanding

Supports Employment Agreements, Vendor Contracts, Lease Agreements, Partnership Deeds, Service Contracts

Handles PDF (text-based), DOC/DOCX, and TXT files

Clause-by-clause extraction and explanation

⚖️ Legal Risk Detection

Clause-level and contract-level risk scoring

Identifies:

Penalty clauses

Indemnities

Unilateral termination

Arbitration & jurisdiction risks

Auto-renewal & lock-in periods

Non-compete & IP transfer risks

SME-focused mitigation recommendations

🌐 Multilingual Intelligence

Native Hindi + English support

Automatic Hindi → English normalization

Legal term preservation during translation

Handles mixed Hindi-English (Hinglish) contracts

🤖 GenAI Reasoning (Optional)

Uses Claude 3 / GPT-4 for legal reasoning only

Rule-based fallback when LLM is unavailable

API-safe, cost-controlled, cached responses

🧾 SME-Friendly Templates

Ready-to-use Indian law-aligned contract templates

Variable-driven customization

Balanced clauses for SME protection

📑 Reports & Audit

Professional PDF export with watermark

JSON-based audit logs (who, what, when)

Confidential, local-only data processing

🏗️ System Architecture
┌───────────────────────────────┐
│        Streamlit UI           │
├───────────────────────────────┤
│     Orchestrator Layer        │
├──────────────┬───────────────┤
│ Document     │ Language       │
│ Processor    │ Handler        │
├──────────────┼───────────────┤
│ Clause       │ Entity         │
│ Extractor   │ Extractor      │
├──────────────┼───────────────┤
│ Risk Engine │ LLM Reasoner   │
├──────────────┴───────────────┤
│ Templates | PDF | Audit Logs │
└───────────────────────────────┘

📂 Project Structure
├── streamlit_app.py          # UI
├── orchestrator.py           # System coordinator
├── document_processor.py     # PDF / DOCX / TXT ingestion
├── language_handler.py       # Hindi-English normalization
├── contract_classifier.py    # Contract type detection
├── clause_extractor.py       # Clause & sub-clause parsing
├── entity_extractor.py       # Parties, amounts, dates, IP, etc.
├── risk_engine.py            # Legal risk scoring engine
├── llm_reasoner.py           # Claude / GPT reasoning (optional)
├── template_engine.py        # SME contract templates
├── pdf_report_generator.py  # Watermarked PDF reports
├── audit_logger.py           # JSON-based audit logs
├── templates/               # Contract templates
├── cache/                   # Translation, risk, LLM caches
├── requirements.txt
└── README.md

⚙️ Installation & Setup
1️⃣ Clone the Repository
git clone https://github.com/your-username/legal-genai-assistant.git
cd legal-genai-assistant

2️⃣ Install Dependencies
pip install -r requirements.txt

3️⃣ Install SpaCy Model
python -m spacy download en_core_web_sm

4️⃣ (Optional) Set LLM API Keys
export OPENAI_API_KEY=your_key_here
export ANTHROPIC_API_KEY=your_key_here


⚠️ LLMs are optional. The system works fully without them.

5️⃣ Run the App
streamlit run streamlit_app.py

🧪 Supported Inputs
Format	Supported
PDF (text-based)	✅
DOC / DOCX	✅
TXT	✅
Scanned PDF (OCR)	❌ (out of scope)
📤 Outputs

📊 Contract risk score (Low / Medium / High)

📌 Highlighted high-risk clauses

📝 Plain-English explanations

🔁 Renegotiation suggestions

📄 Downloadable PDF report

🧾 JSON audit trail

🔐 Security & Privacy

100% local file processing

No document storage in cloud

No external legal databases

Optional auto-cleanup after processing

Audit-ready by design
