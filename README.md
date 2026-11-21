# IMPACT

**Follow the Rupee: where did Mumbai's road repair money go?**

IMPACT traces road repair spending from citizen complaint to work order to contractor to ward budget. It flags jobs that need a second look, shows whether repairs held up, and gives each ward and contractor a fair, evidence-based scorecard. Claude turns the numbers into plain-language summaries a ward officer can act on.

Built for Claude Impact Lab Mumbai (theme: Civic Budget & Accountability).

## How it works

```
data/ -> process_data.py -> processed/ -> analysis.py -> output/ -> claude_summaries.py
```

1. `process_data.py` cleans and joins the raw CSVs into analysis-ready files in `processed/`.
2. `analysis.py` creates audit flags, a ward money trail, a contractor scorecard and a repair-method durability table in `output/`.
3. `claude_summaries.py` asks Claude to write a short, fair summary for a chosen ward.

## Run it

```bash
pip install -r requirements.txt
python process_data.py
python analysis.py
python claude_summaries.py      # needs an API key, see below
```

For step 3, copy `.env.example` to `.env` and add your Anthropic API key. `.env` is git-ignored and must never be committed.

## Audit flags

Flags are items to review, not proof of wrongdoing.

| Flag | Meaning |
|---|---|
| overbilled | cost is more than 1.5x the rate card |
| dlp_paid | BMC paid for a road still under its Defect Liability Period |
| double_billed | same road and repair method billed again within 7 days |
| no_complaint | work order has no linked citizen complaint |

## Data

All data is synthetic (fictional contractors and records) from the Claude Impact Lab dataset, released under CC BY 4.0. No real people, companies or BMC records are used.

## Team

Team 40, Claude Impact Lab Mumbai.
