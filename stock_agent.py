import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import io
import os
import re
import json
import base64
import socket
import urllib3.util.connection as urllib3_cn
from datetime import datetime, timezone, timedelta

# Force IPv4 to prevent Indian ISP IPv6 timeout hangs
urllib3_cn.allowed_gai_family = lambda: socket.AF_INET

# Optional Angel One SmartAPI Imports
try:
    from SmartApi import SmartConnect
    import pyotp
    SMARTAPI_AVAILABLE = True
except ImportError:
    SMARTAPI_AVAILABLE = False

# ---------------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------------
st.set_page_config(
    page_title="Ultimate Stock Market AI Agent",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# CONSTANTS, UNIVERSES & IMPORTANT INDIAN MARKET LINKS
# ---------------------------------------------------------
PAPER_FILE = "paper_portfolio.json"

DEFAULT_WATCHLIST = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
    "BEL", "TATAPOWER", "KPITTECH", "COALINDIA", "IRCTC",
    "AXISBANK", "HAL", "SUNPHARMA", "M&M", "NTPC", "LT",
    "TATASTEEL", "HINDALCO", "SBIN", "BAJFINANCE"
]

NSE_INDEX_URLS = {
    "NSE: Nifty 50": "https://www.niftyindices.com/IndexConstituent/ind_nifty50list.csv",
    "NSE: Nifty Next 50": "https://www.niftyindices.com/IndexConstituent/ind_niftynext50list.csv",
    "NSE: Nifty Midcap 100": "https://www.niftyindices.com/IndexConstituent/ind_niftymidcap100list.csv",
    "NSE: Nifty Smallcap 100": "https://www.niftyindices.com/IndexConstituent/ind_niftysmallcap100list.csv",
    "NSE Sectoral: Nifty Bank": "https://www.niftyindices.com/IndexConstituent/ind_niftybanklist.csv",
    "NSE Sectoral: Nifty PSU Bank": "https://www.niftyindices.com/IndexConstituent/ind_niftypsubanklist.csv",
    "NSE Sectoral: Nifty IT": "https://www.niftyindices.com/IndexConstituent/ind_niftyitlist.csv",
    "NSE Sectoral: Nifty Auto": "https://www.niftyindices.com/IndexConstituent/ind_niftyautolist.csv",
    "NSE Sectoral: Nifty Pharma": "https://www.niftyindices.com/IndexConstituent/ind_niftypharmalist.csv",
    "NSE Sectoral: Nifty FMCG": "https://www.niftyindices.com/IndexConstituent/ind_niftyfmcglist.csv",
    "NSE Sectoral: Nifty Metal": "https://www.niftyindices.com/IndexConstituent/ind_niftymetallist.csv",
    "NSE Sectoral: Nifty Energy": "https://www.niftyindices.com/IndexConstituent/ind_niftyenergylist.csv",
    "NSE Sectoral: Nifty Realty": "https://www.niftyindices.com/IndexConstituent/ind_niftyrealtylist.csv",
    "NSE Sectoral: Nifty Financial Services": "https://www.niftyindices.com/IndexConstituent/ind_niftyfinancelist.csv",
}

BSE_INDEX_LISTS = {
    "BSE: Sensex 30": [
        "RELIANCE.BO", "TCS.BO", "HDFCBANK.BO", "ICICIBANK.BO", "BHARTIARTL.BO",
        "SBIN.BO", "INFY.BO", "ITC.BO", "HINDUNILVR.BO", "LT.BO",
        "BAJFINANCE.BO", "HCLTECH.BO", "MARUTI.BO", "SUNPHARMA.BO", "ADANIPORTS.BO",
        "KOTAKBANK.BO", "TITAN.BO", "AXISBANK.BO", "ULTRACEMCO.BO", "NTPC.BO",
        "M&M.BO", "TATAMOTORS.BO", "POWERGRID.BO", "ASIANPAINT.BO", "BAJAJFINSV.BO",
        "NESTLEIND.BO", "JSWSTEEL.BO", "TATASTEEL.BO", "TECHM.BO", "INDUSINDBK.BO"
    ],
    "BSE Sectoral: BSE Bankex": [
        "HDFCBANK.BO", "ICICIBANK.BO", "SBIN.BO", "KOTAKBANK.BO", "AXISBANK.BO",
        "INDUSINDBK.BO", "BANKBARODA.BO", "FEDERALBNK.BO", "AUBANK.BO", "CANBK.BO"
    ]
}

MACRO_BLACKOUT_DATES = {
    "2026-12-04": "RBI MPC Policy Decision",
    "2027-02-01": "Union Budget Day",
    "2027-02-05": "RBI MPC Policy Decision",
    "2027-04-09": "RBI MPC Policy Decision",
}

IMPORTANT_INDIAN_LINKS = {
    "🏛️ Exchanges & Regulators": [
        ("NSE India (Official)", "https://www.nseindia.com/"),
        ("BSE India (Official)", "https://www.bseindia.com/"),
        ("SEBI (Regulator & Filings)", "https://www.sebi.gov.in/"),
        ("RBI (Monetary Policy)", "https://www.rbi.org.in/"),
        ("Nifty Indices (Constituents)", "https://www.niftyindices.com/")
    ],
    "🔍 Screeners & Charting": [
        ("Screener.in (Fundamentals)", "https://www.screener.in/"),
        ("TradingView India (Charts)", "https://in.tradingview.com/"),
        ("Chartink (Technical Scans)", "https://chartink.com/"),
        ("Tickertape (MMI & Ratios)", "https://www.tickertape.in/"),
        ("Trendlyne (Forensics & DVM)", "https://trendlyne.com/"),
        ("Tijori Finance (Deep Data)", "https://www.tijorifinance.com/")
    ],
    "📰 News, FII/DII & Broker API": [
        ("Moneycontrol Markets", "https://www.moneycontrol.com/stocksmarketsindia/"),
        ("Economic Times Markets", "https://economictimes.indiatimes.com/markets"),
        ("Chittorgarh (IPO & GMP)", "https://www.chittorgarh.com/"),
        ("NSE Option Chain", "https://www.nseindia.com/option-chain"),
        ("Angel One SmartAPI Portal", "https://smartapi.angelbroking.com/")
    ]
}

