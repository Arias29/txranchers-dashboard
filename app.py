import streamlit as st
import gspread
import pandas as pd
import plotly.graph_objects as go
from google.oauth2.service_account import Credentials
from datetime import date
from dateutil.relativedelta import relativedelta

# ── PAGE CONFIG ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Texas Ranchers · Dashboard",
    page_icon="🤠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── BRAND COLORS ───────────────────────────────────────────────────────────────
RED      = "#C8102E"
REDSOFT  = "#E04B62"
BONE     = "#F5F0E8"
BONEDIM  = "#A8A39B"
GREEN    = "#5FB87A"
BG       = "#0E0F11"
PANEL    = "#16181C"
PANEL2   = "#1C1F24"
LINE     = "#2A2E35"

# ── GLOBAL CSS ─────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
  html, body, [class*="css"] {{
    font-family: 'Inter', sans-serif;
    background-color: {BG};
    color: {BONE};
  }}
  .block-container {{ padding: 2rem 2.5rem 4rem; max-width: 1200px; }}
  h1,h2,h3,h4 {{ color: {BONE}; letter-spacing: -0.02em; }}
  .stButton > button {{
    background: {PANEL2}; color: {BONE}; border: 1px solid {LINE};
    border-radius: 8px; font-size: 13px; padding: 8px 16px;
    transition: border-color .15s;
  }}
  .stButton > button:hover {{ border-color: {RED}; color: {BONE}; }}
  div[data-testid="stSelectbox"] > div {{ background: {PANEL2}; border-color: {LINE}; color: {BONE}; }}
  .eyebrow {{
    font-size: 10px; letter-spacing: .22em; text-transform: uppercase;
    font-weight: 700; color: {BONEDIM}; margin: 2rem 0 .75rem;
    border-bottom: 1px solid {LINE}; padding-bottom: .5rem;
  }}
  .eyebrow span {{ color: {RED}; }}
  .card {{
    background: {PANEL}; border: 1px solid {LINE}; border-radius: 12px;
    padding: 18px; cursor: pointer; transition: border-color .15s;
  }}
  .card:hover {{ border-color: {RED}; }}
  .card .k {{ font-size: 10px; letter-spacing: .14em; text-transform: uppercase; color: {BONEDIM}; font-weight: 600; }}
  .card .v {{ font-size: 28px; font-weight: 800; margin-top: 6px; font-variant-numeric: tabular-nums; }}
  .card .up {{ color: {GREEN}; font-size: 12px; font-weight: 600; margin-top: 6px; }}
  .card .dn {{ color: {REDSOFT}; font-size: 12px; font-weight: 600; margin-top: 6px; }}
  .card .mo {{ color: {BONEDIM}; font-weight: 500; }}
  .ytd-band {{
    display: flex; align-items: stretch; flex-wrap: wrap;
    background: {PANEL2}; border: 1px solid {LINE}; border-radius: 12px;
    padding: 12px 6px; margin-top: 14px; gap: 0;
  }}
  .ytd-tag {{
    font-size: 10px; letter-spacing: .18em; text-transform: uppercase;
    font-weight: 800; color: {RED}; padding: 0 18px;
    border-right: 1px solid {LINE}; display: flex; align-items: center; line-height: 1.2;
  }}
  .ytd-item {{
    display: flex; flex-direction: column; justify-content: center;
    padding: 2px 20px; border-right: 1px solid {LINE};
  }}
  .ytd-item:last-child {{ border-right: none; }}
  .yl {{ font-size: 9px; letter-spacing: .09em; text-transform: uppercase; color: {BONEDIM}; font-weight: 600; }}
  .yv {{ font-size: 16px; font-weight: 800; font-variant-numeric: tabular-nums; margin-top: 3px; }}
  .callout {{
    font-size: 13px; background: rgba(200,16,46,.08);
    border-left: 3px solid {RED}; border-radius: 0 8px 8px 0;
    padding: 10px 14px; margin: 10px 0 16px; line-height: 1.6;
  }}
  .note {{ color: {BONEDIM}; font-size: 11px; margin-top: 8px; font-style: italic; }}
  .priority-panel {{
    background: {PANEL}; border: 1px solid #3a2026;
    box-shadow: 0 0 0 1px rgba(200,16,46,.12), 0 18px 40px -28px rgba(200,16,46,.5);
    border-radius: 14px; padding: 20px 22px;
  }}
  .drawer-table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
  .drawer-table th {{
    text-align: left; color: {BONEDIM}; font-weight: 600;
    font-size: 10px; letter-spacing: .06em; text-transform: uppercase;
    padding: 8px; border-bottom: 1px solid {LINE};
  }}
  .drawer-table td {{
    padding: 9px 8px; border-bottom: 1px solid rgba(255,255,255,.04);
    font-variant-numeric: tabular-nums;
  }}
  .chip-row {{ display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 16px; }}
  .chip {{
    background: {PANEL2}; border: 1px solid {LINE}; border-radius: 10px;
    padding: 10px 14px; flex: 1; min-width: 90px;
  }}
  .chip .cl {{ font-size: 9px; letter-spacing: .1em; text-transform: uppercase; color: {BONEDIM}; font-weight: 600; }}
  .chip .cv {{ font-size: 17px; font-weight: 800; margin-top: 4px; font-variant-numeric: tabular-nums; }}
  .tier-chip {{
    background: {PANEL2}; border: 1px solid {LINE}; border-radius: 10px;
    padding: 11px 14px; min-width: 130px; cursor: pointer; transition: border-color .15s;
  }}
  .tier-chip:hover {{ border-color: {RED}; }}
  .stCheckbox label {{ font-size: 13px; color: {BONEDIM}; }}
  footer {{ visibility: hidden; }}
