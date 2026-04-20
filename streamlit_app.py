import streamlit as st
import json
import sqlite3
import pandas as pd
from datetime import datetime
import difflib
import re
import time

try:
    from deep_translator import GoogleTranslator
    HAS_TRANSLATOR = True
except ImportError:
    HAS_TRANSLATOR = False

from admin_dashboard import render_admin_dashboard
try:
    from semantic_matcher import SemanticSearcher
except ImportError:
    SemanticSearcher = None

try:
    from web_scraper import PESCEScraper
    HAS_SCRAPER = True
except ImportError:
    HAS_SCRAPER = False

try:
    from ai_engine import generate_ai_response, search_serpapi, build_context
    HAS_AI_ENGINE = True
except ImportError:
    HAS_AI_ENGINE = False

# ==========================================
# PAGE CONFIG & STYLING
# ==========================================
st.set_page_config(
    page_title="PESCE Campus Info AI 🎓",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* Global Theme Overrides: Deep Red, Gold, White Theme */
    .stApp {
        background-color: #FAFAFA;
    }
    
    /* Global Colors and Heading Fixes */
    h1, h2, h3 {
        color: #8B0000 !important; /* Deep Red */
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #8B0000;
        color: white;
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] p, [data-testid="stSidebar"] label {
        color: white !important;
    }
    
    /* Primary Outline Buttons */
    .stButton>button {
        border-radius: 8px;
        border: 2px solid #FFD700;
        background-color: white;
        color: #8B0000;
        font-weight: 600;
        transition: all 0.2s ease-in-out;
    }
    .stButton>button:hover {
        background-color: #FFD700;
        color: #8B0000;
        border-color: #8B0000;
    }
    
    /* Export Button specifically styling */
    .stDownloadButton>button {
        border-radius: 8px;
        border: 2px solid #FFD700;
        background-color: #FFD700;
        color: #8B0000;
        font-weight: 800;
    }
    
    /* Bottom Chat bar anchoring fix */
    [data-testid="stChatInput"] {
        padding-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)


# ==========================================
# DB SETUP & FUNCTIONS
# ==========================================
DB_NAME = "pesce_chat.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME,
            user_message TEXT,
            bot_response TEXT,
            category TEXT,
            user_satisfaction INTEGER,
            feedback_text TEXT,
            issue_type TEXT
        )
    ''')
    # Backward compatibility with existing DB
    try:
        c.execute("ALTER TABLE conversations ADD COLUMN feedback_text TEXT")
        c.execute("ALTER TABLE conversations ADD COLUMN issue_type TEXT")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

def save_conversation(user_message, bot_response, category):
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('INSERT INTO conversations (timestamp, user_message, bot_response, category) VALUES (?, ?, ?, ?)', 
                 (timestamp, user_message, bot_response, str(category)))
        msg_id = c.lastrowid
        conn.commit()
        conn.close()
        return msg_id
    except Exception:
        return None

def add_feedback(msg_id, rating=None, text=None, issue=None):
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        if rating is not None:
             c.execute('UPDATE conversations SET user_satisfaction = ? WHERE id = ?', (rating, msg_id))
        if text is not None:
             c.execute('UPDATE conversations SET feedback_text = ? WHERE id = ?', (text, msg_id))
        if issue is not None:
             c.execute('UPDATE conversations SET issue_type = ? WHERE id = ?', (issue, msg_id))
        conn.commit()
        conn.close()
    except Exception:
        pass

# Removed get_stats() as it is now securely managed by admin_dashboard.py

init_db()

# ==========================================
# DATA LOADING
# ==========================================
@st.cache_resource
def load_data():
    try:
        with open("pesce_data.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
PESCE_DATA = load_data()


# ==========================================
# TRANSLATION DICTIONARY (Headers & Fallback)
# ==========================================
LANG_DICT = {
    "English": {
        "Academics": "Academics", "Placements": "Placements", "Facilities": "Facilities", "Administrative": "Administrative", "Hostel": "Hostel", "Admission": "Admission",
        "fallback": "Mujhe is baare mein info nahi hai. Puchho: Academics, Placements, Facilities, ya Admin ke baare mein."
    },
    "Hindi": {
        "Academics": "शिक्षा", "Placements": "नियोजन", "Facilities": "सुविधाएं", "Administrative": "प्रशासनिक", "Hostel": "छात्रावास", "Admission": "प्रवेश",
        "fallback": "मुझे इस बारे में जानकारी नहीं है। कृपया शिक्षा, नियोजन, सुविधाओं या प्रवेश के बारे में पूछें।"
    },
    "Kannada": {
        "Academics": "ಶಿಕ್ಷಣ", "Placements": "ನೇಮಕಾತಿ", "Facilities": "ಸೌಲಭ್ಯಗಳು", "Administrative": "ಆಡಳಿತಾತ್ಮಕ", "Hostel": "ವಸತಿಗೃಹ", "Admission": "ಪ್ರವೇಶ",
        "fallback": "ನನಗೆ ಇದರ ಬಗ್ಗೆ ಮಾಹಿತಿ ಇಲ್ಲ. ಶಿಕ್ಷಣ, ನೇಮಕಾತಿ, ಸೌಲಭ್ಯಗಳು, ಅಥವಾ ಪ್ರವೇಶದ ಬಗ್ಗೆ ಕೇಳಿ."
    }
}

def auto_detect_language(text):
    if re.search(r'[\u0C80-\u0CFF]', text): return "Kannada"
    elif re.search(r'[\u0900-\u097F]', text): return "Hindi"
    return None 

def localize_response(response_text, category, lang):
    if lang == "English": return response_text
    if "I don't have specific information" in response_text or "No info" in response_text: return LANG_DICT[lang].get("fallback", response_text)
    if HAS_TRANSLATOR:
        lang_code = "hi" if lang == "Hindi" else "kn"
        try: return GoogleTranslator(source='auto', target=lang_code).translate(response_text)
        except Exception: pass 
            
    localized_text = response_text
    for en_word, translated_word in LANG_DICT[lang].items():
        pattern = re.compile(re.escape(en_word), re.IGNORECASE)
        localized_text = pattern.sub(translated_word, localized_text)
    return localized_text

# ==========================================
# QUERY MATCHER CLASS
# ==========================================
def format_answer(content, category):
    if category == "academics":
        programs = content.get("programs", [])
        return f"**Academic Structure:** {content.get('structure')}\n\n**Semester:** {content.get('semester')}\n\n**Programs:** {', '.join(programs[:5])}... and more"
    elif category == "placements":
        companies = content.get("top_companies", [])
        return f"**Companies:** {', '.join(companies[:7])}\n\n**Total Companies:** {content.get('companies_visited')}\n\n**Placements:** {content.get('students_placed')}"
    elif category == "facilities":
        parts = ["**Campus Facilities:**"]
        if content.get("library"): parts.append(f"- 📚 **Library:** {content['library']}")
        if content.get("boys_hostel"): parts.append(f"- 🏠 **Boys Hostel:** {content['boys_hostel']}")
        if content.get("girls_hostel"): parts.append(f"- 🏠 **Girls Hostel:** {content['girls_hostel']}")
        if content.get("dispensary"): parts.append(f"- 🏥 **Medical:** {content['dispensary']}")
        if content.get("canteen"): parts.append(f"- 🍽️ **Canteen:** {content['canteen']}")
        if content.get("sports"): parts.append(f"- 🏟️ **Sports:** {content['sports']}")
        return "\n".join(parts)
    elif category == "administrative":
        parts = ["**Administrative Info:**"]
        if content.get("principal"): parts.append(f"- 👨‍💼 **Principal:** {content['principal']}")
        if content.get("admission_email"): parts.append(f"- 📧 **Admission Email:** {content['admission_email']}")
        if content.get("admission_phone"): parts.append(f"- 📞 **Phone:** {content['admission_phone']}")
        if content.get("admission_types"): parts.append(f"- 🎓 **Admission Types:** {', '.join(content['admission_types'])}")
        if content.get("required_documents"): parts.append(f"- 📄 **Documents Required:** {', '.join(content['required_documents'][:5])}...")
        return "\n".join(parts)
    elif category == "contacts":
        parts = ["**Contact Information:**"]
        for key, value in content.items():
            label = key.replace("_", " ").title()
            parts.append(f"- 📞 **{label}:** {value}")
        return "\n".join(parts)
    elif category == "faq":
        # Format FAQ sections nicely instead of dumping raw dict
        parts = ["**Frequently Asked Questions:**\n"]
        if isinstance(content, dict):
            for section, questions in content.items():
                parts.append(f"**{section}:**")
                if isinstance(questions, list):
                    for item in questions[:3]:  # Show top 3 per section
                        if isinstance(item, dict):
                            parts.append(f"- **Q:** {item.get('question', '')}")
                            parts.append(f"  **A:** {item.get('answer', '')}")
                        else:
                            parts.append(f"- {item}")
                parts.append("")
        return "\n".join(parts)
    # Generic fallback: try to format dicts nicely instead of raw str()
    if isinstance(content, dict):
        parts = []
        for key, value in content.items():
            label = key.replace("_", " ").title()
            if isinstance(value, list):
                parts.append(f"**{label}:** {', '.join(str(v) for v in value[:5])}")
            elif isinstance(value, dict):
                parts.append(f"**{label}:** (see details below)")
            else:
                parts.append(f"**{label}:** {value}")
        return "\n".join(parts) if parts else str(content)
    return str(content)

class QueryMatcher:
    def __init__(self, data):
        self.data = data
        self.synonyms = {
            "academics": ["branch", "department", "course", "program", "academic", "study", "syllabus", "engineering"],
            "facilities": ["hostel", "dorm", "accommodation", "stay", "library", "canteen", "sports", "dispensary", "medical", "room", "facility"],
            "placements": ["placement", "job", "recruitment", "hiring", "company", "companies", "offer", "package", "salary", "internship", "career"],
            "administrative": ["fee", "tuition", "payment", "cost", "admission", "admin", "contact", "email", "phone", "document", "principal"]
        }
        self.vocab = [w for syns in self.synonyms.values() for w in syns] + list(self.synonyms.keys())

    def correct_typo(self, word):
        matches = difflib.get_close_matches(word.lower(), self.vocab, n=1, cutoff=0.7)
        return matches[0] if matches else word.lower()

    def match(self, query):
        if not self.data: return None, None, 0.0
        corrected_words = [self.correct_typo(w) for w in query.lower().split()]
        # Only score categories that have formatters — skip 'faq' from keyword matching
        # since it's a meta-category (its content gets matched via other categories)
        scorable_cats = {k: v for k, v in self.data.items() if k != "faq"}
        scores = {cat: 0.0 for cat in scorable_cats.keys()}
        
        for word in corrected_words:
            for cat, content in scorable_cats.items():
                if word == cat: scores[cat] += 1.0 
                elif word in self.synonyms.get(cat, []): scores[cat] += 0.8
                elif word in str(content).lower(): scores[cat] += 0.2
                    
        results = [
            {"category": cat, "content": self.data[cat], "confidence": min(score, 1.0)}
            for cat, score in scores.items() if min(score, 1.0) > 0.6
        ]
        results.sort(key=lambda x: x["confidence"], reverse=True)
        if not results: return None, None, 0.0
        best_conf = results[0]["confidence"]
        
        # If multiple categories match, return only the top one for cleaner output
        # (multi-category dumps were producing messy responses)
        cat = results[0]["category"]
        try:
            content = dict(results[0]["content"])
        except (TypeError, ValueError):
            content = results[0]["content"]
        if cat == "placements" and any(cw in ["cse", "cs", "computer"] for cw in corrected_words):
            content["filter_note"] = "💡 Note: Placements listed are overall numbers (includes CSE specific data)."
        return content, cat, best_conf

def find_answer(query):
    """
    Master answer pipeline (5 tiers):
      1. Gather context from semantic search
      2. Gather context from keyword search
      3. Gather context from web scraping (pesce.ac.in)
      4. Feed ALL context to AI Engine (Groq → Gemini) for natural response
      5. Offline fallback: template-based answers if LLMs are unavailable
    """
    semantic_result = None
    keyword_result = None
    keyword_category = None
    scraped_text = None

    # --- STEP 1: Semantic Search (gather context) ---
    if SemanticSearcher is not None:
        try:
            semantic_engine = SemanticSearcher(PESCE_DATA)
            sem_ans, sem_cat, sem_conf = semantic_engine.search(query, threshold=0.40)
            if sem_ans and sem_conf > 0.40:
                semantic_result = sem_ans
                keyword_category = sem_cat
                print(f"[Pipeline] Semantic hit: {sem_cat} ({sem_conf:.2f})")
        except Exception as e:
            print(f"[Pipeline] Semantic failure: {e}")

    # --- STEP 2: Keyword Search (gather context) ---
    matcher = QueryMatcher(PESCE_DATA)
    answer_data, category, confidence = matcher.match(query)
    if confidence > 0.5 and answer_data:
        keyword_result = answer_data
        if not keyword_category:
            keyword_category = category
        print(f"[Pipeline] Keyword hit: {category} ({confidence:.2f})")

    # --- STEP 3: Web Scraping (gather context) ---
    if HAS_SCRAPER:
        try:
            scraper = PESCEScraper()
            scraped, _ = scraper.search(query)
            if scraped:
                scraped_text = scraped
                print(f"[Pipeline] Web scrape: {len(scraped)} chars")
        except Exception as e:
            print(f"[Pipeline] Web scraper failure: {e}")

    # --- STEP 4: AI Engine (Groq → Gemini) ---
    if HAS_AI_ENGINE:
        try:
            ai_response, ai_source = generate_ai_response(
                query=query,
                json_data=PESCE_DATA,
                semantic_result=semantic_result,
                scraped_text=scraped_text,
                lang=st.session_state.get('language', 'English')
            )
            if ai_response:
                return ai_response, ai_source
        except Exception as e:
            print(f"[Pipeline] AI Engine failure: {e}")

    # --- STEP 5: Offline Fallback (template-based) ---
    if keyword_result and keyword_category:
        if isinstance(keyword_category, list):
            # Format each matched category safely
            parts = []
            for c in keyword_category:
                if c in keyword_result:
                    parts.append(format_answer(keyword_result[c], c))
            if parts:
                return "\n\n---\n\n".join(parts), "Multiple"
        else:
            return format_answer(keyword_result, keyword_category), keyword_category

    if scraped_text:
        return f"🌐 **Live from PESCE Website:**\n\n{scraped_text}", "Web Search"

    return "I don't have specific information about that. You can ask me about: **Academics**, **Placements**, **Facilities**, **Admissions**, or **Contact Info**. \n\nOr reach out directly at 📧 admissions@pesce.ac.in | 📞 +91 94482 82588", "General"


# ==========================================
# UI STATE MANAGEMENT
# ==========================================
if 'language' not in st.session_state: st.session_state.language = "English"
if 'last_msg_id' not in st.session_state: st.session_state.last_msg_id = None
if 'messages' not in st.session_state: st.session_state.messages = []
if 'quick_submit' not in st.session_state: st.session_state.quick_submit = None

# ==========================================
# SIDEBAR UI
# ==========================================
with st.sidebar:
    st.markdown("<h2 style='text-align: center; font-size:2em;'>🎓 PESCE AI</h2>", unsafe_allow_html=True)
    st.write("Interactive Campus Knowledge Bot")
    
    st.markdown("---")
    st.header("⚙️ Session Options")
    if st.button("🗑️ New Chat", width='stretch'):
        st.session_state.messages = []
        st.session_state.last_msg_id = None
        st.rerun()
        
    # Export Chat
    chat_raw = f"PESCE Campus Chat Log\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n=====================\n\n"
    for m in st.session_state.messages:
        role = "USER" if m["role"] == "user" else "PESCE BOT"
        chat_raw += f"[{role}]:\n{m['content']}\n\n"
    st.download_button("📥 Export Chat (TXT)", data=chat_raw, file_name="PESCE_Chat_Log.txt", width='stretch')
    
    st.markdown("---")
    st.header("🌐 Language Settings")
    selected_lang = st.selectbox(
        label="Select / चुनें / ಆರಿಸಿ",
        options=["English", "Hindi", "Kannada"],
        index=["English", "Hindi", "Kannada"].index(st.session_state.language),
        label_visibility="hidden"
    )
    if selected_lang != st.session_state.language:
        st.session_state.language = selected_lang
        st.rerun()

    st.markdown("---")
    if st.toggle("📊 Analytics/Admin"):
        st.session_state.view_admin = True
    else:
        st.session_state.view_admin = False

# ==========================================
# MAIN CHAT UI
# ==========================================
st.markdown("<h1 style='text-align: center; color: #8B0000; padding-bottom: 2rem;'>🎓 PESCE Campus Information AI</h1>", unsafe_allow_html=True)

# 0. FAQ PopOut Logic
@st.dialog("📚 Complete PESCE College FAQ")
def render_faq_dialog():
    if "faq" in PESCE_DATA:
        st.caption("Browse all formally categorized institutional policies below.")
        # Process each Dictionary key cleanly
        for section, questions in PESCE_DATA["faq"].items():
            st.markdown(f"#### {section} Level Policies")
            for item in questions:
                with st.expander(f"Q: {item['question']}"):
                    st.write(f"**A:** {item['answer']}")
            st.write("") # Margin padding
    else:
        st.warning("FAQ Data is currently unavailable.")

# Place the Trigger Button directly underneath your Main Chat Header
colA, colB, colC = st.columns([1, 2, 1])
with colB:
    if st.button("📖 Browse PESCE Complete FAQ Reference", width='stretch', type="primary"):
        render_faq_dialog()
st.write("") # Spacing padding before generic Start Screen options

# 1. Start Screen / Quick Action Buttons
if len(st.session_state.messages) == 0:
    st.markdown("""
        <div style="background-color: white; padding: 20px; border-radius: 10px; border-left: 5px solid #FFD700; margin-bottom: 30px; box-shadow: 0px 4px 6px rgba(0,0,0,0.05);">
            <h4 style="color: #333 !important; font-weight: normal; margin-top: 0;">Welcome! Click a topic below or send your own message to begin.</h4>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📚 Programs Offered", width='stretch'): st.session_state.quick_submit = "Tell me about programs offered"
        if st.button("💼 Placement Statistics", width='stretch'): st.session_state.quick_submit = "Placement statistics and top companies"
    with col2:
        if st.button("🏛️ Admission Process", width='stretch'): st.session_state.quick_submit = "Admission process and required documents"
        if st.button("🏠 Hostel Details", width='stretch'): st.session_state.quick_submit = "Give me boys and girls hostel details"
    with col3:
        if st.button("📞 Contact Information", width='stretch'): st.session_state.quick_submit = "What is the contact information and phone number?"
        if st.button("📖 Campus Facilities", width='stretch'): st.session_state.quick_submit = "Library, canteen, and sports facilities"

# 2. Render Existing Chat Log
for message in st.session_state.messages:
    avatar_emoji = "👤" if message["role"] == "user" else "🤖"
    with st.chat_message(message["role"], avatar=avatar_emoji):
        st.markdown(message["content"])
        if message.get("source"):
            st.caption(f"📌 Source: {message['source']} Section")

# 3. Handle Input Processing Loop
prompt = st.chat_input("Ask me about PESCE (e.g., 'Does the college have a pool?')")

# Intercept Quick Action button
if st.session_state.quick_submit:
    prompt = st.session_state.quick_submit
    st.session_state.quick_submit = None

if prompt:
    # Append & Draw User Message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    # Detect Auto-Lang
    detected_lang = auto_detect_language(prompt)
    if detected_lang and detected_lang != st.session_state.language:
        st.session_state.language = detected_lang
        st.toast(f"Swapped to {detected_lang} automatically!", icon="🌐")

    # Spinner Delay & Bot Response Execution
    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("🧠 Gathering data from college records..."):
            time.sleep(0.8) # Slight natural delay for UX immersion
            
            answer, category = find_answer(prompt)
            localized_answer = localize_response(answer, category, st.session_state.language)
            source_cat = "Multiple Matches" if isinstance(category, list) else str(category).capitalize()
            
            st.markdown(localized_answer)
            st.caption(f"📌 Source: {source_cat} Section")
            
            # Formally write array & save DB row
            msg_id = save_conversation(prompt, localized_answer, category)
            st.session_state.last_msg_id = msg_id
            st.session_state.messages.append({"role": "assistant", "content": localized_answer, "source": source_cat})
            
    # Forces UI refresh to ensure interactive Feedback component loads reliably underneath msg
    st.rerun()

# 4. Interactive Feedback Collection
if 'current_rating' not in st.session_state:
    st.session_state.current_rating = None

if st.session_state.last_msg_id:
    st.write("")
    st.markdown("---")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.write("💡 **Was this helpful?**")
        # Star Widget natively supports 0-4 mapping
        feedback = st.feedback("stars")
        
        # Capture raw rating
        if feedback is not None and st.session_state.current_rating is None:
             st.session_state.current_rating = feedback + 1
             add_feedback(st.session_state.last_msg_id, rating=st.session_state.current_rating)
             st.rerun()
             
    with col2:
         with st.popover("🤷 Didn't find what you wanted?"):
             st.write("**Let Admissions Help!**")
             st.markdown("📧 [Email Admissions](mailto:admissions@pesce.ac.in)")
             st.markdown("📞 [Call Us](tel:+919448282588)")

    # Expand Optional Feedback Options if deeply unsatisfied (1-3 Stars)
    if st.session_state.current_rating is not None:
        if st.session_state.current_rating < 4:
            with st.container(border=True):
                st.warning("We're sorry it wasn't perfect. Tell us why!")
                
                # Issue Reporting
                issue = st.radio("What went wrong?", ["Information wrong", "Not helpful", "Too slow", "Want more detail", "Other"], horizontal=True)
                
                # Feedback Text
                f_text = st.text_input("What could be better? (Optional)")
                
                # Follow-Up Logic for severely bad responses
                if st.session_state.current_rating <= 2:
                    st.info("We'll aggressively improve this. Would you like to chat with admin directly for a solution?")
                    
                if st.button("📥 Submit Detailed Feedback", type="primary"):
                    add_feedback(st.session_state.last_msg_id, text=f_text, issue=issue)
                    st.success("Thanks for feedback! ❤️")
                    time.sleep(1.5)
                    st.session_state.last_msg_id = None
                    st.session_state.current_rating = None
                    st.rerun()
        else:
             # Fast-pass success for 4-5 stars
             st.success("Thanks for feedback! ❤️")
             time.sleep(1.5)
             st.session_state.last_msg_id = None
             st.session_state.current_rating = None
             st.rerun()

if st.session_state.get('view_admin', False):
    render_admin_dashboard()