# ---------------------------------------------------------
# SIMPLY WALL ST INSPIRED GLASSMORPHISM THEME ENGINE
# ---------------------------------------------------------
def inject_modern_theme(is_dark, bg_css, overlay_alpha, blur_px):
    if is_dark:
        # Simply Wall St Deep Slate Dashboard Palette
        text_color, subtext_color = "#f1f5f9", "#94a3b8"
        accent_gold = "#eab308"
        card_bg, sidebar_bg = "rgba(26, 34, 46, 0.78)", "rgba(17, 23, 33, 0.90)"
        border_color = "rgba(255, 255, 255, 0.10)"
        overlay_rgba = f"rgba(15, 21, 30, {overlay_alpha})"
        kill_bg, pass_bg = "rgba(239, 68, 68, 0.16)", "rgba(16, 185, 129, 0.16)"
        input_bg = "rgba(21, 27, 36, 0.85)"
        btn_bg = "linear-gradient(135deg, #2563eb, #1d4ed8)"
        btn_txt = "#ffffff"
        hero_bg = "linear-gradient(135deg, rgba(26, 34, 46, 0.88), rgba(30, 41, 59, 0.75))"
        shadow = "0 10px 30px rgba(0, 0, 0, 0.40)"
        light_overrides = ""
    else:
        # Simply Wall St Editorial Cream & Gold Palette (High-Contrast Dark Text)
        text_color, subtext_color = "#111827", "#374151"
        accent_gold = "#92400e"
        card_bg, sidebar_bg = "rgba(255, 253, 248, 0.92)", "rgba(244, 240, 231, 0.96)"
        border_color = "rgba(17, 24, 39, 0.16)"
        overlay_rgba = f"rgba(245, 242, 235, {overlay_alpha})"
        kill_bg, pass_bg = "rgba(239, 68, 68, 0.14)", "rgba(16, 185, 129, 0.14)"
        input_bg = "#ffffff"
        btn_bg = "linear-gradient(135deg, #facc15, #eab308)"
        btn_txt = "#111827"
        hero_bg = "linear-gradient(135deg, rgba(255, 253, 248, 0.96), rgba(244, 238, 224, 0.92))"
        shadow = "0 8px 26px rgba(17, 24, 39, 0.08)"
        light_overrides = f"""
        /* Force crisp dark text across all Streamlit widgets in Light Mode */
        .stApp p, .stApp span, .stApp label, .stApp li,
        .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
        div[data-testid="stMarkdownContainer"] *,
        div[data-testid="stMetricLabel"] *,
        div[data-testid="stMetricValue"] *,
        div[data-testid="stCaptionContainer"] *,
        section[data-testid="stSidebar"] p,
        section[data-testid="stSidebar"] span,
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3,
        div[data-testid="stExpander"] summary *,
        .stTabs [data-baseweb="tab"] *,
        .stSelectbox div[data-baseweb="select"] * {{
            color: {text_color} !important;
        }}
        .stSelectbox div[data-baseweb="select"] > div {{
            background-color: {input_bg} !important;
            border-color: {border_color} !important;
        }}
        .stButton > button:not([kind="primary"]) {{
            background-color: #ffffff !important;
            color: {text_color} !important;
            border: 1px solid {border_color} !important;
        }}
        div[data-testid="stExpander"] {{
            background-color: {card_bg} !important;
            border: 1px solid {border_color} !important;
            border-radius: 12px !important;
        }}
        """

    css = f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
        html, body, [class*="css"] {{ font-family: 'Plus Jakarta Sans', sans-serif !important; color: {text_color} !important; }}
        .stApp {{ {bg_css} background-size: cover !important; background-position: center !important; background-attachment: fixed !important; }}
        .stApp::before {{ content: ""; position: fixed; inset: 0; background: {overlay_rgba}; backdrop-filter: blur({blur_px}px); -webkit-backdrop-filter: blur({blur_px}px); z-index: 0; pointer-events: none; }}
        .main .block-container {{ position: relative; z-index: 1; padding-top: 1.3rem; }}
        section[data-testid="stSidebar"] {{ background: {sidebar_bg} !important; backdrop-filter: blur(18px) !important; border-right: 1px solid {border_color} !important; }}
        header[data-testid="stHeader"] {{ background: transparent !important; }}
        .hero-header {{ background: {hero_bg}; border: 1px solid {border_color}; backdrop-filter: blur(16px); border-radius: 16px; padding: 20px 26px; margin-bottom: 18px; box-shadow: {shadow}; }}
        .hero-title {{ font-size: 1.85rem; font-weight: 800; margin: 0; letter-spacing: -0.02em; }}
        .hero-accent {{ color: {accent_gold} !important; }}
        .hero-sub {{ font-size: 0.93rem; color: {subtext_color} !important; margin-top: 5px; margin-bottom: 0; }}
        .setup-card {{ background: {card_bg}; backdrop-filter: blur(16px); border: 1px solid {border_color}; border-radius: 14px; padding: 18px; margin-bottom: 14px; box-shadow: {shadow}; transition: transform 0.2s ease, border-color 0.2s ease; }}
        .setup-card:hover {{ transform: translateY(-2px); border-color: {accent_gold}; }}
        .sws-badge {{ display: inline-block; padding: 4px 10px; border-radius: 999px; font-size: 0.78rem; font-weight: 700; margin-right: 6px; margin-top: 6px; border: 1px solid {border_color}; }}
        div[data-testid="stMetric"] {{ background: {card_bg} !important; backdrop-filter: blur(14px); border: 1px solid {border_color}; border-radius: 14px; padding: 14px 16px !important; box-shadow: {shadow}; }}
        .kill-box {{ background: {kill_bg}; backdrop-filter: blur(12px); border: 1px solid rgba(239, 68, 68, 0.45); border-left: 5px solid #ef4444; padding: 12px 16px; border-radius: 12px; margin-bottom: 12px; }}
        .pass-box {{ background: {pass_bg}; backdrop-filter: blur(12px); border: 1px solid rgba(16, 185, 129, 0.45); border-left: 5px solid #10b981; padding: 12px 16px; border-radius: 12px; margin-bottom: 12px; }}
        .red-flag {{ background: {kill_bg}; border-left: 4px solid #f85149; padding: 10px 14px; border-radius: 10px; margin-bottom: 8px; }}
        .green-flag {{ background: {pass_bg}; border-left: 4px solid #10b981; padding: 10px 14px; border-radius: 10px; margin-bottom: 8px; }}
        .stTabs [data-baseweb="tab-list"] {{ gap: 8px; background: {card_bg}; padding: 6px; border-radius: 12px; border: 1px solid {border_color}; }}
        .stTabs [data-baseweb="tab"] {{ border-radius: 8px; padding: 8px 14px; font-weight: 600; }}
        .stButton > button[kind="primary"] {{ background: {btn_bg} !important; color: {btn_txt} !important; border: none !important; border-radius: 10px !important; font-weight: 700 !important; box-shadow: 0 4px 14px rgba(0, 0, 0, 0.22) !important; }}
        .stTextInput input, .stTextArea textarea, .stNumberInput input {{ background: {input_bg} !important; color: {text_color} !important; border-radius: 10px !important; border: 1px solid {border_color} !important; }}
        {light_overrides}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

# ---------------------------------------------------------
# SIMPLY WALL ST: SNOWFLAKE RADAR + FINANCIAL SANKEY CHARTS
# ---------------------------------------------------------
def compute_snowflake_scores(info, scr_data=None):
    # 1. VALUE (0 to 6)
    val = 2
    pe, pb, peg = info.get("trailingPE"), info.get("priceToBook"), info.get("pegRatio")
    if pe is not None and 0 < pe < 18: val += 2
    elif pe is not None and 0 < pe < 28: val += 1
    elif pe is not None and pe > 50: val -= 1
    if pb is not None and 0 < pb < 2.5: val += 1
    if peg is not None and 0 < peg < 1.3: val += 1

    # 2. FUTURE (0 to 6)
    fut = 2
    rev_g, earn_g = info.get("revenueGrowth"), info.get("earningsGrowth")
    f_pe = info.get("forwardPE")
    if rev_g is not None and rev_g >= 0.15: fut += 2
    elif rev_g is not None and rev_g >= 0.08: fut += 1
    elif rev_g is not None and rev_g < 0: fut -= 1
    if earn_g is not None and earn_g >= 0.15: fut += 1
    if pe and f_pe and f_pe < pe: fut += 1

    # 3. PAST (0 to 6)
    past = 2
    roe, opm = info.get("returnOnEquity"), info.get("operatingMargins")
    roce = scr_data.get("roce") if scr_data else None
    if roe is not None and roe >= 0.18: past += 2
    elif roe is not None and roe >= 0.12: past += 1
    elif roe is not None and roe < 0.06: past -= 1
    if opm is not None and opm >= 0.15: past += 1
    if roce is not None and roce >= 18: past += 1

    # 4. HEALTH (0 to 6)
    health = 3
    de, cr = info.get("debtToEquity"), info.get("currentRatio")
    ocf, fcf = info.get("operatingCashflow"), info.get("freeCashflow")
    sector = info.get("sector", "")
    if "Financial" not in sector and "Bank" not in sector:
        if de is not None:
            de_r = de / 100.0 if de > 10 else de
            if de_r < 0.4: health += 1
            elif de_r > 1.2: health -= 2
        if cr is not None and cr >= 1.5: health += 1
        elif cr is not None and cr < 1.0: health -= 1
        if ocf is not None and ocf > 0 and fcf is not None and fcf > 0: health += 1
        elif ocf is not None and ocf < 0: health -= 1
    else:
        if roe is not None and roe >= 0.14: health += 2

    # 5. DIVIDEND (0 to 6)
    div_y = (info.get("dividendYield") or 0) * 100
    if div_y >= 4.0: div = 6
    elif div_y >= 2.5: div = 5
    elif div_y >= 1.5: div = 4
    elif div_y >= 0.7: div = 3
    elif div_y > 0: div = 2
    else: div = 1

    scores = {
        "VALUE": max(0, min(6, val)),
        "FUTURE": max(0, min(6, fut)),
        "PAST": max(0, min(6, past)),
        "HEALTH": max(0, min(6, health)),
        "DIVIDEND": max(0, min(6, div))
    }
    return scores

def build_snowflake_chart(scores, is_dark=True):
    cats = ["VALUE", "FUTURE", "PAST", "HEALTH", "DIVIDEND"]
    vals = [scores[c] for c in cats]
    total = sum(vals)

    # Color shifts like Simply Wall St (Green -> Lime/Yellow -> Amber -> Red)
    if total >= 22:
        line_c, fill_c = "#22c55e", "rgba(34, 197, 94, 0.55)"
    elif total >= 16:
        line_c, fill_c = "#a3e635", "rgba(163, 230, 53, 0.58)"
    elif total >= 11:
        line_c, fill_c = "#facc15", "rgba(250, 204, 21, 0.55)"
    else:
        line_c, fill_c = "#ef4444", "rgba(239, 68, 68, 0.52)"

    cats_closed = cats + [cats[0]]
    vals_closed = vals + [vals[0]]
    grid_c = "rgba(255,255,255,0.14)" if is_dark else "rgba(24,24,27,0.14)"
    txt_c = "#e2e8f0" if is_dark else "#18181b"

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=vals_closed,
        theta=cats_closed,
        fill="toself",
        fillcolor=fill_c,
        line=dict(color=line_c, width=3, shape="spline", smoothing=0.8),
        marker=dict(size=5, color=line_c),
        hovertemplate="%{theta}: %{r}/6<extra></extra>"
    ))
    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, range=[0, 6], showticklabels=False, ticks="", gridcolor=grid_c, linecolor="rgba(0,0,0,0)"),
            angularaxis=dict(tickfont=dict(size=10, color=txt_c), gridcolor=grid_c, linecolor=grid_c)
        ),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=230,
        margin=dict(l=35, r=35, t=25, b=25)
    )
    return fig, total

def build_financial_sankey(info, financials_df, is_dark=True):
    rev, cost_rev, gross_p, net_inc, op_exp = None, None, None, None, None

    # Try latest annual column from yfinance financials
    if financials_df is not None and not financials_df.empty:
        col = financials_df.columns[0]
        def _get(keys):
            for k in keys:
                if k in financials_df.index:
                    v = financials_df.loc[k, col]
                    if pd.notna(v) and v != 0:
                        return float(v)
            return None
        rev = _get(["Total Revenue", "Operating Revenue"])
        cost_rev = _get(["Cost Of Revenue", "Reconciled Cost Of Revenue"])
        gross_p = _get(["Gross Profit"])
        net_inc = _get(["Net Income", "Net Income Common Stockholders"])

    # Fallback to ticker.info
    if not rev: rev = info.get("totalRevenue")
    if not gross_p: gross_p = info.get("grossProfits")
    if not net_inc: net_inc = info.get("netIncomeToCommon")

    if not rev or rev <= 0:
        return None

    # Convert to INR Crores for clean display
    rev_cr = rev / 1e7
    net_cr = (net_inc / 1e7) if net_inc is not None else 0.0

    if gross_p is not None and gross_p > 0 and gross_p < rev:
        gp_cr = gross_p / 1e7
        cor_cr = (cost_rev / 1e7) if (cost_rev and cost_rev > 0) else max(0.0, rev_cr - gp_cr)
    else:
        gp_cr = rev_cr
        cor_cr = 0.0

    other_exp_cr = max(0.0, gp_cr - max(0.0, net_cr))
    earnings_pos = max(0.0, net_cr)

    labels, sources, targets, values, node_colors, link_colors = [], [], [], [], [], []
    if cor_cr > 0.1:
        labels = [
            f"Total Revenue<br>₹{rev_cr:,.0f} Cr",
            f"Gross Profit<br>₹{gp_cr:,.0f} Cr",
            f"Cost of Sales<br>₹{cor_cr:,.0f} Cr",
            f"Net Earnings<br>₹{earnings_pos:,.0f} Cr",
            f"OpEx & Taxes<br>₹{other_exp_cr:,.0f} Cr"
        ]
        node_colors = ["#3b82f6", "#0ea5e9", "#f59e0b", "#10b981", "#ef4444"]
        sources = [0, 0, 1, 1]
        targets = [1, 2, 3, 4]
        values = [max(0.1, gp_cr), max(0.1, cor_cr), max(0.1, earnings_pos), max(0.1, other_exp_cr)]
        link_colors = [
            "rgba(14, 165, 233, 0.35)", "rgba(245, 158, 11, 0.32)",
            "rgba(16, 185, 129, 0.42)", "rgba(239, 68, 68, 0.30)"
        ]
    else:
        labels = [
            f"Total Revenue<br>₹{rev_cr:,.0f} Cr",
            f"Net Earnings<br>₹{earnings_pos:,.0f} Cr",
            f"Total Expenses & Tax<br>₹{max(0.1, rev_cr - earnings_pos):,.0f} Cr"
        ]
        node_colors = ["#3b82f6", "#10b981", "#f59e0b"]
        sources = [0, 0]
        targets = [1, 2]
        values = [max(0.1, earnings_pos), max(0.1, rev_cr - earnings_pos)]
        link_colors = ["rgba(16, 185, 129, 0.42)", "rgba(245, 158, 11, 0.32)"]

    txt_c = "#f1f5f9" if is_dark else "#18181b"
    fig = go.Figure(data=[go.Sankey(
        node=dict(pad=18, thickness=20, line=dict(color="rgba(0,0,0,0)", width=0), label=labels, color=node_colors),
        link=dict(source=sources, target=targets, value=values, color=link_colors)
    )])
    fig.update_layout(
        title="💸 Revenue-to-Earnings Visual Flow (Annual, ₹ Crores)",
        font=dict(size=12, color=txt_c),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=310,
        margin=dict(l=10, r=10, t=42, b=12)
    )
    return fig

# ---------------------------------------------------------
# PAPER TRADING ENGINE (LOCAL JSON PERSISTENCE)
# ---------------------------------------------------------
def load_paper_portfolio(default_cap=100000.0):
    if os.path.exists(PAPER_FILE):
        try:
            with open(PAPER_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"cash": float(default_cap), "initial_capital": float(default_cap), "positions": [], "history": []}

def save_paper_portfolio(data):
    with open(PAPER_FILE, "w") as f:
        json.dump(data, f, indent=2)

def place_paper_buy(symbol, qty, price, sl, target, strategy_tag):
    pf = load_paper_portfolio()
    cost = qty * price
    if qty <= 0:
        return False, "Quantity 0 se zyada honi chahiye."
    if cost > pf["cash"]:
        return False, f"Insufficient Paper Cash! Required ₹{cost:,.2f}, Available ₹{pf['cash']:,.2f}."
    pf["cash"] -= cost
    pf["positions"].append({
        "symbol": symbol.upper(),
        "qty": int(qty),
        "entry": round(float(price), 2),
        "sl": round(float(sl), 2),
        "target": round(float(target), 2),
        "strategy": strategy_tag,
        "date": get_ist_now().strftime("%Y-%m-%d %H:%M IST")
    })
    save_paper_portfolio(pf)
    return True, f"Paper BUY Executed: {qty} qty of {symbol.upper()} @ ₹{price:,.2f}"

def close_paper_position(idx, exit_price):
    pf = load_paper_portfolio()
    if idx < 0 or idx >= len(pf["positions"]):
        return False, "Invalid position."
    pos = pf["positions"].pop(idx)
    proceeds = pos["qty"] * exit_price
    pnl = (exit_price - pos["entry"]) * pos["qty"]
    pf["cash"] += proceeds
    pos["exit"] = round(float(exit_price), 2)
    pos["pnl"] = round(float(pnl), 2)
    pos["closed_at"] = get_ist_now().strftime("%Y-%m-%d %H:%M IST")
    pf["history"].insert(0, pos)
    save_paper_portfolio(pf)
    return True, f"Closed {pos['symbol']} @ ₹{exit_price:,.2f} | P&L: ₹{pnl:+,.2f}"

# ---------------------------------------------------------
# ANGEL ONE SMARTAPI ENGINE (LIVE LTP + 1-CLICK ORDER)
# ---------------------------------------------------------
@st.cache_data(ttl=86400)
def fetch_angel_scrip_master():
    try:
        url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            df = pd.DataFrame(resp.json())
            nse_eq = df[(df["exch_seg"] == "NSE") & (df["symbol"].str.endswith("-EQ"))]
            return dict(zip(nse_eq["symbol"].str.replace("-EQ", "", regex=False), nse_eq["token"]))
    except Exception:
        pass
    return {}

def connect_angel_one(api_key, client_id, mpin, totp_secret):
    if not SMARTAPI_AVAILABLE:
        return False, "smartapi-python / pyotp installed nahi hai. Pip install karein."
    try:
        smart_api = SmartConnect(api_key=api_key.strip())
        totp = pyotp.TOTP(totp_secret.strip().replace(" ", "")).now()
        data = smart_api.generateSession(client_id.strip().upper(), mpin.strip(), totp)
        if data.get("status"):
            st.session_state["angel_api"] = smart_api
            st.session_state["angel_connected"] = True
            st.session_state["angel_profile"] = data.get("data", {})
            return True, "Angel One SmartAPI Connected Successfully!"
        return False, f"Login Failed: {data.get('message', 'Unknown Error')}"
    except Exception as e:
        return False, f"Angel One Error: {str(e)}"

def get_live_ltp(symbol, fallback_price):
    if st.session_state.get("angel_connected") and st.session_state.get("angel_api"):
        try:
            clean = symbol.upper().replace(".NS", "").replace(".BO", "")
            token_map = fetch_angel_scrip_master()
            token = token_map.get(clean)
            if token:
                res = st.session_state["angel_api"].ltpData("NSE", f"{clean}-EQ", str(token))
                if res.get("status") and "data" in res:
                    return float(res["data"]["ltp"]), "Angel One Live"
        except Exception:
            pass
    return float(fallback_price), "yfinance"

def place_angel_one_order(symbol, side, qty, product_type="INTRADAY"):
    if not st.session_state.get("angel_connected") or not st.session_state.get("angel_api"):
        return False, "Pehle sidebar mein Angel One SmartAPI connect karein."
    try:
        clean = symbol.upper().replace(".NS", "").replace(".BO", "")
        token_map = fetch_angel_scrip_master()
        token = token_map.get(clean)
        if not token:
            return False, f"{clean}-EQ ka Angel One token nahi mila."
        order_params = {
            "variety": "NORMAL",
            "tradingsymbol": f"{clean}-EQ",
            "symboltoken": str(token),
            "transactiontype": side.upper(),
            "exchange": "NSE",
            "ordertype": "MARKET",
            "producttype": product_type,
            "duration": "DAY",
            "quantity": str(int(qty))
        }
        order_id = st.session_state["angel_api"].placeOrder(order_params)
        return True, f"Angel One Order Placed! Order ID: {order_id}"
    except Exception as e:
        return False, f"Order Failed: {str(e)}"

# ---------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------
def format_inr_crore(val):
    return "N/A" if (val is None or pd.isna(val)) else f"₹{val / 1e7:,.2f} Cr"

def safe_pct(val):
    return "N/A" if (val is None or pd.isna(val)) else f"{val * 100:.2f}%"

def safe_num(val, decimals=2):
    return "N/A" if (val is None or pd.isna(val)) else f"{val:.{decimals}f}"

def normalize_symbol(sym):
    sym = sym.strip().upper()
    return sym if (sym.endswith(".NS") or sym.endswith(".BO")) else sym + ".NS"

def get_ist_now():
    return datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)

def get_secret_safe(key, default=""):
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default

def check_event_blackouts(symbol, is_intraday=False, manual_event_day=False):
    warnings = []
    ist_now = get_ist_now()
    today_str = ist_now.strftime("%Y-%m-%d")

    if is_intraday:
        if manual_event_day:
            warnings.append("Manual Event Blackout ON: Aaj High-Impact Event Day marked hai (Intraday Skip).")
        if today_str in MACRO_BLACKOUT_DATES:
            warnings.append(f"Macro Event Blackout: Aaj {MACRO_BLACKOUT_DATES[today_str]} hai (Intraday Skip).")
        if ist_now.weekday() == 3:
            warnings.append("Expiry Day Volatility: Aaj Weekly/Monthly Expiry day hai — Intraday whipsaw risk high hai.")
    else:
        try:
            ticker = yf.Ticker(normalize_symbol(symbol))
            next_earn_date = None
            cal = ticker.calendar
            if isinstance(cal, dict) and "Earnings Date" in cal and cal["Earnings Date"]:
                ed = cal["Earnings Date"][0]
                next_earn_date = ed.date() if hasattr(ed, "date") else ed
            if next_earn_date is None:
                ts = (ticker.info or {}).get("earningsTimestamp")
                if ts:
                    next_earn_date = datetime.fromtimestamp(ts, tz=timezone.utc).date()
            if next_earn_date is not None:
                days_left = (next_earn_date - ist_now.date()).days
                if 0 <= days_left <= 21:
                    warnings.append(f"Earnings Risk (3-Week Skip): {next_earn_date.strftime('%d-%b-%Y')} ko result hai ({days_left} din baaki).")
        except Exception:
            pass
    return (len(warnings) > 0), warnings

@st.cache_data(ttl=3600)
def check_nifty_market_regime():
    try:
        m_df = yf.Ticker("^NSEI").history(period="3y", interval="1mo")
        if m_df is not None and len(m_df) >= 13:
            if isinstance(m_df.columns, pd.MultiIndex):
                m_df.columns = m_df.columns.get_level_values(0)
            sma12, curr = float(m_df["Close"].rolling(12).mean().iloc[-1]), float(m_df["Close"].iloc[-1])
            return ("BULL", curr, sma12, 1.0) if curr >= sma12 else ("BEAR", curr, sma12, 0.25)
    except Exception:
        pass
    return "UNKNOWN", 0.0, 0.0, 1.0

# ---------------------------------------------------------
# TECHNICAL INDICATORS & DATA FETCHERS
# ---------------------------------------------------------
def add_indicators(df):
    if df is None or df.empty or len(df) < 25:
        return df
    df = df.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    close, high, low, vol = df["Close"], df["High"], df["Low"], df["Volume"]
    df["EMA9"] = close.ewm(span=9, adjust=False).mean()
    df["EMA20"] = close.ewm(span=20, adjust=False).mean()
    df["EMA25"] = close.ewm(span=25, adjust=False).mean()
    df["EMA50"] = close.ewm(span=50, adjust=False).mean()
    df["EMA200"] = close.ewm(span=200, adjust=False).mean()
    df["SMA30"] = close.rolling(window=30).mean()

    delta = close.diff()
    gain, loss = delta.clip(lower=0), -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    df["RSI"] = 100 - (100 / (1 + (avg_gain / avg_loss.replace(0, np.nan))))

    df["MACD"] = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    df["MACD_SIGNAL"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_HIST"] = df["MACD"] - df["MACD_SIGNAL"]

    sma20, std20 = close.rolling(window=20).mean(), close.rolling(window=20).std()
    df["BB_UPPER"], df["BB_LOWER"] = sma20 + (2 * std20), sma20 - (2 * std20)

    prev_close = close.shift(1)
    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    df["ATR"] = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()

    up_move, down_move = high.diff(), -low.diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    atr_safe = df["ATR"].replace(0, np.nan)
    plus_di = 100 * pd.Series(plus_dm, index=df.index).ewm(alpha=1/14, adjust=False).mean() / atr_safe
    minus_di = 100 * pd.Series(minus_dm, index=df.index).ewm(alpha=1/14, adjust=False).mean() / atr_safe
    df["ADX"] = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)).ewm(alpha=1/14, adjust=False).mean()

    df["VOL_SMA20"] = vol.rolling(window=20).mean()
    df["VOL_RATIO"] = vol / df["VOL_SMA20"].replace(0, np.nan)
    df["VOL_SMA60"] = vol.rolling(window=60).mean()
    df["VOL_RATIO_60"] = vol / df["VOL_SMA60"].replace(0, np.nan)
    return df

def add_intraday_vwap(df):
    if df is None or df.empty:
        return df
    df = df.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    df["DateOnly"] = df.index.date
    df["TPV"] = tp * df["Volume"]
    df["VWAP"] = df.groupby("DateOnly")["TPV"].cumsum() / df.groupby("DateOnly")["Volume"].cumsum().replace(0, np.nan)
    return df

@st.cache_data(ttl=86400)
def fetch_index_symbols(index_name):
    if index_name == "Custom Watchlist": return DEFAULT_WATCHLIST
    if index_name in BSE_INDEX_LISTS: return BSE_INDEX_LISTS[index_name]
    if index_name in NSE_INDEX_URLS:
        try:
            resp = requests.get(NSE_INDEX_URLS[index_name], headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            if resp.status_code == 200:
                df_idx = pd.read_csv(io.StringIO(resp.text))
                if "Symbol" in df_idx.columns:
                    return [str(s).strip() for s in df_idx["Symbol"].dropna().tolist()]
        except Exception:
            pass
    return DEFAULT_WATCHLIST

@st.cache_data(ttl=600)
def fetch_stock_bundle(symbol, include_intraday=True):
    ticker = yf.Ticker(normalize_symbol(symbol))
    info = ticker.info or {}
    daily_df = add_indicators(ticker.history(period="5y", interval="1d"))
    weekly_df = add_indicators(ticker.history(period="5y", interval="1wk"))
    df_15m = add_intraday_vwap(add_indicators(ticker.history(period="5d", interval="15m"))) if include_intraday else pd.DataFrame()
    df_5m = add_indicators(ticker.history(period="5d", interval="5m")) if include_intraday else pd.DataFrame()
    try:
        financials_df = ticker.financials if include_intraday else pd.DataFrame()
    except Exception:
        financials_df = pd.DataFrame()
    return info, daily_df, weekly_df, df_15m, df_5m, financials_df

@st.cache_data(ttl=3600)
def fetch_screener_data(symbol):
    clean_sym = symbol.strip().upper().replace(".NS", "").replace(".BO", "")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    soup = None
    for url in [f"https://www.screener.in/company/{clean_sym}/consolidated/", f"https://www.screener.in/company/{clean_sym}/"]:
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200 and "profit-loss" in resp.text:
                soup = BeautifulSoup(resp.text, "lxml")
                break
        except Exception:
            continue

    data = {"roce": None, "promoter_pledge": None, "pnl_df": pd.DataFrame(), "shareholding_df": pd.DataFrame(), "pros": [], "cons": []}
    if soup is None: return data

    for li in soup.select("#top-ratios li"):
        name_el, val_el = li.select_one(".name"), li.select_one(".value")
        if name_el and val_el and name_el.get_text(strip=True).upper() == "ROCE":
            num = re.findall(r"[-+]?\d*\.\d+|\d+", val_el.get_text(strip=True))
            if num: data["roce"] = float(num[0])

    pnl_tbl = soup.select_one("#profit-loss table.data-table")
    if pnl_tbl:
        try:
            hdrs = [th.get_text(strip=True) for th in pnl_tbl.select("thead th")]
            rows = [r for r in [[td.get_text(strip=True) for td in tr.select("td")] for tr in pnl_tbl.select("tbody tr")] if r]
            if hdrs and rows: data["pnl_df"] = pd.DataFrame(rows, columns=hdrs)
        except Exception:
            pass

    sh_tbl = soup.select_one("#shareholding table.data-table")
    if sh_tbl:
        try:
            hdrs = [th.get_text(strip=True) for th in sh_tbl.select("thead th")]
            rows = []
            for tr in sh_tbl.select("tbody tr"):
                cols = [td.get_text(strip=True) for td in tr.select("td")]
                if cols:
                    rows.append(cols)
                    if "pledge" in cols[0].lower() and len(cols) > 1:
                        num = re.findall(r"[-+]?\d*\.\d+|\d+", cols[-1])
                        if num: data["promoter_pledge"] = float(num[0])
            if hdrs and rows: data["shareholding_df"] = pd.DataFrame(rows, columns=hdrs)
        except Exception:
            pass

    data["pros"] = [li.get_text(strip=True) for li in soup.select(".pros li")]
    data["cons"] = [li.get_text(strip=True) for li in soup.select(".cons li")]
    return data

@st.cache_data(ttl=900)
def fetch_google_news(query, max_items=6):
    url = f"https://news.google.com/rss/search?q={query}+stock+NSE+India&hl=en-IN&gl=IN&ceid=IN:en"
    news_list = []
    try:
        resp = requests.get(url, timeout=8)
        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            for item in root.findall("./channel/item")[:max_items]:
                news_list.append({
                    "title": item.find("title").text if item.find("title") is not None else "",
                    "link": item.find("link").text if item.find("link") is not None else "",
                    "date": item.find("pubDate").text if item.find("pubDate") is not None else ""
                })
    except Exception:
        pass
    return news_list

# ---------------------------------------------------------
# ANALYTICAL ENGINES (CLASSIC + PRO)
# ---------------------------------------------------------
def analyze_fundamentals_and_red_flags(info, screener_data=None):
    red_flags, green_flags, score = [], [], 50
    sector = info.get("sector", "Unknown")
    is_fin = "Financial" in sector or "Bank" in sector

    pe, peg, roe = info.get("trailingPE"), info.get("pegRatio"), info.get("returnOnEquity")
    opm, de, curr_ratio = info.get("operatingMargins"), info.get("debtToEquity"), info.get("currentRatio")
    rev_growth, earn_growth = info.get("revenueGrowth"), info.get("earningsGrowth")
    ocf, fcf, net_inc = info.get("operatingCashflow"), info.get("freeCashflow"), info.get("netIncomeToCommon")
    high52, price = info.get("fiftyTwoWeekHigh"), info.get("currentPrice") or info.get("regularMarketPrice")

    if not is_fin:
        if ocf is not None and ocf < 0:
            red_flags.append("Negative Operating Cash Flow (CFO): Core business cash generate nahi kar raha.")
            score -= 15
        elif ocf is not None and net_inc is not None and net_inc > 0 and ocf < (0.6 * net_inc):
            red_flags.append("Profit vs Cash Flow Mismatch: CFO Net Profit ke 60% se kam hai.")
            score -= 10
        elif ocf is not None and ocf > 0 and fcf is not None and fcf > 0:
            green_flags.append("Healthy Cash Conversion: Operating aur Free Cash Flow dono positive hain.")
            score += 10

        if de is not None:
            de_r = de / 100.0 if de > 10 else de
            if de_r > 1.2:
                red_flags.append(f"High Debt Burden: Debt-to-Equity ({de_r:.2f}) safe limit (1.0) se zyada hai.")
                score -= 12
            elif de_r < 0.5:
                green_flags.append(f"Low Debt Balance Sheet: Debt-to-Equity sirf {de_r:.2f} hai.")
                score += 8
        if curr_ratio is not None and curr_ratio < 1.0:
            red_flags.append(f"Short-Term Liquidity Risk: Current Ratio ({curr_ratio:.2f}) 1.0 se neeche hai.")
            score -= 8

    if roe is not None:
        if roe >= 0.18: green_flags.append(f"Strong ROE: {roe*100:.1f}% (18%+ benchmark)."); score += 10
        elif roe < 0.08: red_flags.append(f"Weak ROE ({roe*100:.1f}%): Capital efficiency kamzor hai."); score -= 8
    if opm is not None and opm < 0: red_flags.append(f"Negative Operating Margin ({opm*100:.1f}%)."); score -= 15
    if rev_growth is not None:
        if rev_growth >= 0.15: green_flags.append(f"Strong Revenue Growth: YoY Sales +{rev_growth*100:.1f}%."); score += 10
        elif rev_growth < 0: red_flags.append(f"Shrinking Revenue: YoY Sales {rev_growth*100:.1f}%."); score -= 10
    if earn_growth is not None and earn_growth < -0.10: red_flags.append(f"Earnings Contraction: Quarterly earnings {earn_growth*100:.1f}% giri hain."); score -= 8
    if pe is not None and pe > 65: red_flags.append(f"Expensive Valuation: P/E ({pe:.1f}) bahut high hai."); score -= 7
    if peg is not None and peg > 2.5: red_flags.append(f"High PEG Ratio ({peg:.2f})."); score -= 6
    elif peg is not None and 0 < peg < 1.2: green_flags.append(f"Attractive PEG Ratio ({peg:.2f})."); score += 7
    if price and high52 and high52 > 0 and (((price - high52) / high52) * 100) < -35:
        red_flags.append(f"Deep Drawdown: 52-Week High se {abs(((price - high52) / high52) * 100):.1f}% neeche hai."); score -= 5

    if screener_data:
        if screener_data.get("roce") is not None:
            if screener_data["roce"] >= 18: green_flags.append(f"Strong Screener ROCE: {screener_data['roce']}%"); score += 6
            elif screener_data["roce"] < 10: red_flags.append(f"Low Screener ROCE: {screener_data['roce']}%"); score -= 6
        if screener_data.get("promoter_pledge") is not None and screener_data["promoter_pledge"] > 10:
            red_flags.append(f"High Promoter Pledge: {screener_data['promoter_pledge']}% shares pledged hain."); score -= 12

    return max(0, min(100, score)), red_flags, green_flags

def generate_classic_trade_setups(daily_df, weekly_df, df_15m, capital, risk_pct, regime_mult):
    setups = {}
    risk_amount = capital * (risk_pct / 100.0) * regime_mult

    if df_15m is not None and len(df_15m) >= 20:
        last_i = df_15m.iloc[-1]
        price_i = float(last_i["Close"])
        vwap = float(last_i["VWAP"]) if not pd.isna(last_i["VWAP"]) else price_i
        atr_i = float(last_i["ATR"]) if not pd.isna(last_i["ATR"]) else price_i * 0.008
        rsi_i = float(last_i["RSI"]) if not pd.isna(last_i["RSI"]) else 50.0
        if price_i > vwap and rsi_i > 52:
            bias, entry, sl = "BULLISH (Long Above VWAP)", price_i, max(vwap - 0.5 * atr_i, price_i - 1.2 * atr_i)
            rps = max(entry - sl, 0.5); t1, t2 = entry + 2 * rps, entry + 3 * rps
        elif price_i < vwap and rsi_i < 48:
            bias, entry, sl = "BEARISH (Short Below VWAP)", price_i, min(vwap + 0.5 * atr_i, price_i + 1.2 * atr_i)
            rps = max(sl - entry, 0.5); t1, t2 = entry - 2 * rps, entry - 3 * rps
        else:
            bias, entry, sl = "NEUTRAL (Wait for VWAP Breakout)", price_i, price_i - 1.2 * atr_i
            rps = max(entry - sl, 0.5); t1, t2 = entry + 2 * rps, entry + 3 * rps
        setups["Classic Intraday (15m VWAP)"] = {"bias": bias, "entry": entry, "sl": sl, "t1": t1, "t2": t2, "qty": int(risk_amount / rps)}

    if daily_df is not None and len(daily_df) >= 60:
        last_d = daily_df.iloc[-1]
        price_d = float(last_d["Close"])
        ema20, ema50, ema200 = float(last_d["EMA20"]), float(last_d["EMA50"]), float(last_d["EMA200"])
        rsi_d, adx_d, atr_d = float(last_d["RSI"]), float(last_d["ADX"] or 20.0), float(last_d["ATR"])
        recent_low, recent_high = float(daily_df["Low"].tail(10).min()), float(daily_df["High"].tail(20).max())
        if price_d > ema20 > ema50 and 48 <= rsi_d <= 70 and adx_d >= 20:
            bias, entry, sl = "STRONG SWING LONG (Momentum)", price_d, max(recent_low, price_d - 1.5 * atr_d)
        elif price_d > ema50 and price_d <= ema20 and rsi_d >= 40:
            bias, entry, sl = "PULLBACK BUY ZONE (Near 20/50 EMA)", price_d, max(ema50 - atr_d, price_d - 1.8 * atr_d)
        elif price_d < ema50 and price_d < ema200:
            bias, entry, sl = "AVOID LONG / DOWNTREND", price_d, price_d - 1.5 * atr_d
        else:
            bias, entry, sl = f"CONSOLIDATION (Breakout > ₹{recent_high:.2f})", recent_high, recent_high - 1.5 * atr_d
        rps = max(abs(entry - sl), 1.0)
        setups["Classic Swing (Daily EMA/ADX)"] = {"bias": bias, "entry": entry, "sl": sl, "t1": entry + 2 * rps, "t2": entry + 3 * rps, "qty": int(risk_amount / rps)}

    if weekly_df is not None and len(weekly_df) >= 55:
        last_w = weekly_df.iloc[-1]
        price_w, w_ema20, w_ema50, atr_w = float(last_w["Close"]), float(last_w["EMA20"]), float(last_w["EMA50"]), float(last_w["ATR"])
        bias = "STAGE-2 UPTREND" if (price_w > w_ema20 > w_ema50) else ("BASE BUILDING" if price_w > w_ema50 else "DOWNTREND (Avoid)")
        sl = max(w_ema50 - 0.5 * atr_w, price_w - 2.0 * atr_w)
        rps = max(abs(price_w - sl), 1.0)
        setups["Classic Positional (Weekly)"] = {"bias": bias, "entry": price_w, "sl": sl, "t1": price_w + 2.5 * rps, "t2": price_w + 4.0 * rps, "qty": int(risk_amount / rps)}
    return setups

def run_hard_kill_filters(info, daily_df, screener_data, order_size_inr, symbol="", is_intraday=False, manual_event_day=False):
    kills = []
    if daily_df is None or daily_df.empty: return True, ["No market price data available."]
    price = float(daily_df["Close"].iloc[-1])
    adv_value_1pct = 0.01 * float(daily_df["Volume"].tail(20).mean()) * price

    if adv_value_1pct < order_size_inr: kills.append(f"Illiquid Stock: 1% ADV (₹{adv_value_1pct:,.0f}) order size (₹{order_size_inr:,.0f}) se kam hai.")
    if price < 20.0: kills.append(f"Penny Stock (< ₹20): Current price ₹{price:.2f} hai.")
    pe = info.get("trailingPE")
    if pe is not None and pe > 100: kills.append(f"Bubble Valuation: Triple-digit P/E ({pe:.1f} > 100).")
    if len(daily_df) < 680: kills.append(f"Fresh IPO (< 3 Years): Sirf {len(daily_df)} trading days ka data hai.")
    pledge = screener_data.get("promoter_pledge") if screener_data else None
    if pledge is not None and pledge > 10.0: kills.append(f"High Promoter Pledging: {pledge:.1f}% shares pledged hain.")

    sector = info.get("sector", "")
    if "Financial" not in sector and "Bank" not in sector:
        ocf, net_inc = info.get("operatingCashflow"), info.get("netIncomeToCommon")
        if ocf is not None and net_inc is not None and net_inc > 0 and ocf < 0.5 * net_inc:
            kills.append("Accounting Red Flag: Operating Cash Flow Net Profit ke 50% se kam hai.")

    if symbol:
        ev_blocked, ev_reasons = check_event_blackouts(symbol, is_intraday=is_intraday, manual_event_day=manual_event_day)
        if ev_blocked: kills.extend(ev_reasons)
    return (len(kills) > 0), kills

def evaluate_bob_volman_intraday(df_5m, daily_df, capital, risk_pct, consecutive_losses):
    if consecutive_losses >= 2:
        return {"status": "LOCKED", "score": 0, "direction": "LOCKED (2 Losses Hit)", "time_window": "LOCKED", "entry": 0, "sl": 0, "t1": 0, "t2": 0, "qty": 0}
    if df_5m is None or len(df_5m) < 30 or daily_df is None or len(daily_df) < 2:
        return {"status": "NO_DATA", "score": 0, "direction": "N/A", "time_window": "N/A", "entry": 0, "sl": 0, "t1": 0, "t2": 0, "qty": 0}

    last, prev_4 = df_5m.iloc[-1], df_5m.iloc[-5:-1]
    price, ema25, ema25_prev = float(last["Close"]), float(last["EMA25"]), float(df_5m["EMA25"].iloc[-4])
    atr = float(last["ATR"]) if not pd.isna(last["ATR"]) else price * 0.005
    pdh, pdl = float(daily_df["High"].iloc[-2]), float(daily_df["Low"].iloc[-2])

    bull_dom, bear_dom = (price > ema25 and ema25 > ema25_prev), (price < ema25 and ema25 < ema25_prev)
    is_buildup = float(prev_4["High"].max() - prev_4["Low"].min()) <= (2.2 * atr)
    round_step = 50 if price >= 500 else 10
    clear_up = ((np.ceil(price / round_step) * round_step - price) / price > 0.003) and (abs(pdh - price) / price > 0.003 or price > pdh)
    clear_dn = ((price - np.floor(price / round_step) * round_step) / price > 0.003) and (abs(price - pdl) / price > 0.003 or price < pdl)

    ist = get_ist_now()
    hm = ist.hour * 100 + ist.minute
    time_note = "PRIME (9:45–11:30 IST)" if 945 <= hm <= 1130 else ("AVOID (Open/Lunch)" if (915 <= hm < 945 or 1130 < hm <= 1330) else "AFTERNOON/POST-MKT")

    score, direction = 0, "NEUTRAL"
    if bull_dom:
        score += 40; direction = "LONG (Pattern Break)"
        if clear_up: score += 30
    elif bear_dom:
        score += 40; direction = "SHORT (Pattern Break)"
        if clear_dn: score += 30
    if is_buildup: score += 30

    risk_amt = capital * (min(risk_pct, 1.0) / 100.0)
    if "LONG" in direction:
        entry, sl = float(last["High"]), min(float(prev_4["Low"].min()), float(last["High"]) - atr)
        rps = max(entry - sl, 0.5); t1, t2 = entry + 1.4 * rps, entry + 2.0 * rps
    elif "SHORT" in direction:
        entry, sl = float(last["Low"]), max(float(prev_4["High"].max()), float(last["Low"]) + atr)
        rps = max(sl - entry, 0.5); t1, t2 = entry - 1.4 * rps, entry - 2.0 * rps
    else:
        entry, sl, t1, t2, rps = price, price - atr, price + 1.4 * atr, price + 2 * atr, max(atr, 0.5)
    return {"status": "READY" if score >= 70 else "WAIT", "score": score, "direction": direction, "time_window": time_note, "entry": entry, "sl": sl, "t1": t1, "t2": t2, "qty": int(risk_amt / rps)}

def evaluate_bulkowski_swing(info, daily_df, weekly_df, regime_mult, capital, risk_pct):
    f_score, mcap_cr = 0, (info.get("marketCap") or 0) / 1e7
    pb, psr, pe = info.get("priceToBook"), info.get("priceToSalesTrailing12Months"), info.get("trailingPE")
    de, cr, eg = info.get("debtToEquity"), info.get("currentRatio"), info.get("earningsGrowth")

    if 0 < mcap_cr < 8000: f_score += 3
    if pb is not None and pb < 2.11: f_score += 3
    if psr is not None and psr < 1.0: f_score += 3
    if pe is not None and 0 < pe < 17.1: f_score += 3
    if de is not None and (de / 100 if de > 10 else de) < 0.5: f_score += 3
    if cr is not None and cr > 2.0: f_score += 2
    if eg is not None and eg > 0: f_score += 3

    p_score, stage = 0, "Stage 1 / Base"
    entry = float(daily_df["Close"].iloc[-1])
    sl = entry * 0.92
    if weekly_df is not None and len(weekly_df) >= 35:
        w_sma30, w_sma30_prev, w_close = float(weekly_df["SMA30"].iloc[-1]), float(weekly_df["SMA30"].iloc[-4]), float(weekly_df["Close"].iloc[-1])
        if w_close > w_sma30 and w_sma30 >= w_sma30_prev: stage, p_score, sl = "Weinstein Stage 2 (Breakout)", p_score + 3, w_sma30 * 0.98
        elif w_close < w_sma30: stage, p_score = "Weinstein Stage 4 (Avoid)", p_score - 3

    vol_r60 = float(daily_df["VOL_RATIO_60"].iloc[-1]) if not pd.isna(daily_df["VOL_RATIO_60"].iloc[-1]) else 1.0
    if vol_r60 >= 1.25: p_score += 2
    h52, l52 = info.get("fiftyTwoWeekHigh"), info.get("fiftyTwoWeekLow")
    if h52 and l52 and h52 > l52 and ((entry - l52) / (h52 - l52)) <= 0.35: p_score += 1
    if 0 < mcap_cr < 8000: p_score += 1

    eff_risk = capital * (risk_pct / 100.0) * regime_mult
    rps = max(entry - sl, entry * 0.03)
    return {"score": min(100, int((f_score / 20.0) * 60 + max(0, p_score) * 6)), "fund_score_20": f_score, "pattern_score": p_score, "stage": stage, "entry": entry, "sl": sl, "t1": entry + 2 * rps, "t2": entry + 3 * rps, "qty": int(eff_risk / rps)}

def evaluate_parag_parikh_value(info, screener_data):
    score, notes = 0, []
    price, h52 = info.get("currentPrice") or info.get("regularMarketPrice") or 0, info.get("fiftyTwoWeekHigh") or 0
    eff_roce = screener_data.get("roce") if (screener_data and screener_data.get("roce") is not None) else ((info.get("returnOnEquity") or 0) * 100)
    de = info.get("debtToEquity")
    de_val = (de / 100.0) if (de is not None and de > 10) else de
    fcf, div_y, pe = info.get("freeCashflow"), (info.get("dividendYield") or 0) * 100, info.get("trailingPE")

    if h52 > 0 and price < 0.70 * h52: score += 25; notes.append("30%+ off 52W High")
    if eff_roce >= 15: score += 25; notes.append(f"ROCE/ROE {eff_roce:.1f}%")
    if de_val is not None and de_val < 1.0: score += 15; notes.append(f"D/E {de_val:.2f}")
    if fcf is not None and fcf > 0: score += 15; notes.append("Positive FCF")
    if div_y >= 3.0: score += 20; notes.append(f"Div Yield {div_y:.1f}%")
    elif div_y >= 2.0: score += 10; notes.append(f"Div Yield {div_y:.1f}%")
    if pe is not None and pe < 20: score += 10; notes.append(f"P/E {pe:.1f}")
    return {"score": min(100, score), "notes": notes}

def evaluate_bulkowski_multibagger(info):
    score, notes = 0, []
    mcap_cr = (info.get("marketCap") or 0) / 1e7
    pb, psr = info.get("priceToBook"), info.get("priceToSalesTrailing12Months")
    div_y, roe, rev_g = (info.get("dividendYield") or 0) * 100, (info.get("returnOnEquity") or 0) * 100, (info.get("revenueGrowth") or 0) * 100
    if 0 < mcap_cr < 8000: score += 20; notes.append("Small-Cap")
    if pb is not None and pb <= 1.5: score += 20; notes.append(f"P/BV {pb:.2f}")
    if psr is not None and psr <= 1.0: score += 20; notes.append(f"PSR {psr:.2f}")
    if div_y <= 0.5: score += 15; notes.append("Zero Div (Growth)")
    if 0 < roe < 8.0: score += 15; notes.append(f"Low-Base ROE {roe:.1f}%")
    if rev_g > 10: score += 10; notes.append(f"Sales +{rev_g:.1f}%")
    return {"score": min(100, score), "notes": notes}

def evaluate_cyclical_turnaround(info):
    score, notes = 0, []
    text = (info.get("sector", "") + " " + info.get("industry", "")).lower()
    pe, opm = info.get("trailingPE"), (info.get("operatingMargins") or 0) * 100
    if any(k in text for k in ["metal", "steel", "cement", "sugar", "basic materials", "mining", "oil", "energy", "chemical"]):
        score += 35; notes.append("Cyclical Sector")
    if pe is not None and 0 < pe < 15: score += 35; notes.append(f"Low P/E {pe:.1f}")
    if opm > 8: score += 30; notes.append(f"OPM {opm:.1f}%")
    return {"score": min(100, score), "notes": notes}

# ---------------------------------------------------------
# AI AGENT BRAIN & PLOTLY 3-PANEL CHART
# ---------------------------------------------------------
def call_ai_agent(provider, api_key, base_url, model_name, payload_dict):
    system_prompt = (
        "Tum ek senior Indian Stock Market Quant & Forensic Analyst ho (NSE/BSE expert). "
        "Diye gaye exact JSON data ke base par Romanized Hindi (Hinglish) mein 5 sections mein report likho:\n"
        "1. Hard Kill & Governance Audit\n2. Business & Future Outlook (1-3 Years)\n"
        "3. Technical & Strategy Structure\n4. Best Trade Plan (Intraday vs Swing vs Positional)\n"
        "5. Final Verdict (STRONG BUY / ACCUMULATE / TRADE ONLY / WATCHLIST / STRICT AVOID)"
    )
    user_prompt = "Complete stock analysis karo:\n\n" + json.dumps(payload_dict, indent=2)
    try:
        if provider == "Gemini API (Google)":
            if not api_key: return "Error: Sidebar mein Gemini API Key daalein."
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            body = {"system_instruction": {"parts": [{"text": system_prompt}]}, "contents": [{"parts": [{"text": user_prompt}]}], "generationConfig": {"temperature": 0.25, "maxOutputTokens": 2048}}
            resp = requests.post(url, json=body, timeout=180).json()
            return resp["candidates"][0]["content"]["parts"][0]["text"] if "candidates" in resp else f"API Error: {resp}"
        else:
            headers = {"Content-Type": "application/json"}
            if api_key: headers["Authorization"] = f"Bearer {api_key}"
            body = {"model": model_name, "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}], "temperature": 0.25}
            resp = requests.post(base_url.rstrip("/") + "/chat/completions", headers=headers, json=body, timeout=240).json()
            return resp["choices"][0]["message"]["content"] if "choices" in resp else f"LLM Error: {resp}"
    except Exception as e:
        return f"Connection Error: {str(e)}"

def build_chart(df, symbol, is_intraday=False, is_dark=True):
    plot_df = df.tail(120)
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.04, row_heights=[0.6, 0.2, 0.2])
    fig.add_trace(go.Candlestick(x=plot_df.index, open=plot_df["Open"], high=plot_df["High"], low=plot_df["Low"], close=plot_df["Close"], name="Price"), row=1, col=1)

    if is_intraday:
        fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df["EMA25"], line=dict(color="#f59e0b", width=2), name="25 EMA (Volman)"), row=1, col=1)
    else:
        fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df["EMA20"], line=dict(color="#f59e0b", width=1.5), name="EMA 20"), row=1, col=1)
        fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df["EMA50"], line=dict(color="#3b82f6", width=1.7), name="EMA 50"), row=1, col=1)
        fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df["EMA200"], line=dict(color="#ec4899", width=1.9), name="EMA 200"), row=1, col=1)

    colors = ["#10b981" if c >= o else "#ef4444" for c, o in zip(plot_df["Close"], plot_df["Open"])]
    fig.add_trace(go.Bar(x=plot_df.index, y=plot_df["Volume"], marker_color=colors, name="Volume"), row=2, col=1)
    fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df["RSI"], line=dict(color="#a855f7", width=1.6), name="RSI (14)"), row=3, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="#ef4444", row=3, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="#10b981", row=3, col=1)

    fig.update_layout(
        title=f"{symbol} — {'5-Min Bob Volman' if is_intraday else 'Daily Technical'} Chart",
        template="plotly_dark" if is_dark else "plotly_white",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=640, xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=42, b=10)
    )
    return fig

