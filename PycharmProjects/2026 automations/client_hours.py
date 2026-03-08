import pandas as pd
import os
from datetime import datetime, timedelta

now = datetime.now()

# ────────────────────────────────────────────────
# CONFIG
# ────────────────────────────────────────────────

OUTPUT_DIR = r"C:\DummyOutput\SupportAudit"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ────────────────────────────────────────────────
# DUMMY MASTER DATA
# ────────────────────────────────────────────────

priority_sla = pd.DataFrame({
    "priority": ["P1", "P2", "P3", "P4"],
    "first_response_sla_hours": [1, 4, 8, 24],
    "resolution_sla_hours": [4, 12, 48, 120]
})

team_calendar = pd.DataFrame({
    "team": ["Billing", "Tech", "Onboarding", "VIP"],
    "business_start": ["08:00", "08:00", "09:00", "07:00"],
    "business_end":   ["18:00", "20:00", "17:00", "22:00"],
    "weekend_support": [False, True, False, True]
})

# ────────────────────────────────────────────────
# DUMMY TICKETS
# ────────────────────────────────────────────────

tickets_raw = pd.DataFrame({
    "ticket_id": [
        "TCK001","TCK002","TCK003","TCK004","TCK005",
        "TCK006","TCK007","TCK008","TCK009","TCK010"
    ],
    "team": [
        "Billing","Tech","Tech","Onboarding","VIP",
        "Billing","Tech","VIP","Onboarding","Billing"
    ],
    "priority": ["P1","P2","P2","P3","P1","P4","P3","P1","P2","P3"],
    "channel": ["Email","Chat","Email","Phone","Email","Email","Chat","Phone","Email","Chat"],
    "customer_tier": ["Standard","Standard","Premium","Standard","VIP","Standard","Premium","VIP","Standard","Premium"],
    "status": [
        "Open","Resolved","Open","Pending Customer","Resolved",
        "Open","Resolved","Reopened","Open","Resolved"
    ],
    "created_at": [
        now - timedelta(hours=5),
        now - timedelta(hours=10),
        now - timedelta(hours=16),
        now - timedelta(hours=30),
        now - timedelta(hours=3),
        now - timedelta(hours=80),
        now - timedelta(hours=55),
        now - timedelta(hours=20),
        now - timedelta(hours=7),
        now - timedelta(hours=60),
    ],
    "first_response_at": [
        now - timedelta(hours=3),
        now - timedelta(hours=8),
        None,
        now - timedelta(hours=25),
        now - timedelta(hours=2),
        None,
        now - timedelta(hours=50),
        now - timedelta(hours=18),
        None,
        now - timedelta(hours=56),
    ],
    "resolved_at": [
        None,
        now - timedelta(hours=2),
        None,
        None,
        now - timedelta(hours=1),
        None,
        now - timedelta(hours=2),
        None,
        None,
        now - timedelta(hours=5),
    ],
    "owner": [
        "Alice","Bob",None,"Diana","Eva",
        None,"Frank","Grace","Helen","Ivan"
    ],
    "reopen_count": [0,0,0,0,0,0,0,2,1,0],
    "csat_score": [None,5,None,None,4,None,2,None,None,3],
    "escalated": [True,False,True,False,True,False,False,True,False,False]
})

# Simulated historical report data
previously_flagged_ids = {
    "TCK001": {"count": 2, "audits": ["SLA Breach", "Missing Owner"]},
    "TCK006": {"count": 1, "audits": ["Aging Tickets"]},
    "TCK008": {"count": 1, "audits": ["Reopened Tickets"]},
}

historical_counts = {
    "TCK001": 4,
    "TCK003": 2,
    "TCK006": 5,
    "TCK008": 3,
    "TCK009": 2
}

# ────────────────────────────────────────────────
# CLEANING / ENRICHMENT
# ────────────────────────────────────────────────

