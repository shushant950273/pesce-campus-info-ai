"""PESCE Campus Info AI - Professional Chatbot App"""
import streamlit as st
import json
import os
import time
from datetime import datetime
from dotenv import load_dotenv

# Try to import our robust Gemini Assistant
try:
    from src.gemini_assistant import GeminiAssistant
except ImportError:
    # Fallback if module is not found
    GeminiAssistant = None

load_dotenv()

# ── Page Config ──
st.set_page_config(
    page_title="PESCE Campus AI", 
    page_icon="🎓", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# ── Custom CSS for Professional Presentation ──
st.markdown("""
<style>
    /* Global Colors and Fonts */
    :root {
        --primary-red: #C41E3A;
        --secondary-gold: #FFD700;
        --accent-white: #FFFFFF;
        --bg-light-gray: #F5F5F5;
        --text-dark: #333333;
        --msg-user-bg: #E3F2FD; /* Light Blue */
        --msg-bot-bg: #EEEEEE;  /* Light Gray */
    }
    
    .stApp {
        background-color: var(--bg-light-gray);
        color: var(--text-dark);
        font-family: 'Inter', 'Segoe UI', sans-serif;
    }
    
    h1, h2, h3, h4, h5, h6 {
        color: var(--primary-red) !important;
        font-weight: 700 !important;
    }
    
    /* Header Image & Branding */
    .header-container {
        background: linear-gradient(rgba(196, 30, 58, 0.85), rgba(196, 30, 58, 0.85)), 
                    url('https://images.unsplash.com/photo-1541339907198-e08756dedf3f?ixlib=rb-4.0.3&auto=format&fit=crop&w=1200&q=80');
        background-size: cover;
        background-position: center;
        padding: 2.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        border-bottom: 4px solid var(--secondary-gold);
    }
    .header-container h1 {
        color: var(--accent-white) !important;
        font-size: 2.5rem !important;
        margin-bottom: 0.5rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    .header-container p {
        color: var(--secondary-gold) !important;
        font-size: 1.2rem;
        font-weight: 600;
        margin: 0;
    }

    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: var(--accent-white);
        border-right: 3px solid var(--secondary-gold);
        box-shadow: 2px 0 10px rgba(0,0,0,0.05);
    }
    [data-testid="stSidebar"] * {
        color: var(--text-dark) !important;
    }
    .sidebar-section {
        background-color: var(--bg-light-gray);
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        border-left: 4px solid var(--primary-red);
    }
    
    /* Chat Messages */
    [data-testid="stChatMessage"] {
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }
    
    /* User Message Background */
    [data-testid="stChatMessage"][data-baseweb="box"]:nth-child(even) {
        background-color: var(--msg-bot-bg) !important;
        border-left: 5px solid var(--primary-red);
    }
    
    /* Bot Message Background (Streamlit structure applies roles via order/icons usually, but we use custom HTML below for precision) */
    
    /* Input Box */
    .stChatInputContainer {
        border: 2px solid var(--primary-red) !important;
        border-radius: 25px !important;
        background-color: var(--accent-white) !important;
        box-shadow: 0 4px 12px rgba(196, 30, 58, 0.15) !important;
    }
    
    /* Buttons */
    .stButton > button {
        background-color: var(--accent-white) !important;
        color: var(--primary-red) !important;
        border: 1px solid var(--primary-red) !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        min-height: 48px !important; /* Mobile friendly */
    }
    .stButton > button:hover {
        background-color: var(--primary-red) !important;
        color: var(--accent-white) !important;
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(196, 30, 58, 0.2);
    }
    
    /* Feedback Buttons (small) */
    .feedback-btn .stButton > button {
        min-height: 32px !important;
        padding: 0 10px !important;
        border-radius: 20px !important;
        border: 1px solid #ddd !important;
        background: transparent !important;
        color: #666 !important;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: var(--accent-white);
        padding: 10px 10px 0 10px;
        border-radius: 10px 10px 0 0;
        box-shadow: 0 -2px 10px rgba(0,0,0,0.05);
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        color: #666;
        font-weight: 600;
        padding: 10px 20px;
    }
    .stTabs [aria-selected="true"] {
        background-color: var(--primary-red) !important;
        color: var(--accent-white) !important;
    }
    
    /* Cards */
    .info-card {
        background: var(--accent-white);
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        border-top: 4px solid var(--primary-red);
        margin-bottom: 1.5rem;
        height: 100%;
    }
    .info-card h4 {
        margin-top: 0;
        border-bottom: 2px solid var(--bg-light-gray);
        padding-bottom: 10px;
    }
    
    /* Timestamps */
    .timestamp {
        font-size: 0.75rem;
        color: #888;
        text-align: right;
        margin-top: -10px;
        margin-bottom: 10px;
    }
    
    /* Custom Message Bubbles */
    .user-bubble {
        background-color: var(--msg-user-bg);
        padding: 15px 20px;
        border-radius: 15px 15px 0 15px;
        color: var(--text-dark);
        margin-bottom: 5px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .bot-bubble {
        background-color: var(--msg-bot-bg);
        padding: 15px 20px;
        border-radius: 15px 15px 15px 0;
        color: var(--text-dark);
        margin-bottom: 5px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        border-left: 4px solid var(--primary-red);
    }
</style>
""", unsafe_allow_html=True)

# ── Load Data ──
@st.cache_resource
def load_data():
    paths = ["pesce_data_complete.json", "data/processed/pesce_data.json"]
    for p in paths:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
    return {}

DATA = load_data()

# ── Initialize Assistant ──
@st.cache_resource
def get_assistant():
    api_key = os.getenv("GOOGLE_API_KEY", "")
    if GeminiAssistant:
        return GeminiAssistant(api_key=api_key, pesce_data=DATA)
    return None

assistant = get_assistant()

# ── Session State ──
if "messages" not in st.session_state:
    st.session_state.messages = []
if "personality" not in st.session_state:
    st.session_state.personality = "Professional"
if "language" not in st.session_state:
    st.session_state.language = "English"

def process_query(query):
    """Process user query and generate response."""
    # Add user message
    st.session_state.messages.append({
        "role": "user", 
        "content": query,
        "time": datetime.now().strftime("%I:%M %p")
    })
    
    with st.spinner("Analyzing college data..."):
        time.sleep(0.5) # Smooth animation feel
        if assistant:
            resp, followups = assistant.generate_response(
                user_query=query, 
                chat_history=st.session_state.messages,
                personality=st.session_state.personality,
                language=st.session_state.language
            )
        else:
            # Simple fallback if module missing
            resp = "I am currently operating in offline mode. For full AI capabilities, please ensure `src.gemini_assistant` is available and API keys are configured."
            followups = ["What are the admission requirements?", "Tell me about placements."]
            
    # Add bot message
    st.session_state.messages.append({
        "role": "assistant", 
        "content": resp,
        "followups": followups,
        "time": datetime.now().strftime("%I:%M %p")
    })

# ═══════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════
with st.sidebar:
    st.image("assets/logo.svg", width=180)
    st.markdown("### 🎓 Campus Assistant")
    
    st.markdown("""<div class="sidebar-section">
    <strong>⚙️ Preferences</strong><br><br>
    </div>""", unsafe_allow_html=True)
    
    st.session_state.language = st.selectbox("🌐 Language", ["English", "Hindi", "Kannada"], index=0)
    st.session_state.personality = st.selectbox("🎭 AI Tone", ["Professional", "Friendly", "Expert", "Student", "Parent"], index=0)

    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown("""<div class="sidebar-section">
    <strong>⚡ Quick Actions</strong>
    </div>""", unsafe_allow_html=True)
    
    quick_qs = {
        "🏫 Admissions Info": "How do I get admission to PESCE? What is the process?",
        "💼 Placement Stats": "What are the latest placement statistics and top recruiters?",
        "📚 UG Programs": "List all undergraduate (B.E.) programs offered.",
        "💰 Fee Structure": "What is the fee structure for B.E. programs?",
        "🏠 Hostel Details": "Tell me about boys and girls hostel facilities.",
    }
    
    for label, q in quick_qs.items():
        if st.button(label, use_container_width=True):
            process_query(q)
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🗑️ Clear Conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.markdown("**📍 Contact Info**")
    st.caption("📞 +91 8232 220043\n\n📧 principal@pesce.ac.in\n\n🗺️ Mandya, Karnataka")

# ═══════════════════════════════════════════
# MAIN CONTENT
# ═══════════════════════════════════════════

# Header
st.markdown("""
<div class="header-container">
    <h1>P.E.S. College of Engineering</h1>
    <p>Interactive Campus Information AI</p>
</div>
""", unsafe_allow_html=True)

# Tabs
tab_chat, tab_faq, tab_info, tab_contact = st.tabs([
    "💬 AI Assistant", 
    "❓ FAQ", 
    "📊 Quick Stats", 
    "📞 Directory"
])

# ── Tab 1: Chat ──
with tab_chat:
    
    # Welcome Message
    if not st.session_state.messages:
        st.markdown("""
        <div class="info-card" style="text-align: center; border-top: 4px solid var(--secondary-gold);">
            <h3>👋 Welcome to the PESCE AI Assistant</h3>
            <p style="font-size: 1.1rem; color: #555;">I can answer questions about academics, admissions, placements, facilities, and more using official college data.</p>
            <p><strong>Try asking:</strong> <em>"What is the highest placement package?"</em> or <em>"How do I apply for CSE?"</em></p>
        </div>
        """, unsafe_allow_html=True)

    # Display Chat History using custom HTML for perfect styling
    for i, msg in enumerate(st.session_state.messages):
        is_user = msg["role"] == "user"
        avatar = "🧑" if is_user else "🤖"
        bubble_class = "user-bubble" if is_user else "bot-bubble"
        align = "right" if is_user else "left"
        
        # We use st.chat_message for standard layout, but inject custom HTML inside
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(f"<div class='timestamp'>{msg.get('time', '')}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='{bubble_class}'>{msg['content']}</div>", unsafe_allow_html=True)
            
            if not is_user:
                # Actions row
                col1, col2, col3, col4 = st.columns([1,1,1,7])
                with col1:
                    if st.button("😊", key=f"up_{i}", help="Helpful"): st.toast("Feedback received! 👍")
                with col2:
                    if st.button("😞", key=f"dn_{i}", help="Not helpful"): st.toast("Feedback received! We will improve.")
                with col3:
                    if st.button("📋", key=f"cp_{i}", help="Copy"): st.toast("Copied to clipboard!")
                
                # Follow-ups
                followups = msg.get("followups", [])
                if followups:
                    st.markdown("**💡 Suggested Follow-ups:**")
                    for fi, fq in enumerate(followups):
                        if st.button(f"👉 {fq}", key=f"fu_{i}_{fi}"):
                            process_query(fq)
                            st.rerun()

    # Chat Input
    st.markdown("<br>", unsafe_allow_html=True)
    if user_input := st.chat_input("Type your question here (e.g., 'Tell me about the library')..."):
        process_query(user_input)
        st.rerun()

# ── Tab 2: FAQ ──
with tab_faq:
    st.markdown("### ❓ Frequently Asked Questions")
    
    search = st.text_input("🔍 Search FAQs", placeholder="Type a keyword...")
    
    faqs = [
        ("How do I apply for admission?", "Admissions are merit-based through CET (AIDED - E023), UNAIDED (E058), and COMED-K (E089). Please contact the admissions office for current year intake details."),
        ("What is the placement record?", "PESCE has a strong placement record with 359+ visiting companies. In recent years, over 1034 offers were made to students. Top recruiters include TCS, Infosys, Wipro, Accenture, and IBM."),
        ("Are hostel facilities available?", "Yes, there are separate, well-equipped hostels for boys (capacity 350) and girls (capacity 371) located within the campus. They include WiFi, medical facilities, and a mess."),
        ("Is PESCE an autonomous college?", "Yes, PESCE was granted autonomous status by the UGC in the year 2008-09. It remains permanently affiliated to Visvesvaraya Technological University (VTU), Belagavi."),
        ("What undergraduate programs do you offer?", "We offer 13 B.E. programs including Computer Science, Civil, Mechanical, Electronics & Communication, Electrical & Electronics, Artificial Intelligence & Machine Learning, Data Science, and Robotics."),
        ("What are the library hours?", "The Central Library is open on weekdays from 8:00 AM to 8:00 PM (Reference) and 10:00 AM to 5:30 PM (Lending). On Saturdays, it closes at 5:00 PM."),
    ]
    
    filtered_faqs = [faq for faq in faqs if search.lower() in faq[0].lower() or search.lower() in faq[1].lower()]
    
    for q, a in filtered_faqs:
        with st.expander(f"**{q}**"):
            st.markdown(f"<div style='padding: 10px; color: #444;'>{a}</div>", unsafe_allow_html=True)

# ── Tab 3: Quick Info ──
with tab_info:
    st.markdown("### 📊 College Overview")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="info-card">
            <h4>🏆 Rankings & Accreditations</h4>
            <ul>
                <li><b>NAAC:</b> Accredited with 'A' Grade</li>
                <li><b>NBA:</b> Accredited Programs</li>
                <li><b>AICTE:</b> Approved Institution</li>
                <li><b>Status:</b> Autonomous under VTU</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="info-card">
            <h4>👨‍🎓 Campus Statistics</h4>
            <ul>
                <li><b>Total Students:</b> 4000+</li>
                <li><b>Alumni Network:</b> 25,000+ global alumni</li>
                <li><b>Research Publications:</b> 2050+</li>
                <li><b>PhDs Awarded:</b> 140+</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="info-card">
            <h4>🏢 Infrastructure</h4>
            <ul>
                <li><b>Campus Area:</b> 55+ acres lush green campus</li>
                <li><b>Library:</b> 13,000+ sq.ft, 69,000+ volumes</li>
                <li><b>Computing:</b> High-speed WiFi, modern labs</li>
                <li><b>Sports:</b> Playgrounds, indoor courts, gymnasium</li>
                <li><b>Medical:</b> On-campus dispensary, 24/7 emergency</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="info-card">
            <h4>💼 Top Recruiters</h4>
            <p>TCS, Infosys, Wipro, Accenture, Capgemini, HCL, IBM, Tech Mahindra, Cognizant, MindTree, DXC Technology, L&T.</p>
        </div>
        """, unsafe_allow_html=True)

# ── Tab 4: Directory ──
with tab_contact:
    st.markdown("### 📞 Important Contacts")
    
    contacts = [
        ("Principal Office", "Dr. N.L. Murali Krishna", "+91 94482 82580", "principal@pesce.ac.in"),
        ("Admissions", "Manish Kumar S", "+91 94482 82588", "admissions@pesce.ac.in"),
        ("Placement Cell", "Dr. Vinay S", "+91 94482 82589", "placement@pesce.ac.in"),
        ("Dean Research", "Dr. Mahesh Koti", "+91 89711 06671", "deanresearch@pesce.ac.in"),
        ("College Office", "General Inquiry", "+91 8232 220043", ""),
    ]
    
    for dept, name, phone, email in contacts:
        st.markdown(f"""
        <div class="info-card" style="margin-bottom: 1rem; padding: 1rem;">
            <div style="display: flex; justify-content: space-between; flex-wrap: wrap;">
                <div style="flex: 1; min-width: 200px;">
                    <strong style="color: var(--primary-red); font-size: 1.1rem;">{dept}</strong><br>
                    <span style="color: #666;">{name}</span>
                </div>
                <div style="flex: 1; min-width: 200px;">
                    📞 {phone}<br>
                    {'📧 ' + email if email else ''}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("""
    <div class="info-card" style="background-color: var(--primary-red); color: white;">
        <h4 style="color: white; border-bottom: 1px solid rgba(255,255,255,0.3);">📍 Address</h4>
        <p style="color: white;">
            P.E.S. College of Engineering<br>
            K V Shankaragowda Road, PES College Campus<br>
            Mandya, Karnataka 571401, India
        </p>
    </div>
    """, unsafe_allow_html=True)