# ---------------------------------------------------------
# SIDEBAR: UI STUDIO + IMPORTANT LINKS + ANGEL ONE + CONTROLS
# ---------------------------------------------------------
st.sidebar.title("🦅 Ultimate Stock Agent")

with st.sidebar.expander("🎨 UI Theme & Wallpaper Studio", expanded=False):
    theme_mode = st.radio("Theme Style (Simply Wall St):", ["🌙 Deep Slate Dark", "☀️ Editorial Cream Light"], horizontal=True)
    is_dark = "Dark" in theme_mode
    wp_source = st.selectbox("Background Wallpaper:", ["Simply Wall St Clean (Default)", "Upload Custom Image", "Paste Image URL"])
    bg_css = "background: linear-gradient(145deg, #111721 0%, #151b24 55%, #1c2431 100%) !important;" if is_dark else "background: linear-gradient(145deg, #f5f2eb 0%, #faf8f4 55%, #efe9dc 100%) !important;"
    if wp_source == "Upload Custom Image":
        up_file = st.file_uploader("Wallpaper Upload (JPG/PNG/WEBP)", type=["jpg", "jpeg", "png", "webp"])
        if up_file is not None:
            bg_css = f'background-image: url("data:image/png;base64,{base64.b64encode(up_file.read()).decode()}") !important;'
    elif wp_source == "Paste Image URL":
        wp_url = st.text_input("Direct Image URL:", placeholder="https://images.unsplash.com/...")
        if wp_url.strip():
            bg_css = f'background-image: url("{wp_url.strip()}") !important;'
    overlay_alpha = st.slider("Background Dim / Tint", 0.15, 0.90, 0.45 if is_dark else 0.40, 0.05)
    blur_px = st.slider("Background Blur (px)", 0, 20, 4, 1)

