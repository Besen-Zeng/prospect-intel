"""
analyzer.py — send prospect data to Claude and get a structured 5P analysis.

Returns a dict with keys:
  people, product, place, price, promotion,
  opportunity_level (High | Mid | Low), next_action
"""

import json
import os

import anthropic
from dotenv import load_dotenv

load_dotenv(override=True)

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You are a B2B sales intelligence analyst for a smart pool robot manufacturer.
Analyze the given prospect and return ONLY a valid JSON object — no markdown, no explanation, no extra text.

The JSON must have exactly these keys:
{
  "people":            "...",   // who the decision-maker is and what matters to them
  "product":           "...",   // what pool/wellness products or services they sell
  "place":             "...",   // market position, geography, distribution channel
  "price":             "...",   // price sensitivity, segment (budget / mid / premium)
  "promotion":         "...",   // how they market: e-commerce, trade shows, social, B2B direct
  "opportunity_level": "High|Mid|Low",   // fit for smart pool robot partnership
  "next_action":       "..."    // single most impactful next step for our BD team
}"""

USER_TEMPLATE = """Analyze this prospect for our smart pool robot company.

Company:      {company}
Country:      {country}
Client Type:  {client_type}
Contact:      {contact_name}
Contact notes: {people_notes}

Website content:
{website_text}

Return the JSON object now."""

# Fallback used when Claude can't be reached or returns malformed JSON
FALLBACK = {
    "people": "",
    "product": "",
    "place": "",
    "price": "",
    "promotion": "",
    "opportunity_level": "Low",
    "next_action": "Manual research required — API call failed",
}

REQUIRED_KEYS = set(FALLBACK.keys())


def analyze(row: dict, website_text: str) -> dict:
    """Call Claude and return the 5P analysis dict."""
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    prompt = USER_TEMPLATE.format(
        company=row.get("company", ""),
        country=row.get("country", ""),
        client_type=row.get("client_type", ""),
        contact_name=row.get("contact_name", ""),
        people_notes=row.get("people_notes", ""),
        website_text=website_text or "(website unavailable)",
    )

    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        result = json.loads(raw)

        # Ensure all required keys exist
        if not REQUIRED_KEYS.issubset(result.keys()):
            missing = REQUIRED_KEYS - result.keys()
            raise ValueError(f"Missing keys in Claude response: {missing}")

        return result

    except json.JSONDecodeError as e:
        print(f"  [{row.get('company')}] WARNING: Claude returned non-JSON: {e}")
        return FALLBACK.copy()

    except Exception as e:
        print(f"  [{row.get('company')}] WARNING: Claude API error: {e}")
        return FALLBACK.copy()
