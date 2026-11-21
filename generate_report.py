"""
IMPACT - markdown report generator
Run AFTER process_data.py:   python generate_report.py
Reads ./processed/  ->  writes ./REPORT.md (renders nicely on GitHub)
"""
import pandas as pd

wo = pd.read_csv("processed/work_orders_processed.csv", parse_dates=["assigned_at"])
cp = pd.read_csv("processed/complaints_processed.csv")
lk = pd.read_csv("processed/complaint_workorder_links.csv")
ws = pd.read_csv("processed/ward_summary.csv")
short = lambda s: s.replace(" (synthetic)", "")

def cr(v):  return f"₹{v/1e7:.2f} Cr" if v >= 1e7 else f"₹{v/1e5:.1f} L"
def table(df):
    head = "| " + " | ".join(df.columns) + " |\n|" + "|".join("---" for _ in df.columns) + "|\n"
    return head + "\n".join("| " + " | ".join(str(x) for x in r) + " |" for r in df.itertuples(index=False)) + "\n"

# ---------- numbers ----------
tot = wo.cost_inr.sum(); failed = wo[wo.reopened_within_30d].cost_inr.sum()
wo = wo.sort_values(["road_id", "repair_method", "assigned_at"])
wo["f_over"] = wo.cost_ratio > 1.5
wo["f_dlp"] = wo.under_dlp
wo["f_dbl"] = wo.groupby(["road_id", "repair_method"]).assigned_at.diff().dt.days.le(7)
wo["f_nocomp"] = ~wo.has_complaint_link
wo["any_flag"] = wo[["f_over", "f_dlp", "f_dbl", "f_nocomp"]].any(axis=1)

ward = ws.copy()
ward["failed"] = ward.ward_code.map(wo[wo.reopened_within_30d].groupby("ward_code").cost_inr.sum()).fillna(0)
ward["flagged"] = ward.ward_code.map(wo[wo.any_flag].groupby("ward_code").size()).fillna(0).astype(int)
ward = ward.sort_values("budget_used_pct", ascending=False)
ward_t = pd.DataFrame({"Ward": ward.ward_code, "Area": ward.ward_name, "Spend": ward.spend_inr.map(cr),
    "Budget": ward.monsoon_repair_budget_inr_2025.map(cr), "Budget used": ward.budget_used_pct.map(lambda x: f"{x}%"),
    "Reopen %": ward.reopen_pct, "Flagged jobs": ward.flagged})

con = wo.groupby("contractor_name").agg(jobs=("work_order_id", "count"), spend=("cost_inr", "sum"),
    sla=("sla_met", "mean"), reopen=("reopened_within_30d", "mean"), ratio=("cost_ratio", "median"),
    over=("f_over", "sum")).reset_index().sort_values("reopen", ascending=False)
con_t = pd.DataFrame({"Contractor": con.contractor_name.map(short), "Jobs": con.jobs, "Spend": con.spend.map(cr),
    "SLA met": (100 * con.sla).round(1).map(lambda x: f"{x}%"), "Reopen": (100 * con.reopen).round(1).map(lambda x: f"{x}%"),
    "Median cost vs rate card": con.ratio.round(2).map(lambda x: f"{x}x"), "Jobs over 1.5x": con.over})

def grp(col):
    g = wo.groupby(col).agg(jobs=("work_order_id", "count"), spend=("cost_inr", "sum"),
        reopen=("reopened_within_30d", "mean")).reset_index().sort_values("reopen", ascending=False)
    return pd.DataFrame({col.replace("_", " ").title(): g[col], "Jobs": g.jobs, "Spend": g.spend.map(cr),
                         "Reopen %": (100 * g.reopen).round(1)})
mon = wo.groupby("month").agg(jobs=("work_order_id", "count"), spend=("cost_inr", "sum")).reset_index()
mon_t = pd.DataFrame({"Month": mon.month, "Jobs": mon.jobs, "Spend": mon.spend.map(cr)})

flags_t = pd.DataFrame([
    ["Overbilled", "Cost is more than 1.5x the rate card", int(wo.f_over.sum())],
    ["DLP paid", "Road is under its Defect Liability Period, so repair should be free", int(wo.f_dlp.sum())],
    ["Double billed", "Same road and repair method billed again within 7 days", int(wo.f_dbl.sum())],
    ["No complaint", "Work order has no linked citizen complaint", int(wo.f_nocomp.sum())]],
    columns=["Flag", "Rule", "Jobs"])

flood = wo.assign(risk=pd.qcut(wo.low_lying_index, 3, labels=["Low", "Mid", "High"])).groupby("risk", observed=True) \
    .reopened_within_30d.mean().mul(100).round(1)

