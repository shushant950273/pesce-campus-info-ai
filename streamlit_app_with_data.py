"""
PESCE Campus Info AI - Updated with Real Data
Using collected data from pesce_data_complete.json
"""

import streamlit as st
import json
import os
from datetime import datetime

# ===== PAGE CONFIG =====
st.set_page_config(
    page_title="PESCE Campus Info AI 🎓",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===== LOAD PESCE DATA =====
def load_pesce_data():
    """Load PESCE data from JSON file"""
    try:
        with open('pesce_data_complete.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("Data file not found. Please ensure pesce_data_complete.json is in the same directory.")
        return None

PESCE_DATA = load_pesce_data()

# ===== INTELLIGENT QUERY MATCHING =====
def find_answer(query: str) -> tuple:
    """Find relevant answer using intelligent matching"""
    query_lower = query.lower()
    
    best_match = None
    best_score = 0
    best_category = None
    
    if not PESCE_DATA:
        return "Data not loaded. Please check the data file.", "Error", 0
    
    # Search through all categories
    for category, content in PESCE_DATA.items():
        score = score_category(category, content, query_lower)
        if score > best_score:
            best_score = score
            best_match = content
            best_category = category
    
    if best_match and best_score > 0:
        answer = format_answer(best_match, query_lower, best_category)
        return answer, best_category.replace('_', ' ').title(), best_score
    
    return "I don't have specific information about that. Try asking about: Academics, Placements, Facilities, or Administration.", "General", 0

def score_category(category: str, content: dict, query: str) -> int:
    """Score relevance of category to query"""
    score = 0
    content_str = str(content).lower()
    
    # Keyword matching
    keywords = query.split()
    for keyword in keywords:
        if keyword in content_str:
            score += 10
        if keyword in category:
            score += 20
    
    # Category-specific keywords
    category_keywords = {
        "academics": ["semester", "exam", "calendar", "curriculum", "course", "structure", "program"],
        "placements": ["placement", "company", "internship", "recruitment", "job", "package"],
        "facilities": ["library", "lab", "hostel", "medical", "canteen", "sports", "doctor"],
        "clubs": ["club", "society", "activity", "cultural", "technical", "sports"],
        "administrative": ["admission", "fee", "document", "contact", "enrollment"]
    }
    
    if category in category_keywords:
        for kw in category_keywords[category]:
            if kw in query:
                score += 30
    
    return score

def format_answer(content: dict, query: str, category: str) -> str:
    """Format answer based on category"""
    
    if category == "academics":
        if "semester" in query:
            return f"**Semester Structure:** {content.get('semester', 'Not available')}\n\n**Structure:** {content.get('structure', '')}"
        elif "exam" in query or "evaluation" in query:
            return f"**Exam Pattern:** {content.get('exam_pattern', 'Not available')}"
        elif "program" in query or "course" in query:
            programs = content.get('programs', [])
            prog_list = '\n'.join([f"• {p}" for p in programs[:5]])
            return f"**Programs Offered at PESCE:**\n\n{prog_list}\n\n...and {len(programs)-5} more programs"
        else:
            return f"**Academic Structure:** {content.get('structure', '')}\n\n**Semester Timings:** {content.get('semester', '')}"
    
    elif category == "placements":
        if "company" in query or "companies" in query:
            companies = content.get('top_companies', [])
            comp_list = ', '.join(companies[:8])
            return f"**Top Companies Visiting PESCE:** {comp_list}\n\n...and many more (359 companies total)"
        elif "package" in query or "salary" in query:
            return f"**Placement Statistics:**\n\n• Total Companies: {content.get('companies_visited', 'N/A')}\n• Offers Rolled Out: {content.get('total_offers', 'N/A')}\n• Students Placed: {content.get('students_placed', 'N/A')}"
        else:
            return f"**Placement Cell Location:** {content.get('cell_location', 'Not available')}\n\n**Contact:** For placement information, visit the placement cell or email admissions@pesce.ac.in"
    
    elif category == "facilities":
        if "library" in query:
            lib = content.get('library', {})
            return f"**Library and Information Center**\n\n⏰ **Weekday:** {lib.get('timing_weekday', '')}\n⏰ **Saturday:** {lib.get('timing_saturday', '')}\n\n📚 **Capacity:** {lib.get('capacity', '')} students\n🏢 **Area:** {lib.get('area', '')}"
        elif "hostel" in query:
            boys = content.get('hostel_boys', {})
            girls = content.get('hostel_girls', {})
            return f"**Hostel Facilities**\n\n👨 **Boys Hostel:** {boys.get('capacity', '')} capacity\n👩 **Girls Hostel:** {girls.get('capacity', '')} capacity\n\n✨ **Facilities:** Free medical, Library, WiFi, TV room, Solar water heaters, CCTV, Mess"
        elif "medical" in query or "doctor" in query or "health" in query:
            medical = content.get('medical', {})
            doctors = medical.get('doctors', [])
            doc_list = '\n'.join([f"• {d}" for d in doctors])
            return f"**Medical Dispensary**\n\n👨‍⚕️ **Doctors Available:**\n{doc_list}\n\n🏥 **Services:** Essential medicines, Bed facilities, 24/7 emergency"
        elif "canteen" in query or "food" in query:
            canteen = content.get('canteen', {})
            return f"**Canteen Facilities**\n\n⏰ **Timing:** {canteen.get('timing', '')}\n👥 **Capacity:** {canteen.get('capacity', '')}\n🍽️ **Food Type:** {canteen.get('food_type', '')}"
        else:
            return "**PESCE Facilities:** Library, Hostels (Boys & Girls), Medical Dispensary, Canteen, Labs, Sports"
    
    elif category == "administrative":
        if "admission" in query or "admit" in query:
            adm = content.get('admission', {})
            return f"**Admission Information**\n\n📋 **Process:** {adm.get('process', '')}\n\n📞 **Contact:** {adm.get('contact_person', '')}\n📧 **Email:** {adm.get('email', '')}\n☎️ **Phone:** {adm.get('phone', '')}"
        elif "fee" in query or "fees" in query:
            fees = content.get('fees', {})
            programs = fees.get('programs', [])
            prog_list = '\n'.join([f"• {p}" for p in programs])
            return f"**Fee Structure**\n\nDifferent fees for:\n{prog_list}\n\nVisit website for detailed fee structure"
        elif "document" in query or "documents" in query:
            docs = content.get('documents_required', {})
            orig = docs.get('original_documents', [])[:3]
            orig_list = '\n'.join([f"• {d}" for d in orig])
            return f"**Documents Required for Admission**\n\n📄 **Original Documents:**\n{orig_list}\n\n...and more (See website for complete list)"
        else:
            contact = content.get('contact_info', {})
            return f"**Administrative Contact**\n\n📧 Email: {contact.get('email', '')}\n☎️ Phone: {contact.get('phone', '')}\n👤 Coordinator: {contact.get('admissions_coordinator', '')}"
    
    return str(content)

# ===== SIDEBAR =====
with st.sidebar:
    st.image("https://pesce.ac.in/assets/img/logo.png", width=150)
    st.title("🎓 PESCE Campus AI")
    st.write("Interactive Campus Information Assistant")
    
    st.divider()
    
    st.subheader("📚 Categories")
    categories = ["📖 Academics", "💼 Placements", "🏢 Facilities", "📋 Admin"]
    selected = st.selectbox("Select Category:", categories)
    
    st.divider()
    
    st.info("""
    **About This Bot:**
    Campus information for PESCE Mandya using real college data.
    
    Ask about academics, placements, facilities, or administration.
    """)

# ===== MAIN CONTENT =====
st.markdown("<h1 style='text-align: center; color: #1f77b4;'>🎓 PESCE Campus Information AI</h1>", unsafe_allow_html=True)

st.markdown("""
<div style='background-color: #f0f2f6; padding: 15px; border-radius: 8px; margin: 20px 0;'>
    <strong>Welcome!</strong> Ask me anything about PES College of Engineering, Mandya.
</div>
""", unsafe_allow_html=True)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("source"):
            st.caption(f"📌 Source: {message['source']}")

st.divider()

# Chat input
col1, col2 = st.columns([0.9, 0.1])

with col1:
    user_input = st.chat_input("Ask about PESCE Mandya...")

with col2:
    submit = st.button("📤", key="send")

# Process input
if user_input and submit:
    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })
    
    answer, source, score = find_answer(user_input)
    
    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "source": source
    })
    
    st.rerun()