tickets = tickets_raw.copy()
tickets["created_at"] = pd.to_datetime(tickets["created_at"])
tickets["first_response_at"] = pd.to_datetime(tickets["first_response_at"])
tickets["resolved_at"] = pd.to_datetime(tickets["resolved_at"])

tickets = tickets.merge(priority_sla, on="priority", how="left")
tickets = tickets.merge(team_calendar, on="team", how="left")

tickets["ticket_age_hours"] = ((now - tickets["created_at"]).dt.total_seconds() / 3600).round(2)
tickets["first_response_elapsed_hours"] = (
    (tickets["first_response_at"].fillna(now) - tickets["created_at"]).dt.total_seconds() / 3600
).round(2)
tickets["resolution_elapsed_hours"] = (
    (tickets["resolved_at"].fillna(now) - tickets["created_at"]).dt.total_seconds() / 3600
).round(2)

# ────────────────────────────────────────────────
# AUDIT 1 — FIRST RESPONSE SLA BREACH
# ────────────────────────────────────────────────

def first_response_sla_flag(row):
    if pd.notna(row["first_response_at"]):
        return row["first_response_elapsed_hours"] > row["first_response_sla_hours"]
    return row["ticket_age_hours"] > row["first_response_sla_hours"]

sla_response_breach = tickets[tickets.apply(first_response_sla_flag, axis=1)].copy()
sla_response_breach["audit_reason"] = "First response SLA breached"

# ────────────────────────────────────────────────
# AUDIT 2 — RESOLUTION SLA BREACH
# ────────────────────────────────────────────────

def resolution_sla_flag(row):
    if row["status"] == "Resolved" and pd.notna(row["resolved_at"]):
        return row["resolution_elapsed_hours"] > row["resolution_sla_hours"]
    return row["ticket_age_hours"] > row["resolution_sla_hours"]

sla_resolution_breach = tickets[tickets.apply(resolution_sla_flag, axis=1)].copy()
sla_resolution_breach["audit_reason"] = "Resolution SLA breached"

# ────────────────────────────────────────────────
# AUDIT 3 — MISSING OWNER
# ────────────────────────────────────────────────

missing_owner = tickets[
    (tickets["status"].isin(["Open", "Pending Customer", "Reopened"])) &
    (tickets["owner"].isna())
].copy()
missing_owner["audit_reason"] = "Ticket has no assigned owner"

# ────────────────────────────────────────────────
# AUDIT 4 — REOPENED HIGH RISK
# ────────────────────────────────────────────────

reopened_high_risk = tickets[
    (tickets["reopen_count"] >= 1) &
    (tickets["priority"].isin(["P1", "P2"]) | tickets["customer_tier"].eq("VIP"))
].copy()
reopened_high_risk["audit_reason"] = "High-risk reopened ticket"

# ────────────────────────────────────────────────
# AUDIT 5 — LOW CSAT RESOLVED
# ────────────────────────────────────────────────

low_csat = tickets[
    (tickets["status"] == "Resolved") &
    (tickets["csat_score"].notna()) &
    (tickets["csat_score"] <= 3)
].copy()
low_csat["audit_reason"] = "Resolved ticket with low CSAT"

# ────────────────────────────────────────────────
# AUDIT 6 — OUT OF BUSINESS HOURS CREATION
# ────────────────────────────────────────────────

def created_outside_business_hours(row):
    created = row["created_at"]
    weekday = created.weekday()  # 0 Monday, 6 Sunday

    start = datetime.strptime(row["business_start"], "%H:%M").time()
    end = datetime.strptime(row["business_end"], "%H:%M").time()
    current_time = created.time()

    weekend = weekday >= 5
    if weekend and not row["weekend_support"]:
        return True

    return not (start <= current_time <= end)

outside_business_hours = tickets[tickets.apply(created_outside_business_hours, axis=1)].copy()
outside_business_hours["audit_reason"] = "Ticket created outside business support hours"

