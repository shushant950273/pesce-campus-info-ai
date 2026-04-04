import requests
from bs4 import BeautifulSoup
from config import COLLEGE_WEBSITE

class WebScraper:
    def __init__(self, base_url=COLLEGE_WEBSITE):
        self.base_url = base_url
        # Target URLs 
        self.target_pages = {
            "Academics": f"{self.base_url}/academics.php",
            "Placements": f"{self.base_url}/placement.php",
            "Facilities": f"{self.base_url}/facilities.php",
            "Admissions": f"{self.base_url}/admission.php"
        }

    def scrape_url(self, url):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            text = soup.get_text(separator='\n', strip=True)
            return text
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return ""

    def scrape_all_targets(self):
        scraped_data = {}
        for category, url in self.target_pages.items():
            print(f"Scraping category: {category} from {url}")
            text = self.scrape_url(url)
            scraped_data[category] = text
        return scraped_data

if __name__ == "__main__":
    scraper = WebScraper()
    print("WebScraper initialized.")