# ===== TABS =====
st.divider()

tab1, tab2, tab3 = st.tabs(["💬 Chat", "❓ Popular Queries", "ℹ️ About"])

with tab1:
    st.subheader("Quick Questions")
    
    quick_queries = {
        "🎓 Academics": "What is the academic structure?",
        "💼 Placements": "What companies visit PESCE?",
        "📚 Library": "What are library timings?",
        "🏠 Hostel": "Tell me about hostel facilities",
        "🏥 Medical": "Is there a medical center?"
    }
    
    for label, q in quick_queries.items():
        if st.button(f"{label}", use_container_width=True, key=f"quick_{label}"):
            st.session_state.messages.append({"role": "user", "content": q})
            answer, source, _ = find_answer(q)
            st.session_state.messages.append({"role": "assistant", "content": answer, "source": source})
            st.rerun()

with tab2:
    st.subheader("Frequently Asked Questions")
    
    faqs = {
        "How do I apply for admission?": "PESCE accepts merit-based admission through CET (AIDED - E023), UNAIDED (E058), and COMED-K (E089). Contact: admissions@pesce.ac.in or +91 94482 82588",
        "What documents do I need?": "You need SSLC marks, PUC marks, CET/COMED-K allotment order, Transfer Certificate, and other certificates. Check the website for complete list.",
        "What are the placement statistics?": "359 companies visit PESCE. In 2022-23, 1034 offers were rolled out and 549 students were placed.",
        "Can I stay in hostel?": "Yes, separate hostels for boys (350 capacity) and girls (371 capacity) with excellent facilities including medical, WiFi, and mess."
    }
    
    for q, a in faqs.items():
        with st.expander(q):
            st.write(a)

with tab3:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📖 About PESCE")
        st.write("""
        **PES College of Engineering**
        - Location: Mandya, Karnataka
        - Autonomous since: 2008
        - Programs: B.Tech, M.Tech, Diploma, PhD
        - Contact: admissions@pesce.ac.in
        """)
    
    with col2:
        st.subheader("🤖 About This Bot")
        st.write("""
        **Campus Info AI v2.0**
        - Real college data
        - Intelligent matching
        - Multi-category support
        - Always accurate
        """)

# Footer
st.divider()
col1, col2, col3 = st.columns(3)
with col1:
    st.caption("🌐 pesce.ac.in")
with col2:
    st.caption("📧 admissions@pesce.ac.in")
with col3:
    st.caption(f"⏰ {datetime.now().strftime('%d-%b-%Y')}")

st.caption("Campus Information AI for PESCE Mandya | Built with ❤️")
