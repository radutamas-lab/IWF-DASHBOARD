#!/usr/bin/env python3
"""
Dashboard Facturare WIL & WISE — v3
Rulare: python -m streamlit run dashboard_v3.py
"""

import streamlit as st
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import calendar
from pathlib import Path

st.set_page_config(
    page_title="Dashboard Facturare — WIL & WISE",
    page_icon="📊",
    layout="wide"
)

st.markdown("""
<style>
    .main { background-color: #f8f9fb; }
    .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }
    .kpi-card {
        background: white; border-radius: 12px;
        padding: 18px 20px; border: 1px solid #e0e6f0; text-align: center;
    }
    .kpi-val { font-size: 2rem; font-weight: 700; line-height: 1.1; }
    .kpi-lbl { font-size: 0.75rem; color: #7f8c8d; text-transform: uppercase;
               letter-spacing: 0.08em; margin-top: 4px; }
    .kpi-sub { font-size: 0.72rem; color: #95a5a6; margin-top: 2px; }
    .section-title {
        font-size: 1rem; font-weight: 600; color: #1B4F91;
        border-left: 4px solid #1B4F91;
        padding-left: 10px; margin: 20px 0 12px 0;
    }
</style>
""", unsafe_allow_html=True)

# ── CITIRE DATE ────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_data():
    import gspread
    from google.oauth2.service_account import Credentials
    import pandas as pd

    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

 import streamlit as st

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=SCOPES
)

    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key("1cWPfnZrBfFPaeGEBDW1VevM7yRImgtEpscYpb7d-McQ")

    ws_wil = spreadsheet.worksheet("WILL")
    ws_wise = spreadsheet.worksheet("WISE")

    wil_rows = ws_wil.get_all_records()
    wise_rows = ws_wise.get_all_records()

    df_wil = pd.DataFrame(wil_rows)
    df_wise = pd.DataFrame(wise_rows)

    if not df_wil.empty:
        df_wil["entitate"] = "WIL"

    if not df_wise.empty:
        df_wise["entitate"] = "WISE"

    df = pd.concat([df_wil, df_wise], ignore_index=True)

    if df.empty:
        return df

    df["data"] = pd.to_datetime(df["Data_emitere"], format="%d/%m/%Y", errors="coerce")
    df["total"] = pd.to_numeric(df["Total_cu_TVA"], errors="coerce")
    df["luna_nr"] = pd.to_numeric(df["Luna_nr"], errors="coerce")
    df["zi"] = pd.to_numeric(df["Zi_emitere"], errors="coerce")
    df["tardiva"] = df["Tardiva"].astype(str).str.lower().eq("da")
    df["luna"] = df["Luna"]

    return df
df = load_data()

# ── HEADER + FILTRE ───────────────────────────────────────────────────────────
col_t, col_f1, col_f2, col_f3 = st.columns([2.5, 1, 1, 1])
with col_t:
    st.markdown("## 📊 Dashboard Facturare — WIL & WISE")
    st.caption("Ianuarie–Martie 2026  ·  Date din sistem contabil")

with col_f1:
    entitate_opt = st.selectbox("Entitate", ["WIL + WISE", "WIL", "WISE"])

with col_f2:
    luni_disponibile = sorted(
        df['luna'].dropna().unique().tolist(),
        key=lambda x: {'Ianuarie':1,'Februarie':2,'Martie':3}.get(x.split()[0], 99)
    )
    luna_sel_single = st.selectbox("Luna", ["Toate lunile"] + luni_disponibile)
    luna_sel = luni_disponibile if luna_sel_single == "Toate lunile" else [luna_sel_single]

with col_f3:
    zi_min = int(df['zi'].min())
    zi_max = int(df['zi'].max())
    zi_range = st.slider("Zile emitere", zi_min, zi_max, (zi_min, zi_max))

# ── FILTRARE ──────────────────────────────────────────────────────────────────
dff = df.copy()
if entitate_opt != "WIL + WISE":
    dff = dff[dff['entitate'] == entitate_opt]
luna_nr_map = {'Ianuarie 2026':1,'Februarie 2026':2,'Martie 2026':3}
luni_sel_nr = [luna_nr_map[l] for l in luna_sel] if luna_sel else list(luna_nr_map.values())
luna_nr_sel = luni_sel_nr[-1] if len(luni_sel_nr) == 1 else None

