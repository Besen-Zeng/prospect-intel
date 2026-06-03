"""
fetcher.py — scrape visible text from a company website.

Returns a dict: {"text": str, "error": str | None}
If scraping fails, text is empty and error describes why — the pipeline continues.
"""

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}
TIMEOUT = 10        # seconds
MAX_CHARS = 3000    # keeps token usage predictable


def fetch(url: str, company: str = "") -> dict:
    """Fetch and return visible text from a URL."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
        text = _extract_text(response.text)
        return {"text": text[:MAX_CHARS], "error": None}

    except requests.exceptions.Timeout:
        _log(company, f"timed out after {TIMEOUT}s")
        return {"text": "", "error": "timeout"}

    except requests.exceptions.ConnectionError as e:
        _log(company, f"connection error: {e}")
        return {"text": "", "error": "connection error"}

    except requests.exceptions.HTTPError as e:
        _log(company, f"HTTP {e.response.status_code}")
        return {"text": "", "error": f"HTTP {e.response.status_code}"}

    except Exception as e:
        _log(company, str(e))
        return {"text": "", "error": str(e)}


def _extract_text(html: str) -> str:
    """Strip tags and return clean visible text."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "head"]):
        tag.decompose()
    lines = [line.strip() for line in soup.get_text(separator="\n").splitlines()]
    return "\n".join(line for line in lines if line)


def _log(company: str, message: str) -> None:
    label = f"[{company}]" if company else "[fetcher]"
    print(f"  {label} WARNING: {message} — skipping website content")
