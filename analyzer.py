"""
analyzer.py — send prospect data to Claude and get a structured 5P analysis.

Returns a dict with keys:
  people, product, place, price, promotion,
  opportunity_level (High | Mid | Low), next_action,
  suggested_client_type (e.g. "B1", "B3+C3"), type_reasoning,
  web_intel (2-3 sentence summary of what web search found beyond the website)
"""

import json
import os
import time
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

_WEB_SEARCH_INSTRUCTIONS = (
    "\n\nBefore writing the JSON, use web_search to actively research the prospect:\n"
    "1. Recent news about the company from the past 12 months.\n"
    "2. Public background on the contact person — Google results often surface LinkedIn\n"
    "   profile summaries, trade show speaker lists, and industry interviews.\n"
    "   Direct LinkedIn scraping is unavailable; rely on what Google indexes publicly.\n"
    "3. Competitor mentions or market positioning data for this company.\n"
    "\n"
    "If searches return nothing beyond the official website, note that briefly.\n"
    "Summarise web search findings (beyond the website) in 'web_intel' (2-3 sentences).\n"
)

SYSTEM_PROMPT = (
    "You are a B2B sales intelligence analyst for a smart pool robot manufacturer.\n"
    "Analyze the given prospect and return ONLY a valid JSON object — no markdown, no explanation, no extra text.\n\n"
    + _CLASSIFICATION_RULES
    + _WEB_SEARCH_INSTRUCTIONS
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
  "type_reasoning":        "...",       // one sentence explaining the classification based on website evidence
  "web_intel":             "..."        // 2-3 sentences on what web search found beyond the official website
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
    "web_intel": "",
}

REQUIRED_KEYS = set(FALLBACK.keys())


_WEB_SEARCH_TOOLS = [{"type": "web_search_20250305", "name": "web_search"}]


def _run_with_web_search(client: anthropic.Anthropic, messages: list) -> str:
    """
    Call Claude with web search enabled, looping until stop_reason is end_turn.
    For Anthropic's server-side web_search tool this typically completes in one
    call; the loop is a safety net for unexpected tool_use stop reasons.
    """
    for _ in range(10):
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=_WEB_SEARCH_TOOLS,
            messages=messages,
        )

        text_blocks = [b.text for b in response.content if getattr(b, "type", "") == "text"]

        if response.stop_reason == "end_turn":
            return text_blocks[-1] if text_blocks else ""

        # tool_use: append the assistant turn and let the loop continue
        if response.stop_reason == "tool_use":
            messages = messages + [{"role": "assistant", "content": response.content}]
            continue

        return text_blocks[-1] if text_blocks else ""

    raise RuntimeError("web search loop exceeded 10 iterations without end_turn")


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
    """Call Claude with web search and return the full analysis dict."""
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    prompt = USER_TEMPLATE.format(
        company=row.get("company", ""),
        country=row.get("country", ""),
        client_type=row.get("client_type", ""),
        contact_name=row.get("contact_name", ""),
        people_notes=row.get("people_notes", ""),
        website_text=website_text or "(website unavailable)",
    )

    messages = [{"role": "user", "content": prompt}]
    company  = row.get("company", "?")

    for attempt in range(1, 4):  # up to 3 attempts
        try:
            raw    = _run_with_web_search(client, messages)
            result = json.loads(_extract_json(raw))

            if not REQUIRED_KEYS.issubset(result.keys()):
                missing = REQUIRED_KEYS - result.keys()
                raise ValueError(f"Missing keys: {missing}")

            return result

        except json.JSONDecodeError:
            if attempt < 3:
                print(f"  [{company}] non-JSON response on attempt {attempt}, retrying in 15s…")
                time.sleep(15)
                continue
            print(f"  [{company}] WARNING: Claude returned non-JSON after 3 attempts")
            return FALLBACK.copy()

        except anthropic.RateLimitError:
            wait = 60 * attempt
            print(f"  [{company}] rate limit hit, waiting {wait}s before retry {attempt}/3…")
            time.sleep(wait)
            continue

        except Exception as e:
            print(f"  [{company}] WARNING: Claude API error: {e}")
            return FALLBACK.copy()

    return FALLBACK.copy()
