"""
IMPACT - step 3: Claude writes plain-language summaries
Run AFTER analysis.py:   python claude_summaries.py
Needs: pip install anthropic python-dotenv   and an API key in .env (see .env.example)

NOTE: this is a starting point. Edit the prompt and the ward code to suit your demo.
"""
import os
import pandas as pd
from dotenv import load_dotenv
import anthropic

load_dotenv()                                   # reads ANTHROPIC_API_KEY from .env
client = anthropic.Anthropic()                  # never write the key in this file

WARD = "E"                                      # change to the ward you want to demo
MODEL = "claude-sonnet-5-5"

ward = pd.read_csv("output/ward_money_trail.csv")
flagged = pd.read_csv("output/flagged_work_orders.csv")
score = pd.read_csv("output/contractor_scorecard.csv")

w = ward[ward["ward_code"] == WARD].iloc[0]
top_flags = flagged[flagged["ward_code"] == WARD].sort_values("cost_inr", ascending=False).head(5)

prompt = f"""You are helping a Mumbai ward officer understand road repair spending.
Write a plain-language summary in under 120 words. Be factual and fair:
state only what the numbers show, do not accuse anyone, and note that flags
are items to review, not proof of wrongdoing.

Ward {WARD} ({w['ward_name']}):
- Spend: Rs {w['spend_inr']:,.0f} against a budget of Rs {w['monsoon_repair_budget_inr_2025']:,.0f} ({w['budget_used_pct']}% used)
- Share of spend on fixes that failed within 30 days: {w['failed_fix_pct']}%
- Jobs flagged for review: {w['flagged_jobs']}
- Low-lying index (higher = more flood-prone): {w['low_lying_index']}

Largest flagged jobs:
{top_flags[['work_order_id', 'contractor_name', 'cost_inr', 'reason']].to_string(index=False)}
"""

reply = client.messages.create(
    model=MODEL,
    max_tokens=500,
    messages=[{"role": "user", "content": prompt}],
)
summary = reply.content[0].text
print(summary)

os.makedirs("output", exist_ok=True)
with open(f"output/summary_ward_{WARD.replace('/', '-')}.txt", "w", encoding="utf-8") as f:
    f.write(summary)