</style>
""", unsafe_allow_html=True)

# ── PASSWORD GATE ──────────────────────────────────────────────────────────────
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if st.session_state.authenticated:
        return True
    st.markdown(f"""
    <div style="max-width:380px;margin:6rem auto;background:{PANEL};border:1px solid {LINE};
    border-radius:14px;padding:36px 32px;">
      <div style="font-size:11px;letter-spacing:.22em;text-transform:uppercase;
      color:{RED};font-weight:800;margin-bottom:8px;">Texas Ranchers</div>
      <div style="font-size:22px;font-weight:800;margin-bottom:4px;">Revenue Dashboard</div>
      <div style="font-size:13px;color:{BONEDIM};margin-bottom:24px;">Enter the access password to continue.</div>
    </div>
    """, unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        pwd = st.text_input("Password", type="password", label_visibility="collapsed", placeholder="Password")
        if st.button("Enter", use_container_width=True):
            if pwd == st.secrets["APP_PASSWORD"]:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password.")
    return False

if not check_password():
    st.stop()

# ── DATA LOADING ───────────────────────────────────────────────────────────────
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly",
          "https://www.googleapis.com/auth/drive.readonly"]
SHEET_ID = "1_2yQg56wqCuBA4WOyj4JrWyOLQeQR-3IO1Ju7V96y_g"

@st.cache_data(ttl=300)
def load_data():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPES)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SHEET_ID)

    # Orders tab
    orders_ws = sh.worksheet("Orders")
    orders_data = orders_ws.get_all_records()
    orders = pd.DataFrame(orders_data)

    # Monthly Summary tab
    summary_ws = sh.worksheet("Monthly Summary")
    summary_data = summary_ws.get_all_records()
    summary = pd.DataFrame(summary_data)

    return orders, summary

try:
    orders, summary = load_data()
except Exception as e:
    st.error(f"Could not load data from Google Sheets: {e}")
    st.stop()

# ── DATA PREP ──────────────────────────────────────────────────────────────────
# Parse Month Start in summary
summary["Month Start"] = pd.to_datetime(summary["Month Start"], errors="coerce")
summary = summary.dropna(subset=["Month Start"])
summary = summary.sort_values("Month Start")

# Parse dates in orders
orders["Created At"] = pd.to_datetime(orders["Created At"], errors="coerce")
orders["Month Start"] = orders["Created At"].dt.to_period("M").dt.to_timestamp()

# Latest complete month (first of last complete month)
today = date.today()
latest_month = (today.replace(day=1) - relativedelta(months=1))
latest_ts = pd.Timestamp(latest_month)
prior_ts  = latest_ts - relativedelta(months=1)

# ── HELPERS ────────────────────────────────────────────────────────────────────
def fmt_currency(v):
    if pd.isna(v) or v == 0: return "$0"
    return f"${v:,.2f}"

def fmt_delta(current, prior):
    if prior == 0 or pd.isna(prior): return "—", ""
    pct = (current - prior) / prior * 100
    arrow = "▲" if pct >= 0 else "▼"
    css   = "up" if pct >= 0 else "dn"
    return f"{arrow} {abs(pct):.1f}% <span class='mo'>vs prior mo</span>", css

def get_summary_val(col, month_ts):
    row = summary[summary["Month Start"] == month_ts]
    if row.empty or col not in row.columns: return 0
    v = row.iloc[0][col]
    return float(str(v).replace("$","").replace(",","")) if v != "" else 0

def summary_months():
    return summary[summary["Month Start"] <= latest_ts]["Month Start"].sort_values(ascending=False).unique()

def month_label(ts):
    return pd.Timestamp(ts).strftime("%b %Y")

# ── CURRENT MONTH VALUES ───────────────────────────────────────────────────────
merch_rev    = get_summary_val("Merch Revenue", latest_ts)
merch_rev_p  = get_summary_val("Merch Revenue", prior_ts)
mrr          = get_summary_val("Membership Revenue", latest_ts)
mrr_p        = get_summary_val("Membership Revenue", prior_ts)
active_mem   = get_summary_val("Active Members", latest_ts)
active_mem_p = get_summary_val("Active Members", prior_ts)
new_mem      = get_summary_val("New Members", latest_ts)
new_mem_p    = get_summary_val("New Members", prior_ts)
total_rev    = merch_rev + mrr
total_rev_p  = merch_rev_p + mrr_p

# YTD (2026 Jan – latest complete)
ytd_start = pd.Timestamp(f"{latest_ts.year}-01-01")
ytd = summary[(summary["Month Start"] >= ytd_start) & (summary["Month Start"] <= latest_ts)]
ytd_total     = ytd["Merch Revenue"].astype(float).sum() + ytd["Membership Revenue"].astype(float).sum()
ytd_merch     = ytd["Merch Revenue"].astype(float).sum()
ytd_membership= ytd["Membership Revenue"].astype(float).sum()
ytd_orders    = ytd["Merch Orders"].astype(float).sum() if "Merch Orders" in ytd.columns else 0

# ── DRAWER STATE ───────────────────────────────────────────────────────────────
if "drawer" not in st.session_state:
    st.session_state.drawer = None
if "drawer_data" not in st.session_state:
    st.session_state.drawer_data = {}

def open_drawer(key, title, eyebrow, chips, df):
    st.session_state.drawer = key
    st.session_state.drawer_data = {"title": title, "eyebrow": eyebrow, "chips": chips, "df": df}

def close_drawer():
    st.session_state.drawer = None
    st.session_state.drawer_data = {}

# ── DRAWER DATASETS ────────────────────────────────────────────────────────────
def drawer_total_rev():
    df = orders[orders["Month Start"] == latest_ts][["Order Name","Created At","Email","Product Category","Adjusted Revenue"]].copy()
    df["Created At"] = df["Created At"].dt.strftime("%b %d")
    df.columns = ["Order","Date","Customer","Type","Revenue"]
    df["Revenue"] = df["Revenue"].apply(lambda x: fmt_currency(float(str(x).replace(",",""))) if x != "" else "$0")
    chips = [{"l":"Total","v":fmt_currency(total_rev)},{"l":"Merch","v":fmt_currency(merch_rev)},{"l":"Membership","v":fmt_currency(mrr)}]
    open_drawer("total_rev", f"Total Revenue · {month_label(latest_ts)}", "Monthly · All Revenue", chips, df)

def drawer_mrr():
    df = orders[(orders["Month Start"]==latest_ts)&(orders["Product Category"]=="Membership")][["Email","Membership Tier","Subscription Event","Adjusted Revenue"]].copy()
    df.columns = ["Member","Tier","Status","Charge"]
    df["Charge"] = df["Charge"].apply(lambda x: fmt_currency(float(str(x).replace(",",""))) if x != "" else "$0")
    chips = [{"l":"MRR","v":fmt_currency(mrr)},{"l":"Members","v":str(int(active_mem))}]
    open_drawer("mrr", f"MRR · {month_label(latest_ts)}", "Monthly · Membership", chips, df)

def drawer_active():
    df = orders[(orders["Month Start"]==latest_ts)&(orders["Product Category"]=="Membership")][["Email","Membership Tier","Subscription Event","Created At"]].copy()
    df["Created At"] = df["Created At"].dt.strftime("%b %d")
    df.columns = ["Member","Tier","Status","Last Charge"]
    chips = [{"l":"Active","v":str(int(active_mem))},{"l":"MRR","v":fmt_currency(mrr)}]
    open_drawer("active", f"Active Members · {month_label(latest_ts)}", "Monthly · Active", chips, df)

def drawer_new():
    df = orders[(orders["Month Start"]==latest_ts)&(orders["Product Category"]=="Membership")&(orders["Subscription Event"]=="First Order")][["Email","Membership Tier","Created At"]].copy()
    df["Created At"] = df["Created At"].dt.strftime("%b %d")
    df.columns = ["Member","Tier","Date"]
    chips = [{"l":"New","v":str(int(new_mem))},{"l":"Month","v":month_label(latest_ts)}]
    open_drawer("new", f"New Members · {month_label(latest_ts)}", "Monthly · New Signups", chips, df)

def drawer_ytd_total():
    rows = []
    for _,r in ytd.iterrows():
        m = fmt_currency(float(r["Merch Revenue"]))
        mem = fmt_currency(float(r["Membership Revenue"]))
        t = fmt_currency(float(r["Merch Revenue"])+float(r["Membership Revenue"]))
        rows.append([month_label(r["Month Start"]),m,mem,t])
    df = pd.DataFrame(rows,columns=["Month","Merch","Membership","Total"])
    chips=[{"l":"Total","v":fmt_currency(ytd_total)},{"l":"Months","v":f"Jan–{month_label(latest_ts)}"}]
    open_drawer("ytd_total","2026 YTD · Total Revenue","YTD · All Streams",chips,df)

def drawer_ytd_merch():
    rows=[]
    for _,r in ytd.iterrows():
        rows.append([month_label(r["Month Start"]),fmt_currency(float(r["Merch Revenue"])),str(int(float(r.get("Merch Orders",0)))),str(int(float(r.get("Merch Units",0))))])
    df=pd.DataFrame(rows,columns=["Month","Revenue","Orders","Units"])
    chips=[{"l":"Merch","v":fmt_currency(ytd_merch)},{"l":"Orders","v":str(int(ytd_orders))}]
    open_drawer("ytd_merch","2026 YTD · Merch","YTD · Merchandise",chips,df)

def drawer_ytd_membership():
    rows=[]
    for _,r in ytd.iterrows():
        rows.append([month_label(r["Month Start"]),fmt_currency(float(r["Membership Revenue"])),str(int(float(r.get("Active Members",0)))),str(int(float(r.get("New Members",0))))])
    df=pd.DataFrame(rows,columns=["Month","MRR","Active","New"])
    chips=[{"l":"Membership","v":fmt_currency(ytd_membership)},{"l":"Active now","v":str(int(active_mem))}]
    open_drawer("ytd_membership","2026 YTD · Membership","YTD · TRAP",chips,df)

def drawer_ytd_active():
    df = orders[(orders["Month Start"]==latest_ts)&(orders["Product Category"]=="Membership")][["Email","Membership Tier","Subscription Event","Created At"]].copy()
    df["Created At"]=df["Created At"].dt.strftime("%b %d")
    df.columns=["Member","Tier","Status","Last Charge"]
    chips=[{"l":"Active now","v":str(int(active_mem))},{"l":"Adult","v":"11"},{"l":"Junior","v":"1"}]
    open_drawer("ytd_active","Current Active Members","Point-in-time · Now",chips,df)

def drawer_ytd_orders():
    rows=[]
    for _,r in ytd.iterrows():
        rev=float(r["Merch Revenue"]); ords=float(r.get("Merch Orders",0))
        aov=fmt_currency(rev/ords) if ords>0 else "—"
        rows.append([month_label(r["Month Start"]),str(int(ords)),fmt_currency(rev),aov])
    df=pd.DataFrame(rows,columns=["Month","Orders","Revenue","AOV"])
    chips=[{"l":"Orders","v":str(int(ytd_orders))},{"l":"Revenue","v":fmt_currency(ytd_merch)}]
    open_drawer("ytd_orders","2026 YTD · Merch Orders","YTD · Orders",chips,df)

def drawer_product(product_name):
    df=orders[(orders["Line Item Title"]==product_name)&(orders["Product Category"]=="Merchandise")][["Order Name","Created At","Email","Variant Title","Quantity","Adjusted Revenue"]].copy()
    df["Created At"]=df["Created At"].dt.strftime("%b %d")
    df.columns=["Order","Date","Customer","Variant","Qty","Revenue"]
    df["Revenue"]=df["Revenue"].apply(lambda x: fmt_currency(float(str(x).replace(",",""))) if x!="" else "$0")
    total=df["Revenue"].count()
    chips=[{"l":"Product","v":product_name[:20]},{"l":"Orders","v":str(len(df))}]
    open_drawer(f"prod_{product_name}",product_name,"Product · Detail",chips,df)

def drawer_tier(tier):
    df=orders[(orders["Month Start"]==latest_ts)&(orders["Membership Tier"]==tier)][["Email","Subscription Event","Created At"]].copy()
    df["Created At"]=df["Created At"].dt.strftime("%b %d")
    df.columns=["Member","Status","Last Charge"]
    count=len(df)
    price=160 if tier=="Junior" else 150
    chips=[{"l":"Members","v":str(count)},{"l":"MRR","v":fmt_currency(count*price)},{"l":"Price","v":f"${price}"}]
    open_drawer(f"tier_{tier}",f"TRAP {tier}","Membership · Tier",chips,df)

def drawer_month(month_label_str, month_ts):
    df=orders[(orders["Month Start"]==month_ts)&(orders["Product Category"]=="Membership")][["Email","Membership Tier","Subscription Event","Created At"]].copy()
    df["Created At"]=df["Created At"].dt.strftime("%b %d")
    df.columns=["Member","Tier","Status","Date"]
    active=get_summary_val("Active Members",month_ts)
    new=get_summary_val("New Members",month_ts)
    mrr_val=get_summary_val("Membership Revenue",month_ts)
    chips=[{"l":"Active","v":str(int(active))},{"l":"New","v":str(int(new))},{"l":"MRR","v":fmt_currency(mrr_val)}]
    open_drawer(f"month_{month_label_str}",f"{month_label_str} · Membership","Monthly · Detail",chips,df)

# ── RENDER DRAWER ──────────────────────────────────────────────────────────────
def render_drawer():
    if not st.session_state.drawer:
        return
    d = st.session_state.drawer_data
    with st.sidebar:
        st.markdown(f"""
        <div style='font-size:10px;letter-spacing:.2em;text-transform:uppercase;color:{RED};font-weight:800;margin-bottom:6px'>{d['eyebrow']}</div>
        <div style='font-size:20px;font-weight:800;margin-bottom:16px'>{d['title']}</div>
        """, unsafe_allow_html=True)
        chips_html = "<div class='chip-row'>"
        for c in d["chips"]:
            chips_html += f"<div class='chip'><div class='cl'>{c['l']}</div><div class='cv'>{c['v']}</div></div>"
        chips_html += "</div>"
        st.markdown(chips_html, unsafe_allow_html=True)
        st.markdown(f"<div style='font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:{BONEDIM};font-weight:700;margin:8px 0 10px'>Transactions</div>", unsafe_allow_html=True)
        df = d["df"]
        if df.empty:
            st.markdown(f"<div style='color:{BONEDIM};font-size:13px;padding:20px 0;text-align:center'>No records in this slice.</div>", unsafe_allow_html=True)
        else:
            tbl = "<table class='drawer-table'><thead><tr>"
            for col in df.columns:
                tbl += f"<th>{col}</th>"
            tbl += "</tr></thead><tbody>"
            for _, row in df.iterrows():
                tbl += "<tr>" + "".join(f"<td>{v}</td>" for v in row) + "</tr>"
            tbl += "</tbody></table>"
            st.markdown(tbl, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("✕  Close", use_container_width=True):
            close_drawer()
            st.rerun()

# ── HEADER ─────────────────────────────────────────────────────────────────────
col_brand, col_controls = st.columns([2, 3])
with col_brand:
    st.markdown(f"""
    <div style='border-left:3px solid {RED};padding-left:14px;margin-top:8px'>
      <div style='font-size:16px;font-weight:800;letter-spacing:.16em;text-transform:uppercase'>{month_label(latest_ts)}</div>
      <div style='font-size:10px;letter-spacing:.28em;color:{BONEDIM};font-weight:600;text-transform:uppercase'>Revenue &amp; Membership Dashboard</div>
    </div>
    """, unsafe_allow_html=True)
with col_controls:
    c1, c2, c3 = st.columns([2,1,1])
    with c1:
        month_options = [month_label(m) for m in summary_months()]
        selected_label = st.selectbox("Period", month_options, label_visibility="collapsed")
    with c2:
        exclude_internal = st.checkbox("Exclude internal", value=False)
    with c3:
        st.markdown(f"<a href='https://docs.google.com/spreadsheets/d/{SHEET_ID}' target='_blank' style='color:{BONEDIM};font-size:13px;text-decoration:none'>View in Sheets ↗</a>", unsafe_allow_html=True)

st.markdown(f"<div style='font-size:12px;color:{BONEDIM};margin-top:4px'>Compared to prior month · Data refreshes every 5 min</div>", unsafe_allow_html=True)
st.markdown("---")

# ── HERO CARDS ─────────────────────────────────────────────────────────────────
def hero_card(label, value, delta_html, css, key, on_click):
    col = st.container()
    html = f"""
    <div class='card' onclick='void(0)'>
      <div class='k'>{label}</div>
      <div class='v'>{value}</div>
      <div class='{css}'>{delta_html}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
    if st.button(f"Detail →", key=key, use_container_width=True):
        on_click()
        st.rerun()

