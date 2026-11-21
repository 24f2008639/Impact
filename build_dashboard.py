"""
IMPACT - dashboard builder
Run AFTER process_data.py and analysis.py:   python build_dashboard.py
Reads ./processed/ and ./output/  ->  writes ./impact_dashboard.html (open it in any browser)
"""
import json, sys
import pandas as pd

OUTFILE = sys.argv[1] if len(sys.argv) > 1 else "impact_dashboard.html"
short = lambda s: s.replace(" (synthetic)", "")

wo = pd.read_csv("processed/work_orders_processed.csv")
ward = pd.read_csv("output/ward_money_trail.csv")
score = pd.read_csv("output/contractor_scorecard.csv")
method = pd.read_csv("output/method_durability.csv")
flag = pd.read_csv("output/flagged_work_orders.csv")

over = wo[wo["cost_ratio"] > 1.5].groupby("contractor_name").size()
data = {
 "kpi": {"spend": int(wo.cost_inr.sum()), "jobs": len(wo), "flagged": len(flag),
         "reopen": round(100 * wo.reopened_within_30d.mean(), 1), "sla": round(100 * wo.sla_met.mean(), 1),
         "failed": int(wo[wo.reopened_within_30d].cost_inr.sum()),
         "overwards": int((ward.budget_used_pct > 100).sum())},
 "wards": [dict(c=r.ward_code, n=r.ward_name, jobs=int(r.jobs), spend=int(r.spend_inr),
                bud=int(r.monsoon_repair_budget_inr_2025), used=r.budget_used_pct, fail=r.failed_fix_pct,
                flg=int(r.flagged_jobs), sla=r.sla_met_pct, re=r.reopen_pct, low=r.low_lying_index,
                top=[dict(w=t.work_order_id, k=short(t.contractor_name), m=t.repair_method, c=int(t.cost_inr),
                          e=int(t.expected_cost_inr), r=t.reason)
                     for t in flag[flag.ward_code == r.ward_code].sort_values("cost_inr", ascending=False).head(5).itertuples()])
           for r in ward.itertuples()],
 "con": [dict(n=short(r.contractor_name), jobs=int(r.jobs), spend=int(r.total_spend_inr), sla=r.sla_met_pct,
              re=r.reopen_pct, ratio=r.median_cost_ratio, over=int(over.get(r.contractor_name, 0)))
         for r in score.itertuples()],
 "meth": [dict(n=r.repair_method, jobs=int(r.jobs), re=r.reopen_pct) for r in method.itertuples()],
 "mon": [dict(m=m, spend=int(g.cost_inr.sum()), jobs=len(g)) for m, g in wo.groupby("month")],
 "flags": {k: int(flag.reason.str.contains(p).sum()) for k, p in
           {"Same road + method billed within 7 days": "within 7 days", "Road under DLP, should be free": "DLP",
            "Billed over 1.5x rate card": "rate card", "No complaint linked": "no complaint"}.items()},
}

