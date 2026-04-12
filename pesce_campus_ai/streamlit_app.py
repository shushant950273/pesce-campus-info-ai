
import streamlit as st
import json
from datetime import datetime

# Page config
st.set_page_config(
    page_title="PESCE Campus Info AI 🎓",
    page_icon="🎓",
    layout="wide"
)

# Load data
@st.cache_resource
def load_data():
    with open("pesce_data.json", "r", encoding="utf-8") as f:
        return json.load(f)

PESCE_DATA = load_data()

# Query matching function
def find_answer(query):
    query_lower = query.lower()
    best_match = None
    best_category = None
    best_score = 0

    for category, content in PESCE_DATA.items():
        score = 0
        content_str = str(content).lower()
        keywords = query_lower.split()

        for keyword in keywords:
            if keyword in content_str:
                score += 10
            if keyword in category:
                score += 20

        if score > best_score:
            best_score = score
            best_match = content
            best_category = category

    if best_match and best_score > 0:
        return format_answer(best_match, best_category), best_category

    return "Mujhe is baare mein info nahi hai. Puchho: Academics, Placements, Facilities, ya Admin ke baare mein.", "General"

def format_answer(content, category):
    if category == "academics":
        programs = content.get("programs", [])
        return f"**Academic Structure:** {content.get('structure')}\n\n**Semester:** {content.get('semester')}\n\n**Programs:** {', '.join(programs[:5])}... aur aur bhi"

    elif category == "placements":
        companies = content.get("top_companies", [])
        return f"**Companies:** {', '.join(companies[:7])}\n\n**Total Companies:** {content.get('companies_visited')}\n\n**Placements:** {content.get('students_placed')}"

    elif category == "facilities":
        return "**Facilities:**\n- Library: 100 capacity\n- Boys Hostel: 350 capacity\n- Girls Hostel: 371 capacity\n- Medical: 24/7 emergency\n- Canteen: 250 students capacity"

    elif category == "administrative":
        return f"**Admission Email:** admissions@pesce.ac.in\n**Phone:** +91 94482 82588\n\n**Documents:** SSLC, PUC, Aadhar, Transfer Certificate, aur aur..."

    return str(content)

# UI
st.markdown("<h1 style='text-align: center; color: #1f77b4;'>🎓 PESCE Campus Information AI</h1>", unsafe_allow_html=True)

with st.sidebar:
    st.title("PESCE Campus AI")
    st.write("Interactive Campus Information Assistant")
    st.info("Pucho PESCE ke baare mein!")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
user_input = st.chat_input("PESCE ke baare mein poochho...")

if user_input:
    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })

    answer, source = find_answer(user_input)

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer
    })

    st.rerun()

# Tabs
tab1, tab2, tab3 = st.tabs(["Chat", "FAQ", "About"])

with tab1:
    st.subheader("Quick Questions")
    if st.button("🎓 Academics"):
        st.session_state.messages.append({"role": "user", "content": "Tell me about academics"})
        answer, _ = find_answer("academics")
        st.session_state.messages.append({"role": "assistant", "content": answer})
        st.rerun()

    if st.button("💼 Placements"):
        st.session_state.messages.append({"role": "user", "content": "Tell me about placements"})
        answer, _ = find_answer("placements")
        st.session_state.messages.append({"role": "assistant", "content": answer})
        st.rerun()

with tab2:
    st.subheader("FAQ")
    with st.expander("Admission kaise hota hai?"):
        st.write("CET, UNAIDED ya COMED-K se admission hota hai. Email: admissions@pesce.ac.in")

    with st.expander("Hostel facilities kaun si hain?"):
        st.write("Boys aur Girls dono ke liye separate hostels. Medical, WiFi, Mess, sab hai!")

with tab3:
    st.write("**PESCE Campus AI v1.0**\nBuilt with ❤️ for PESCE students")
    st.write(f"**Date:** {datetime.now().strftime('%d-%b-%Y')}")
