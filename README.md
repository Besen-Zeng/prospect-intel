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

| Company | Country | Opportunity | People | Next Action |
|---|---|---|---|---|
| *(generated after running — see below)* | | | | |

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

### 5P Analysis fields (Claude output)

| Field | Description |
|---|---|
| `people` | Decision-maker profile and what matters to them |
| `product` | What they sell / their product focus |
| `place` | Market position, geography, distribution |
| `price` | Price sensitivity and segment |
| `promotion` | How they market (e-commerce, trade shows, etc.) |
| `opportunity_level` | High / Mid / Low fit rating |
| `next_action` | Single most impactful next BD step |

---

*Built by a BD professional to automate pre-outreach research for overseas smart pool robot sales.*