# ────────────────────────────────────────────────
# HISTORICAL ENRICHMENT
# ────────────────────────────────────────────────

def add_history_info(df):
    if df.empty:
        return df

    df = df.copy()
    df["previously_flagged"] = df["ticket_id"].apply(lambda x: x in previously_flagged_ids)
    df["previous_flag_count"] = df["ticket_id"].apply(
        lambda x: previously_flagged_ids.get(x, {}).get("count", 0)
    )
    df["historical_flag_count"] = df["ticket_id"].apply(
        lambda x: historical_counts.get(x, 0)
    )
    return df

sla_response_breach = add_history_info(sla_response_breach)
sla_resolution_breach = add_history_info(sla_resolution_breach)
missing_owner = add_history_info(missing_owner)
reopened_high_risk = add_history_info(reopened_high_risk)
low_csat = add_history_info(low_csat)
outside_business_hours = add_history_info(outside_business_hours)

# ────────────────────────────────────────────────
# SUMMARY TABLES
# ────────────────────────────────────────────────

def build_summary_df(audits):
    rows = []
    for audit_name, df in audits.items():
        total = len(df)
        prev = len(df[df["previously_flagged"] == True]) if not df.empty else 0
        rows.append({
            "audit_name": audit_name,
            "total_flags": total,
            "previously_flagged": prev,
            "repeat_ratio": f"{prev}/{total}" if total else "0/0"
        })
    return pd.DataFrame(rows)

audit_map = {
    "First Response SLA": sla_response_breach,
    "Resolution SLA": sla_resolution_breach,
    "Missing Owner": missing_owner,
    "Reopened High Risk": reopened_high_risk,
    "Low CSAT": low_csat,
    "Outside Business Hours": outside_business_hours
}

summary_df = build_summary_df(audit_map)

# ────────────────────────────────────────────────
# EXCEL REPORT
# ────────────────────────────────────────────────

def save_excel_report(audit_map, summary_df, output_dir):
    date_str = now.strftime("%Y%m%d")
    path = os.path.join(output_dir, f"Support_Audit_Report_{date_str}.xlsx")

    with pd.ExcelWriter(path, engine="xlsxwriter") as writer:
        wb = writer.book
        yellow_fmt = wb.add_format({'bg_color': '#FFFF00'})
        red_fmt = wb.add_format({'bg_color': '#FFC7CE'})

        summary_df.to_excel(writer, sheet_name="Summary", index=False)

        for sheet_name, df in audit_map.items():
            export_df = df.copy()

            if not export_df.empty:
                selected_cols = [
                    "ticket_id", "team", "priority", "status", "owner",
                    "customer_tier", "created_at", "first_response_at", "resolved_at",
                    "ticket_age_hours", "first_response_elapsed_hours",
                    "resolution_elapsed_hours", "audit_reason",
                    "previously_flagged", "previous_flag_count", "historical_flag_count"
                ]
                selected_cols = [c for c in selected_cols if c in export_df.columns]
                export_df = export_df[selected_cols].sort_values("ticket_id")

            safe_sheet_name = sheet_name[:31]
            export_df.to_excel(writer, sheet_name=safe_sheet_name, index=False)

            ws = writer.sheets[safe_sheet_name]
            cols = export_df.columns.tolist()

            if not export_df.empty:
                for row_idx, (_, row) in enumerate(export_df.iterrows(), start=1):
                    if "previously_flagged" in cols and row.get("previously_flagged", False):
                        ws.write(row_idx, cols.index("ticket_id"), row["ticket_id"], yellow_fmt)
                    if "priority" in cols and row.get("priority") == "P1":
                        ws.write(row_idx, cols.index("priority"), row["priority"], red_fmt)

            for i, col in enumerate(cols):
                max_len = max(export_df[col].astype(str).map(len).max() if len(export_df) else 0, len(col)) + 2
                ws.set_column(i, i, max_len)

    return path

