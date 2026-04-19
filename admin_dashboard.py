import sqlite3
import streamlit as st
import csv
import io
from datetime import datetime, timedelta

DB_PATH = "pesce_chat.db"
ADMIN_PASSWORD = "pesce"

def fetch_basic_stats():
    """Queries core statistics purely with sqlite3"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 1. Total today
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT COUNT(*) FROM conversations WHERE timestamp LIKE ?", (f"{today}%",))
    total_today = c.fetchone()[0]
    
    # 2. Most popular category
    c.execute("SELECT category, COUNT(*) as cnt FROM conversations GROUP BY category ORDER BY cnt DESC LIMIT 1")
    cat_row = c.fetchone()
    most_cat = cat_row[0] if cat_row else "None"
    
    # 3. Average Satisfaction
    c.execute("SELECT AVG(user_satisfaction) FROM conversations WHERE user_satisfaction IS NOT NULL")
    sat_row = c.fetchone()
    avg_sat = round(sat_row[0], 1) if sat_row[0] else 0.0
    
    # 4. Peak Hours
    c.execute("SELECT STRFTIME('%H', timestamp) as hr, COUNT(*) as cnt FROM conversations WHERE hr IS NOT NULL GROUP BY hr ORDER BY cnt DESC LIMIT 1")
    peak_row = c.fetchone()
    if peak_row and peak_row[0] is not None:
        hr = int(peak_row[0])
        am_pm = "AM" if hr < 12 else "PM"
        hr_12 = hr if hr <= 12 else hr - 12
        hr_12 = 12 if hr_12 == 0 else hr_12
        peak_hour = f"{hr_12} {am_pm} - {hr_12+1 if hr_12 != 12 else 1} {am_pm}"
    else:
        peak_hour = "Not enough data"
        
    conn.close()
    return total_today, most_cat, avg_sat, peak_hour

def fetch_chart_data():
    """Queries dictionaries formatted natively for Streamlit charts"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Category Distribution
    c.execute("SELECT category, COUNT(*) FROM conversations GROUP BY category")
    categories = {row[0]: row[1] for row in c.fetchall()}
    
    # 7-Day Trend
    c.execute("SELECT DATE(timestamp), COUNT(*) FROM conversations WHERE DATE(timestamp) >= DATE('now', '-7 days') GROUP BY DATE(timestamp)")
    trend_raw = {row[0]: row[1] for row in c.fetchall()}
    
    # Fills empty days so the graph doesn't break
    trend_dict = {}
    for i in range(6, -1, -1):
        day = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        trend_dict[day] = trend_raw.get(day, 0)
        
    # Top 10 Questions
    c.execute("SELECT user_message, COUNT(*) as cnt FROM conversations GROUP BY user_message ORDER BY cnt DESC LIMIT 10")
    top_10 = [{"Question": row[0], "Count": row[1]} for row in c.fetchall()]
    
    # For CSV Export
    c.execute("SELECT * FROM conversations ORDER BY timestamp DESC")
    all_records = c.fetchall()
    
    conn.close()
    return categories, trend_dict, top_10, all_records

def render_admin_dashboard():
    """Renders the password protected Streamlit UI"""
    st.markdown("---")
    st.header("📊 Admin Analytics Dashboard")
    
    # Secure Password Protection
    if 'admin_unlocked' not in st.session_state:
        st.session_state.admin_unlocked = False

    if not st.session_state.admin_unlocked:
        pwd = st.text_input("Enter Admin Password:", type="password")
        if st.button("Unlock"):
            if pwd == ADMIN_PASSWORD:
                st.session_state.admin_unlocked = True
                st.rerun()
            else:
                st.error("Incorrect password")
        return # Stops rendering anything else if locked

    if st.button("🔒 Lock Dashboard"):
        st.session_state.admin_unlocked = False
        st.rerun()

    # --- Dash Render Flow ---
    total_today, most_cat, avg_sat, peak_hour = fetch_basic_stats()
    cat_dict, trend_dict, top_10, all_records = fetch_chart_data()

    # SECTION 1: Insight Metrics
    cols = st.columns(4)
    cols[0].metric("Queries Today", total_today)
    cols[1].metric("Top Topic", most_cat)
    cols[2].metric("Average Rating", f"{avg_sat} ⭐")
    cols[3].metric("Peak Traffic", peak_hour)

    # SECTION 2: Visual Charts
    colA, colB = st.columns(2)
    with colA:
        st.subheader("Traffic Over Last 7 Days")
        st.line_chart(trend_dict) # Maps python dict directly natively!
    with colB:
        st.subheader("Questions by Category")
        st.bar_chart(cat_dict) 
        
    # SECTION 3: Top Questions & Export
    col_table, col_export = st.columns([3, 1])
    with col_table:
        st.subheader("Top 10 Most Asked Questions")
        # Renders standard list of dictionaries beautifully into a table
        st.dataframe(top_10, width='stretch')
        
    with col_export:
        st.subheader("Data Export")
        st.write("Download the raw SQL data.")
        
        # Build CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Timestamp", "Message", "Bot Answer", "Category", "Rating"])
        for record in all_records:
            writer.writerow(record)
            
        st.download_button(
            label="📥 Download CSV",
            data=output.getvalue(),
            file_name="pesce_chat_data.csv",
            mime="text/csv",
            width='stretch'
        )
