# 🎓 PESCE Campus Information AI

> **AI-Powered Interactive Campus Knowledge Bot** for PES College of Engineering, Mandya

An intelligent chatbot that answers questions about PESCE using a multi-layered AI pipeline combining local knowledge, live web scraping, and LLM-powered response generation.

---

## ✨ Key Features

### 🤖 AI-Powered Responses
- **Groq (Llama 3.3 70B)** — Primary LLM for ultra-fast, natural language answers
- **Google Gemini (Flash)** — Fallback LLM for redundancy
- Context-aware responses that synthesize data from multiple sources

### 🕷️ Deep Web Scraping (Live Data)
- **Real-time faculty extraction** from all 15+ department pages on pesce.ac.in
- Automatic HOD, Professor, and Staff role detection
- **50+ page mappings** covering every section of the college website
- Smart department detection with word-boundary matching (no false positives)
- 30-minute session cache for optimal performance

### 📊 Comprehensive Knowledge Base
- **9 data sections**: College Overview, Administrative, Academics, Departments, Placements, Facilities, Contacts, Cells & Committees, FAQ
- **36+ curated FAQs** across 6 categories
- **Full faculty rosters** for CSE (30 members) and ISE (9 members)
- **Complete placement team** with contacts
- **Hostel details** including wardens, managers, and room breakdowns

### 🔍 5-Tier Answer Resolution
1. **Semantic Search** — Sentence-transformer similarity matching
2. **Keyword Matching** — Synonym-aware category scoring
3. **Live Web Scraping** — Deep page parsing from pesce.ac.in
4. **AI Generation** — LLM synthesis of all gathered context
5. **Template Fallback** — Structured offline responses

### 🌐 Additional Features
- 🌤️ **Live Weather** for Mandya (Weatherstack API)
- 🔎 **Web Search** fallback (SerpAPI)
- 🌍 **Multi-language** support (English, Hindi, Kannada)
- 📈 **Admin Dashboard** with analytics
- 💬 **Chat Export** to TXT
- ⭐ **Feedback System** with ratings
- 🗄️ **SQLite** conversation history

---

## 🏗️ Architecture

```
User Query
    │
    ▼
┌──────────────┐
│  Streamlit UI │
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────────┐
│           Answer Pipeline                 │
│                                           │
│  1. Semantic Search (sentence-transformers)│
│  2. Keyword Matcher (synonym scoring)     │
│  3. Web Scraper (pesce.ac.in deep scrape) │
│  4. AI Engine (Groq → Gemini fallback)    │
│  5. Template Fallback (offline JSON)      │
└──────────────────────────────────────────┘
       │
       ▼
┌──────────────────┐
│  AI Engine        │
│  ┌─────────────┐  │
│  │ Groq (Fast) │──┼──► Natural Language
│  │ Gemini (FB) │  │    Response
│  └─────────────┘  │
└──────────────────┘
```

---

## 📁 Project Structure

```
pesce-campus-info-ai/
├── streamlit_app.py      # Main UI + answer pipeline
├── ai_engine.py          # LLM integration (Groq/Gemini)
├── web_scraper.py        # Deep web scraper for pesce.ac.in
├── pesce_data.json       # Comprehensive knowledge base (scraped data)
├── admin_dashboard.py    # Analytics dashboard
├── requirements.txt      # Python dependencies
├── .streamlit/
│   └── secrets.toml      # API keys (not in git)
└── README.md
```

---

## 🚀 Setup & Run

### 1. Clone
```bash
git clone https://github.com/shushant950273/pesce-campus-info-ai.git
cd pesce-campus-info-ai
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure API Keys
Create `.streamlit/secrets.toml`:
```toml
GROQ_API_KEY = "your-groq-key"
GEMINI_API_KEY = "your-gemini-key"
SERPAPI_API_KEY = "your-serpapi-key"
WEATHERSTACK_API_KEY = "your-weatherstack-key"
EXCHANGERATE_API_KEY = "your-exchangerate-key"
```

### 4. Run
```bash
streamlit run streamlit_app.py
```

---

## 🕷️ Web Scraper Coverage

The deep scraper covers **50+ pages** on pesce.ac.in:

| Category | Pages Scraped |
|---|---|
| **Departments** | CSE, ISE, ECE, EEE, ME, Civil, AIML, DS, CSBS, Auto, IPE, Robotics, VLSI, MCA, MBA, Math, Physics, Chemistry |
| **Administration** | Principal, Vice Principal, Governing Body, Founder, President |
| **Facilities** | Hostel, Library, Canteen, Dispensary, Sports, Bank/ATM, Guest House, Secure Campus |
| **Academics** | Academic Office, COE, Admissions, Fee Structure, NAAC, NIRF |
| **Student Life** | Placements, NSS, Professional Bodies, Committees, Career, Alumni |
| **Other** | IIIC, AICTE Idea Lab, RTI, Downloads, Media, Jnana Cauvery |

### Faculty Extraction
The scraper uses a 2-strategy approach:
1. **h3/h4 pattern matching** — Parses consecutive heading pairs (Name + Designation)
2. **Link card parsing** — Extracts from anchor tags with multi-line text

Results are grouped by: 🏛️ HOD → 👨‍🏫 Professors → 👤 Staff

---

## 🔑 Data Freshness

| Data Type | Source | Freshness |
|---|---|---|
| Faculty, HOD, Principal, Warden | **Live website scrape** | Real-time (30min cache) |
| Programs, Fee Structure | JSON + Website | Updated periodically |
| Placement Stats, Companies | JSON knowledge base | Static (manual update) |
| Weather | Weatherstack API | Real-time |

> The AI is instructed to **always prefer live web data** over static JSON for personnel information.

---

## 📝 License

This project is for educational purposes as part of the PESCE campus information system.

---

*Built with ❤️ for PESCE Mandya — Established 1962*