h1,h2,h3,h4 = st.columns(4)
d1,css1 = fmt_delta(total_rev, total_rev_p)
d2,css2 = fmt_delta(mrr, mrr_p)
d3,css3 = fmt_delta(active_mem, active_mem_p)
d4,css4 = fmt_delta(new_mem, new_mem_p)

with h1:
    st.markdown(f"<div class='card'><div class='k'>Total Revenue</div><div class='v'>{fmt_currency(total_rev)}</div><div class='{css1}'>{d1}</div></div>", unsafe_allow_html=True)
    if st.button("Detail →", key="btn_total", use_container_width=True): drawer_total_rev(); st.rerun()
with h2:
    st.markdown(f"<div class='card'><div class='k'>MRR</div><div class='v'>{fmt_currency(mrr)}</div><div class='{css2}'>{d2}</div></div>", unsafe_allow_html=True)
    if st.button("Detail →", key="btn_mrr", use_container_width=True): drawer_mrr(); st.rerun()
with h3:
    st.markdown(f"<div class='card'><div class='k'>Active Members</div><div class='v'>{int(active_mem)}</div><div class='{css3}'>{d3}</div></div>", unsafe_allow_html=True)
    if st.button("Detail →", key="btn_active", use_container_width=True): drawer_active(); st.rerun()
