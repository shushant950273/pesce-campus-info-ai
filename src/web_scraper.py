"""
PESCE Web Scraper - Complete website data extraction tool.
Extracts ALL information from https://pesce.ac.in/ including academics,
placements, facilities, admissions, contact info, and more.

Usage:
    python src/web_scraper.py
    
Output:
    data/processed/pesce_data.json
"""

import requests
from bs4 import BeautifulSoup
import json
import os
import re
import time
import logging
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# ─── Logging Setup ───────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("pesce_scraper")

# ─── Constants ───────────────────────────────────────────────────────────────
BASE_URL = "https://pesce.ac.in"
REQUEST_TIMEOUT = 15
RATE_LIMIT_DELAY = 0.3  # seconds between requests
MAX_WORKERS = 4  # concurrent threads
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# All target pages discovered from the site navigation
TARGET_PAGES = {
    # ── About ──
    "about": "/about-pes-college-of-engineering.php",
    "founder": "/founder.php",
    "president": "/president.php",
    "principal": "/principal.php",
    "vice_principal": "/vice-principal.php",
    "governing_body": "/governing_body.php",
    "other_pet_institutions": "/other-pet-institution.php",
    # ── Academics ──
    "academic_office": "/academic-office.php",
    "coe": "/coe.php",
    "admissions": "/admissions.php",
    # ── UG Departments ──
    "dept_automobile": "/department-automobile-engineering.php",
    "dept_civil": "/department-civil-engineering.php",
    "dept_cse": "/department-computer-science.php",
    "dept_aiml": "/department-artificial-intelligence-machine-learning.php",
    "dept_ds": "/department-data-science.php",
    "dept_csbs": "/dep-cs-business-system.php",
    "dept_ece": "/dep-electrionics-communication-engg.php",
    "dept_eee": "/dep-electrical-electronics-engg.php",
    "dept_ipe": "/dep-industrial-production-engg.php",
    "dept_ise": "/dep-information-science-engg.php",
    "dept_mech": "/dep-mechanical-engg.php",
    "dept_robotics": "/dep-robotics.php",
    "dept_vlsi": "/dep-electrionics-communication-engg-VLSI.php",
    # ── PG / Others ──
    "dept_mca": "/dep-master-computer-application.php",
    "dept_mba": "/dep-master-business-administration.php",
    "phd": "/phd.php",
    # ── Basic Science ──
    "dept_math": "/dep-math.php",
    "dept_physics": "/dep-physics.php",
    "dept_chemistry": "/dep-chem.php",
    # ── Placements ──
    "placements": "/placement.php",
    # ── Facilities ──
    "library": "/library.php",
    "bank_atm": "/bank_atm.php",
    "hostel": "/hostel.php",
    "canteen": "/canteen.php",
    "dispensary": "/Dispensary.php",
    "cooperative_society": "/Cooperative_Society.php",
    "sports": "/sports.php",
    "secure_campus": "/secure-campus.php",
    "guest_house": "/guest-house.php",
    # ── Alumni ──
    "alumni": "/alumni.php",
    "distinguished_alumni": "/distinguished-alumni.php",
    "alumni_chapters": "/alumni_chapters.php",
    "alumni_news": "/alumni_news_gallery.php",
    # ── Other ──
    "contact": "/contact-us.php",
    "nirf": "/nirf.php",
    "naac": "/naac.php",
    "iic": "/iic.php",
    "jnana_cauvery": "/jnana-cauvery.php",
    "announcements": "/announcement.php",
}


# ═════════════════════════════════════════════════════════════════════════════
# Helper utilities
# ═════════════════════════════════════════════════════════════════════════════

def clean_text(text: str) -> str:
    """Remove excess whitespace and normalise a string."""
    if not text:
        return ""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def safe_get(url: str, session: requests.Session) -> BeautifulSoup | None:
    """Fetch a page and return its BeautifulSoup, or None on failure."""
    try:
        resp = session.get(url, timeout=REQUEST_TIMEOUT, headers=HEADERS)
        resp.raise_for_status()
        return BeautifulSoup(resp.content, "lxml")
    except requests.exceptions.Timeout:
        log.warning("Timeout: %s", url)
    except requests.exceptions.ConnectionError:
        log.warning("Connection error: %s", url)
    except requests.exceptions.HTTPError as exc:
        log.warning("HTTP %s: %s", exc.response.status_code, url)
    except Exception as exc:
        log.error("Unexpected error for %s: %s", url, exc)
    return None


