"""
PESCE Website Deep Scraper Module
===================================
Scrapes live data from https://pesce.ac.in/ including:
  - Faculty lists (name, designation, department)
  - Principal / Vice Principal / HOD details
  - Warden information
  - Department-specific content
  - Announcements and news

Uses requests + BeautifulSoup for lightweight HTML parsing.
Results are cached per-session (30 min TTL) via Streamlit.
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
REQUEST_TIMEOUT = 10  # seconds

# ==========================================
# DEPARTMENT URL MAP (Complete)
# ==========================================
DEPARTMENT_PAGES = {
    "cse": "/department-computer-science.php",
    "computer science": "/department-computer-science.php",
    "cs": "/department-computer-science.php",
    "ai": "/department-artificial-intelligence-machine-learning.php",
    "ai ml": "/department-artificial-intelligence-machine-learning.php",
    "aiml": "/department-artificial-intelligence-machine-learning.php",
    "machine learning": "/department-artificial-intelligence-machine-learning.php",
    "artificial intelligence": "/department-artificial-intelligence-machine-learning.php",
    "data science": "/department-data-science.php",

    "csbs": "/dep-cs-business-system.php",
    "business system": "/dep-cs-business-system.php",
    "ece": "/dep-electrionics-communication-engg.php",
    "electronics communication": "/dep-electrionics-communication-engg.php",

    "eee": "/dep-electrical-electronics-engg.php",
    "electrical": "/dep-electrical-electronics-engg.php",

    "mechanical": "/dep-mechanical-engg.php",
    "mech": "/dep-mechanical-engg.php",

    "civil": "/department-civil-engineering.php",

    "ise": "/dep-information-science-engg.php",
    "information science": "/dep-information-science-engg.php",

    "automobile": "/department-automobile-engineering.php",
    "auto": "/department-automobile-engineering.php",

    "robotics": "/dep-robotics.php",
    "rai": "/dep-robotics.php",
    "industrial production": "/dep-industrial-production-engg.php",
    "ipe": "/dep-industrial-production-engg.php",

    "vlsi": "/dep-electrionics-communication-engg-VLSI.php",
    "mba": "/dep-master-business-administration.php",
    "mca": "/dep-master-computer-application.php",
    "mathematics": "/dep-math.php",
    "math": "/dep-math.php",
    "physics": "/dep-physics.php",
    "chemistry": "/dep-chem.php",
}

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
    "warden": "/hostel.php",
    "library": "/library.php",
    "canteen": "/canteen.php",
    "dispensary": "/Dispensary.php",
    "medical": "/Dispensary.php",
    "doctor": "/Dispensary.php",
    "sports": "/sports.php",
    "contact": "/contact-us.php",
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
    "phd": "/phd.php",
    "research": "/phd.php",
    "governing": "/governing_body.php",
    "career": "/career.php",
    "industry": "/IIIC.php",
    "iiic": "/IIIC.php",
    "secure campus": "/secure-campus.php",
    "security": "/secure-campus.php",
    "cctv": "/secure-campus.php",
    "rti": "/rti.php",
    "mandatory disclosure": "/footer-mandatory-disclosure.php",
    "jnana cauvery": "/jnana-cauvery.php",
    "idea lab": "/aicte_Idea_lab.php",
    "aicte": "/footer-aicte.php",
    "professional bodies": "/professional-bodies.php",
    "committees": "/committees.php",
    "grievance": "/committees.php",
    "download": "/footer-download.php",
    "media": "/in-media.php",
    "erp": "https://pesgroup.dhi-edu.com/",
    "counselling": "/placement.php",
    "counsellor": "/placement.php",
    "regulation": "/academic-office.php",
    "curriculum": "/academic-office.php",
    "calendar": "/academic-office.php",
    "graduation": "/academic-office.php",
    "nss": "/nss.php",
}

# Merge department pages into page map
PAGE_MAP.update(DEPARTMENT_PAGES)


# ==========================================
# RAW FETCHING
# ==========================================
def _fetch_page(url):
    """Fetch raw HTML from a URL with error handling."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        print(f"[WebScraper] Failed to fetch {url}: {e}")
        return None