tern = lambda s: s.value_counts().rename_axis("Value").reset_index(name="Complaints")
st = tern(cp.status); ch = tern(cp.channel); ca = tern(cp.category_reported); la = tern(cp.language)
for t in (st, ch, ca, la): t["Share"] = (100 * t.Complaints / len(cp)).round(1).map(lambda x: f"{x}%")

# ---------- column dictionary ----------
D = {"work_order_id": "Unique repair job ID", "linked_complaint_ids": "Complaint IDs separated by a pipe character",
 "ward_code": "BMC ward code", "road_id": "Road segment ID", "work_type": "Kind of problem fixed",
 "repair_method": "How it was fixed", "contractor_id": "Contractor ID", "contractor_name": "Contractor (fictional)",
 "assigned_at": "When the job was assigned", "work_started_at": "When work began", "completed_at": "When work finished",
 "area_sqm": "Area repaired (sq m)", "cost_inr": "Amount billed (₹)", "sla_hours": "Allowed hours (deadline)",
 "sla_met": "True if finished within the SLA", "reopened_within_30d": "True if the fix failed within 30 days",
 "engineer_remark": "Free-text engineer note", "unit": "Rate card unit (per sqm or per job)",
 "standard_rate_inr": "Rate card price (₹)", "road_name": "Road name", "road_type": "Road class",
 "surface": "Road surface", "length_m": "Road segment length (m)", "last_resurfaced": "Date last resurfaced",
 "under_dlp": "True if road is under a Defect Liability Period", "bus_route": "True if on a bus route",
 "ward_name": "Ward area names", "zone": "BMC zone", "low_lying_index": "Flood-proneness (higher = more)",
 "monsoon_repair_budget_inr_2025": "Ward monsoon repair budget (₹)", "expected_cost_inr": "Rate-card cost for this job (₹)",
 "cost_ratio": "Billed ÷ expected (1.0 = exactly rate card)", "hours_to_start": "Assigned to work start (hours)",
 "hours_to_complete": "Assigned to completion (hours)", "month": "Month assigned (YYYY-MM)",
 "n_linked_complaints": "Number of linked complaints", "has_complaint_link": "True if at least one complaint is linked",
 "complaint_id": "Unique complaint ID", "received_at": "When the complaint arrived", "channel": "How it was reported",
 "category_reported": "Category chosen by the citizen", "description": "Complaint text (en, hi, mr, hi-en)",
 "language": "Language of the text", "locality_text": "Locality named in the complaint", "lat": "Latitude (often missing)",
 "lon": "Longitude (often missing)", "gps_accuracy_m": "GPS accuracy (m)", "photo_url": "Photo link (often missing)",
 "photo_description": "Text description of the photo", "complainant_id": "Anonymised citizen ID", "upvotes": "Citizen upvotes",
 "status": "Complaint status", "resolved_at": "When resolved (blank if not)", "ward_code_filled": "Ward, filled from locality when missing",
 "ward_was_missing": "True if ward was blank in raw data", "has_gps": "True if coordinates present", "has_photo": "True if photo present",
 "hours_to_resolve": "Received to resolved (hours)", "is_duplicate": "True if closed as duplicate",
 "is_not_bmc": "True if rejected or forwarded to another body", "linked_to_work_order": "True if a work order links to it",
 "jobs": "Jobs in ward", "spend_inr": "Total billed in ward (₹)", "reopened_jobs": "Jobs that failed within 30 days",
 "sla_met_pct": "% jobs within SLA", "reopen_pct": "% jobs reopened", "budget_used_pct": "Spend ÷ budget × 100",
 "complaints": "Complaints in ward"}
def cols(df, name):
    rows = [(f"`{c}`", str(t).replace("object", "text").replace("str", "text").replace("int64", "integer")
             .replace("float64", "decimal").replace("bool", "True/False"), D.get(c, "From raw data")) for c, t in df.dtypes.items()]
    return f"#### `{name}`\n\n" + table(pd.DataFrame(rows, columns=["Column", "Type", "Meaning"]))

s0 = wo.sort_values("work_order_id").iloc[0]
sample = "\n".join(f"- `{k}`: {s0[k]}" for k in ["work_order_id", "ward_code", "road_name", "work_type", "repair_method",
    "contractor_name", "cost_inr", "expected_cost_inr", "cost_ratio", "sla_met", "reopened_within_30d", "under_dlp"])