inject_modern_theme(is_dark, bg_css, overlay_alpha, blur_px)

# IMPORTANT INDIAN MARKET LINKS IN LEFT SIDEBAR
with st.sidebar.expander("🔗 Important Market Links", expanded=False):
    for cat, links in IMPORTANT_INDIAN_LINKS.items():
        st.markdown(f"**{cat}**")
        for label, url in links:
            st.markdown(f"• [{label}]({url})")

# ANGEL ONE SMARTAPI CONNECTION PANEL
with st.sidebar.expander("⚡ Angel One SmartAPI (Live)", expanded=False):
    if st.session_state.get("angel_connected"):
        st.success("🟢 Connected to Angel One Live")
        if st.button("Disconnect Angel One"):
            st.session_state["angel_connected"] = False
            st.session_state["angel_api"] = None
            st.rerun()
    else:
        a_api_key = st.text_input("SmartAPI Key", type="password", key="a_key")
        a_client_id = st.text_input("Client ID", key="a_cid")
        a_mpin = st.text_input("MPIN", type="password", key="a_mpin")
        a_totp = st.text_input("TOTP Secret Key", type="password", key="a_totp")
        if st.button("🔌 Connect Angel One"):
            ok, msg = connect_angel_one(a_api_key, a_client_id, a_mpin, a_totp)
            if ok: st.success(msg); st.rerun()
            else: st.error(msg)