with h4:
    st.markdown(f"<div class='card'><div class='k'>New Members</div><div class='v'>{int(new_mem)}</div><div class='{css4}'>{d4}</div></div>", unsafe_allow_html=True)
    if st.button("Detail →", key="btn_new", use_container_width=True): drawer_new(); st.rerun()

# ── YTD BAND ───────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class='ytd-band'>
  <div class='ytd-tag'>2026<br>YTD</div>
  <div class='ytd-item'><span class='yl'>Total Revenue</span><span class='yv'>{fmt_currency(ytd_total)}</span></div>
  <div class='ytd-item'><span class='yl'>Merch</span><span class='yv'>{fmt_currency(ytd_merch)}</span></div>
  <div class='ytd-item'><span class='yl'>Membership</span><span class='yv'>{fmt_currency(ytd_membership)}</span></div>
  <div class='ytd-item'><span class='yl'>Active Members · now</span><span class='yv'>{int(active_mem)}</span></div>
  <div class='ytd-item'><span class='yl'>Merch Orders</span><span class='yv'>{int(ytd_orders)}</span></div>
</div>
""", unsafe_allow_html=True)

yb1,yb2,yb3,yb4,yb5 = st.columns(5)
with yb1:
    if st.button("Total Rev ↗", key="ytd_tr", use_container_width=True): drawer_ytd_total(); st.rerun()
with yb2:
    if st.button("Merch ↗", key="ytd_m", use_container_width=True): drawer_ytd_merch(); st.rerun()
with yb3:
    if st.button("Membership ↗", key="ytd_mem", use_container_width=True): drawer_ytd_membership(); st.rerun()
with yb4:
    if st.button("Active ↗", key="ytd_a", use_container_width=True): drawer_ytd_active(); st.rerun()
with yb5:
    if st.button("Orders ↗", key="ytd_o", use_container_width=True): drawer_ytd_orders(); st.rerun()

# ── MEMBERSHIP HEALTH ──────────────────────────────────────────────────────────
st.markdown(f"<div class='eyebrow'><span>Priority</span> · Membership Health</div>", unsafe_allow_html=True)
st.markdown(f"<div class='priority-panel'>", unsafe_allow_html=True)

mem_summary = summary[summary["Month Start"] >= pd.Timestamp("2026-01-01")].copy()
months_labels = [month_label(m) for m in mem_summary["Month Start"]]
active_vals = mem_summary["Active Members"].astype(float).tolist()
new_vals    = mem_summary["New Members"].astype(float).tolist()
mrr_vals    = mem_summary["Membership Revenue"].astype(float).tolist()

st.markdown(f"""
<div class='callout'>
Acquisition has <b style='color:{REDSOFT}'>paused</b>. After a surge in April, new members fell to zero while the active base declined.
The recurring engine is contracting — <b style='color:{REDSOFT}'>retention is the priority, not volume.</b>
</div>
""", unsafe_allow_html=True)

mc1, mc2 = st.columns([1.4, 1])
with mc1:
    fig_mem = go.Figure()
    fig_mem.add_trace(go.Bar(name="New signups", x=months_labels, y=new_vals,
        marker_color="rgba(200,16,46,0.35)", marker_line_color=RED, marker_line_width=1,
        yaxis="y", opacity=0.9))
    fig_mem.add_trace(go.Scatter(name="Active members", x=months_labels, y=active_vals,
        line=dict(color=REDSOFT, width=2.5), mode="lines+markers",
        marker=dict(size=5, color=REDSOFT), yaxis="y"))
    fig_mem.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color=BONEDIM, height=270, margin=dict(l=0,r=0,t=20,b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, font_size=11),
        xaxis=dict(showgrid=False, color=BONEDIM),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.04)", color=BONEDIM, tickformat="d"),
        barmode="overlay")
    st.plotly_chart(fig_mem, use_container_width=True, config={"displayModeBar": False})

with mc2:
    fig_mrr = go.Figure()
    fig_mrr.add_trace(go.Scatter(name="MRR", x=months_labels, y=mrr_vals,
        line=dict(color=BONE, width=2), fill="tozeroy",
        fillcolor="rgba(245,240,232,0.06)", mode="lines+markers",
        marker=dict(size=4, color=BONE)))
    fig_mrr.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color=BONEDIM, height=270, margin=dict(l=0,r=0,t=20,b=0),
        showlegend=False, title=dict(text="Monthly Recurring Revenue", font_color=BONEDIM, font_size=11, x=0),
        xaxis=dict(showgrid=False, color=BONEDIM),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.04)", color=BONEDIM, tickprefix="$", tickformat=",.0f"))
    st.plotly_chart(fig_mrr, use_container_width=True, config={"displayModeBar": False})

# Month click buttons
st.markdown(f"<div style='font-size:10px;color:{BONEDIM};margin-bottom:6px;letter-spacing:.08em'>CLICK A MONTH FOR MEMBER DETAIL</div>", unsafe_allow_html=True)
month_cols = st.columns(len(months_labels))
for i, (ml, mts) in enumerate(zip(months_labels, mem_summary["Month Start"])):
    with month_cols[i]:
        if st.button(ml, key=f"mo_{i}", use_container_width=True):
            drawer_month(ml, pd.Timestamp(mts))
            st.rerun()

# Tier breakdown
st.markdown(f"<div style='border-top:1px solid {LINE};margin:18px 0 14px'></div>", unsafe_allow_html=True)
tier_cols = st.columns([1, 3])
with tier_cols[0]:
    fig_tier = go.Figure(go.Pie(
        labels=["Adult","Junior","Senior"], values=[11,1,0],
        marker_colors=[RED,"#E8836F","#C9A24B"],
        hole=0.64, textinfo="none"))
    fig_tier.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", height=160, margin=dict(l=0,r=0,t=0,b=0),
        showlegend=False,
        annotations=[dict(text="by tier", x=0.5, y=0.5, font_size=10, font_color=BONEDIM, showarrow=False)])
    st.plotly_chart(fig_tier, use_container_width=True, config={"displayModeBar": False})
with tier_cols[1]:
    tc1, tc2, tc3 = st.columns(3)
    with tc1:
        st.markdown(f"<div class='tier-chip'><div style='font-size:10px;color:{BONEDIM};font-weight:600;text-transform:uppercase;letter-spacing:.08em'>● Adult</div><div style='font-size:20px;font-weight:800;margin-top:4px'>11</div><div style='font-size:11px;color:{BONEDIM};margin-top:2px'>$1,650 MRR · $150</div></div>", unsafe_allow_html=True)
        if st.button("Adult →", key="tier_adult", use_container_width=True): drawer_tier("Adult"); st.rerun()
    with tc2:
        st.markdown(f"<div class='tier-chip'><div style='font-size:10px;color:#E8836F;font-weight:600;text-transform:uppercase;letter-spacing:.08em'>● Junior</div><div style='font-size:20px;font-weight:800;margin-top:4px'>1</div><div style='font-size:11px;color:{BONEDIM};margin-top:2px'>$160 MRR · $160</div></div>", unsafe_allow_html=True)
        if st.button("Junior →", key="tier_junior", use_container_width=True): drawer_tier("Junior"); st.rerun()
    with tc3:
        st.markdown(f"<div class='tier-chip'><div style='font-size:10px;color:#C9A24B;font-weight:600;text-transform:uppercase;letter-spacing:.08em'>● Senior</div><div style='font-size:20px;font-weight:800;margin-top:4px'>0</div><div style='font-size:11px;color:{BONEDIM};margin-top:2px'>no members yet</div></div>", unsafe_allow_html=True)
        if st.button("Senior →", key="tier_senior", use_container_width=True): drawer_tier("Senior"); st.rerun()

st.markdown(f"<div class='note'>Membership status derived from Shopify subscription orders. Dips may include billing-cycle timing, not only cancellations.</div>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# ── REVENUE TREND ──────────────────────────────────────────────────────────────
st.markdown(f"<div class='eyebrow'><span>Context</span> · Revenue Over Time</div>", unsafe_allow_html=True)
st.markdown(f"""<div class='callout' style='background:rgba(245,240,232,.04);border-left-color:{BONEDIM}'>
Merch is <b style='color:{BONE}'>event-driven</b>. The May and October 2025 spikes are tentpole months.
June's softness is a seasonal trough, not a decline.</div>""", unsafe_allow_html=True)

