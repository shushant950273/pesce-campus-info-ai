"""
PESCE Website Scraper Module
=============================
Scrapes live data from https://pesce.ac.in/ as a fallback
when the local JSON knowledge base can't answer a query.
Uses requests + BeautifulSoup for lightweight HTML parsing.
Results are cached per-session via Streamlit's @st.cache_resource.
"""

import re
import requests
from bs4 import BeautifulSoup
import streamlit as st
import difflib

# ==========================================
# CONFIGURATION
# ==========================================
BASE_URL = "https://pesce.ac.in"
HEADERS = {
    "User-Agent": "PESCE-CampusBot/1.0 (Student Project; +https://github.com/shushant950273/pesce-campus-info-ai)"
}
REQUEST_TIMEOUT = 8  # seconds

# Map of keywords → specific PESCE pages to scrape
PAGE_MAP = {
    "about": "/about-pes-college-of-engineering.php",
    "college": "/about-pes-college-of-engineering.php",
    "history": "/about-pes-college-of-engineering.php",
    "vision": "/about-pes-college-of-engineering.php",
    "mission": "/about-pes-college-of-engineering.php",
    "principal": "/principal.php",
    "vice principal": "/vice-principal.php",
    "founder": "/founder.php",
    "president": "/president.php",
    "placement": "/placement.php",
    "training": "/placement.php",
    "recruit": "/placement.php",
    "admission": "/admissions.php",
    "fee": "/admissions.php",
    "hostel": "/hostel.php",
    "library": "/library.php",
    "canteen": "/canteen.php",
    "dispensary": "/Dispensary.php",
    "medical": "/Dispensary.php",
    "sports": "/sports.php",
    "contact": "/contact-us.php",
    "cse": "/department-computer-science.php",
    "computer science": "/department-computer-science.php",
    "ai": "/department-artificial-intelligence-machine-learning.php",
    "machine learning": "/department-artificial-intelligence-machine-learning.php",
    "data science": "/department-data-science.php",
    "ece": "/dep-electrionics-communication-engg.php",
    "electronics": "/dep-electrionics-communication-engg.php",
    "eee": "/dep-electrical-electronics-engg.php",
    "electrical": "/dep-electrical-electronics-engg.php",
    "mechanical": "/dep-mechanical-engg.php",
    "civil": "/department-civil-engineering.php",
    "ise": "/dep-information-science-engg.php",
    "information science": "/dep-information-science-engg.php",
    "automobile": "/department-automobile-engineering.php",
    "robotics": "/dep-robotics.php",
    "mba": "/dep-master-business-administration.php",
    "mca": "/dep-master-computer-application.php",
    "phd": "/phd.php",
    "research": "/phd.php",
    "alumni": "/alumni.php",
    "exam": "/coe.php",
    "examination": "/coe.php",
    "academic office": "/academic-office.php",
    "news": "/",
    "event": "/",
    "announcement": "/announcement.php",
    "naac": "/naac.php",
    "nirf": "/nirf.php",
    "guest house": "/guest-house.php",
    "cooperative": "/Cooperative_Society.php",
    "bank": "/bank_atm.php",
    "atm": "/bank_atm.php",
}


def _fetch_page(url):
    """Fetch raw HTML from a URL with error handling."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        print(f"[WebScraper] Failed to fetch {url}: {e}")
        return None


def _extract_text(html):
    """
    Parse HTML and return clean, readable text.
    Strips navigation, scripts, styles, and footer boilerplate.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove noisy elements
    for tag in soup.find_all(["script", "style", "nav", "footer", "header", "noscript", "iframe"]):
        tag.decompose()

    # Try to find the main content area (common patterns on pesce.ac.in)
    main_content = (
        soup.find("div", class_="content-area")
        or soup.find("div", class_="main-content")
        or soup.find("section", class_="content")
        or soup.find("div", id="content")
        or soup.find("main")
        or soup.find("article")
    )

    target = main_content if main_content else soup.body if soup.body else soup

    # Extract text, preserving some structure
    lines = []
    for elem in target.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "td", "th", "span", "div"]):
        text = elem.get_text(separator=" ", strip=True)
        if text and len(text) > 3:  # Skip tiny fragments
            # Deduplicate consecutive identical lines
            if not lines or lines[-1] != text:
                lines.append(text)

    raw_text = "\n".join(lines)

    # Clean up excessive whitespace
    raw_text = re.sub(r'\n{3,}', '\n\n', raw_text)
    raw_text = re.sub(r'[ \t]{2,}', ' ', raw_text)

    return raw_text.strip()


