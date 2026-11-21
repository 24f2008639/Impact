"""
IMPACT - raw data -> processed data
Run from the main folder (the one that contains data/):   python process_data.py
Needs: pip install pandas
Creates ./processed/ with clean, analysis-ready files. Raw files in data/ are never changed.
"""
import os
import pandas as pd

RAW, OUT = "data", "processed"
os.makedirs(OUT, exist_ok=True)

# ---------- 1. LOAD RAW ----------
wo = pd.read_csv(f"{RAW}/work_orders.csv", parse_dates=["assigned_at", "work_started_at", "completed_at"])
rate = pd.read_csv(f"{RAW}/rate_card.csv")
roads = pd.read_csv(f"{RAW}/roads.csv", parse_dates=["last_resurfaced"])
wards = pd.read_csv(f"{RAW}/wards.csv")
comp = pd.read_csv(f"{RAW}/complaints.csv", parse_dates=["received_at", "resolved_at"])
localities = pd.read_csv(f"{RAW}/localities.csv")

# ---------- 2. WORK ORDERS: merge + derived columns ----------
wo = (wo.merge(rate, on="repair_method", how="left")
        .merge(roads[["road_id", "road_name", "road_type", "surface", "length_m",
                      "last_resurfaced", "under_dlp", "bus_route"]], on="road_id", how="left")
        .merge(wards[["ward_code", "ward_name", "zone", "low_lying_index",
                      "monsoon_repair_budget_inr_2025"]], on="ward_code", how="left"))

# expected cost from the rate card (per sqm jobs scale with area, others are fixed)
wo["expected_cost_inr"] = wo.apply(
    lambda r: r["area_sqm"] * r["standard_rate_inr"] if r["unit"] == "per sqm" else r["standard_rate_inr"], axis=1)
wo["cost_ratio"] = (wo["cost_inr"] / wo["expected_cost_inr"]).round(3)   # 1.0 = exactly rate card

# time columns
wo["hours_to_start"] = ((wo["work_started_at"] - wo["assigned_at"]).dt.total_seconds() / 3600).round(1)
wo["hours_to_complete"] = ((wo["completed_at"] - wo["assigned_at"]).dt.total_seconds() / 3600).round(1)
wo["month"] = wo["assigned_at"].dt.to_period("M").astype(str)

# turn Y/N text into True/False so maths is easy
for col in ["sla_met", "reopened_within_30d", "under_dlp", "bus_route"]:
    wo[col] = wo[col].map({"Y": True, "N": False})

# complaint links
wo["n_linked_complaints"] = wo["linked_complaint_ids"].fillna("").apply(lambda s: len([x for x in s.split("|") if x]))
wo["has_complaint_link"] = wo["n_linked_complaints"] > 0
wo["engineer_remark"] = wo["engineer_remark"].fillna("")

wo.to_csv(f"{OUT}/work_orders_processed.csv", index=False)

# ---------- 3. LINK TABLE: one row per (work order, complaint) ----------
link = wo[["work_order_id", "linked_complaint_ids"]].dropna().copy()
link["complaint_id"] = link["linked_complaint_ids"].str.split("|")
link = link.explode("complaint_id")[["work_order_id", "complaint_id"]]
link.to_csv(f"{OUT}/complaint_workorder_links.csv", index=False)

# ---------- 4. COMPLAINTS: clean ----------
# fill missing ward_code using locality name (only where it matches the localities table)
loc_map = localities.drop_duplicates("locality").set_index("locality")["ward_code"]
comp["ward_code_filled"] = comp["ward_code"].fillna(comp["locality_text"].map(loc_map))
comp["ward_was_missing"] = comp["ward_code"].isna()
comp["has_gps"] = comp["lat"].notna()
comp["has_photo"] = comp["photo_url"].notna()
comp["hours_to_resolve"] = ((comp["resolved_at"] - comp["received_at"]).dt.total_seconds() / 3600).round(1)
comp["is_duplicate"] = comp["status"].eq("Closed - Duplicate")
comp["is_not_bmc"] = comp["status"].str.startswith(("Rejected", "Forwarded"))
comp["linked_to_work_order"] = comp["complaint_id"].isin(link["complaint_id"])
comp["month"] = comp["received_at"].dt.to_period("M").astype(str)
comp.to_csv(f"{OUT}/complaints_processed.csv", index=False)

# ---------- 5. WARD-LEVEL SUMMARY ----------
ward_sum = wo.groupby("ward_code").agg(
    jobs=("work_order_id", "count"),
    spend_inr=("cost_inr", "sum"),
    reopened_jobs=("reopened_within_30d", "sum"),
    sla_met_pct=("sla_met", lambda s: round(100 * s.mean(), 1)),
).reset_index()
ward_sum["reopen_pct"] = (100 * ward_sum["reopened_jobs"] / ward_sum["jobs"]).round(1)
ward_sum = ward_sum.merge(wards[["ward_code", "ward_name", "low_lying_index", "monsoon_repair_budget_inr_2025"]], on="ward_code")
ward_sum["budget_used_pct"] = (100 * ward_sum["spend_inr"] / ward_sum["monsoon_repair_budget_inr_2025"]).round(1)
ward_sum["complaints"] = ward_sum["ward_code"].map(comp.groupby("ward_code_filled").size()).fillna(0).astype(int)
ward_sum.to_csv(f"{OUT}/ward_summary.csv", index=False)

# ---------- 6. QUALITY REPORT ----------
print("work_orders_processed :", wo.shape)
print("complaints_processed  :", comp.shape)
print("links                 :", len(link))
print("work orders with no complaint link:", int((~wo['has_complaint_link']).sum()))
print("complaints missing ward  :", int(comp['ward_was_missing'].sum()),
      "-> still missing after fill:", int(comp['ward_code_filled'].isna().sum()))
print("rate card unmatched jobs :", int(wo['standard_rate_inr'].isna().sum()))
print("complaints that are duplicates:", int(comp['is_duplicate'].sum()))
print("\nSaved to ./processed/ :", sorted(os.listdir(OUT)))