app_mode = st.sidebar.radio("App Mode:", [
    "🔍 Single Stock Deep-Dive",
    "🧭 Strategy Router & Index Scanner",
    "📝 Paper Trading & Angel One Desk"
])

st.sidebar.markdown("---")
st.sidebar.subheader("🎯 Strategy Router")
strategy = st.sidebar.selectbox("Active Scanner Strategy:", [
    "Classic Multi-Factor (Fund + Tech Confluence)",
    "Bob Volman Intraday (5m + 25 EMA)",
    "Bulkowski Swing & Positional (Stage 2)",
    "Parag Parikh Value (Conservative)",
    "Bulkowski Multibagger Hunt (Aggressive)",
    "Parag Parikh Cyclical Turnaround"
])
apply_hard_kill = st.sidebar.checkbox("Apply Global Hard-Kill Filters in Scanner", value=True)

st.sidebar.markdown("---")
st.sidebar.subheader("💰 Capital & Risk Guardrails")
capital = st.sidebar.number_input("Trading Capital (₹)", min_value=10000, value=100000, step=10000)
risk_pct = st.sidebar.slider("Max Risk Per Trade (%)", 0.5, 3.0, 1.0, 0.5)
order_size_inr = st.sidebar.number_input("Avg Order Size (₹) [Liquidity]", min_value=5000, value=25000, step=5000)
consecutive_losses = st.sidebar.number_input("Today's Consecutive Losses (Intraday Lock)", min_value=0, max_value=5, value=0)
manual_event_day = st.sidebar.checkbox("🚫 Today is RBI / Budget / Event Day (Intraday Skip)", value=False)

