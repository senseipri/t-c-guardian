🛡️ T&C Guardian

AI-powered Chrome Extension that analyzes Terms & Conditions in real-time and highlights potentially harmful clauses.

🚀 Overview

T&C Guardian is a full-stack AI system that helps users understand legal agreements instantly. It scans any webpage, extracts legal content, and uses an LLM to generate a structured risk report.

✨ Features
🔍 Scan any webpage in one click
🧠 AI-powered legal analysis
📊 Safety score (0–100) + grade (A–F)
⚠️ Highlights risky clauses (Privacy, Legal, Financial, Data)
⚡ Real-time results inside browser
🧠 Architecture Flow
┌──────────────────────────────────────────────────────────────┐
│                 CHROME EXTENSION (Manifest V3)               │
│                                                              │
│  popup.js                                                    │
│   ├─ chrome.tabs.query() → get active tab URL                │
│   ├─ POST http://localhost:8000/scan { url }                 │
│   └─ Render: grade, score, summary, findings                 │
└───────────────────────────┬──────────────────────────────────┘
                            │ HTTP POST /scan
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                    FASTAPI BACKEND (main.py)                 │
│                                                              │
│  • Validates URL format                                      │
│  • Initializes AgentState                                    │
│  • Invokes LangGraph pipeline                               │
│  • Handles errors → returns HTTP 400                         │
│  • Returns JSON response                                     │
└───────────────────────────┬──────────────────────────────────┘
                            │ await graph_app.ainvoke(state)
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                 LANGGRAPH PIPELINE (workflow.py)             │
│                 Deterministic State Machine                  │
│                                                              │
│        ┌──────────────┐        ┌───────────────┐             │
│        │  scrape_node │───────▶│ analyze_node  │────▶ END    │
│        │              │        │               │             │
│        │ scraper.py   │        │ analyzer.py   │             │
│        │ (httpx + BS) │        │ (Groq LLM)    │             │
│        └──────────────┘        └───────────────┘             │
│                                                              │
│  ✓ No loops                                                  │
│  ✓ No conditional edges                                      │
│  ✓ Guaranteed termination                                    │
└──────────────────────────────────────────────────────────────┘
⚙️ Tech Stack
Backend: FastAPI
Orchestration: LangGraph
LLM: Groq (LLaMA 3.3 70B)
Scraping: httpx + BeautifulSoup
Frontend: Chrome Extension (Vanilla JS)
📁 Project Structure
tc-guardian/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── graph/
│   │   ├── state.py         # Shared state schema
│   │   ├── nodes.py         # Pipeline nodes
│   │   └── workflow.py      # LangGraph workflow
│   └── tools/
│       ├── scraper.py       # Web scraping logic
│       └── analyzer.py      # LLM analysis
│
├── extension/
│   ├── manifest.json        # Chrome extension config
│   ├── popup.html           # UI
│   └── popup.js             # Controller logic
│
├── .env
└── requirements.txt
🔄 How It Works
User clicks “Scan This Page”
Extension sends current URL to backend
FastAPI invokes LangGraph pipeline
Scraper extracts readable content
LLM analyzes legal risks
Results returned and rendered
📊 Example Output
{
  "score": 72,
  "grade": "B",
  "summary": "Moderate risk due to data sharing clauses.",
  "findings": [
    {
      "category": "Privacy",
      "severity": "High",
      "finding": "Your data may be shared with third parties."
    }
  ]
}
🛠️ Setup Instructions
1. Clone Repository
git clone <repo-url>
cd tc-guardian
2. Create Virtual Environment
python -m venv .venv
.venv\Scripts\activate   # Windows
3. Install Dependencies
pip install -r requirements.txt
4. Add Environment Variables

Create .env in root:

GROQ_API_KEY=your_api_key_here
5. Run Backend
uvicorn backend.main:app --reload
6. Test API

Open:

http://127.0.0.1:8000/docs
🌐 Chrome Extension Setup
Open chrome://extensions/
Enable Developer Mode
Click Load unpacked
Select the extension/ folder
🧪 Test URLs

Use real legal pages:

https://www.google.com/policies/terms/
https://docs.github.com/en/site-policy/github-terms/github-terms-of-service
https://www.amazon.in/gp/help/customer/display.html?nodeId=201909000
⚠️ Error Handling
400 Bad Request

Occurs when:

Page is not a legal document
Scraping fails
LLM returns invalid response