if luna_sel:
    dff = dff[dff['luna_nr'].isin(luni_sel_nr)]
dff = dff[(dff['zi'] >= zi_range[0]) & (dff['zi'] <= zi_range[1])]

# date fara filtru zi pentru graficele lunare
dff_nozi = df.copy()
if entitate_opt != "WIL + WISE":
    dff_nozi = dff_nozi[dff_nozi['entitate'] == entitate_opt]
if luna_sel:
    dff_nozi = dff_nozi[dff_nozi['luna_nr'].isin(luni_sel_nr)]

# ── KPI-URI ───────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Indicatori Cheie</div>', unsafe_allow_html=True)

n_total   = len(dff)
zi_med    = round(dff['zi'].mean(), 1) if n_total > 0 else 0
pct_10    = round((dff['zi'] <= 10).sum() / n_total * 100, 1) if n_total > 0 else 0
total_ron = round(dff['total'].sum() / 1_000_000, 2) if n_total > 0 else 0

def kpi(col, val, label, sub="", color="#1B4F91"):
    col.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-val" style="color:{color}">{val}</div>
        <div class="kpi-lbl">{label}</div>
        <div class="kpi-sub">{sub}</div>
    </div>""", unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
kpi(c1, f"Ziua {zi_med}", "Zi Medie Emitere",
    ', '.join(luna_sel) if luna_sel else 'toate lunile',
    "#C0392B" if zi_med > 15 else ("#E67E22" if zi_med > 10 else "#1A6B3C"))
kpi(c2, f"{pct_10}%", "In primele 10 zile", f"din {n_total} facturi",
    "#1A6B3C" if pct_10 >= 50 else "#C0392B")
kpi(c3, f"{total_ron}M RON", "Total Facturat",
    ', '.join(luna_sel) if luna_sel else 'toate lunile')

st.markdown("<br>", unsafe_allow_html=True)

# ── STILURI GRAFICE ───────────────────────────────────────────────────────────
BG   = 'white'; GRID = '#EBF0F7'; TEXT = '#1A1A2E'; SUB = '#7F8C8D'
COLORS_LUNA = {1:'#B03020', 2:'#E67E22', 3:'#1A6B3C'}
luni   = [1, 2, 3]
luni_n = ['Ianuarie\n2026', 'Februarie\n2026', 'Martie\n2026']

col_g1, col_g2 = st.columns(2)

# ── GRAFIC 1: Zi Medie ────────────────────────────────────────────────────────
with col_g1:
    st.markdown('<div class="section-title">Viteza de Facturare — Ziua Medie de Emitere</div>',
                unsafe_allow_html=True)
    zi_vals = []
    for m in luni:
        d = dff_nozi[dff_nozi['luna_nr'] == m]
        zi_vals.append(round(d['zi'].mean(), 1) if len(d) > 0 else 0)

    fig, ax = plt.subplots(figsize=(6, 4), facecolor=BG)
    ax.set_facecolor(BG)
    x = np.arange(3)
    bar_colors = [COLORS_LUNA[m] for m in luni]
    bars = ax.bar(x, zi_vals, color=bar_colors, width=0.5, zorder=3,
                  edgecolor='white', linewidth=1)

    for bar, val, col in zip(bars, zi_vals, bar_colors):
        if val > 0:
            ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.25,
                    f'Ziua {val}', ha='center', va='bottom',
                    fontsize=12, fontweight='bold', color=col)

    ax.axhline(10, color='#1A6B3C', linestyle=':', linewidth=2, zorder=2, alpha=0.8)
    ax.text(2.42, 10.15, 'target\n≤ 10', ha='left', va='bottom',
            fontsize=8, color='#1A6B3C', style='italic')

    for i in range(len(zi_vals)-1):
        if zi_vals[i] > 0 and zi_vals[i+1] > 0:
            delta = round(zi_vals[i+1] - zi_vals[i], 1)
            ax.annotate('', xy=(i+1, zi_vals[i+1]+0.2),
                        xytext=(i, zi_vals[i]+0.2),
                        arrowprops=dict(arrowstyle='->', color='#2C3E50',
                                       lw=1.5, linestyle='dashed' if i==0 else 'solid'))
            ax.text(i+0.5, (zi_vals[i]+zi_vals[i+1])/2+1.2,
                    f'{delta:+.1f} zile', ha='center', fontsize=8.5,
                    style='italic', fontweight='bold',
                    color='#1A6B3C' if delta < 0 else '#C0392B')

    ax.set_xticks(x); ax.set_xticklabels(luni_n, fontsize=9, color=TEXT)
    ax.set_ylim(0, max(zi_vals+[0])+5 if any(zi_vals) else 25)
    ax.set_ylabel('Ziua medie de emitere', fontsize=8.5, color=SUB)
    ax.grid(axis='y', color=GRID, linewidth=0.8, zorder=0)
    ax.spines[['top','right','left']].set_visible(False)
    ax.spines['bottom'].set_color(GRID)
    ax.tick_params(left=False, colors=SUB)
    fig.tight_layout()
    st.pyplot(fig); plt.close()

# ── GRAFIC 2: % Cumulative (fostul pie) ──────────────────────────────────────
with col_g2:
    st.markdown('<div class="section-title">Procent Facturi în Primele N Zile</div>',
                unsafe_allow_html=True)
    cutoffs    = [10, 15, 20]
    labels_cut = ['Până la\nziua 10', 'Până la\nziua 15', 'Până la\nziua 20']

    fig, ax = plt.subplots(figsize=(6, 4), facecolor=BG)
    ax.set_facecolor(BG)
    x = np.arange(3); w = 0.25

    for i, (m, col, lbl) in enumerate(zip(luni,
            [COLORS_LUNA[m] for m in luni], ['Ianuarie','Februarie','Martie'])):
        d = dff_nozi[dff_nozi['luna_nr'] == m]; n = len(d)
        pcts = [round((d['zi']<=c).sum()/n*100, 1) if n > 0 else 0 for c in cutoffs]
        b = ax.bar(x + (i-1)*w, pcts, w, color=col, label=lbl,
                   zorder=3, alpha=0.9, edgecolor='white')
        for bar, pct in zip(b, pcts):
            if pct > 0:
                ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.5,
                        f'{pct:.0f}%', ha='center', va='bottom',
                        fontsize=7.5, fontweight='bold', color=col)

    ax.set_xticks(x); ax.set_xticklabels(labels_cut, fontsize=9, color=TEXT)
    ax.set_ylim(0, 115)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v,_: f'{v:.0f}%'))
    ax.set_ylabel('% din total facturi', fontsize=8.5, color=SUB)
    ax.grid(axis='y', color=GRID, linewidth=0.8, zorder=0)
    ax.spines[['top','right','left']].set_visible(False)
    ax.spines['bottom'].set_color(GRID)
    ax.tick_params(left=False, colors=SUB)
    ax.legend(frameon=False, fontsize=8.5, loc='upper left')
    fig.tight_layout()
    st.pyplot(fig); plt.close()

st.markdown("<br>", unsafe_allow_html=True)

# ── GRAFIC 3 + 4 ──────────────────────────────────────────────────────────────
col_g3, col_g4 = st.columns(2)

with col_g3:
    st.markdown('<div class="section-title">Facturi Emise după Ziua 20</div>',
                unsafe_allow_html=True)
    tard_vals = [int((dff_nozi[dff_nozi['luna_nr']==m]['zi']>20).sum()) for m in luni]

    fig, ax = plt.subplots(figsize=(6, 3.8), facecolor=BG)
    ax.set_facecolor(BG)
    bars = ax.bar(np.arange(3), tard_vals, color=bar_colors, width=0.5,
                  zorder=3, edgecolor='white', linewidth=1)
    for bar, val, col in zip(bars, tard_vals, bar_colors):
        label = str(val) if val > 0 else '✓ ZERO'
        ax.text(bar.get_x()+bar.get_width()/2,
                bar.get_height()+0.3 if val > 0 else 0.5,
                label, ha='center', va='bottom',
                fontsize=13, fontweight='bold', color=col)
    ax.set_xticks(np.arange(3))
    ax.set_xticklabels(['Ianuarie','Februarie','Martie'], fontsize=9, color=TEXT)
    ax.set_ylim(0, max(tard_vals+[1])+8)
    ax.set_ylabel('Nr. facturi tardive', fontsize=8.5, color=SUB)
    ax.grid(axis='y', color=GRID, linewidth=0.8, zorder=0)
    ax.spines[['top','right','left']].set_visible(False)
    ax.spines['bottom'].set_color(GRID)
    ax.tick_params(left=False, colors=SUB)
    fig.tight_layout()
    st.pyplot(fig); plt.close()

with col_g4:
    st.markdown('<div class="section-title">WIL vs WISE — Zi Medie Comparativ</div>',
                unsafe_allow_html=True)
    fig, ax = plt.subplots(figsize=(6, 3.8), facecolor=BG)
    ax.set_facecolor(BG)
    x4 = np.arange(3); w4 = 0.35
    for i, (ent, col) in enumerate([('WIL','#1B4F91'),('WISE','#C0392B')]):
        vals = []
        for m in luni:
            d = dff_nozi[(dff_nozi['luna_nr']==m) & (dff_nozi['entitate']==ent)]
            vals.append(round(d['zi'].mean(),1) if len(d)>0 else 0)
        b = ax.bar(x4+(i-0.5)*w4, vals, w4, color=col, label=ent,
                   zorder=3, edgecolor='white', alpha=0.9)
        for bar, val in zip(b, vals):
            if val > 0:
                ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.15,
                        f'{val}', ha='center', va='bottom',
                        fontsize=9, fontweight='bold', color=col)
    ax.axhline(10, color='#1A6B3C', linestyle=':', linewidth=1.5, zorder=2, alpha=0.7)
    ax.set_xticks(x4)
    ax.set_xticklabels(['Ianuarie','Februarie','Martie'], fontsize=9, color=TEXT)
    ax.set_ylabel('Ziua medie de emitere', fontsize=8.5, color=SUB)
    ax.set_ylim(0, 22)
    ax.grid(axis='y', color=GRID, linewidth=0.8, zorder=0)
    ax.spines[['top','right','left']].set_visible(False)
    ax.spines['bottom'].set_color(GRID)
    ax.tick_params(left=False, colors=SUB)
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    st.pyplot(fig); plt.close()

st.markdown("<br>", unsafe_allow_html=True)

# ── CALENDAR ──────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Calendar Activitate Facturare</div>',
            unsafe_allow_html=True)

cal_luna_nr = luni_sel_nr[-1] if luni_sel_nr else 3
cal_luna_name = {1:'IANUARIE',2:'FEBRUARIE',3:'MARTIE'}.get(cal_luna_nr,'')

dff_cal = df.copy()
if entitate_opt != "WIL + WISE":
    dff_cal = dff_cal[dff_cal['entitate'] == entitate_opt]
dff_cal = dff_cal[dff_cal['luna_nr'] == cal_luna_nr]

zi_counts = dff_cal.groupby('zi').size().to_dict()
max_count = max(zi_counts.values()) if zi_counts else 1

def get_color(n, mx):
    if n == 0: return '#EBF0F7'
    pct = n / mx
    if pct <= 0.25: return '#C0DD97'
    if pct <= 0.50: return '#639922'
    if pct <= 0.75: return '#3B6D11'
    return '#1A6B3C'

first_day, days_in_month = calendar.monthrange(2026, cal_luna_nr)
first_day = first_day % 7

zile_saptamana = ['L','Ma','Mi','J','V','S','D']
header_html = ''.join([
    f'<div style="text-align:center;font-size:12px;font-weight:600;'
    f'font-family:Calibri,sans-serif;color:#7F8C8D;padding:4px 0">{z}</div>'
    for z in zile_saptamana
])

cells = ['<div style="background:transparent"></div>'] * first_day
for day in range(1, days_in_month+1):
    n = zi_counts.get(day, 0)
    color = get_color(n, max_count)
    tooltip = f'{n} facturi' if n > 0 else 'nicio factura'
    cells.append(f"""
    <div title="{tooltip}" style="
        background:{color};border-radius:6px;aspect-ratio:1;
        display:flex;align-items:center;justify-content:center;
        font-size:12px;font-family:Calibri,sans-serif;
        color:{'#1A1A2E' if n>0 else '#7F8C8D'};
        font-weight:{'600' if n>0 else '400'};cursor:default;"
        onmouseover="this.style.transform='scale(1.1)'"
        onmouseout="this.style.transform='scale(1)'">
        {day}
    </div>""")

while len(cells) % 7 != 0:
    cells.append('<div style="background:transparent"></div>')

legend_html = """
<div style="display:flex;align-items:center;gap:8px;margin-top:14px;
     font-size:12px;font-family:Calibri,sans-serif;color:#7F8C8D;">
    <span>Mai puțin</span>
    <div style="width:14px;height:14px;border-radius:3px;background:#C0DD97"></div>
    <div style="width:14px;height:14px;border-radius:3px;background:#639922"></div>
    <div style="width:14px;height:14px;border-radius:3px;background:#3B6D11"></div>
    <div style="width:14px;height:14px;border-radius:3px;background:#1A6B3C"></div>
    <span>Mai mult</span>
