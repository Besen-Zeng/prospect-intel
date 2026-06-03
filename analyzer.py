"""
analyzer.py — send prospect data to Claude and get a structured 5P analysis.

Returns a dict with keys:
  people, product, place, price, promotion,
  opportunity_level (High | Mid | Low), next_action,
  suggested_client_type (e.g. "B1", "B3+C3"), type_reasoning
"""

import json
import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv(override=True)

MODEL = "claude-sonnet-4-6"

# Load classification rules from the editable text file next to this module.
# Edit classification_rules.txt to change behaviour — no code change needed.
_RULES_PATH = Path(__file__).parent / "classification_rules.txt"
try:
    _CLASSIFICATION_RULES = _RULES_PATH.read_text(encoding="utf-8").strip()
except FileNotFoundError:
    _CLASSIFICATION_RULES = "(classification_rules.txt not found — use best judgement)"

SYSTEM_PROMPT = (
    "You are a B2B sales intelligence analyst for a smart pool robot manufacturer.\n"
    "Analyze the given prospect and return ONLY a valid JSON object — no markdown, no explanation, no extra text.\n\n"
    + _CLASSIFICATION_RULES
    + """

The JSON must have exactly these keys:
{
  "people":                "...",       // who the decision-maker is and what matters to them
  "product":               "...",       // what pool/wellness products or services they sell
  "place":                 "...",       // market position, geography, distribution channel
  "price":                 "...",       // price sensitivity, segment (budget / mid / premium)
  "promotion":             "...",       // how they market: e-commerce, trade shows, social, B2B direct
  "opportunity_level":     "High|Mid|Low",  // fit for smart pool robot partnership
  "next_action":           "...",       // single most impactful next step for our BD team
  "suggested_client_type": "...",       // inferred type code(s) from the classification rules above
  "type_reasoning":        "..."        // one sentence explaining the classification based on website evidence
}"""
)

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
    "suggested_client_type": "",
    "type_reasoning": "",
}

REQUIRED_KEYS = set(FALLBACK.keys())


def _extract_json(text: str) -> str:
    """Strip markdown code fences if Claude wrapped the JSON in ```json ... ```."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # Drop the opening fence line and the closing ``` line
        inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        text = "\n".join(inner).strip()
    return text


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
        raw = _extract_json(message.content[0].text)
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