HTML = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>IMPACT: Follow the Rupee</title>
<style>
:root{--bg:#f6f7f9;--card:#fff;--tx:#1b2430;--mu:#667085;--bd:#e3e6ea;--ac:#0f766e;--wa:#c2410c;--bad:#b42318;--bar:#d7efec;
box-sizing:border-box;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#10151b;--card:#18202a;--tx:#e8ecf1;--mu:#98a2b3;--bd:#2a3441;--ac:#2dd4bf;--wa:#fb923c;--bad:#f87171;--bar:#17403c;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#10151b;--card:#18202a;--tx:#e8ecf1;--mu:#98a2b3;--bd:#2a3441;--ac:#2dd4bf;--wa:#fb923c;--bad:#f87171;--bar:#17403c;color-scheme:dark}
html{scroll-padding-top:env(safe-area-inset-top,0px)}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--tx);font:14px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
.w{max-width:1100px;margin:0 auto;padding:18px 14px 40px}
h1{font-size:22px;margin:0}h2{font-size:15px;margin:0 0 10px}.sub{color:var(--mu);margin:2px 0 14px}
.g{display:grid;gap:12px}.k{grid-template-columns:repeat(auto-fit,minmax(150px,1fr))}.two{grid-template-columns:repeat(auto-fit,minmax(320px,1fr))}
.c{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:14px;margin-bottom:12px;min-width:0}
.kv{font-size:22px;font-weight:650}.kl{color:var(--mu);font-size:12px}
.sc{overflow-x:auto}table{border-collapse:collapse;width:100%;min-width:480px}th,td{padding:6px 8px;border-bottom:1px solid var(--bd);text-align:left;white-space:nowrap}
th{color:var(--mu);font-weight:500;font-size:12px}tr.r{cursor:pointer}tr.r:hover,tr.sel{background:var(--bar)}
.b{height:8px;background:var(--bd);border-radius:4px;min-width:70px;overflow:hidden}.b i{display:block;height:100%;background:var(--ac)}.b i.o{background:var(--bad)}
.row{display:grid;grid-template-columns:minmax(120px,38%) 1fr 48px;gap:8px;align-items:center;margin:6px 0;font-size:13px}
.n{color:var(--mu);font-size:12px}.bad{color:var(--bad)}.pill{display:inline-block;padding:1px 7px;border-radius:9px;background:var(--bar);font-size:12px}
.note{color:var(--mu);font-size:12px;margin-top:8px}.cols{display:flex;gap:6px;align-items:flex-end;height:110px}.cols div{flex:1;text-align:center;font-size:11px;color:var(--mu)}.cols i{display:block;background:var(--ac);border-radius:3px 3px 0 0;margin-bottom:3px}
</style></head><body><div class="w">
<h1>IMPACT <span class="n">Follow the Rupee: where did Mumbai’s road repair money go?</span></h1>
<p class="sub">Synthetic data, June to October 2025. Flags are items to review, not proof of wrongdoing.</p>
<div class="g k" id="kpi"></div><div style="height:12px"></div>
<div class="g two"><div class="c"><h2>Wards: budget used (click a ward)</h2><div class="sc"><table id="wt"></table></div></div>
<div class="c" id="wd"></div></div>
<div class="c"><h2>Contractor scorecard</h2><div class="sc"><table id="ct"></table></div>
<p class="note">Reopen % = jobs that failed within 30 days. Compare with ward flood risk before judging a contractor.</p></div>
<div class="g two"><div class="c"><h2>Repair method durability (reopen %)</h2><div id="mt"></div></div>
<div class="c"><h2>Audit flags raised</h2><div id="fl"></div><h2 style="margin-top:16px">Monthly spend (₹ Cr)</h2><div class="cols" id="mo"></div></div></div>
</div><script>
const D=__DATA__;
const cr=v=>v>=1e7?"₹"+(v/1e7).toFixed(2)+" Cr":"₹"+(v/1e5).toFixed(1)+" L";
const $=id=>document.getElementById(id);
const K=D.kpi,kp=[["Total spend",cr(K.spend)],["Work orders",K.jobs],["Flagged for review",K.flagged],["Reopened in 30 days",K.reopen+"%"],["SLA met",K.sla+"%"],["Spend on failed fixes",cr(K.failed)],["Wards over budget",K.overwards+" of 24"]];
$("kpi").innerHTML=kp.map(a=>`<div class="c" style="margin:0"><div class="kv">${a[1]}</div><div class="kl">${a[0]}</div></div>`).join("");
const W=[...D.wards].sort((a,b)=>b.used-a.used);
$("wt").innerHTML="<tr><th>Ward</th><th>Spend</th><th>Budget used</th><th>Failed fix</th><th>Flags</th></tr>"+W.map(w=>`<tr class="r" data-c="${w.c}"><td>${w.c}</td><td>${cr(w.spend)}</td><td><div style="display:flex;gap:6px;align-items:center"><div class="b" style="width:80px"><i class="${w.used>100?"o":""}" style="width:${Math.min(w.used,130)/1.3}%"></i></div><span class="${w.used>100?"bad":""}">${w.used}%</span></div></td><td>${w.fail}%</td><td>${w.flg}</td></tr>`).join("");
function show(c){const w=D.wards.find(x=>x.c==c);
document.querySelectorAll("#wt tr.r").forEach(r=>r.classList.toggle("sel",r.dataset.c==c));
$("wd").innerHTML=`<h2>Ward ${w.c}: ${w.n}</h2><div class="g k" style="grid-template-columns:repeat(2,1fr)">
<div><div class="kv">${cr(w.spend)}</div><div class="kl">spent of ${cr(w.bud)} budget</div></div>
<div><div class="kv ${w.used>100?"bad":""}">${w.used}%</div><div class="kl">budget used</div></div>
<div><div class="kv">${w.fail}%</div><div class="kl">spend on fixes that failed</div></div>
<div><div class="kv">${w.re}%</div><div class="kl">jobs reopened (SLA met ${w.sla}%)</div></div></div>
<p class="note">Flood risk (low-lying index): ${w.low}. ${w.jobs} jobs, ${w.flg} flagged.</p>
<h2 style="margin-top:12px">Largest flagged jobs</h2><div class="sc"><table><tr><th>Work order</th><th>Contractor</th><th>Billed</th><th>Rate card</th><th>Reason</th></tr>`+
w.top.map(t=>`<tr><td>${t.w}</td><td>${t.k}</td><td>${cr(t.c)}</td><td>${cr(t.e)}</td><td style="white-space:normal;min-width:180px">${t.r}</td></tr>`).join("")+"</table></div>"}
$("wt").onclick=e=>{const r=e.target.closest("tr.r");if(r)show(r.dataset.c)};show(W[0].c);
$("ct").innerHTML="<tr><th>Contractor</th><th>Jobs</th><th>Spend</th><th>SLA met</th><th>Reopen</th><th>Median cost vs rate card</th><th>Over 1.5x</th></tr>"+D.con.map(c=>`<tr><td>${c.n}</td><td>${c.jobs}</td><td>${cr(c.spend)}</td><td>${c.sla}%</td><td class="${c.re>30?"bad":""}">${c.re}%</td><td>${c.ratio}x</td><td class="${c.over>20?"bad":""}">${c.over}</td></tr>`).join("");
const mx=Math.max(...D.meth.map(m=>m.re));
$("mt").innerHTML=D.meth.map(m=>`<div class="row"><span>${m.n}</span><div class="b"><i class="${m.re>30?"o":""}" style="width:${m.re/mx*100}%"></i></div><b>${m.re}%</b></div>`).join("");
const fm=Math.max(...Object.values(D.flags));
$("fl").innerHTML=Object.entries(D.flags).map(f=>`<div class="row"><span>${f[0]}</span><div class="b"><i style="width:${f[1]/fm*100}%"></i></div><b>${f[1]}</b></div>`).join("")+'<p class="note">A job can carry more than one flag. The DLP and 7-day rules are broad, so review samples before acting.</p>';
const sm=Math.max(...D.mon.map(m=>m.spend));
$("mo").innerHTML=D.mon.map(m=>`<div><i style="height:${m.spend/sm*85}px"></i>${m.m.slice(5)}<br>${(m.spend/1e7).toFixed(2)}</div>`).join("");
</script></body></html>"""
open(OUTFILE, "w", encoding="utf-8").write(HTML.replace("__DATA__", json.dumps(data, ensure_ascii=False)))
print("Wrote", OUTFILE)