st.sidebar.markdown("---")
st.sidebar.subheader("🧠 AI Brain (Local / Cloud)")
ai_provider = st.sidebar.selectbox("LLM Provider", ["Local LLM (LM Studio / Colibri / Ollama)", "Gemini API (Google)", "Groq API"])
if ai_provider == "Gemini API (Google)":
    api_key = st.sidebar.text_input("Gemini API Key", value=get_secret_safe("GEMINI_API_KEY", ""), type="password")
    base_url, model_name = "", st.sidebar.text_input("Model", value="gemini-3.8-flash")
elif ai_provider == "Groq API":
    api_key = st.sidebar.text_input("Groq API Key", type="password")
    base_url = st.sidebar.text_input("Base URL", value="https://api.groq.com/openai/v1")
    model_name = st.sidebar.text_input("Model", value="llama-3.3-70b-versatile")
else:
    api_key = st.sidebar.text_input("API Key (Optional)", value="local")
    base_url = st.sidebar.text_input("Endpoint URL", value="http://localhost:1234/v1")
    model_name = st.sidebar.text_input("Model Name", value="qwen2.5-7b-instruct")

# ---------------------------------------------------------
# TOP HERO HEADER + MARKET REGIME BANNER
# ---------------------------------------------------------
st.markdown("""
<div class="hero-header">
    <p class="hero-title">🦅 Portfolio <span class="hero-accent">Command Center.</span></p>
    <p class="hero-sub">Snowflake Visual Analytics • Forensic Audit • Paper Trading • Angel One SmartAPI • Local & Cloud AI Brain</p>
</div>
""", unsafe_allow_html=True)

regime, nifty_curr, nifty_sma12, regime_mult = check_nifty_market_regime()
if regime == "BULL":
    st.markdown(f'<div class="pass-box">🟢 <b>Market Regime: BULLISH</b> — Nifty 50 (₹{nifty_curr:,.1f}) ABOVE 12-Month SMA (₹{nifty_sma12:,.1f}). Full Position Sizing (100%).</div>', unsafe_allow_html=True)