# ═════════════════════════════════════════════════════════════════════════════
# Extractors – specialised functions for each section
# ═════════════════════════════════════════════════════════════════════════════

def extract_tables(soup: BeautifulSoup) -> list[dict]:
    """Extract all HTML tables into list-of-dicts."""
    results = []
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        headers = [clean_text(th.get_text()) for th in rows[0].find_all(["th", "td"])]
        for row in rows[1:]:
            cells = [clean_text(td.get_text()) for td in row.find_all("td")]
            if cells and any(cells):
                entry = {}
                for i, cell in enumerate(cells):
                    key = headers[i] if i < len(headers) and headers[i] else f"col_{i}"
                    entry[key] = cell
                results.append(entry)
    return results


def extract_links(soup: BeautifulSoup, base: str) -> list[dict]:
    """Extract meaningful links from the page."""
    links = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href = urljoin(base, a["href"])
        text = clean_text(a.get_text())
        if href not in seen and text and "pesce.ac.in" in href:
            seen.add(href)
            links.append({"text": text, "url": href})
    return links


def extract_images(soup: BeautifulSoup, base: str) -> list[dict]:
    """Extract image URLs with alt text."""
    images = []
    seen = set()
    for img in soup.find_all("img", src=True):
        src = urljoin(base, img["src"])
        if src not in seen:
            seen.add(src)
            alt = img.get("alt", "")
            images.append({"src": src, "alt": clean_text(alt)})
    return images


def extract_lists(soup: BeautifulSoup) -> list[str]:
    """Extract all list items as flat strings."""
    items = []
    for li in soup.find_all("li"):
        text = clean_text(li.get_text())
        if text and len(text) > 3:
            items.append(text)
    return list(dict.fromkeys(items))  # deduplicate, preserve order


def extract_headings(soup: BeautifulSoup) -> dict:
    """Extract headings grouped by level."""
    headings = {}
    for level in range(1, 7):
        tag = f"h{level}"
        found = [clean_text(h.get_text()) for h in soup.find_all(tag)]
        found = [h for h in found if h]
        if found:
            headings[tag] = list(dict.fromkeys(found))
    return headings


def extract_paragraphs(soup: BeautifulSoup) -> list[str]:
    """Extract paragraph text, skipping short / junk paragraphs."""
    paras = []
    for p in soup.find_all("p"):
        text = clean_text(p.get_text())
        if text and len(text) > 15:
            paras.append(text)
    return list(dict.fromkeys(paras))