all_months = summary["Month Start"].tolist()
all_labels = [month_label(m) for m in all_months]
merch_vals_all = summary["Merch Revenue"].astype(float).tolist()
mem_vals_all   = summary["Membership Revenue"].astype(float).tolist()

fig_rev = go.Figure()
fig_rev.add_trace(go.Bar(name="Merch", x=all_labels, y=merch_vals_all,
    marker_color="rgba(245,240,232,0.55)", marker_line_width=0))
fig_rev.add_trace(go.Bar(name="Membership", x=all_labels, y=mem_vals_all,
    marker_color=RED, marker_line_width=0))
fig_rev.update_layout(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font_color=BONEDIM, height=300, margin=dict(l=0,r=0,t=10,b=0),
    barmode="stack", legend=dict(orientation="h", yanchor="bottom", y=1.02, font_size=11),
    xaxis=dict(showgrid=False, color=BONEDIM, tickangle=0),
    yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.04)", color=BONEDIM, tickprefix="$", tickformat=",.0f"))
st.plotly_chart(fig_rev, use_container_width=True, config={"displayModeBar": False})

# ── OPERATIONS ─────────────────────────────────────────────────────────────────
st.markdown(f"<div class='eyebrow'><span>Operations</span> · What's Selling</div>", unsafe_allow_html=True)
op1, op2 = st.columns(2)