elif regime == "BEAR":
    st.markdown(f'<div class="kill-box">🔴 <b>Market Regime: BEARISH</b> — Nifty 50 (₹{nifty_curr:,.1f}) BELOW 12-Month SMA (₹{nifty_sma12:,.1f}). Position Sizing auto-scaled to <b>1/4 (25%)</b>.</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# MODE 1: SINGLE STOCK DEEP-DIVE
# ---------------------------------------------------------
if app_mode == "🔍 Single Stock Deep-Dive":
    sym_in = st.text_input("🔍 NSE/BSE Symbol search karein (e.g. BEL, TATAPOWER, TCS, COALINDIA):", value="BEL")

    if sym_in:
        with st.spinner(f"{sym_in.upper()} ka complete data aur Snowflake profile ban raha hai..."):
            info, d_df, w_df, df_15m, df_5m, fin_df = fetch_stock_bundle(sym_in, include_intraday=True)
            scr_data = fetch_screener_data(sym_in)
            news = fetch_google_news(info.get("longName", sym_in))

        if d_df is None or d_df.empty:
            st.error("Valid NSE/BSE stock data nahi mila.")
        else:
            yf_price = float(d_df["Close"].iloc[-1])
            price, price_src = get_live_ltp(sym_in, yf_price)
            prev_c = float(d_df["Close"].iloc[-2]) if len(d_df) > 1 else price
            chg_pct = ((price - prev_c) / prev_c) * 100

            is_killed, kill_reasons = run_hard_kill_filters(
                info, d_df, scr_data, order_size_inr,
                symbol=sym_in, is_intraday=("Intraday" in strategy), manual_event_day=manual_event_day
            )
            fund_score, red_flags, green_flags = analyze_fundamentals_and_red_flags(info, scr_data)
            classic_setups = generate_classic_trade_setups(d_df, w_df, df_15m, capital, risk_pct, regime_mult)
            volman_res = evaluate_bob_volman_intraday(df_5m, d_df, capital, risk_pct, consecutive_losses)
            swing_res = evaluate_bulkowski_swing(info, d_df, w_df, regime_mult, capital, risk_pct)
            val_res = evaluate_parag_parikh_value(info, scr_data)
            mb_res = evaluate_bulkowski_multibagger(info)
            cyc_res = evaluate_cyclical_turnaround(info)
            snow_scores = compute_snowflake_scores(info, scr_data)
            snow_fig, snow_total = build_snowflake_chart(snow_scores, is_dark=is_dark)

            # SIMPLY WALL ST STYLE HEADER: SNOWFLAKE RADAR + COMPANY OVERVIEW
            col_snow, col_overview = st.columns([1, 2.6])
            with col_snow:
                st.plotly_chart(snow_fig, use_container_width=True, config={"displayModeBar": False})
            with col_overview:
                st.markdown(f"""
                <div class="setup-card" style="margin-top: 8px;">
                    <h2 style="margin:0;">{info.get('longName', sym_in.upper())}</h2>
                    <p style="margin:4px 0 8px 0; opacity:0.8;"><b>{normalize_symbol(sym_in)}</b> • {info.get('sector', 'N/A')} | {info.get('industry', 'N/A')} • Feed: {price_src}</p>
                    <span class="sws-badge">❄️ Snowflake: {snow_total}/30</span>
                    <span class="sws-badge">Value: {snow_scores['VALUE']}/6</span>
                    <span class="sws-badge">Future: {snow_scores['FUTURE']}/6</span>
                    <span class="sws-badge">Past: {snow_scores['PAST']}/6</span>
                    <span class="sws-badge">Health: {snow_scores['HEALTH']}/6</span>
                    <span class="sws-badge">Dividend: {snow_scores['DIVIDEND']}/6</span>
                </div>
                """, unsafe_allow_html=True)

            if is_killed:
                st.markdown('<div class="kill-box"><b>🚫 GLOBAL HARD-KILL TRIGGERED:</b><br>' + "<br>".join([f"• {k}" for k in kill_reasons]) + "</div>", unsafe_allow_html=True)
            else:
                st.markdown('<div class="pass-box"><b>✅ PASSED ALL GLOBAL HARD-KILL & EVENT FILTERS</b></div>', unsafe_allow_html=True)

            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("CMP (LTP)", f"₹{price:,.2f}", f"{chg_pct:+.2f}%")
            m2.metric("Market Cap", format_inr_crore(info.get("marketCap")))
            m3.metric("P/E Ratio", safe_num(info.get("trailingPE")))
            m4.metric("ROE / ROCE", f"{safe_pct(info.get('returnOnEquity'))} / {scr_data.get('roce', 'N/A')}%")
            m5.metric("Fundamental Score", f"{fund_score}/100")

            st.write("")
            t1, t2, t3, t4, t5, t6 = st.tabs([
                "🎯 Pro Strategy Setups", "⚡ Classic Trade Setups", "🚩 Fundamentals & Sankey Flow",
                "📊 Technical Charts", "📰 Latest News", "🧠 AI Agent Verdict"
            ])

            with t1:
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"""<div class="setup-card"><h4>⚡ Bob Volman Intraday (5m + 25 EMA)</h4>
                    <p><b>Status:</b> {volman_res['status']} ({volman_res['score']}/100) | <b>Window:</b> {volman_res['time_window']}</p>
                    <p><b>Direction:</b> {volman_res['direction']}</p>
                    <p><b>Entry:</b> ₹{volman_res['entry']:,.2f} | <b>SL:</b> ₹{volman_res['sl']:,.2f} | <b>T2 (1:2):</b> ₹{volman_res['t2']:,.2f} | <b>Qty:</b> {volman_res['qty']}</p></div>""", unsafe_allow_html=True)
                    b1, b2 = st.columns(2)
                    if b1.button("📝 Paper Buy (Volman)", key="pb_vol"):
                        ok, msg = place_paper_buy(sym_in, max(1, volman_res["qty"]), price, volman_res["sl"], volman_res["t2"], "Bob Volman Intraday")
                        st.success(msg) if ok else st.error(msg)
                    if b2.button("⚡ Angel One BUY (Intraday)", key="ao_vol"):
                        ok, msg = place_angel_one_order(sym_in, "BUY", max(1, volman_res["qty"]), "INTRADAY")
                        st.success(msg) if ok else st.error(msg)

                with c2:
                    st.markdown(f"""<div class="setup-card"><h4>📈 Bulkowski Swing / Positional (Stage 2)</h4>
                    <p><b>Score:</b> {swing_res['score']}/100 | <b>Fund:</b> {swing_res['fund_score_20']}/20 | <b>Stage:</b> {swing_res['stage']}</p>
                    <p><b>Entry:</b> ₹{swing_res['entry']:,.2f} | <b>30W SMA SL:</b> ₹{swing_res['sl']:,.2f} | <b>T1:</b> ₹{swing_res['t1']:,.2f} | <b>Qty:</b> {swing_res['qty']}</p></div>""", unsafe_allow_html=True)
                    b3, b4 = st.columns(2)
                    if b3.button("📝 Paper Buy (Swing)", key="pb_sw"):
                        ok, msg = place_paper_buy(sym_in, max(1, swing_res["qty"]), price, swing_res["sl"], swing_res["t1"], "Bulkowski Swing")
                        st.success(msg) if ok else st.error(msg)
                    if b4.button("⚡ Angel One BUY (Delivery)", key="ao_sw"):
                        ok, msg = place_angel_one_order(sym_in, "BUY", max(1, swing_res["qty"]), "DELIVERY")
                        st.success(msg) if ok else st.error(msg)

                c3, c4, c5 = st.columns(3)
                c3.metric("Parag Parikh Value", f"{val_res['score']}/100")
                c4.metric("Bulkowski Multibagger", f"{mb_res['score']}/100")
                c5.metric("Cyclical Turnaround", f"{cyc_res['score']}/100")

            with t2:
                cols = st.columns(len(classic_setups)) if classic_setups else []
                for idx, (sname, s) in enumerate(classic_setups.items()):
                    with cols[idx]:
                        st.markdown(f"""<div class="setup-card"><h4>{sname}</h4>
                        <p><b>Signal:</b> {s['bias']}</p><p><b>Entry:</b> ₹{s['entry']:,.2f}</p>
                        <p><b>SL:</b> ₹{s['sl']:,.2f}</p><p><b>T1:</b> ₹{s['t1']:,.2f} | <b>T2:</b> ₹{s['t2']:,.2f}</p>
                        <p><b>Qty:</b> {s['qty']} shares</p></div>""", unsafe_allow_html=True)

            with t3:
                # SIMPLY WALL ST STYLE SANKEY FINANCIAL FLOW
                sankey_fig = build_financial_sankey(info, fin_df, is_dark=is_dark)
                if sankey_fig is not None:
                    st.plotly_chart(sankey_fig, use_container_width=True)

                cr, cg = st.columns(2)
                with cr:
                    st.markdown("### 🚩 Forensic Red Flags")
                    for rf in red_flags: st.markdown(f'<div class="red-flag">⚠️ {rf}</div>', unsafe_allow_html=True)
                    if not red_flags: st.success("Koi major red flag detect nahi hua.")
                with cg:
                    st.markdown("### ✅ Key Strengths")
                    for gf in green_flags: st.markdown(f'<div class="green-flag">✔️ {gf}</div>', unsafe_allow_html=True)
                    if not green_flags: st.info("Limited strength signals.")

                st.markdown("### 📋 Complete Fundamental Sheet")
                fund_table = pd.DataFrame([
                    ["Market Cap", format_inr_crore(info.get("marketCap")), "Trailing P/E", safe_num(info.get("trailingPE"))],
                    ["Forward P/E", safe_num(info.get("forwardPE")), "PEG Ratio", safe_num(info.get("pegRatio"))],
                    ["Price to Book (P/B)", safe_num(info.get("priceToBook")), "Dividend Yield", safe_pct(info.get("dividendYield"))],
                    ["ROE", safe_pct(info.get("returnOnEquity")), "Screener ROCE", f"{scr_data.get('roce', 'N/A')}%"],
                    ["Operating Margin", safe_pct(info.get("operatingMargins")), "Profit Margin", safe_pct(info.get("profitMargins"))],
                    ["Revenue Growth", safe_pct(info.get("revenueGrowth")), "Earnings Growth", safe_pct(info.get("earningsGrowth"))],
                    ["Debt to Equity", safe_num(info.get("debtToEquity")), "Current Ratio", safe_num(info.get("currentRatio"))],
                    ["Operating Cash Flow", format_inr_crore(info.get("operatingCashflow")), "Free Cash Flow", format_inr_crore(info.get("freeCashflow"))],
                    ["52-Week High", f"₹{safe_num(info.get('fiftyTwoWeekHigh'))}", "52-Week Low", f"₹{safe_num(info.get('fiftyTwoWeekLow'))}"]
                ], columns=["Metric", "Value", "Metric ", "Value "])
                st.dataframe(fund_table, use_container_width=True, hide_index=True)

                st.markdown("### 🏛️ Screener.in — 10-Year P&L & Shareholding")
                if not scr_data["pnl_df"].empty: st.dataframe(scr_data["pnl_df"], use_container_width=True, hide_index=True)
                if not scr_data["shareholding_df"].empty: st.dataframe(scr_data["shareholding_df"], use_container_width=True, hide_index=True)

            with t4:
                chart_choice = st.radio("Chart Timeframe:", ["Daily (EMA 20/50/200 + RSI)", "5-Minute (Bob Volman 25 EMA)"], horizontal=True)
                if "5-Minute" in chart_choice and not df_5m.empty:
                    st.plotly_chart(build_chart(df_5m, sym_in.upper(), is_intraday=True, is_dark=is_dark), use_container_width=True)
                else:
                    st.plotly_chart(build_chart(d_df, sym_in.upper(), is_intraday=False, is_dark=is_dark), use_container_width=True)
                last_d = d_df.iloc[-1]
                k1, k2, k3, k4, k5 = st.columns(5)
                k1.metric("RSI (14)", safe_num(last_d["RSI"]))
                k2.metric("ADX (14)", safe_num(last_d["ADX"]))
                k3.metric("ATR (14)", f"₹{safe_num(last_d['ATR'])}")
                k4.metric("Volume Ratio", f"{safe_num(last_d['VOL_RATIO'])}x")
                k5.metric("MACD Hist", safe_num(last_d["MACD_HIST"]))

            with t5:
                for n in news: st.markdown(f"- [{n['title']}]({n['link']})  \n  *{n['date']}*")

            with t6:
                if st.button("✨ Generate Complete AI Report", type="primary"):
                    payload = {
                        "company": info.get("longName", sym_in), "price": round(price, 2), "market_regime": regime,
                        "snowflake_scores_out_of_6": snow_scores, "hard_kill_passed": not is_killed, "hard_kill_reasons": kill_reasons,
                        "fundamental_score": fund_score, "red_flags": red_flags, "green_flags": green_flags,
                        "screener_roce": scr_data.get("roce"), "promoter_pledge": scr_data.get("promoter_pledge"),
                        "classic_setups": classic_setups, "volman_intraday": volman_res, "bulkowski_swing": swing_res,
                        "parag_parikh_value": val_res, "multibagger": mb_res, "latest_news": [n["title"] for n in news]
                    }
                    with st.spinner("AI Agent report generate kar raha hai..."):
                        st.markdown(call_ai_agent(ai_provider, api_key, base_url, model_name, payload))