def extract_contact_info(soup: BeautifulSoup) -> dict:
    """Extract phone numbers, emails, and addresses from page text."""
    full_text = soup.get_text()
    phones = list(set(re.findall(r"[\+]?[\d\s\-]{7,15}", full_text)))
    phones = [p.strip() for p in phones if len(p.strip()) >= 10]
    emails = list(set(re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", full_text)))
    return {"phones": phones[:20], "emails": emails[:10]}


def extract_faculty(soup: BeautifulSoup) -> list[dict]:
    """Extract faculty cards / lists from department pages."""
    faculty = []
    # Common patterns: cards with name + designation
    for card in soup.find_all(["div", "li"], class_=re.compile(r"faculty|team|staff|member|card", re.I)):
        name_tag = card.find(["h3", "h4", "h5", "strong", "b"])
        name = clean_text(name_tag.get_text()) if name_tag else ""
        rest = clean_text(card.get_text())
        if name and len(name) > 2:
            faculty.append({"name": name, "details": rest})
    # Also try tables that look like faculty lists
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        for row in rows:
            cells = [clean_text(td.get_text()) for td in row.find_all("td")]
            if len(cells) >= 2 and any("prof" in c.lower() or "dr" in c.lower() or "hod" in c.lower() for c in cells):
                faculty.append({"name": cells[0] if cells[0] else cells[1], "details": " | ".join(cells)})
    return faculty


def extract_page_content(soup: BeautifulSoup, url: str) -> dict:
    """Generic full-page content extraction."""
    # Remove script/style/noscript to get cleaner body text
    for tag in soup.find_all(["script", "style", "noscript"]):
        tag.decompose()

    main = soup.body or soup

    data = {
        "url": url,
        "title": clean_text(soup.title.string) if soup.title else "",
        "headings": extract_headings(main),
        "paragraphs": extract_paragraphs(main),
        "lists": extract_lists(main),
        "tables": extract_tables(main),
        "contact_info": extract_contact_info(main),
        "faculty": extract_faculty(main),
        "images": extract_images(main, url),
    }
    # Full body text for downstream NLP
    data["full_text"] = clean_text(main.get_text(separator="\n", strip=True))
    return data


# ═════════════════════════════════════════════════════════════════════════════
# Homepage-specific extractor
# ═════════════════════════════════════════════════════════════════════════════

def extract_homepage(soup: BeautifulSoup) -> dict:
    """Parse the PESCE homepage for stats, programmes, and news."""
    text = soup.get_text()

    # Key statistics (scraped from the counter section)
    stats = {}
    stat_patterns = {
        "students": r"(\d[\d,]+)\+?\s*(?:Students|Student)",
        "placements": r"(\d[\d,]+)\+?\s*Placements?",
        "phd_awarded": r"(\d[\d,]+)\+?\s*(?:Awarded\s*Ph\.?D|Ph\.?D)",
        "publications": r"(\d[\d,]+)\+?\s*(?:Plus\s*)?Publications?",
    }
    for key, pat in stat_patterns.items():
        m = re.search(pat, text, re.I)
        if m:
            stats[key] = m.group(1).replace(",", "")

    # News / happenings
    news = []
    for card_text in re.findall(
        r"(\d{1,2}\s+\w+\s+\d{4})\s*\n\s*###\s*(.*?)(?=\n####|\n##|\Z)",
        text, re.S
    ):
        news.append({"date": card_text[0].strip(), "title": card_text[1].strip()})

    return {
        "college_name": "P.E.S. College of Engineering, Mandya",
        "tagline": "Top Engineering College in Karnataka",
        "established": 1962,
        "affiliation": "Visvesvaraya Technological University (VTU), Belagavi",
        "autonomy": "Autonomous since 2008-09 (UGC)",
        "accreditation": ["AICTE", "NBA", "NAAC A Grade"],
        "statistics": stats,
        "recent_news": news[:15],
    }


# ═════════════════════════════════════════════════════════════════════════════
# Main Scraper Class
# ═════════════════════════════════════════════════════════════════════════════

class PESCEScraper:
    """Complete web scraper for https://pesce.ac.in/"""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.scraped: dict = {}
        self._request_count = 0

    # ── Internal helpers ─────────────────────────────────────────────────

    def _get_soup(self, path: str) -> BeautifulSoup | None:
        url = f"{self.base_url}{path}" if path.startswith("/") else path
        self._request_count += 1
        time.sleep(RATE_LIMIT_DELAY)
        return safe_get(url, self.session)

    def _scrape_page(self, key: str, path: str) -> tuple[str, dict | None]:
        """Scrape a single page and return (key, data)."""
        url = f"{self.base_url}{path}"
        log.info("Scraping [%s] → %s", key, url)
        soup = self._get_soup(path)
        if not soup:
            return key, None
        return key, extract_page_content(soup, url)

    # ── Public API ───────────────────────────────────────────────────────

    def scrape_homepage(self) -> dict:
        """Scrape the homepage for overview data."""
        log.info("Scraping homepage …")
        soup = self._get_soup("/")
        if not soup:
            return {}
        return extract_homepage(soup)

    def scrape_all_pages(self) -> dict:
        """Scrape every target page using a thread pool."""
        results = {}
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = {
                pool.submit(self._scrape_page, key, path): key
                for key, path in TARGET_PAGES.items()
            }
            for future in as_completed(futures):
                key, data = future.result()
                if data:
                    results[key] = data
                    log.info("  ✓ %s (%d chars)", key, len(data.get("full_text", "")))
                else:
                    log.warning("  ✗ %s — skipped (no data)", key)
        return results

    def build_structured_data(self, pages: dict) -> dict:
        """Organise raw page data into a clean, structured JSON."""
        structured = {}

        # ── Homepage ──
        structured["homepage"] = self.scraped.get("homepage", {})

        # ── About Section ──
        about_keys = ["about", "founder", "president", "principal",
                       "vice_principal", "governing_body", "other_pet_institutions",
                       "jnana_cauvery"]
        structured["about"] = {k: pages[k] for k in about_keys if k in pages}

        # ── Academics ──
        academic_keys = ["academic_office", "coe", "announcements"]
        structured["academics"] = {
            "office": {k: pages[k] for k in academic_keys if k in pages},
        }

        # ── Departments (UG) ──
        ug_keys = [k for k in pages if k.startswith("dept_") and k not in
                   ("dept_mca", "dept_mba", "dept_math", "dept_physics", "dept_chemistry")]
        structured["departments_ug"] = {k: pages[k] for k in ug_keys}

        # ── Departments (PG / Others) ──
        pg_keys = ["dept_mca", "dept_mba"]
        structured["departments_pg"] = {k: pages[k] for k in pg_keys if k in pages}

        # ── Basic Science ──
        sci_keys = ["dept_math", "dept_physics", "dept_chemistry"]
        structured["basic_science"] = {k: pages[k] for k in sci_keys if k in pages}

        # ── PhD / Research ──
        if "phd" in pages:
            structured["research"] = pages["phd"]

        # ── Placements ──
        if "placements" in pages:
            structured["placements"] = pages["placements"]

        # ── Admissions ──
        if "admissions" in pages:
            structured["admissions"] = pages["admissions"]

        # ── Facilities ──
        fac_keys = ["library", "bank_atm", "hostel", "canteen", "dispensary",
                     "cooperative_society", "sports", "secure_campus", "guest_house"]
        structured["facilities"] = {k: pages[k] for k in fac_keys if k in pages}

        # ── Alumni ──
        alumni_keys = ["alumni", "distinguished_alumni", "alumni_chapters", "alumni_news"]
        structured["alumni"] = {k: pages[k] for k in alumni_keys if k in pages}

        # ── Contact ──
        if "contact" in pages:
            structured["contact"] = pages["contact"]

        # ── Accreditation / Rankings ──
        acc_keys = ["nirf", "naac", "iic"]
        structured["accreditation"] = {k: pages[k] for k in acc_keys if k in pages}

        return structured

    def run(self) -> dict:
        """Execute the full scraping pipeline."""
        start = time.time()
        log.info("=" * 60)
        log.info("PESCE Web Scraper — Starting")
        log.info("Target: %s", self.base_url)
        log.info("Pages to scrape: %d", len(TARGET_PAGES) + 1)
        log.info("=" * 60)

        # 1) Homepage
        self.scraped["homepage"] = self.scrape_homepage()

        # 2) All other pages (concurrent)
        pages = self.scrape_all_pages()

        # 3) Structure the data
        result = self.build_structured_data(pages)

        elapsed = time.time() - start
        log.info("=" * 60)
        log.info("Scraping complete in %.1f seconds", elapsed)
        log.info("Total HTTP requests: %d", self._request_count)
        log.info("Pages scraped successfully: %d / %d",
                 len(pages), len(TARGET_PAGES))
        log.info("=" * 60)

        # Add metadata
        result["_metadata"] = {
            "source": self.base_url,
            "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "total_pages": len(pages) + 1,
            "elapsed_seconds": round(elapsed, 2),
            "scraper_version": "2.0.0",
        }
        return result


# ═════════════════════════════════════════════════════════════════════════════
# CLI Entry Point
# ═════════════════════════════════════════════════════════════════════════════

def main():
    # Resolve output path relative to project root
    project_root = Path(__file__).resolve().parent.parent
    out_dir = project_root / "data" / "processed"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "pesce_data.json"

    scraper = PESCEScraper(BASE_URL)
    data = scraper.run()

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    log.info("Data saved → %s  (%.1f KB)", out_path, out_path.stat().st_size / 1024)


if __name__ == "__main__":
    main()