with op1:
    st.markdown(f"<div style='font-size:14px;font-weight:700;margin-bottom:12px'>Top Products <span style='font-size:11px;color:{BONEDIM}'>by revenue · all time</span></div>", unsafe_allow_html=True)
    top_prods = (orders[orders["Product Category"]=="Merchandise"]
        .groupby("Line Item Title")["Adjusted Revenue"]
        .sum().sort_values(ascending=False).head(10).reset_index())
    top_prods.columns = ["Product","Revenue"]
    max_rev = top_prods["Revenue"].max()
    for _, row in top_prods.iterrows():
        pct = int(row["Revenue"]/max_rev*100)
        name = row["Product"]
        rev  = fmt_currency(row["Revenue"])
        st.markdown(f"""
        <div style='margin-bottom:10px;cursor:pointer;padding:3px 4px;border-radius:6px' 
             onmouseover="this.style.background='#1C1F24'" onmouseout="this.style.background='transparent'">
          <div style='display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px'>
            <span>{name}</span><span style='font-weight:700'>{rev}</span>
          </div>
          <div style='height:6px;background:#1C1F24;border-radius:3px;overflow:hidden'>
            <div style='height:100%;width:{pct}%;background:linear-gradient(90deg,{RED},{REDSOFT});border-radius:3px'></div>
          </div>
        </div>""", unsafe_allow_html=True)
        if st.button(f"↗", key=f"prod_{name[:20]}", use_container_width=False):
            drawer_product(name); st.rerun()