def _pick_best_pages(query, top_n=2):
    """
    Given a user query, figure out which PESCE pages are most relevant.
    Returns a list of (keyword, path) tuples.
    """
    query_lower = query.lower()
    scored = []

    for keyword, path in PAGE_MAP.items():
        # Direct substring match
        if keyword in query_lower:
            scored.append((keyword, path, 1.0))
        else:
            # Fuzzy match each query word against the keyword
            for word in query_lower.split():
                matches = difflib.get_close_matches(word, [keyword], n=1, cutoff=0.75)
                if matches:
                    scored.append((keyword, path, 0.7))
                    break

    # Sort by score descending, deduplicate paths
    scored.sort(key=lambda x: x[2], reverse=True)
    seen_paths = set()
    results = []
    for kw, path, score in scored:
        if path not in seen_paths and len(results) < top_n:
            seen_paths.add(path)
            results.append((kw, path))

    # Default fallback: scrape the homepage
    if not results:
        results = [("general", "/")]

    return results


def _summarize_text(text, query, max_chars=1500):
    """
    Extract the most relevant portion of scraped text for the query.
    Returns a trimmed, focused snippet.
    """
    if not text:
        return ""

    query_words = [w.lower() for w in query.split() if len(w) > 2]
    paragraphs = [p.strip() for p in text.split("\n") if p.strip() and len(p.strip()) > 15]

    if not paragraphs:
        return text[:max_chars]

    # Score each paragraph by relevance
    scored_paras = []
    for para in paragraphs:
        para_lower = para.lower()
        score = sum(1 for word in query_words if word in para_lower)
        scored_paras.append((score, para))

    # Sort by relevance, take top paragraphs
    scored_paras.sort(key=lambda x: x[0], reverse=True)

    result = []
    char_count = 0
    for score, para in scored_paras:
        if char_count + len(para) > max_chars:
            break
        result.append(para)
        char_count += len(para)

    return "\n\n".join(result) if result else text[:max_chars]


@st.cache_resource(ttl=1800)  # Cache for 30 minutes
def _cached_fetch(url):
    """Session-cached page fetch to avoid redundant network calls."""
    html = _fetch_page(url)
    if html:
        return _extract_text(html)
    return None


class PESCEScraper:
    """
    Web scraper for pesce.ac.in.
    
    Usage:
        scraper = PESCEScraper()
        answer, source_url = scraper.search("Tell me about the CSE department")
    """

    def search(self, query):
        """
        Search the PESCE website for information relevant to the query.
        
        Returns:
            tuple: (answer_text, source_label) or (None, None) if nothing found.
        """
        pages = _pick_best_pages(query)
        all_text = []
        source_labels = []

        for keyword, path in pages:
            url = BASE_URL + path
            text = _cached_fetch(url)
            if text:
                all_text.append(text)
                # Create a clean source label
                page_name = path.replace("/", "").replace(".php", "").replace("-", " ").replace("_", " ").title()
                source_labels.append(f"[{page_name}]({url})")

        if not all_text:
            return None, None

        combined = "\n\n---\n\n".join(all_text)
        summary = _summarize_text(combined, query, max_chars=1500)

        if not summary or len(summary) < 20:
            return None, None

        source_label = "PESCE Website: " + ", ".join(source_labels)
        return summary, source_label


# ==========================================
# STANDALONE TEST
# ==========================================
if __name__ == "__main__":
    print("=" * 60)
    print("PESCE Web Scraper - Standalone Test")
    print("=" * 60)

    # Remove Streamlit cache decorator for standalone testing
    test_queries = [
        "Tell me about CSE department",
        "What are the placement statistics?",
        "Hostel facilities",
        "Who is the principal?",
    ]

    for q in test_queries:
        print(f"\n📝 Query: {q}")
        pages = _pick_best_pages(q)
        for kw, path in pages:
            url = BASE_URL + path
            html = _fetch_page(url)
            if html:
                text = _extract_text(html)
                summary = _summarize_text(text, q, max_chars=500)
                print(f"   🌐 Page: {url}")
                print(f"   📄 Result ({len(summary)} chars): {summary[:200]}...")
            else:
                print(f"   ❌ Failed to fetch {url}")
        print("-" * 60)
