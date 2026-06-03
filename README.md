## prospect-intel

> AI-powered B2B prospect research tool for overseas sales teams

**Problem:** Manual client research before outreach takes 2+ hours per company.  
**Solution:** Feed a CSV of prospects → get a structured 5P intelligence report in Excel.  
**Stack:** Python · Claude API (Anthropic) · BeautifulSoup · openpyxl

---

### How it works

```
prospects.csv
     │
     ▼
 fetcher.py          ← scrapes company website (handles timeouts / 403s gracefully)
     │
     ▼
 analyzer.py         ← calls Claude API with company info + website text
     │               → returns structured 5P JSON
     ▼
output/report.xlsx   ← colour-coded Excel report (Green = High opportunity)
```

---

### Sample output

Real output from a pipeline run against 4 anonymized prospects:

| Company | Country | Opportunity | People | Next Action |
|---|---|---|---|---|
| SoDramar | Brazil 🇧🇷 | **High** | Douglas — engineer & quote authority; responds to AI/automation demos | Schedule technical demo focused on smart mapping & AI navigation |
| Esparindo | Indonesia 🇮🇩 | **High** | Husni — German-educated engineer; high QC standards; phasing out Dolphin | Send technically detailed brief emphasizing European engineering standards |
| Fahrenheit Wellness | India 🇮🇳 | **High** | Harsh — owner; premium-bullish; wants sample + quote | Send premium sample kit + tailored quote immediately |
| INNPRO | Poland 🇵🇱 | **High** | Lukasz — PM; enthusiastic on iGarden ecosystem; plans dedicated team | Schedule partnership scoping call to position robot as iGarden extension |

*Full report includes 5P fields (people / product / place / price / promotion) + colour-coded opportunity cells in Excel.*

---

### Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Add your Anthropic API key
cp .env.example .env
# then edit .env and paste your key

# 3. Run
python main.py
```

Output appears at `output/report.xlsx`.

---

### Input format (`prospects.csv`)

| Column | Description |
|---|---|
| `company` | Company name |
| `website` | Domain (with or without https://) |
| `country` | Country |
| `client_type` | Internal tier label (e.g. B2, B3+C3) |
| `contact_name` | Primary contact |
| `people_notes` | Notes on decision-maker |

---

### Output fields (Claude analysis)

| Field | Description |
|---|---|
| `suggested_client_type` | Auto-inferred B/C classification from website content (see rules below) |
| `type_reasoning` | One-sentence explanation of why Claude chose that classification |
| `people` | Decision-maker profile and what matters to them |
| `product` | What they sell / their product focus |
| `place` | Market position, geography, distribution |
| `price` | Price sensitivity and segment |
| `promotion` | How they market (e-commerce, trade shows, etc.) |
| `opportunity_level` | High / Mid / Low fit rating |
| `next_action` | Single most impactful next BD step |

### Auto client-type classification

Claude infers the client type from website content using these rules:

| Code | Meaning |
|---|---|
| `B1` | Manufactures its own products |
| `B2` | Large distributor or multinational group (multi-country, large SKU range, many sub-brands) |
| `B3` | Local or single-category distributor (limited region or limited product scope) |
| `C1` | Chain store (vertical specialty retailer or mass KA like Costco) |
| `C2` | Pure e-commerce (online only, no physical stores) |
| `C3` | Has a few own physical retail stores |

Combined types are supported (e.g. `B3+C3`). If you leave `client_type` blank in the CSV, the auto-inferred value fills the cell automatically (shown in blue in Excel).

---

*Built by a BD professional to automate pre-outreach research for overseas smart pool robot sales.*