# ==========================================
# FACULTY EXTRACTION (Deep Scrape)
# ==========================================
def _extract_faculty_from_html(html):
    """
    Extract faculty information (name + designation) from a department page.
    
    PESCE site patterns:
    1. Link cards: <a>Name\nDesignation\nView more</a> with h3/h4 siblings
    2. Consecutive <h3>Name</h3> <h4>Designation</h4> pairs
    
    Returns a list of dicts: [{"name": "...", "designation": "..."}]
    """
    soup = BeautifulSoup(html, "html.parser")
    faculty_list = []
    seen_names = set()

    # Known designation keywords
    DESIG_KEYWORDS = [
        "professor", "hod", "head", "assistant", "associate",
        "lecturer", "instructor", "dean", "director"
    ]

    # Known section headers and noise to skip
    SKIP_WORDS = [
        "contact", "quick link", "general", "happenings", "explore",
        "welcome", "choose", "announcements", "funded", "academic",
        "syllabus", "virtual", "links for", "about nba", "congratulations",
        "overview", "tech premiere", "induction", "proud moment",
        "webinar", "hearty", "energy", "technical session",
        "mongodb", "technical talk", "pesce alumni", "professional",
        "total intake", "program type", "duration", "vision", "mission",
        "program educational", "program outcomes", "program specific",
        "engineering knowledge", "problem analysis", "design/development",
        "bachelor of engineering", "ug program", "pg program",
        "undergraduate", "postgraduate", "doctoral", "basic science",
        "funded project", "happenings @", "research program",
        "iste", "related links", "ieee", "csi chapter", "acm",
        "non teaching", "teaching faculty"
    ]

    def _is_designation(text):
        return any(kw in text.lower() for kw in DESIG_KEYWORDS)

    def _is_noise(text):
        t = text.lower()
        return any(skip in t for skip in SKIP_WORDS) or len(text) > 80 or len(text) < 3

    # ---- Strategy 1: Parse consecutive h3 (name) + h4 (designation) pairs ----
    # This is the dominant pattern on pesce.ac.in
    all_h3 = soup.find_all("h3")
    for h3 in all_h3:
        name = h3.get_text(strip=True)
        name = re.sub(r'(View more|Read more|Click here)', '', name, flags=re.I).strip()
        
        if not name or _is_noise(name):
            continue

        # Look for designation in the next h4
        designation = ""
        next_elem = h3.find_next_sibling()
        if next_elem and next_elem.name == "h4":
            desig_text = next_elem.get_text(strip=True)
            if _is_designation(desig_text):
                designation = desig_text

        # Also try find_next (not just sibling)
        if not designation:
            h4 = h3.find_next("h4")
            if h4:
                desig_text = h4.get_text(strip=True)
                if _is_designation(desig_text):
                    # Make sure this h4 is close to our h3 (not far away)
                    designation = desig_text

        if designation and name not in seen_names:
            seen_names.add(name)
            faculty_list.append({"name": name, "designation": designation})

    # ---- Strategy 2: Parse link cards with multi-line text ----
    # Pattern: <a href="...">Name\nDesignation\nView more</a>
    if not faculty_list:
        for link in soup.find_all("a"):
            text = link.get_text(separator="\n", strip=True)
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            
            if len(lines) >= 2:
                # Filter out "View more" lines
                clean_lines = [l for l in lines if l.lower() not in ["view more", "read more", "click here"]]
                if len(clean_lines) >= 2:
                    potential_name = clean_lines[0]
                    potential_desig = clean_lines[1]
                    
                    if _is_designation(potential_desig) and not _is_noise(potential_name):
                        if potential_name not in seen_names:
                            seen_names.add(potential_name)
                            faculty_list.append({"name": potential_name, "designation": potential_desig})

    return faculty_list