with op2:
    st.markdown(f"<div style='font-size:14px;font-weight:700;margin-bottom:12px'>Category Mix <span style='font-size:11px;color:{BONEDIM}'>share of merch revenue</span></div>", unsafe_allow_html=True)
    cat_data = (orders[orders["Product Category"]=="Merchandise"]
        .groupby("Merch Bucket")["Adjusted Revenue"]
        .sum().sort_values(ascending=False).reset_index())
    cat_data.columns = ["Category","Revenue"]
    cat_colors = [RED,REDSOFT,"#7E1220","#E8836F","#C9A24B","#5FB87A","#5B6BB0","#6E727A"]
    fig_cat = go.Figure(go.Pie(
        labels=cat_data["Category"], values=cat_data["Revenue"],
        marker_colors=cat_colors[:len(cat_data)],
        hole=0.62, textinfo="none"))
    fig_cat.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", height=260, margin=dict(l=0,r=0,t=0,b=0),
        legend=dict(font_size=11, orientation="v"))
    st.plotly_chart(fig_cat, use_container_width=True, config={"displayModeBar": False})
    st.markdown(f"<div class='note'>Based on Merch Bucket column in Orders tab.</div>", unsafe_allow_html=True)

# ── FOOTER ─────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(f"<div style='color:{BONEDIM};font-size:11.5px'>Data source: Shopify online sales only. Square in-person and TIXR ticketing not included — figures will not match QuickBooks totals.</div>", unsafe_allow_html=True)

# ── RENDER DRAWER ──────────────────────────────────────────────────────────────
render_drawer()