md = f"""# IMPACT: Data Report

**Follow the Rupee: where did Mumbai's road repair money go?**

Generated from the files in `processed/` by `generate_report.py`. All data is synthetic (Claude Impact Lab dataset, CC BY 4.0). Flags are items to review, not proof of wrongdoing.

## 1. Pipeline

```mermaid
flowchart LR
    A[data/ raw CSVs] --> B[process_data.py]
    B --> C[processed/]
    C --> D[analysis.py]
    D --> E[output/]
    C --> F[generate_report.py]
    F --> G[REPORT.md]
```

## 2. Processed files

| File | Rows | Columns | One row is |
|---|---|---|---|
| `work_orders_processed.csv` | {len(wo):,} | 37 | A repair job, joined with rate card, road and ward details |
| `complaints_processed.csv` | {len(cp):,} | 26 | A citizen complaint, cleaned |
| `complaint_workorder_links.csv` | {len(lk):,} | 2 | One complaint linked to one work order |
| `ward_summary.csv` | {len(ws)} | 11 | A ward, with spend, budget and quality totals |

Period covered: {wo.assigned_at.min():%d %b %Y} to {wo.assigned_at.max():%d %b %Y}.

## 3. Column structure

{cols(pd.read_csv("processed/work_orders_processed.csv", nrows=5), "work_orders_processed.csv")}
{cols(pd.read_csv("processed/complaints_processed.csv", nrows=5), "complaints_processed.csv")}
{cols(ws, "ward_summary.csv")}
{cols(lk, "complaint_workorder_links.csv")}
### Example row (work order)

{sample}

## 4. Headline numbers

| Measure | Value |
|---|---|
| Total spend | {cr(tot)} |
| Work orders | {len(wo):,} |
| Spend on fixes that failed within 30 days | {cr(failed)} ({100*failed/tot:.0f}%) |
| Jobs reopened within 30 days | {100*wo.reopened_within_30d.mean():.1f}% |
| Jobs meeting SLA | {100*wo.sla_met.mean():.1f}% |
| Jobs with at least one flag | {int(wo.any_flag.sum())} of {len(wo):,} |
| Wards over budget | {int((ward.budget_used_pct > 100).sum())} of {len(ward)} |

## 5. Wards: budget vs spend

{table(ward_t)}
## 6. Contractor scorecard

{table(con_t)}
Reopen % is the share of a contractor's jobs that failed within 30 days. Read it next to ward flood risk (section 9) before judging a contractor.

## 7. Repair method and work type

{table(grp("repair_method"))}
{table(grp("work_type"))}
## 8. Monthly activity

{table(mon_t)}
## 9. Fairness check: flood risk vs failures

Wards split into three equal groups by `low_lying_index`:

| Flood risk | Jobs reopened within 30 days |
|---|---|
| Low | {flood.get("Low")}% |
| Mid | {flood.get("Mid")}% |
| High | {flood.get("High")}% |

Failure rates are similar across risk groups, so flood risk alone does not explain why repairs fail.

## 10. Audit flags

{table(flags_t)}
A job can carry more than one flag. The DLP and double-billing rules are broad and should be sampled by hand before any conclusion is drawn.

## 11. Complaints

- Total complaints: {len(cp):,}; closed as duplicates: {int(cp.is_duplicate.sum()):,} ({100*cp.is_duplicate.mean():.1f}%)
- Median time to resolve (resolved complaints): {cp.hours_to_resolve.median():.1f} hours
- Missing ward in raw data: {int(cp.ward_was_missing.sum())}; still missing after filling from locality: {int(cp.ward_code_filled.isna().sum())}
- With GPS: {100*cp.has_gps.mean():.0f}%; with photo: {100*cp.has_photo.mean():.0f}%

**Status**

{table(st)}
**Channel**

{table(ch)}
**Category**

{table(ca)}
**Language**

{table(la)}
## 12. Limitations

- The data is synthetic, so findings describe this dataset only.
- Flag thresholds (1.5x rate card, 7 days) are starting points and need review.
- Duplicate and out-of-scope complaints are marked, not removed.
- October 2025 has very few records, so monthly trends for that month are not reliable.
"""
open("REPORT.md", "w", encoding="utf-8").write(md)
print("Wrote REPORT.md", f"({len(md):,} characters)")

# ---------- ALSO REFRESH THE REPORT SECTION INSIDE README.md ----------
# README.md must contain the two marker lines below; everything between them is replaced.
import os
START, END = "<!-- REPORT:START -->", "<!-- REPORT:END -->"
if os.path.exists("README.md"):
    readme = open("README.md", encoding="utf-8").read()
    if START in readme and END in readme:
        body = md[md.index("## 1. Pipeline"):]
        body = body.replace("\n#### ", "\n##### ").replace("\n### ", "\n#### ").replace("\n## ", "\n### ")
        body = "### " + body[3:] if body.startswith("## ") else body
        new = readme.split(START)[0] + START + "\n" + body + "\n" + END + readme.split(END)[1]
        open("README.md", "w", encoding="utf-8").write(new)
        print("Updated report section in README.md")