</div>"""

cal_html = f"""
<div style="background:white;border-radius:14px;padding:24px 28px;
     border:1px solid #e0e6f0;max-width:680px;">
    <div style="font-size:1.1rem;font-weight:700;color:#1A1A2E;
         font-family:Calibri,sans-serif;margin-bottom:2px;">
         📅 Calendar Activitate Facturare</div>
    <div style="font-size:0.72rem;font-weight:600;color:#1B4F91;
         font-family:Calibri,sans-serif;letter-spacing:0.15em;
         text-transform:uppercase;margin-bottom:16px;">
         Distributie zile facturare — {cal_luna_name} 2026</div>
    <div style="display:grid;grid-template-columns:repeat(7,1fr);
         gap:5px;margin-bottom:4px;">{header_html}</div>
    <div style="display:grid;grid-template-columns:repeat(7,1fr);gap:5px;">
        {''.join(cells)}
    </div>
    {legend_html}
</div>"""

col_cal, _ = st.columns([2, 1])
with col_cal:
    st.markdown(cal_html, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── TABEL SUMAR ───────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Tabel Sumar Detaliat</div>', unsafe_allow_html=True)

rows = []
luni_tabel = luni_sel_nr if luni_sel_nr else [1,2,3]
luna_names = {1:'Ianuarie 2026',2:'Februarie 2026',3:'Martie 2026'}

for m in luni_tabel:
    for ent in ['WIL','WISE','TOTAL']:
        base = dff_nozi if luna_nr_sel else df
        if entitate_opt != "WIL + WISE" and ent != 'TOTAL':
            if ent != entitate_opt: continue
        d = base[base['luna_nr']==m] if ent=='TOTAL' \
            else base[(base['luna_nr']==m)&(base['entitate']==ent)]
        n = len(d)
        if n == 0: continue
        rows.append({
            'Luna': luna_names[m], 'Entitate': ent, 'Nr. Facturi': n,
            'Zi Medie': round(d['zi'].mean(),1),
            '% in 10z': f"{round((d['zi']<=10).sum()/n*100,1)}%",
            '% in 15z': f"{round((d['zi']<=15).sum()/n*100,1)}%",
            '% in 20z': f"{round((d['zi']<=20).sum()/n*100,1)}%",
            'Tardive': int((d['zi']>20).sum()),
            'Total RON': f"{round(d['total'].sum()/1e6,2)}M",
        })

if rows:
    tbl = pd.DataFrame(rows)
    def color_rows(row):
        if row['Entitate'] == 'TOTAL':
            return ['background-color:#2C3E50;color:white']*len(row)
        elif row['Entitate'] == 'WIL':
            return ['background-color:#DCE6F1;color:#1A1A2E']*len(row)
        return ['background-color:#FCE4D6;color:#1A1A2E']*len(row)
    st.dataframe(tbl.style.apply(color_rows, axis=1),
                 use_container_width=True, hide_index=True)

st.markdown("---")
st.caption("Sursa: WIL_facturi_emise.xlsx & WISE_facturi_emise.xlsx  ·  Confidential")
