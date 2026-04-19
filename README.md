# 🎓 PESCE Campus Info AI

Interactive AI-Powered Campus Information Agent for PES College of Engineering, Mandya.

## ✨ Features
- 🤖 **AI-Powered Responses** — Groq (Llama 3.3 70B) + Google Gemini for natural language answers
- 🧠 **Semantic Search** — Sentence-transformer meaning-based matching
- 🌐 **Live Web Scraping** — Real-time data from pesce.ac.in
- 🔍 **Google Search** — SerpAPI fallback for extended knowledge
- 🌤️ **Live Weather** — Current Mandya weather via Weatherstack
- 🌏 **Multi-Language** — English, Hindi, Kannada support
- 📊 **Admin Dashboard** — Usage analytics & feedback tracking
- 📚 **FAQ System** — Categorized college policy reference

## 🏗️ Architecture
```
User Query
    │
    ▼
┌─────────────────┐
│ Semantic Search  │ ──→ Context
│ (MiniLM-L6-v2)  │
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ Keyword Matcher  │ ──→ Context
│ (Fuzzy + Typo)   │
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ Web Scraper      │ ──→ Context
│ (pesce.ac.in)    │
└─────────────────┘
    │
    ▼
┌─────────────────────────────┐
│ AI Engine (All Context)     │
│ Groq Llama 3.3 → Gemini    │
│ Generates natural response  │
└─────────────────────────────┘
```

## 🚀 Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure API Keys
Create `.streamlit/secrets.toml`:
```toml
GROQ_API_KEY = "your_groq_key"
GEMINI_API_KEY = "your_gemini_key"
SERPAPI_API_KEY = "your_serpapi_key"
WEATHERSTACK_API_KEY = "your_weatherstack_key"
```

### 3. Run
```bash
streamlit run streamlit_app.py
```

## 📁 Project Structure
```
├── streamlit_app.py      # Main chat UI & pipeline orchestration
├── ai_engine.py          # LLM integration (Groq + Gemini)
├── semantic_matcher.py   # Sentence-transformer search engine
├── web_scraper.py        # Live PESCE website scraper
├── admin_dashboard.py    # Analytics & admin panel
├── pesce_data.json       # Local knowledge base
├── requirements.txt      # Python dependencies
└── .streamlit/
    ├── config.toml       # Streamlit theme
    └── secrets.toml      # API keys (gitignored)
```

## 🛠️ Built With
- Python 3.x
- Streamlit
- Groq API (Llama 3.3 70B)
- Google Gemini API
- Sentence Transformers
- BeautifulSoup4
- SerpAPI
- Weatherstack API

## 📄 Data
Real PESCE college information collected from official sources and live website.

---
Made with ❤️ for PESCE Mandya
