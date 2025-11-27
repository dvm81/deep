"""Web scraping functionality for company research."""

from dataclasses import dataclass
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
import html2text
from .schema import PageContent, ResearchBrief


@dataclass
class CompanyScraper:
    """Scraper for company websites with domain validation and markdown conversion."""

    brief: ResearchBrief
    timeout: int = 30

    def _validate_url(self, url: str) -> None:
        """Validate that URL is in allowed domains.

        Args:
            url: The URL to validate

        Raises:
            ValueError: If URL domain is not in allowed domains
        """
        parsed = urlparse(url)
        if parsed.netloc not in self.brief.allowed_domains:
            raise ValueError(f"URL not in allowed domains: {url}")

    def fetch(self, url: str) -> PageContent:
        """Fetch and parse a web page, converting to markdown.

        Args:
            url: The URL to fetch

        Returns:
            PageContent with markdown-formatted text

        Raises:
            ValueError: If URL is not in allowed domains
            requests.HTTPError: If HTTP request fails
            Exception: If parsing fails
        """
        self._validate_url(url)

        try:
            # Use headers to mimic a real browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            resp = requests.get(url, timeout=self.timeout, headers=headers)
            resp.raise_for_status()
        except requests.RequestException as e:
            raise Exception(f"Failed to fetch {url}: {str(e)}")

        try:
            html = resp.text
            soup = BeautifulSoup(html, "html.parser")

            # Extract title
            title = (soup.title.string or "").strip() if soup.title else ""

            # Remove unwanted elements (scripts, styles, nav, footer)
            for element in soup(['script', 'style', 'nav', 'footer', 'header']):
                element.decompose()

            # Extract main content - prioritize main, article, or body
            main = soup.find("main") or soup.find("article") or soup.body or soup

            # Convert HTML to markdown
            h = html2text.HTML2Text()
            h.ignore_links = False  # Keep links for citations
            h.ignore_images = True  # Skip images
            h.ignore_emphasis = False  # Keep bold/italic
            h.body_width = 0  # Don't wrap lines
            h.unicode_snob = True  # Use unicode
            h.skip_internal_links = False

            # Convert to markdown - get ALL content, no truncation
            markdown_text = h.handle(str(main))

            return PageContent(url=url, title=title, text=markdown_text, raw_html=html)
        except Exception as e:
            raise Exception(f"Failed to parse {url}: {str(e)}")