# ---------------------------------------------------------
# MODE 2: STRATEGY ROUTER & MULTI-INDEX SCANNER
# ---------------------------------------------------------
elif app_mode == "🧭 Strategy Router & Index Scanner":
    st.subheader(f"🧭 {strategy}")
    index_options = ["Custom Watchlist"] + list(NSE_INDEX_URLS.keys()) + list(BSE_INDEX_LISTS.keys())
    selected_index = st.selectbox("📂 Index ya Watchlist Chunein (NSE / BSE / Sectoral):", index_options)
    fetched_symbols = fetch_index_symbols(selected_index)
    custom_list = st.text_area(f"Selected Symbols ({len(fetched_symbols)} stocks):", value=", ".join(fetched_symbols), height=95)

    if st.button("🚀 Run Scan", type="primary"):
        symbols = [s.strip().upper() for s in custom_list.split(",") if s.strip()]
        passed_rows, killed_rows = [], []
        progress = st.progress(0)

        for i, sym in enumerate(symbols):
            try:
                is_intra = "Intraday" in strategy
                info, d_df, w_df, _, df_5m, _ = fetch_stock_bundle(sym, include_intraday=is_intra)
                is_killed, kill_reasons = run_hard_kill_filters(
                    info, d_df, None, order_size_inr,
                    symbol=sym, is_intraday=is_intra, manual_event_day=manual_event_day
                ) if apply_hard_kill else (False, [])

                if is_killed:
                    killed_rows.append({"Symbol": sym, "Kill Reason": " | ".join(kill_reasons)})
                elif d_df is not None and len(d_df) >= 60:
                    price = float(d_df["Close"].iloc[-1])
                    if "Classic Multi-Factor" in strategy:
                        f_s, r_f, _ = analyze_fundamentals_and_red_flags(info)
                        last = d_df.iloc[-1]
                        t_s = (25 if price > last["EMA200"] else 0) + (20 if price > last["EMA50"] else 0) + (20 if price > last["EMA20"] > last["EMA50"] else 0) + (15 if 50 <= last["RSI"] <= 68 else 0) + (10 if (last["ADX"] or 0) >= 20 else 0) + (10 if (last["VOL_RATIO"] or 0) >= 1.2 else 0)
                        passed_rows.append({"Symbol": sym, "CMP (₹)": round(price, 2), "Total Score": round(0.5*f_s + 0.5*t_s, 1), "Fund Score": f_s, "Tech Score": t_s, "RSI": round(float(last["RSI"]), 1), "ADX": round(float(last["ADX"] or 0), 1), "Red Flags": len(r_f)})
                    elif "Bob Volman" in strategy:
                        res = evaluate_bob_volman_intraday(df_5m, d_df, capital, risk_pct, consecutive_losses)
                        passed_rows.append({"Symbol": sym, "CMP (₹)": round(price, 2), "Score": res["score"], "Signal": res["direction"], "Entry": round(res["entry"], 2), "SL": round(res["sl"], 2), "Target (1:2)": round(res["t2"], 2), "Qty": res["qty"]})
                    elif "Bulkowski Swing" in strategy:
                        res = evaluate_bulkowski_swing(info, d_df, w_df, regime_mult, capital, risk_pct)
                        passed_rows.append({"Symbol": sym, "CMP (₹)": round(price, 2), "Score": res["score"], "Fund (/20)": res["fund_score_20"], "Stage": res["stage"], "SL (30W SMA)": round(res["sl"], 2), "Qty": res["qty"]})
                    elif "Parag Parikh Value" in strategy:
                        res = evaluate_parag_parikh_value(info, None)
                        passed_rows.append({"Symbol": sym, "CMP (₹)": round(price, 2), "Value Score": res["score"], "P/E": safe_num(info.get("trailingPE")), "Div Yield": safe_pct(info.get("dividendYield")), "Highlights": " | ".join(res["notes"][:3])})
                    elif "Multibagger" in strategy:
                        res = evaluate_bulkowski_multibagger(info)
                        passed_rows.append({"Symbol": sym, "CMP (₹)": round(price, 2), "Multibagger Score": res["score"], "P/BV": safe_num(info.get("priceToBook")), "PSR": safe_num(info.get("priceToSalesTrailing12Months")), "Highlights": " | ".join(res["notes"][:3])})
                    else:
                        res = evaluate_cyclical_turnaround(info)
                        passed_rows.append({"Symbol": sym, "CMP (₹)": round(price, 2), "Cyclical Score": res["score"], "P/E": safe_num(info.get("trailingPE")), "OPM": safe_pct(info.get("operatingMargins")), "Highlights": " | ".join(res["notes"])})
            except Exception:
                pass
            progress.progress((i + 1) / len(symbols))

        if passed_rows:
            df_pass = pd.DataFrame(passed_rows)
            sort_col = [c for c in df_pass.columns if "Score" in c][0]
            df_pass = df_pass.sort_values(by=sort_col, ascending=False)
            st.success(f"✅ {len(df_pass)} Stocks Shortlisted ({strategy})")
            st.dataframe(df_pass, use_container_width=True, hide_index=True)
            st.download_button("📥 Download Results (CSV)", df_pass.to_csv(index=False).encode("utf-8"), "ultimate_stock_picks.csv", "text/csv")
        else:
            st.warning("Koi stock pass nahi hua. Sidebar mein Hard-Kill toggle check karein ya dusra index try karein.")

        if killed_rows:
            with st.expander(f"🚫 Excluded by Hard-Kill Filters ({len(killed_rows)} stocks)"):
                st.dataframe(pd.DataFrame(killed_rows), use_container_width=True, hide_index=True)

# ---------------------------------------------------------
# MODE 3: PAPER TRADING & ANGEL ONE EXECUTION DESK
# ---------------------------------------------------------
else:
    st.subheader("📝 Paper Trading Portfolio & ⚡ Angel One Live Desk")
    pf = load_paper_portfolio(capital)

    open_pnl_total, invested_total = 0.0, 0.0
    live_rows = []
    for idx, pos in enumerate(pf["positions"]):
        try:
            hist = yf.Ticker(normalize_symbol(pos["symbol"])).history(period="2d", interval="1d")
            yf_ltp = float(hist["Close"].iloc[-1]) if not hist.empty else pos["entry"]
        except Exception:
            yf_ltp = pos["entry"]
        ltp, _ = get_live_ltp(pos["symbol"], yf_ltp)
        pnl = (ltp - pos["entry"]) * pos["qty"]
        open_pnl_total += pnl
        invested_total += pos["entry"] * pos["qty"]
        status = "🎯 TARGET HIT" if ltp >= pos["target"] else ("🛑 SL HIT" if ltp <= pos["sl"] else "ACTIVE")
        live_rows.append({"#": idx, "Symbol": pos["symbol"], "Qty": pos["qty"], "Entry (₹)": pos["entry"], "LTP (₹)": round(ltp, 2), "SL": pos["sl"], "Target": pos["target"], "P&L (₹)": round(pnl, 2), "Status": status, "Strategy": pos["strategy"]})

    realized_pnl = sum(h.get("pnl", 0) for h in pf["history"])
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Available Paper Cash", f"₹{pf['cash']:,.2f}")
    p2.metric("Invested Capital", f"₹{invested_total:,.2f}")
    p3.metric("Live Unrealized P&L", f"₹{open_pnl_total:+,.2f}")
    p4.metric("Realized P&L", f"₹{realized_pnl:+,.2f}")

    st.markdown("### 📊 Open Paper Positions")
    if live_rows:
        st.dataframe(pd.DataFrame(live_rows), use_container_width=True, hide_index=True)
        c_sel, c_btn = st.columns([2, 1])
        pos_idx = c_sel.selectbox("Close Position Select karein:", [f"{r['#']} — {r['Symbol']} (LTP: ₹{r['LTP (₹)']})" for r in live_rows])
        if c_btn.button("🔒 Close Selected Paper Trade", type="primary"):
            idx_num = int(pos_idx.split(" — ")[0])
            exit_p = live_rows[idx_num]["LTP (₹)"]
            ok, msg = close_paper_position(idx_num, exit_p)
            st.success(msg) if ok else st.error(msg)
            st.rerun()
    else:
        st.info("Abhi koi open paper position nahi hai. Single Stock Deep-Dive → Pro Strategy Setups se '📝 Paper Buy' click karein.")

    with st.expander("📜 Closed Paper Trade History & Reset"):
        if pf["history"]:
            st.dataframe(pd.DataFrame(pf["history"]), use_container_width=True, hide_index=True)
        if st.button("🔄 Reset Paper Portfolio to ₹1,00,000"):
            save_paper_portfolio({"cash": 100000.0, "initial_capital": 100000.0, "positions": [], "history": []})
            st.success("Paper Portfolio reset ho gaya!")
            st.rerun()

    st.markdown("---")
    st.markdown("### ⚡ Angel One Live Demat Desk")
    if st.session_state.get("angel_connected") and st.session_state.get("angel_api"):
        if st.button("🔄 Fetch Live Margin & Order Book"):
            try:
                rms = st.session_state["angel_api"].rmsLimit()
                if rms.get("status"):
                    net_cash = rms["data"].get("net", "N/A")
                    st.success(f"💰 Angel One Available Margin: ₹{net_cash}")
                ob = st.session_state["angel_api"].orderBook()
                if ob.get("status") and ob.get("data"):
                    st.dataframe(pd.DataFrame(ob["data"])[["tradingsymbol", "transactiontype", "quantity", "orderstatus", "averageprice"]], use_container_width=True, hide_index=True)
                else:
                    st.info("Aaj Angel One par koi live order nahi hai.")
            except Exception as e:
                st.error(f"Fetch Error: {e}")
    else:
        st.info("Live Demat Margin aur 1-Click Orders ke liye left sidebar mein **⚡ Angel One SmartAPI (Live)** connect karein.")