# ────────────────────────────────────────────────
# HTML EMAIL SUMMARY
# ────────────────────────────────────────────────

def create_audit_section(audit_name, df, group_col):
    if df.empty:
        return ""

    top = df[group_col].value_counts().head(5)
    prev = len(df[df["previously_flagged"] == True]) if "previously_flagged" in df.columns else 0

    html = f"""
    <tr style="background-color:#E0E0E0;">
        <td style="border:1px solid #ddd;padding:8px;font-weight:bold;">{audit_name}</td>
        <td style="border:1px solid #ddd;padding:8px;text-align:center;">{len(df)}</td>
    </tr>
    """

    if prev > 0:
        html += f"""
        <tr style="background-color:#FFF2CC;">
            <td style="border:1px solid #ddd;padding:8px 8px 8px 30px;font-style:italic;">
                Previously flagged
            </td>
            <td style="border:1px solid #ddd;padding:8px;text-align:center;">{prev}</td>
        </tr>
        """

    for label, count in top.items():
        html += f"""
        <tr>
            <td style="border:1px solid #ddd;padding:8px 8px 8px 20px;">{label}</td>
            <td style="border:1px solid #ddd;padding:8px;text-align:center;">{count}</td>
        </tr>
        """
    return html

def create_html_summary(audit_map, summary_df):
    html = f"""
    <html>
    <body style="font-family:Arial,sans-serif;color:#333;">
        <h2>Customer Support SLA Audit Daily Report</h2>
        <p><strong>Generated:</strong> {now.strftime('%Y-%m-%d %H:%M')}</p>

        <h3>Flags per Audit</h3>
        <table style="border-collapse:collapse;width:45%;font-size:14px;background-color:white;">
            <tr>
                <th style="border:1px solid #ddd;padding:8px;background-color:#ADD8E6;">Audit</th>
                <th style="border:1px solid #ddd;padding:8px;background-color:#ADD8E6;">Total</th>
                <th style="border:1px solid #ddd;padding:8px;background-color:#ADD8E6;">Repeat</th>
            </tr>
    """

    for _, row in summary_df.iterrows():
        html += f"""
            <tr>
                <td style="border:1px solid #ddd;padding:8px;">{row['audit_name']}</td>
                <td style="border:1px solid #ddd;padding:8px;text-align:center;">{row['total_flags']}</td>
                <td style="border:1px solid #ddd;padding:8px;text-align:center;">{row['repeat_ratio']}</td>
            </tr>
        """

    html += "</table><br>"

    html += """
        <h3>Top Offenders</h3>
        <table style="border-collapse:collapse;width:35%;font-size:14px;background-color:white;">
            <tr>
                <th style="border:1px solid #ddd;padding:8px;background-color:#D9EAD3;">Group</th>
                <th style="border:1px solid #ddd;padding:8px;background-color:#D9EAD3;">Count</th>
            </tr>
    """

    grouping_rules = {
        "First Response SLA": "team",
        "Resolution SLA": "team",
        "Missing Owner": "team",
        "Reopened High Risk": "team",
        "Low CSAT": "owner",
        "Outside Business Hours": "team"
    }

    for audit_name, df in audit_map.items():
        group_col = grouping_rules[audit_name]
        if group_col in df.columns:
            html += create_audit_section(audit_name, df, group_col)

    html += """
        </table>
    </body>
    </html>
    """
    return html

# ────────────────────────────────────────────────
# SAVE + PRINT
# ────────────────────────────────────────────────

excel_path = save_excel_report(audit_map, summary_df, OUTPUT_DIR)
html_summary = create_html_summary(audit_map, summary_df)

print("=== SUPPORT AUDIT SUMMARY ===")
print(summary_df)
print(f"\nExcel report saved to: {excel_path}")
print("\nEmail subject:")
print(f"Customer Support SLA Audit Daily Report - {now.strftime('%Y-%m-%d')}")
print("\nHTML preview:")
print(html_summary[:1000])