def _format_faculty_list(faculty_list, department_name=""):
    """Format faculty list into readable markdown text."""
    if not faculty_list:
        return ""

    header = f"**Faculty of {department_name} Department:**\n\n" if department_name else "**Faculty Members:**\n\n"
    lines = []

    # Group by designation
    hods = [f for f in faculty_list if "hod" in f["designation"].lower() or "head" in f["designation"].lower()]
    professors = [f for f in faculty_list if "professor" in f["designation"].lower() and f not in hods]
    others = [f for f in faculty_list if f not in hods and f not in professors]

    if hods:
        lines.append("🏛️ **Head of Department:**")
        for f in hods:
            lines.append(f"  - **{f['name']}** — {f['designation']}")
        lines.append("")

    if professors:
        lines.append("👨‍🏫 **Teaching Faculty:**")
        for f in professors:
            lines.append(f"  - **{f['name']}** — {f['designation']}")
        lines.append("")

    if others:
        lines.append("👤 **Other Staff:**")
        for f in others:
            lines.append(f"  - **{f['name']}** — {f['designation']}")

    return header + "\n".join(lines)


# ==========================================
# GENERAL TEXT EXTRACTION
# ==========================================
def _extract_text(html):
    """
    Parse HTML and return clean, readable text.
    Strips navigation, scripts, styles, and footer boilerplate.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove noisy elements
    for tag in soup.find_all(["script", "style", "nav", "footer", "header", "noscript", "iframe"]):
        tag.decompose()

    # Try to find the main content area
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
        if text and len(text) > 3:
            if not lines or lines[-1] != text:
                lines.append(text)

    raw_text = "\n".join(lines)
    raw_text = re.sub(r'\n{3,}', '\n\n', raw_text)
    raw_text = re.sub(r'[ \t]{2,}', ' ', raw_text)

    return raw_text.strip()


# ==========================================
# INTELLIGENT PAGE PICKER
# ==========================================
def _detect_department(query):
    """
    Check if the query is asking about a specific department.
    Returns (dept_keyword, dept_url_path) or (None, None).
    
    Uses word-boundary matching for short keywords (<=3 chars) to avoid
    false positives like "is" matching the English word "is".
    Prioritizes longer keyword matches for accuracy.
    """
    q = query.lower()
    matches = []

    for keyword, path in DEPARTMENT_PAGES.items():
        if len(keyword) <= 3:
            # Short keywords: require word boundary match
            # e.g., "ise" should match "ise department" but NOT "advise"
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, q):
                matches.append((keyword, path, len(keyword)))
        else:
            # Longer keywords: substring match is fine
            if keyword in q:
                matches.append((keyword, path, len(keyword)))

    if matches:
        # Prefer the longest keyword match for accuracy
        matches.sort(key=lambda x: x[2], reverse=True)
        return matches[0][0], matches[0][1]

    # Fuzzy match (only for words >= 4 chars to avoid false positives)
    for word in q.split():
        if len(word) < 4:
            continue
        for keyword, path in DEPARTMENT_PAGES.items():
            if len(keyword) < 4:
                continue
            fmatches = difflib.get_close_matches(word, [keyword], n=1, cutoff=0.80)
            if fmatches:
                return keyword, path

    return None, None


def _is_faculty_query(query):
    """Check if the query is asking about faculty/staff/HOD/warden/principal."""
    q = query.lower()
    faculty_keywords = [
        "faculty", "professor", "teacher", "staff", "hod",
        "head of department", "warden", "principal", "vice principal",
        "who teaches", "who is", "doctor", "dr.", "sir", "madam",
        "teaching", "non teaching", "instructor", "lecturer"
    ]
    return any(kw in q for kw in faculty_keywords)


def _pick_best_pages(query, top_n=2):
    """
    Given a user query, figure out which PESCE pages are most relevant.
    Returns a list of (keyword, path) tuples.
    """
    query_lower = query.lower()
    scored = []

    for keyword, path in PAGE_MAP.items():
        if keyword in query_lower:
            scored.append((keyword, path, 1.0))
        else:
            for word in query_lower.split():
                matches = difflib.get_close_matches(word, [keyword], n=1, cutoff=0.75)
                if matches:
                    scored.append((keyword, path, 0.7))
                    break

    scored.sort(key=lambda x: x[2], reverse=True)
    seen_paths = set()
    results = []
    for kw, path, score in scored:
        if path not in seen_paths and len(results) < top_n:
            seen_paths.add(path)
            results.append((kw, path))

    if not results:
        results = [("general", "/")]

    return results


def _summarize_text(text, query, max_chars=2500):
    """
    Extract the most relevant portion of scraped text for the query.
    Increased max_chars to allow more comprehensive context for the LLM.
    """
    if not text:
        return ""

    query_words = [w.lower() for w in query.split() if len(w) > 2]
    paragraphs = [p.strip() for p in text.split("\n") if p.strip() and len(p.strip()) > 10]

    if not paragraphs:
        return text[:max_chars]

    scored_paras = []
    for para in paragraphs:
        para_lower = para.lower()
        score = sum(1 for word in query_words if word in para_lower)
        # Bonus for faculty-related content
        if any(kw in para_lower for kw in ["professor", "hod", "faculty", "warden", "principal"]):
            score += 2
        scored_paras.append((score, para))

    scored_paras.sort(key=lambda x: x[0], reverse=True)

    result = []
    char_count = 0
    for score, para in scored_paras:
        if char_count + len(para) > max_chars:
            break
        result.append(para)
        char_count += len(para)

    return "\n\n".join(result) if result else text[:max_chars]


# ==========================================
# SESSION-CACHED FETCH
# ==========================================
@st.cache_resource(ttl=1800)  # Cache for 30 minutes
def _cached_fetch_text(url):
    """Session-cached text extraction."""
    html = _fetch_page(url)
    if html:
        return _extract_text(html)
    return None


@st.cache_resource(ttl=1800)
def _cached_fetch_faculty(url):
    """Session-cached faculty extraction."""
    html = _fetch_page(url)
    if html:
        return _extract_faculty_from_html(html)
    return []


@st.cache_resource(ttl=1800)
def _cached_fetch_raw(url):
    """Session-cached raw HTML fetch (for combined extraction)."""
    return _fetch_page(url)


# ==========================================
# MAIN SCRAPER CLASS
# ==========================================
class PESCEScraper:
    """
    Deep web scraper for pesce.ac.in.

    Handles:
      - Faculty queries → extracts and formats faculty lists
      - Department queries → deep scrapes department content
      - General queries → scrapes relevant pages and summarizes

    Usage:
        scraper = PESCEScraper()
        answer, source = scraper.search("Who are the faculty in ISE department?")
    """

    def search(self, query):
        """
        Search the PESCE website for information relevant to the query.

        Returns:
            tuple: (answer_text, source_label) or (None, None) if nothing found.
        """
        is_faculty = _is_faculty_query(query)
        dept_keyword, dept_path = _detect_department(query)

        # ===== CASE 1: Faculty query for a specific department =====
        if is_faculty and dept_path:
            return self._handle_faculty_query(query, dept_keyword, dept_path)

        # ===== CASE 2: Department query (general info) =====
        if dept_path:
            return self._handle_department_query(query, dept_keyword, dept_path)

        # ===== CASE 3: General query (principal, hostel, warden, etc.) =====
        return self._handle_general_query(query)

    def _handle_faculty_query(self, query, dept_keyword, dept_path):
        """Deep scrape faculty list from a department page."""
        url = BASE_URL + dept_path
        html = _cached_fetch_raw(url)
        if not html:
            return None, None

        faculty = _extract_faculty_from_html(html)
        dept_name = dept_keyword.upper() if len(dept_keyword) <= 4 else dept_keyword.title()

        if faculty:
            formatted = _format_faculty_list(faculty, dept_name)
            # Also get general department text for additional context
            general_text = _extract_text(html)
            summary = _summarize_text(general_text, query, max_chars=1000)
            combined = formatted + "\n\n---\n\n" + summary if summary else formatted
            source = f"PESCE Website: [{dept_name} Dept]({url})"
            return combined, source

        # Fallback: just return text
        text = _extract_text(html)
        summary = _summarize_text(text, query, max_chars=2500)
        if summary and len(summary) > 20:
            return summary, f"PESCE Website: [{dept_name}]({url})"
        return None, None

    def _handle_department_query(self, query, dept_keyword, dept_path):
        """Deep scrape department page for comprehensive info."""
        url = BASE_URL + dept_path
        html = _cached_fetch_raw(url)
        if not html:
            return None, None

        # Get both text and faculty
        text = _extract_text(html)
        faculty = _extract_faculty_from_html(html)
        dept_name = dept_keyword.upper() if len(dept_keyword) <= 4 else dept_keyword.title()

        parts = []
        summary = _summarize_text(text, query, max_chars=2000)
        if summary:
            parts.append(summary)

        if faculty:
            parts.append(_format_faculty_list(faculty, dept_name))

        if parts:
            combined = "\n\n---\n\n".join(parts)
            return combined, f"PESCE Website: [{dept_name} Dept]({url})"

        return None, None

    def _handle_general_query(self, query):
        """Scrape relevant pages based on keyword matching."""
        pages = _pick_best_pages(query, top_n=2)
        all_text = []
        source_labels = []
        all_faculty = []

        for keyword, path in pages:
            url = BASE_URL + path
            html = _cached_fetch_raw(url)
            if not html:
                continue

            text = _extract_text(html)
            if text:
                all_text.append(text)

            # If it's a people-related query, also try faculty extraction
            if _is_faculty_query(query):
                faculty = _extract_faculty_from_html(html)
                if faculty:
                    page_name = keyword.title()
                    all_faculty.append(_format_faculty_list(faculty, page_name))

            page_name = path.replace("/", "").replace(".php", "").replace("-", " ").replace("_", " ").title()
            source_labels.append(f"[{page_name}]({url})")

        if not all_text and not all_faculty:
            return None, None

        parts = []
        if all_text:
            combined_text = "\n\n---\n\n".join(all_text)
            summary = _summarize_text(combined_text, query, max_chars=2500)
            if summary:
                parts.append(summary)

        if all_faculty:
            parts.extend(all_faculty)

        if not parts:
            return None, None

        result = "\n\n---\n\n".join(parts)
        if len(result) < 20:
            return None, None

        source_label = "PESCE Website: " + ", ".join(source_labels)
        return result, source_label


# ==========================================
# STANDALONE TEST
# ==========================================
if __name__ == "__main__":
    print("=" * 60)
    print("PESCE Deep Web Scraper - Standalone Test")
    print("=" * 60)

    test_queries = [
        "Who are the faculty in ISE department?",
        "Who is the HOD of CSE?",
        "Tell me about placements",
        "Who is the principal?",
        "Hostel warden details",
    ]

    for q in test_queries:
        print(f"\n📝 Query: {q}")
        dept_kw, dept_path = _detect_department(q)
        is_fac = _is_faculty_query(q)
        print(f"   Dept detected: {dept_kw} | Faculty query: {is_fac}")

        if dept_path:
            url = BASE_URL + dept_path
            html = _fetch_page(url)
            if html:
                faculty = _extract_faculty_from_html(html)
                if faculty:
                    print(f"   ✅ Found {len(faculty)} faculty members:")
                    for f in faculty[:5]:
                        print(f"      - {f['name']} ({f['designation']})")
                    if len(faculty) > 5:
                        print(f"      ... and {len(faculty) - 5} more")
                else:
                    print("   ⚠️ No faculty extracted")
        else:
            pages = _pick_best_pages(q)
            for kw, path in pages:
                url = BASE_URL + path
                html = _fetch_page(url)
                if html:
                    text = _extract_text(html)
                    summary = _summarize_text(text, q, max_chars=300)
                    print(f"   🌐 {url}: {summary[:150]}...")
        print("-" * 60)
