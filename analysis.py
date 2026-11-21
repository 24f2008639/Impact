"""
IMPACT - step 2: audit flags, ward money trail, contractor scorecard
Run AFTER process_data.py:   python analysis.py
Reads ./processed/  ->  writes ./output/
"""
import os
import pandas as pd

IN, OUT = "processed", "output"
os.makedirs(OUT, exist_ok=True)

wo = pd.read_csv(f"{IN}/work_orders_processed.csv", parse_dates=["assigned_at", "work_started_at", "completed_at"])
ward_sum = pd.read_csv(f"{IN}/ward_summary.csv")

# ---------- FLAGS (each flag = one clear, checkable reason) ----------
# Normal jobs vary ~20-30% around the rate card, so only flag clearly above that.
wo["flag_overbilled"] = wo["cost_ratio"] > 1.5
wo["flag_dlp_paid"] = wo["under_dlp"]                  # BMC paid for a road still under DLP
wo["flag_no_complaint"] = ~wo["has_complaint_link"]

# same road + same repair method billed again within 7 days
wo = wo.sort_values(["road_id", "repair_method", "assigned_at"])
gap = wo.groupby(["road_id", "repair_method"])["assigned_at"].diff().dt.days
wo["flag_double_billed"] = gap.le(7)

money_flags = ["flag_overbilled", "flag_dlp_paid", "flag_double_billed", "flag_no_complaint"]
wo["money_flag_count"] = wo[money_flags].sum(axis=1)

def reason(r):
    out = []
    if r["flag_overbilled"]:    out.append(f"billed {r['cost_ratio']:.1f}x rate card")
    if r["flag_dlp_paid"]:      out.append("road under DLP, should be free")
    if r["flag_double_billed"]: out.append("same road + method billed within 7 days")
    if r["flag_no_complaint"]:  out.append("no complaint linked")
    return "; ".join(out)

flagged = wo[wo["money_flag_count"] > 0].copy()
flagged["reason"] = flagged.apply(reason, axis=1)
flagged[["work_order_id", "ward_code", "road_id", "contractor_name", "repair_method",
         "cost_inr", "expected_cost_inr", "reason"]].to_csv(f"{OUT}/flagged_work_orders.csv", index=False)

# ---------- WARD MONEY TRAIL ----------
failed = wo[wo["reopened_within_30d"]].groupby("ward_code")["cost_inr"].sum()
flag_n = wo[wo["money_flag_count"] > 0].groupby("ward_code").size()
ward = ward_sum.copy()
ward["failed_fix_spend_inr"] = ward["ward_code"].map(failed).fillna(0)
ward["failed_fix_pct"] = (100 * ward["failed_fix_spend_inr"] / ward["spend_inr"]).round(1)
ward["flagged_jobs"] = ward["ward_code"].map(flag_n).fillna(0).astype(int)
ward.sort_values("budget_used_pct", ascending=False).to_csv(f"{OUT}/ward_money_trail.csv", index=False)

# ---------- CONTRACTOR SCORECARD ----------
score = wo.groupby("contractor_name").agg(
    jobs=("work_order_id", "count"),
    total_spend_inr=("cost_inr", "sum"),
    sla_met_pct=("sla_met", lambda s: round(100 * s.mean(), 1)),
    reopen_pct=("reopened_within_30d", lambda s: round(100 * s.mean(), 1)),
    median_cost_ratio=("cost_ratio", "median"),
).round(2).reset_index()
score.to_csv(f"{OUT}/contractor_scorecard.csv", index=False)

# ---------- REPAIR METHOD DURABILITY ----------
method = wo.groupby("repair_method").agg(
    jobs=("work_order_id", "count"),
    reopen_pct=("reopened_within_30d", lambda s: round(100 * s.mean(), 1)),
    median_cost_ratio=("cost_ratio", "median"),
).reset_index().sort_values("reopen_pct")
method.to_csv(f"{OUT}/method_durability.csv", index=False)

# ---------- QUICK SUMMARY ----------
print("Total spend (Rs):", f"{wo['cost_inr'].sum():,.0f}")
print("Flagged jobs:", len(flagged), "of", len(wo))
print("\nFlag counts:\n", wo[money_flags].sum())
print("\nTop 5 wards by budget used %:\n",
      ward.sort_values("budget_used_pct", ascending=False)
      .head(5)[["ward_code", "spend_inr", "monsoon_repair_budget_inr_2025", "budget_used_pct"]])
print("\nContractor scorecard:\n", score)
print("\nMethod durability:\n", method)
