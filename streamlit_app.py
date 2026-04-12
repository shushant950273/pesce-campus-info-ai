import streamlit as st
import time

st.set_page_config(
    page_title="PESCE Campus Info AI",
    page_icon="🎓",
    layout="wide"
)

def build_sidebar():
    with st.sidebar:
        st.title("🎓 PESCE Mandya AI")
        st.write("Welcome to the Interactive Campus Info AI Agent.")
        
        st.subheader("Filter by Category")
        category = st.selectbox(
            "Select Category",
            ["All", "Academics", "Placements", "Facilities", "Clubs", "Administrative"]
        )
        
        st.divider()
        st.markdown("**Powered by LangChain & Streamlit**")
    return category

def build_main_ui():
    st.header("Interactive Campus Info AI Agent")
    st.write("Ask anything about PESCE Mandya!")
    
    tab1, tab2 = st.tabs(["Chat", "Popular Queries & FAQ"])
    
    with tab1:
        display_chat_interface()
        
    with tab2:
        st.subheader("Popular Queries")
        st.button("What are the placement statistics for CS?")
        st.button("Where is the library located and what are the timings?")
        st.button("How do I apply for hostel accommodation?")
        st.button("What clubs are available for extracurriculars?")

def display_chat_interface():
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask a question about PESCE..."):
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        sample_responses = {
            "placement": "PESCE Mandya has an active placement cell. Top recruiters include TCS, Infosys, and Wipro.",
            "academics": "PESCE offers numerous undergraduate and postgraduate courses affiliated with VTU.",
            "hostel": "The campus has separate hostel facilities for boys and girls.",
            "hello": "Hello! How can I help you regarding PESCE Mandya today?"
        }
        
        def fallback_response(query):
            query = query.lower()
            for key, val in sample_responses.items():
                if key in query:
                    return val
            return "Based on the internal knowledge, I couldn't find an exact answer. Please refer to https://pesce.ac.in/."

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            
            response = fallback_response(prompt)
            for chunk in response.split():
                full_response += chunk + " "
                time.sleep(0.05)
                message_placeholder.markdown(full_response + "▌")
            message_placeholder.markdown(full_response)
            
        st.session_state.messages.append({"role": "assistant", "content": full_response})

if __name__ == "__main__":
    selected_category = build_sidebar()
    build_main_ui()
