#[Project: Feelfree Travel Ledger / Version: v26.05.04.002]
#[Strategic Partner: Gem / Core: Force Rate Re-Induction Engine]
#[Status: Smart Line Parser (Newline priority) Applied - 65.1 KB]

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, timezone, date as dt_date
from streamlit_gsheets import GSheetsConnection
import time
import requests
import base64
import re

# --- SECTION 1: Configuration & Global Setup ---
st.set_page_config(page_title="Feelfree: 글로벌 여행 가계부", page_icon="🌏", layout="wide", initial_sidebar_state="expanded")

TZ_KST = timezone(timedelta(hours=9))

TRIP_CONFIGS = {
    "🇻🇳 푸꾸옥 (2026)": {
        "sheet": "PQ_2026", "currency": "VND", "symbol": "₫", 
        "timezone": 7, "multiplier": 100,
        "cats":["식사", "간식", "Grab", "VinBus", "마사지", "팁", "마트", "선물", "투어", "입장료", "통신", "수수료", "택시", "지하철", "항공권", "호텔", "보험"]
    },
    "🇨🇳 칭다오 (2025)": {
        "sheet": "QD_2025", "currency": "CNY", "symbol": "¥", 
        "timezone": 8, "multiplier": 1,
        "cats":["식사", "간식", "DiDi", "지하철", "마사지", "팁", "마트", "선물", "투어", "입장료", "통신", "수수료", "택시", "항공권", "호텔", "보험", "보증금"]
    }
}

MACRO_MAP = {
    "Grab": "🚗 교통", "VinBus": "🚗 교통", "DiDi": "🚗 교통", "지하철": "🚗 교통", "택시": "🚗 교통",
    "식사": "🍔 식음료", "간식": "🍔 식음료", "마트": "🍔 식음료",
    "마사지": "🏄 액티비티", "투어": "🏄 액티비티", "입장료": "🏄 액티비티",
    "선물": "🎁 쇼핑", "통신": "📱 통신/기타", "수수료": "📱 통신/기타", "팁": "📱 통신/기타",
    "항공권": "✈️ 항공권", "호텔": "🏨 숙박", "보험": "🛡️ 보험", "보증금": "🏦 자산이동"
}

CORE_COLUMNS =['Date', 'Country', 'Category', 'Description', 'Currency', 'Amount', 'PaymentMethod', 'Receipt_URL']
SYSTEM_LOGIC_COLUMNS =['IsExpense', 'AppliedRate', 'Cum_Budget_KRW', 'Cum_Card_Local', 'Cum_Cash_Local', 'Note']
FINAL_COLUMNS = CORE_COLUMNS + SYSTEM_LOGIC_COLUMNS

IMGBB_API_KEY = "81181bf834001b6191aaa90fa772c6f9"
BILLS =[500000, 200000, 100000, 50000, 20000, 10000, 5000, 2000, 1000]

VERSION = "v26.05.04.002"
UPDATE_LOG_TEXT = """* `[Fixed]` 스마트 줄바꿈 파서 탑재: 영수증 세부 내역을 분해할 때 기존의 단순 쉼표(,) 분할 방식이 문장을 훼손하는 문제를 해결하기 위해, 줄바꿈(엔터)을 최우선 기준으로 분할하여 엑셀 복사/붙여넣기 데이터의 무결성을 100% 보존함."""

conn = st.connection("gsheets", type=GSheetsConnection)

def auto_update_log_to_gsheets():
    try:
        log_df = conn.read(worksheet="version_log", ttl="0s")
        if log_df is None or log_df.empty: log_df = pd.DataFrame(columns=["Version", "Date", "Log"])
    except: log_df = pd.DataFrame(columns=["Version", "Date", "Log"])
    
    if VERSION not in log_df['Version'].values:
        new_log = pd.DataFrame([{"Version": VERSION, "Date": datetime.now(TZ_KST).strftime("%Y-%m-%d %H:%M:%S"), "Log": UPDATE_LOG_TEXT}])
        log_df = pd.concat([new_log, log_df], ignore_index=True)
        try: conn.update(worksheet="version_log", data=log_df)
        except: pass
auto_update_log_to_gsheets()

st.markdown("""
    <script>var link=document.createElement('link'); link.rel='apple-touch-icon'; link.href='https://img.icons8.com/color/512/globe--v1.png'; document.getElementsByTagName('head')[0].appendChild(link);</script>
    <style>
    .main { background-color: #0e1117; }
    .kpi-box { background-color: #1e2130; padding: 20px; border-radius: 15px; border-left: 8px solid #00FF00; margin-bottom: 20px; min-height: 130px; box-shadow: 4px 6px 15px rgba(0,0,0,0.5); }
    .kpi-title { font-size: 15px; color: #cccccc; margin-bottom: 10px; font-weight: 600; }
    .kpi-value-krw { font-size: 26px; font-weight: bold; color: #ffffff; line-height: 1.1; }
    .kpi-value-vnd { font-size: 18px; color: #00FF00; margin-top: 8px; font-family: 'Courier New', monospace; font-weight: 500; }
    div[data-testid="stTable"] { border: 1px solid #444; border-radius: 10px; overflow: hidden; }
    .stTabs[data-baseweb="tab-list"] { gap: 15px; padding-bottom: 10px; }
    .stTabs[data-baseweb="tab"] { background-color: #1c1f2b; border-radius: 8px 8px 0 0; padding: 12px 25px; color: #ffffff; }
    .stTabs[aria-selected="true"] { background-color: #00FF00 !important; color: #000000 !important; font-weight: bold; }

    /* [Added] 사이드바 여행지 선택기(Selectbox) 고대비 스타일링 */
    div[data-testid="stSidebar"] div[data-baseweb="select"] > div {
        border: 2px solid #00FF00 !important; /* Neon Green 테두리 */
        background-color: #1e2130 !important; /* 배경을 약간 밝게 */
        border-radius: 10px !important;
    }
    div[data-testid="stSidebar"] .stSelectbox label {
        color: #00FF00 !important; /* 라벨 텍스트 강조 */
        font-weight: bold !important;
        font-size: 1.1rem !important;
    }
    /* [Added] 드롭다운(풀다운) 리스트에서 선택된 항목 하이라이트 */
    div[data-baseweb="popover"] li[aria-selected="true"] {
        background-color: #FFA500 !important; /* 주황색 배경 */
        color: #000000 !important; /* 검정색 글자 */
        font-weight: bold !important;
    }

    /* [Added] 드롭다운 리스트 마우스 호버(Hover) 시 스타일 */
    div[data-baseweb="popover"] li:hover {
        background-color: #FFD700 !important; /* 호버 시 노란색 계열 */
        color: #000000 !important;
    }

    /* 사이드바 전용 선택기 라벨 색상 보정 */
    div[data-testid="stSidebar"] .stSelectbox label p {
        color: #FFD700 !important; /* 라벨을 노란색으로 더 강조 */
    }
    
    </style>
    """, unsafe_allow_html=True)

if 'current_trip' not in st.session_state: st.session_state.current_trip = list(TRIP_CONFIGS.keys())[0]

ACTIVE_SHEET = TRIP_CONFIGS[st.session_state.current_trip]["sheet"]
TRAVEL_CURRENCY = TRIP_CONFIGS[st.session_state.current_trip]["currency"]
LOCAL_SYM = TRIP_CONFIGS[st.session_state.current_trip]["symbol"]
TRIP_TZ = timezone(timedelta(hours=TRIP_CONFIGS[st.session_state.current_trip]["timezone"]))
MULTIPLIER = TRIP_CONFIGS[st.session_state.current_trip]["multiplier"]
EXPENSE_CATS = TRIP_CONFIGS[st.session_state.current_trip]["cats"]
SURVIVAL_CATS =["간식", "Grab", "DiDi", "VinBus", "지하철", "마사지", "팁", "식사"]
FIXED_COST_CATS =["항공권", "호텔", "보험"]
DOMESTIC_CATS =["항공권", "호텔", "보험", "지하철", "택시"]

if 'current_tz' not in st.session_state: st.session_state.current_tz = TZ_KST
if 'shared_date' not in st.session_state: st.session_state.shared_date = datetime.now(st.session_state.current_tz).date()
if 'last_cat_idx' not in st.session_state: st.session_state.last_cat_idx = 0

# --- SECTION 2:[Module A] Data Engine ---
def get_asset_class(text):
    txt = str(text).replace(" ", "")
    if "현금" in txt: return "CASH" 
    if any(k in txt for k in["트래블", "월렛", "카드VND", "카드CNY", "카드USD"]): return "PREPAID" 
    return "DOMESTIC" 

def get_default_rate(curr):
    if curr == "VND": return 0.0561
    if curr == "CNY": return 195.00
    if curr == "USD": return 1350.0
    return 1.0

def upload_image_to_imgbb(image_file):
    try:
        payload = {"key": IMGBB_API_KEY, "image": base64.b64encode(image_file.read()).decode("utf-8")}
        res = requests.post("https://api.imgbb.com/1/upload", data=payload)
        if res.status_code == 200: return res.json()['data']['url']
    except: pass
    return ""

def normalize_date(d_str):
    d_str = str(d_str).strip()
    match = re.match(r'^(?:20)?(\d{2})[\.\-\/]\s*(\d{1,2})[\.\-\/]\s*(\d{1,2})\.?$', d_str)
    if match:
        y, m, d = match.groups()
        dt_obj = datetime.strptime(f"20{y}-{int(m):02d}-{int(d):02d}", "%Y-%m-%d")
        return dt_obj.strftime("%m/%d(%a)")
    return d_str

def load_data():
    try:
        df = conn.read(worksheet=ACTIVE_SHEET, ttl="0s")
        if df is None or df.empty: return pd.DataFrame(columns=FINAL_COLUMNS)

        # [Modified] Country 컬럼 처리: 헤더가 없으면 삽입, 헤더만 있고 비어있으면 채우기
        default_country = "베트남" if "PQ" in ACTIVE_SHEET else "중국"
        
        if 'Country' not in df.columns:
            df.insert(1, 'Country', default_country)
        else:
            # 데이터가 문자열 'nan', 'None' 또는 실제 빈값인 경우 기본값으로 채움
            df['Country'] = df['Country'].astype(str).str.strip().replace(['nan', 'None', ''], None)
            df['Country'] = df['Country'].fillna(default_country)
        
        if 'Cum_Card_VND' in df.columns: df.rename(columns={'Cum_Card_VND': 'Cum_Card_Local'}, inplace=True)
        if 'Cum_Cash_VND' in df.columns: df.rename(columns={'Cum_Cash_VND': 'Cum_Cash_Local'}, inplace=True)
        if 'Receipt_URL' not in df.columns: df['Receipt_URL'] = ""
            
        df = df.dropna(subset=['Date', 'Category'], how='any')
        df['Category'] = df['Category'].astype(str).str.strip()
        df['PaymentMethod'] = df['PaymentMethod'].astype(str).str.strip()
        df['Currency'] = df['Currency'].astype(str).str.strip()
        df['Date'] = df['Date'].apply(normalize_date)
        
        df = df.reindex(columns=FINAL_COLUMNS)
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
        df['AppliedRate'] = pd.to_numeric(df['AppliedRate'], errors='coerce').fillna(0.0)
        df['IsExpense'] = pd.to_numeric(df['IsExpense'], errors='coerce').fillna(0).astype(int)
        df['Note'] = df['Note'].fillna("").astype(str)
        df['Receipt_URL'] = df['Receipt_URL'].fillna("").astype(str)
        return df
    except Exception: return pd.DataFrame(columns=FINAL_COLUMNS)

# [Added] 모든 여행지의 데이터를 통합 로드하는 함수 (Line 146에 삽입)
def load_all_trips_data():
    all_dfs = []
    with st.spinner("🌍 모든 여행 기록을 불러오는 중..."):
        for trip_name, config in TRIP_CONFIGS.items():
            try:
                # 각 시트 읽기 (ttl=0으로 실시간성 확보)
                df_t = conn.read(worksheet=config['sheet'], ttl="0s")
                if df_t is None or df_t.empty: continue
                
                # Country 컬럼 보정 로직 (기존 load_data와 동일)
                if 'Country' not in df_t.columns:
                    default_country = "베트남" if "PQ" in config['sheet'] else "중국"
                    df_t.insert(1, 'Country', default_country)
                else:
                    df_t['Country'] = df_t['Country'].astype(str).str.strip().replace(['nan', 'None', ''], None)
                    df_t['Country'] = df_t['Country'].fillna("베트남" if "PQ" in config['sheet'] else "중국")

                # 스키마 정렬
                df_t = df_t.reindex(columns=FINAL_COLUMNS)
                all_dfs.append(df_t)
            except: continue
            
    if not all_dfs: return pd.DataFrame(columns=FINAL_COLUMNS)
    return pd.concat(all_dfs, ignore_index=True)

def recalculate_entire_ledger(df):
    temp_df = df.copy()
    temp_df = temp_df.sort_values(by='Date', kind='mergesort', ignore_index=True)
    
    for i, row in temp_df.iterrows():
        cat = str(row['Category']).strip()
        asset_cls = get_asset_class(row['PaymentMethod'])
        if cat in EXPENSE_CATS and cat != '보증금' and asset_cls != "DOMESTIC":
            temp_df.at[i, 'AppliedRate'] = 0.0
            
        temp_df.at[i, 'Note'] = ""; temp_df.at[i, 'Cum_Budget_KRW'] = 0.0; temp_df.at[i, 'Cum_Card_Local'] = 0.0; temp_df.at[i, 'Cum_Cash_Local'] = 0.0
    
    inv_batches = { f"트래블로그({TRAVEL_CURRENCY})":[], f"현금({TRAVEL_CURRENCY})":[], "트래블로그(USD)":[], "현금(USD)":[] }
    c_budget = 0.0
    
    for i, row in temp_df.iterrows():
        qty, curr = row['Amount'], row['Currency']
        cat, method, desc = str(row['Category']).strip(), str(row['PaymentMethod']).strip(), str(row['Description']).strip()
        is_exp = 1 if cat in EXPENSE_CATS and cat not in['환불', '보증금'] else 0
        temp_df.at[i, 'IsExpense'] = is_exp
        
        is_deductible = 1 if (is_exp == 1 or cat == '보증금') else 0
        rate = temp_df.at[i, 'AppliedRate'] 
        
        asset_cls = get_asset_class(method)
        
        if cat in['충전', '환전', '입금', '직접환전']:
            if curr != 'KRW' and (pd.isna(rate) or rate <= 0.0 or rate == 1.0): rate = get_default_rate(curr)

            dest_cls = get_asset_class(desc + method)
            target = f"트래블로그({curr})" if dest_cls == "PREPAID" else f"현금({curr})"
            
            if curr != 'KRW' and target in inv_batches: inv_batches[target].append({'rate': rate, 'qty': qty})
            if asset_cls == "DOMESTIC": c_budget += qty if curr == 'KRW' else qty * rate
        
        elif cat == '환불':
            if curr != 'KRW' and (pd.isna(rate) or rate <= 0.0 or rate == 1.0): rate = get_default_rate(curr)
            if asset_cls == "DOMESTIC":
                c_budget -= qty if curr == 'KRW' else qty * rate 
            else:
                target = f"트래블로그({curr})" if asset_cls == "PREPAID" else f"현금({curr})"
                if curr != 'KRW' and target in inv_batches: inv_batches[target].append({'rate': rate, 'qty': qty})
        
        elif cat == 'ATM출금':
            temp_qty = qty; total_inherited_krw = 0.0
            target_from = f"트래블로그({curr})"; target_to = f"현금({curr})"
            if target_from in inv_batches:
                for batch in inv_batches[target_from]:
                    if temp_qty <= 0: break
                    if batch['qty'] <= 0: continue
                    take = min(temp_qty, batch['qty']); batch['qty'] -= take
                    inv_batches[target_to].append({'rate': batch['rate'], 'qty': take}); total_inherited_krw += take * batch['rate']; temp_qty -= take
            if qty > 0: rate = total_inherited_krw / qty if total_inherited_krw > 0 else get_default_rate(curr)
        
        elif is_deductible == 1:
            if asset_cls == "DOMESTIC":
                if curr != 'KRW' and (pd.isna(rate) or rate <= 0.0): rate = get_default_rate(curr)
                c_budget += qty if curr == 'KRW' else qty * rate
                rate = 1.0 if curr == 'KRW' else rate
            elif curr in[TRAVEL_CURRENCY, 'USD']:
                target = f"트래블로그({curr})" if asset_cls == "PREPAID" else f"현금({curr})"
                temp_qty = qty; total_cost_krw = 0.0; decomposed =[]
                if target in inv_batches:
                    for batch in inv_batches[target]:
                        if temp_qty <= 0: break
                        if batch['qty'] <= 0: continue
                        take = min(temp_qty, batch['qty']); batch['qty'] -= take; temp_qty -= take
                        total_cost_krw += take * batch['rate']
                        take_str = f"{take:,.2f}" if curr != "VND" else f"{take:,.0f}"
                        rate_str = f"{batch['rate']:.2f}" if curr != "VND" else f"{batch['rate']:.4f}"
                        decomposed.append(f"{take_str}@{rate_str}")
                if qty > 0:
                    rate = total_cost_krw / qty if total_cost_krw > 0 else 0.0
                    if decomposed: temp_df.at[i, 'Note'] = "Decomposed: " + " + ".join(decomposed)
                else: rate = 0.0

        rnd_dec = 0 if TRAVEL_CURRENCY == "VND" else 2
        temp_df.at[i, 'AppliedRate'] = rate
        temp_df.at[i, 'Cum_Budget_KRW'] = round(c_budget, 2)
        temp_df.at[i, 'Cum_Card_Local'] = round(sum([b['qty'] for b in inv_batches[f"트래블로그({TRAVEL_CURRENCY})"]]), rnd_dec)
        temp_df.at[i, 'Cum_Cash_Local'] = round(sum([b['qty'] for b in inv_batches[f"현금({TRAVEL_CURRENCY})"]]), rnd_dec)
        
    return temp_df

def save_data(df, metrics=None):
    if df is None or len(df) == 0: return False
    with st.status("클라우드 동기화 중...", expanded=False):
        try:
            final_df = recalculate_entire_ledger(df)
            conn.update(worksheet=ACTIVE_SHEET, data=final_df.reindex(columns=FINAL_COLUMNS))
            if metrics:
                current_time_str = datetime.now(st.session_state.current_tz).strftime("%H:%M")
                summary = pd.DataFrame({"항목":["🏦 예산(KRW)", f"💳 카드({TRAVEL_CURRENCY})", f"💵 현금({TRAVEL_CURRENCY})", "🕒 업데이트"], "수치":[f"{metrics[0]:,.0f}", f"{metrics[1]:,.0f}", f"{metrics[2]:,.0f}", current_time_str]})
                try: conn.update(worksheet="summary", data=summary)
                except: pass
            st.cache_data.clear(); return True
        except Exception as e:
            st.error(f"Cloud 저장 실패. 해당 탭({ACTIVE_SHEET})이 구글 시트에 존재하는지 확인하세요. 에러: {e}"); return False

ledger_df = load_data()

# --- SECTION 3:[Module B] URDI Engine ---
def get_inventory_status(df):
    temp_df = df.sort_values(by='Date', kind='mergesort', ignore_index=True) if not df.empty else df
    inv_batches = { f"트래블로그({TRAVEL_CURRENCY})":[], f"현금({TRAVEL_CURRENCY})":[], "트래블로그(USD)":[], "현금(USD)":[] }
    if temp_df.empty: return inv_batches
    for _, row in temp_df.iterrows():
        qty, rate, desc, cat, method, curr = row['Amount'], row['AppliedRate'], str(row['Description']), str(row['Category']).strip(), str(row['PaymentMethod']), row['Currency']
        asset_cls = get_asset_class(method)
        
        if cat in['충전', '환전', '입금', '직접환전']:
            dest_cls = get_asset_class(desc + method)
            target = f"트래블로그({curr})" if dest_cls == "PREPAID" else f"현금({curr})"
            if curr != 'KRW' and target in inv_batches: inv_batches[target].append({'rate': rate, 'qty': qty, 'initial': qty})
        elif cat == '환불':
            if asset_cls != "DOMESTIC":
                target = f"트래블로그({curr})" if asset_cls == "PREPAID" else f"현금({curr})"
                if curr != 'KRW' and target in inv_batches: inv_batches[target].append({'rate': rate, 'qty': qty, 'initial': qty})
        elif cat == 'ATM출금':
            temp_qty = qty; target_from = f"트래블로그({curr})"; target_to = f"현금({curr})"
            if target_from in inv_batches:
                for batch in inv_batches[target_from]:
                    if temp_qty <= 0: break
                    if batch['qty'] <= 0: continue
                    take = min(temp_qty, batch['qty']); batch['qty'] -= take
                    inv_batches[target_to].append({'rate': batch['rate'], 'qty': take, 'initial': take}); temp_qty -= take
        elif (row['IsExpense'] == 1 or cat == '보증금') and curr in[TRAVEL_CURRENCY, 'USD']:
            if asset_cls != "DOMESTIC":
                target = f"트래블로그({curr})" if asset_cls == "PREPAID" else f"현금({curr})"
                temp_qty = qty
                if target in inv_batches:
                    for batch in inv_batches[target]:
                        if temp_qty <= 0: break
                        if batch['qty'] <= 0: continue
                        take = min(temp_qty, batch['qty']); batch['qty'] -= take; temp_qty -= take
    return inv_batches

current_inventory_batches = get_inventory_status(ledger_df)

sw_df_loc = ledger_df[(ledger_df['Category'].str.strip().isin(['충전','환전','입금','직접환전'])) & (ledger_df['Currency'].str.strip() == TRAVEL_CURRENCY)]
WAR_LOCAL = (sw_df_loc['Amount'] * sw_df_loc['AppliedRate']).sum() / sw_df_loc['Amount'].sum() if not sw_df_loc.empty and sw_df_loc['Amount'].sum() > 0 else get_default_rate(TRAVEL_CURRENCY)

sw_df_usd = ledger_df[(ledger_df['Category'].str.strip().isin(['충전','환전','입금','직접환전'])) & (ledger_df['Currency'].str.strip() == 'USD')]
WAR_USD = (sw_df_usd['Amount'] * sw_df_usd['AppliedRate']).sum() / sw_df_usd['Amount'].sum() if not sw_df_usd.empty and sw_df_usd['Amount'].sum() > 0 else 1350.0

def auto_calc_fifo_rate(amount, method, curr=TRAVEL_CURRENCY):
    asset_cls = get_asset_class(method)
    if asset_cls == "DOMESTIC": return WAR_LOCAL 
    
    target = f"트래블로그({curr})" if asset_cls == "PREPAID" else f"현금({curr})"
    temp_inv = get_inventory_status(ledger_df)
    if target not in temp_inv: return WAR_USD if curr == 'USD' else WAR_LOCAL
    available_batches =[b for b in temp_inv[target] if b['qty'] > 0]
    if not available_batches: return WAR_USD if curr == 'USD' else WAR_LOCAL
    total_cost_krw, remaining = 0.0, amount
    for batch in available_batches:
        if remaining <= 0: break
        take = min(remaining, batch['qty']); total_cost_krw += take * batch['rate']; remaining -= take
    if remaining > 0: total_cost_krw += remaining * available_batches[-1]['rate']
    return total_cost_krw / amount if amount > 0 else 0

def calculate_summary_metrics(df):
    if df.empty: return 0.0, 0.0, 0.0, 0.0
    temp_df = df.sort_values(by='Date', kind='mergesort', ignore_index=True)
    b_total = temp_df['Cum_Budget_KRW'].iloc[-1] if 'Cum_Budget_KRW' in temp_df.columns else 0
    spent_total = (temp_df[temp_df['IsExpense'] == 1].apply(lambda r: r['Amount'] if str(r['Currency']).strip() == 'KRW' else r['Amount'] * r['AppliedRate'], axis=1)).sum()
    card_v = sum([b['qty'] for b in current_inventory_batches[f"트래블로그({TRAVEL_CURRENCY})"]])
    cash_v = sum([b['qty'] for b in current_inventory_batches[f"현금({TRAVEL_CURRENCY})"]])
    return b_total, card_v, cash_v, spent_total

# --- SECTION 5:[Sidebar] ---
with st.sidebar:
    sel_trip = st.selectbox("✈️ 내 여행함 (Trip Selector)", list(TRIP_CONFIGS.keys()), index=list(TRIP_CONFIGS.keys()).index(st.session_state.current_trip))
    if sel_trip != st.session_state.current_trip:
        st.session_state.current_trip = sel_trip; st.rerun()

    st.divider()
    st.title("💰 Wallet Status")
    b_val, card_val, cash_val, spent_val = calculate_summary_metrics(ledger_df)
    
    fmt_str = "{:,.2f}" if TRAVEL_CURRENCY != 'VND' else "{:,.0f}"
    rate_fmt = ".2f" if TRAVEL_CURRENCY != 'VND' else ".4f"
    
    st.metric(f"💵 현금 {TRAVEL_CURRENCY} 잔액", f"{LOCAL_SYM} {fmt_str.format(cash_val)}")
    if current_inventory_batches.get(f"현금({TRAVEL_CURRENCY})"):
        with st.expander("↳ 현금 환율 배치", expanded=False):
            for b in current_inventory_batches[f"현금({TRAVEL_CURRENCY})"]:
                status = fmt_str.format(b['qty']) if b['qty'] > 0 else "소진"
                st.caption(f"• {status}{LOCAL_SYM} @ {b['rate']:{rate_fmt}}원")
                
    st.metric(f"💳 카드 {TRAVEL_CURRENCY} 잔액", f"{LOCAL_SYM} {fmt_str.format(card_val)}")
    if current_inventory_batches.get(f"트래블로그({TRAVEL_CURRENCY})"):
        with st.expander("↳ 카드 환율 배치", expanded=False):
            for b in current_inventory_batches[f"트래블로그({TRAVEL_CURRENCY})"]:
                status = fmt_str.format(b['qty']) if b['qty'] > 0 else "소진"
                st.caption(f"• {status}{LOCAL_SYM} @ {b['rate']:{rate_fmt}}원")
    
    usd_card = sum([b['qty'] for b in current_inventory_batches.get("트래블로그(USD)",[])])
    usd_cash = sum([b['qty'] for b in current_inventory_batches.get("현금(USD)",[])])
    if usd_cash > 0 or usd_card > 0:
        st.divider()
        st.metric("💵 현금 USD 잔액", f"${usd_cash:,.2f}")
        if current_inventory_batches.get("현금(USD)"):
            with st.expander("↳ USD 현금 배치", expanded=False):
                for b in current_inventory_batches["현금(USD)"]:
                    status = f"{b['qty']:,.2f}" if b['qty'] > 0 else "소진"
                    st.caption(f"• ${status} @ {b['rate']:.2f}원")
                    
        st.metric("💳 카드 USD 잔액", f"${usd_card:,.2f}")
        if current_inventory_batches.get("트래블로그(USD)"):
            with st.expander("↳ USD 카드 배치", expanded=False):
                for b in current_inventory_batches["트래블로그(USD)"]:
                    status = f"{b['qty']:,.2f}" if b['qty'] > 0 else "소진"
                    st.caption(f"• ${status} @ {b['rate']:.2f}원")

    st.divider()
    st.metric("🏦 총 예산 (KRW)", f"{b_val:,.0f} 원")
    st.metric("💸 지출총액 (KRW)", f"{spent_val:,.0f} 원")
    st.caption(f"가중평균({TRAVEL_CURRENCY}): {MULTIPLIER}{LOCAL_SYM} = {WAR_LOCAL*MULTIPLIER:.2f}원")

    st.divider()
    tz_sel = st.radio("📍 기준 시간 (Timezone)",["🇰🇷 한국 시간", "🌍 여행지 현지 시간"], horizontal=True, index=0 if "한국" in str(st.session_state.current_tz) else 1)
    st.session_state.current_tz = TZ_KST if "한국" in tz_sel else TRIP_TZ
    if st.button("🔄 Cloud Refresh", use_container_width=True): st.cache_data.clear(); st.rerun()

# --- SECTION 4:[Module C] Intelligent Input (📝 입력) ---
st.title(f"{st.session_state.current_trip}")
tab_in, tab_his, tab_stats, tab_final = st.tabs(["📝 입력", "🔍 조회", "📊 일일", "🏁 리포트"])

with tab_in:
    mode = st.radio("기록 모드 선택",["일반 지출", "자산 이동", "환불(취소)", "출입국"], horizontal=True, key="mode_radio")
    sel_date = st.date_input("날짜 선택", value=datetime.now(st.session_state.current_tz).date(), key="shared_date_input")
    
    if mode == "일반 지출":
        cat = st.radio("항목 선택", EXPENSE_CATS, index=min(st.session_state.last_cat_idx, len(EXPENSE_CATS)-1), horizontal=True, key="exp_cat")
        st.session_state.last_cat_idx = EXPENSE_CATS.index(cat)
        
        col_desc, col_receipt = st.columns([3, 1])
        with col_desc: desc = st.text_input("내용 (상호명 및 상세메모)", placeholder="예: 안바카페 - 소고기버거, 반미정식", key="exp_desc")
        with col_receipt: uploaded_file = st.file_uploader("📸 영수증 첨부", type=['png', 'jpg', 'jpeg'], key="exp_receipt")
            
        col_m1, col_m2, col_m3 = st.columns([1, 1, 1])
        with col_m1: curr = st.selectbox("통화",[TRAVEL_CURRENCY, "KRW", "USD"], key="exp_curr")
        with col_m2:
            met_options =[f"현금({curr})", f"트래블로그({curr})", "원화계좌(한국)", "원화계좌(현지)"] if curr != "KRW" else["원화계좌(한국)", "원화계좌(현지)"]
            met = st.selectbox("결제 자산(Asset)", met_options, index=0, key="exp_met")
        with col_m3:
            harvested_tags = set()
            if not ledger_df.empty:
                extracted = ledger_df['Description'].str.extractall(r'\[(.*?)\]')
                if not extracted.empty: harvested_tags = set(extracted[0].dropna().unique())
            
            default_gateways =["알리페이", "위챗페이", "네이버페이", "카카오페이", "Apple Pay", "토스페이", "Trip.com", "Agoda", "Booking.com"]
            combined_gateways =["선택안함 (기본)"] + sorted(list(set(default_gateways) | harvested_tags)) + ["➕ 직접 입력하기"]
            gateway_sel = st.selectbox("결제 플랫폼 (Gateway)", combined_gateways, key="exp_gw")
            
            final_gateway = ""
            if gateway_sel == "➕ 직접 입력하기": final_gateway = st.text_input("새로운 플랫폼 이름 입력", placeholder="예: 마이리얼트립")
            elif gateway_sel != "선택안함 (기본)": final_gateway = gateway_sel

        col_a1, col_a2 = st.columns(2)
        with col_a1:
            if curr == "KRW" or (curr == TRAVEL_CURRENCY and MULTIPLIER == 100):
                amt = st.number_input(f"금액 ({curr})", min_value=0, step=1000 if curr != "KRW" else 1, format="%d", key="exp_amt_int")
            else:
                amt = st.number_input(f"금액 ({curr})", min_value=0.0, step=1.0, format="%.2f", key="exp_amt_float")
        with col_a2:
            if curr in[TRAVEL_CURRENCY, 'USD'] and amt > 0:
                calc_rate = auto_calc_fifo_rate(amt, met, curr)
                st.caption(f"💡 {curr} 인벤토리 계산 환율: **{calc_rate:.5f}**")
                cr_final = st.number_input("확정 환율", value=float(calc_rate), format="%.5f", key=f"exp_cr_auto_{met}_{amt}")
            else: cr_final = st.number_input("확정 환율", value=(1.0 if curr=="KRW" else get_default_rate(curr)), format="%.5f", key=f"exp_cr_man_{curr}")
            
        if st.button("🚀 지출 기록하기", use_container_width=True):
            receipt_url = ""
            if uploaded_file is not None:
                with st.spinner("📸 영수증 클라우드 링킹 중..."):
                    receipt_url = upload_image_to_imgbb(uploaded_file)
                    if receipt_url: st.toast("✅ 영수증 링킹 완료!")
            
            final_desc = f"[{final_gateway}] {desc}" if final_gateway else desc
            curr_country = "베트남" if "푸꾸옥" in st.session_state.current_trip else "중국"
            new_row = pd.DataFrame([{
                'Date': sel_date.strftime("%m/%d(%a)"),
                'Country': curr_country, # [Added] 14컬럼 데이터
                'Category': cat,
                'Description': final_desc,
                'Currency': curr,
                'Amount': amt,
                'PaymentMethod': met,
                'IsExpense': 1,
                'AppliedRate': cr_final,
                'Note': '',
                'Receipt_URL': receipt_url
            }])
            
            if save_data(pd.concat([ledger_df, new_row], ignore_index=True)): st.rerun()

    elif mode == "자산 이동":
        st.subheader("🔁 자산 이동 및 환전")
        ty = st.selectbox("유형",["직접환전 (원화계좌 -> 지폐)", "충전 (원화계좌 -> 카드)", "ATM출금 (카드 -> 지폐)"], key="tr_type")
        c1, c2 = st.columns(2)
        with c1:
            curr_tr = st.selectbox("대상 통화",[TRAVEL_CURRENCY, "USD"], key="tr_curr")
            if curr_tr == TRAVEL_CURRENCY and MULTIPLIER == 100:
                t_amt = st.number_input(f"받은 금액 ({curr_tr})", min_value=0, step=1000, format="%d", key="tr_target_int")
            else:
                t_amt = st.number_input(f"받은 금액 ({curr_tr})", min_value=0.0, step=10.0, format="%.2f", key="tr_target_flt")
                
            if "ATM" in ty:
                inherited_r = auto_calc_fifo_rate(t_amt, f"트래블로그({curr_tr})", curr_tr)
                st.info(f"💳 카드 재고 계승 환율: **{inherited_r:.5f}**")
                s_cost = st.number_input("인출 원금 확인", value=float(t_amt), key="tr_source_atm")
                applied_tr_rate = inherited_r
            else:
                s_cost = st.number_input("소요 원금 (KRW)", min_value=0, step=1, format="%d", key="tr_source_swap")
                applied_tr_rate = s_cost / t_amt if t_amt > 0 else 0
        with c2:
            if curr_tr == TRAVEL_CURRENCY and MULTIPLIER == 100:
                fee_amt = st.number_input(f"ATM 수수료 ({curr_tr})", min_value=0, step=1000, format="%d", key="tr_fee_int")
            else:
                fee_amt = st.number_input(f"ATM 수수료 ({curr_tr})", min_value=0.0, step=1.0, format="%.2f", key="tr_fee_flt")
                
        if st.button("🔄 이동 실행", use_container_width=True):
            dest = f"트래블로그({curr_tr})" if "카드" in ty else f"현금({curr_tr})"
            source = "원화계좌(한국)" if "원화계좌" in ty else f"트래블로그({curr_tr})"
            main_row = pd.DataFrame([{'Date': sel_date.strftime("%m/%d(%a)"), 'Category': ty.split(" ")[0], 'Description': f"{ty.split(' ')[0]} (-> {dest})", 'Currency': curr_tr, 'Amount': t_amt, 'PaymentMethod': source, 'IsExpense': 0, 'AppliedRate': applied_tr_rate, 'Note': '', 'Receipt_URL': ''}])
            final_entry = pd.concat([ledger_df, main_row], ignore_index=True)
            if fee_amt > 0:
                fee_rate = auto_calc_fifo_rate(fee_amt, f"트래블로그({curr_tr})", curr_tr)
                fee_row = pd.DataFrame([{'Date': sel_date.strftime("%m/%d(%a)"), 'Category': "수수료", 'Description': f"{ty.split(' ')[0]} 수수료", 'Currency': curr_tr, 'Amount': fee_amt, 'PaymentMethod': f"트래블로그({curr_tr})", 'IsExpense': 1, 'AppliedRate': fee_rate, 'Note': '', 'Receipt_URL': ''}])
                final_entry = pd.concat([final_entry, fee_row], ignore_index=True)
            if save_data(final_entry): st.rerun()

    elif mode == "환불(취소)":
        st.subheader("🔙 결제 취소 및 환불 (Rollback)")
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            r_curr = st.selectbox("취소된 통화",[TRAVEL_CURRENCY, "KRW", "USD"], key="rf_curr")
            r_met = st.selectbox("돌려받을 지갑",[f"현금({r_curr})", f"트래블로그({r_curr})", "원화계좌(한국)", "원화계좌(현지)"] if r_curr != "KRW" else["원화계좌(한국)", "원화계좌(현지)"], key="rf_met")
            if r_curr == "KRW" or (r_curr == TRAVEL_CURRENCY and MULTIPLIER == 100):
                r_amt = st.number_input("환불 금액", min_value=0, step=1000 if r_curr != "KRW" else 1, format="%d", key="rf_amt_int")
            else:
                r_amt = st.number_input("환불 금액", min_value=0.0, step=1.0, format="%.2f", key="rf_amt_flt")
        with col_r2:
            r_rate = st.number_input("과거 결제 시 적용됐던 환율", value=(1.0 if r_curr=="KRW" else get_default_rate(r_curr)), format="%.5f", key="rf_rate")
            r_desc = st.text_input("취소 내역 메모", placeholder="예: 호텔 보증금 반환", key="rf_desc")
        if st.button("🔙 환불 인벤토리 롤백 실행", use_container_width=True):
            new_row = pd.DataFrame([{'Date': sel_date.strftime("%m/%d(%a)"), 'Category': '환불', 'Description': f"취소: {r_desc}", 'Currency': r_curr, 'Amount': r_amt, 'PaymentMethod': r_met, 'IsExpense': 0, 'AppliedRate': r_rate, 'Note': 'Rollback', 'Receipt_URL': ''}])
            if save_data(pd.concat([ledger_df, new_row], ignore_index=True)): st.rerun()

    else:
        st.subheader("✈️ 출입국 일정 기록")
        io_type = st.radio("구분",["출국", "입국"], horizontal=True, key="io_radio")
        desc = st.text_input("내용 (메모)", placeholder="편명, 시간 등", key="io_desc")
        if st.button("🚀 일정 기록 완료", use_container_width=True):
            new_row = pd.DataFrame([{'Date': sel_date.strftime("%m/%d(%a)"), 'Category': io_type, 'Description': desc, 'Currency': 'KRW', 'Amount': 0, 'PaymentMethod': '원화계좌(한국)', 'IsExpense': 1, 'AppliedRate': 1.0, 'Note': '', 'Receipt_URL': ''}])
            if save_data(pd.concat([ledger_df, new_row], ignore_index=True)): st.rerun()

# --- SECTION 6:[Module D, E: History & Settlement] ---
with tab_his:
    st.info("💡 **표의 행(Row)을 클릭(터치)하시면 바로 아래에 상세 내역 수정과 영수증 첨부 화면이 펼쳐집니다!**")
    
    viewer_placeholder = st.empty()
    
    # [Modified] 검색바 레이아웃 변경 (토글 추가 / Line 438)
    c_search, c_global, c_tog = st.columns([2, 1, 1])
    with c_search: 
        search_query = st.text_input("🔎 검색어 입력", placeholder="상호명, 메모, 카테고리 등", key="his_search", label_visibility="collapsed")
    with c_global:
        global_search = st.toggle("🌍 전체 검색", value=False, key="global_search_toggle")
    with c_tog: 
        edit_mode = st.toggle("✏️ 직접 수정 모드", value=False, key="his_edit_toggle")

    # [Modified] 데이터 소스 결정 (Line 446)
    if global_search and search_query.strip():
        # 전체 여행 검색 시에는 수정을 막기 위해 안내 메시지 출력
        st.warning("⚠️ '전체 검색' 모드에서는 내역 조회만 가능하며, 수정은 불가능합니다.")
        edit_mode = False # 강제로 수정 모드 해제
        display_df = load_all_trips_data()
    else:
        display_df = ledger_df.copy()
        
    if st.button("🔄 장부 전체 다시 계산 (Recalculate All)", use_container_width=True, type="primary"):
        if save_data(ledger_df):
            st.success("데이터 정합성 복구 완료!"); time.sleep(1); st.rerun()
            
# --- [Modified/Added] 교체 구간 시작 ---
    if not display_df.empty: # [Modified] ledger_df 대신 상단에서 정의한 display_df 사용
        display_df = display_df.sort_values(by='Date', kind='mergesort').reset_index(drop=True)
        display_df = display_df.reindex(columns=FINAL_COLUMNS)
        link_cfg = st.column_config.LinkColumn("영수증 📸", display_text="🔗 보기", disabled=True)
        
        if search_query.strip():
            # [Modified] Country 필드까지 검색 범위 확장
            mask = (
                display_df['Category'].str.contains(search_query, case=False, na=False) | 
                display_df['Description'].str.contains(search_query, case=False, na=False) | 
                display_df['Note'].str.contains(search_query, case=False, na=False) |
                display_df['Country'].str.contains(search_query, case=False, na=False) # [Added]
            )
            filtered_df = display_df[mask]
            st.write(f"🔎 검색 결과: {len(filtered_df)}건") # [Added] 건수 표시
            st.dataframe(filtered_df, use_container_width=True, column_config={"Receipt_URL": link_cfg})
            
        elif edit_mode:
            edited_df = st.data_editor(display_df, use_container_width=True, num_rows="dynamic", key="editor_gtl_final", column_config={"Receipt_URL": link_cfg})
            if not display_df.equals(edited_df) and st.button("💾 데이터베이스 수정사항 저장", use_container_width=True):
                if save_data(edited_df): st.rerun()
                
        else:
            df_event = st.dataframe(display_df, use_container_width=True, column_config={"Receipt_URL": link_cfg}, selection_mode="single-row", on_select="rerun")
            
            if df_event.selection.rows:
                selected_idx = df_event.selection.rows[0]
                row_data = display_df.iloc[selected_idx]
                
                with viewer_placeholder.container():
                    st.markdown("---")
                    c_info, c_edit = st.columns([1, 1])
                    
                    with c_info:
                        st.subheader("🧾 상세 내역 및 영수증 뷰어")
                        amt_fmt2 = "{:,.2f}" if MULTIPLIER == 1 and row_data['Currency'] != 'KRW' else "{:,.0f}"
                        st.markdown(f"### 🛒 {row_data['Category']} ({amt_fmt2.format(row_data['Amount'])} {row_data['Currency']})")
                        st.markdown(f"**🏦 결제수단:** {row_data['PaymentMethod']}")
                        
                        desc_full = str(row_data['Description'])
                        if "-" in desc_full:
                            parts = desc_full.split("-", 1)
                            st.markdown(f"**🏪 상호명:** {parts[0].strip()}")
                            detail_str = parts[1].strip()
                            st.markdown("**📝 세부 구매 내역:**")
                            # [Modified] 줄바꿈(\n)이 있으면 최우선으로 분할, 없으면 쉼표(,)로 분할 (스마트 파서)
                            items = detail_str.split("\n") if "\n" in detail_str else detail_str.split(",")
                            for item in items: 
                                if item.strip(): st.markdown(f"- {item.strip()}")
                        else:
                            if "\n" in desc_full:
                                st.markdown("**📝 세부 내역:**")
                                for item in desc_full.split("\n"):
                                    if item.strip(): st.markdown(f"- {item.strip()}")
                            else:
                                st.markdown(f"**📝 내역:** {desc_full}")
                            
                        if str(row_data['Receipt_URL']).startswith("http"):
                            st.image(row_data['Receipt_URL'], use_container_width=True)
                        else:
                            st.info("첨부된 영수증 사진이 없습니다.")
                            
                    with c_edit:
                        st.subheader("✏️ 내역 보강 및 영수증 첨부")
                        st.caption("세부 내역을 엑셀에서 복사해 붙여넣거나 엔터(줄바꿈)로 여러 개 입력하시면, 왼쪽 뷰어에서 깔끔하게 분리되어 표시됩니다.")
                        new_desc = st.text_area("📝 세부 내역 (수정/추가)", value=row_data['Description'], height=150)
                        new_receipt = st.file_uploader("📸 새 영수증 사진 업로드", type=['png', 'jpg', 'jpeg'], key="inline_receipt")
                        
                        if st.button("💾 이 내역 업데이트", use_container_width=True):
                            display_df.at[selected_idx, 'Description'] = new_desc
                            if new_receipt:
                                with st.spinner("클라우드 전송 중..."):
                                    url = upload_image_to_imgbb(new_receipt)
                                    if url: display_df.at[selected_idx, 'Receipt_URL'] = url
                            if save_data(display_df): st.success("업데이트 완료!"); time.sleep(1); st.rerun()
                    st.markdown("---")

with tab_stats:
    if not ledger_df.empty:
        exp_df = ledger_df.sort_values(by='Date', kind='mergesort', ignore_index=True)
        exp_df = exp_df[exp_df['IsExpense'] == 1].copy()
        
        if not exp_df.empty:
            exp_df['Macro_Category'] = exp_df['Category'].map(MACRO_MAP).fillna("기타")
            
            def get_krw_val(r):
                if str(r['Currency']).strip() == 'KRW': return r['Amount']
                elif str(r['Currency']).strip() in[TRAVEL_CURRENCY, 'USD']: return r['Amount'] * r['AppliedRate']
                return 0
                
            exp_df['KRW_val'] = exp_df.apply(get_krw_val, axis=1)
            exp_df['Local_val'] = exp_df.apply(lambda r: r['Amount'] if str(r['Currency']).strip() == TRAVEL_CURRENCY else (r['Amount'] * r['AppliedRate'] / WAR_LOCAL if WAR_LOCAL>0 else 0), axis=1)
            exp_df['IsSurvival'] = exp_df['Category'].apply(lambda x: 1 if x in SURVIVAL_CATS else 0)
            
            st.subheader("🏁 여행 경제 요약")
            c1, c2 = st.columns(2)
            with c1:
                dom_df = exp_df[(exp_df['PaymentMethod'].str.strip() == '원화계좌(한국)') & (~exp_df['Category'].isin(['입국','출국']))]
                st.info("🇰🇷 사전 결제 및 고정 지출"); st.metric("총액", f"{dom_df['KRW_val'].sum():,.0f} 원")
                dg = dom_df.groupby('Category').agg({'KRW_val':'sum', 'Date':'count'}).sort_values(by='KRW_val', ascending=False)
                for cat_name, row_data in dg.iterrows(): st.write(f"- {cat_name}({int(row_data['Date'])}회): {row_data['KRW_val']:,.0f} 원")
            with c2:
                ovr_df = exp_df[(exp_df['PaymentMethod'].str.strip() != '원화계좌(한국)') & (~exp_df['Category'].isin(['입국','출국']))]
                st.success(f"🌏 현지 체류 지출 (USD 포함)"); st.metric("총액 (원화환산)", f"{ovr_df['KRW_val'].sum():,.0f} 원")
                og = ovr_df.groupby('Category').agg({'KRW_val':'sum', 'Date':'count'}).sort_values(by='KRW_val', ascending=False)
                for cat_name, row_data in og.iterrows(): st.write(f"- {cat_name}({int(row_data['Date'])}회): {row_data['KRW_val']:,.0f} 원")
            
            st.divider(); daily_set = exp_df.groupby('Date').agg({'KRW_val': 'sum', 'Local_val': 'sum'}).reset_index()
            surv_only = exp_df[exp_df['IsSurvival'] == 1].groupby('Date').agg({'KRW_val': 'sum', 'Local_val': 'sum'}).reset_index().rename(columns={'KRW_val': 'S_KRW', 'Local_val': 'S_Loc'})
            daily_table = pd.merge(daily_set, surv_only, on='Date', how='left').fillna(0)
            fmt_local = "{:,.2f}" if MULTIPLIER == 1 else "{:,.0f}"
            st.table(daily_table.rename(columns={'Date':'날짜','KRW_val':'총(원)','Local_val':f'총({LOCAL_SYM})','S_KRW':'일상(원)','S_Loc':f'일상({LOCAL_SYM})'}).style.format({'총(원)': '{:,.0f}', f'총({LOCAL_SYM})': fmt_local, '일상(원)': '{:,.0f}', f'일상({LOCAL_SYM})': fmt_local}))
            
            c_mode = st.radio("표시 통화 선택",["원화(KRW)", f"현지화({TRAVEL_CURRENCY})"], horizontal=True, key="st_curr")
            y_col = 'KRW_val' if "원화" in c_mode else 'Local_val'
            
            color_map = {
                "식사": "#2E7D32", "간식": "#4CAF50", "마트": "#E91E63", 
                "Grab": "#00897B", "VinBus": "#00ACC1", "DiDi": "#00897B", "지하철": "#00ACC1", "택시": "#009688",
                "마사지": "#0288D1", "투어": "#673AB7", "입장료": "#3F51B5", 
                "선물": "#9C27B0", "통신": "#FF9800", "수수료": "#795548", "팁": "#03A9F4",
                "항공권": "#D32F2F", "호텔": "#1976D2", "보험": "#FBC02D"
            }
            macro_color_map = {
                "🍔 식음료": "#4CAF50", "🚗 교통": "#00ACC1", "🏄 액티비티": "#0288D1", 
                "🎁 쇼핑": "#9C27B0", "📱 통신/기타": "#FF9800", "✈️ 항공권": "#D32F2F", "🏨 숙박": "#1976D2", "🛡️ 보험": "#FBC02D", "기타": "#9E9E9E"
            }
            
            if not dom_df.empty:
                dom_df['Date_Clean'] = dom_df['Date'].str.split('(').str[0]
                # [Modified] title을 None으로 설정하여 내부 제목 제거
                fig1 = px.bar(dom_df, x='Date_Clean', y=y_col, color='Macro_Category', title=None, color_discrete_map=macro_color_map)
                
                fig1.update_layout(
                    barmode='stack', 
                    margin=dict(l=10, r=10, t=30, b=120), # 상단(t) 여백을 30으로 축소
                    legend=dict(orientation="h", yanchor="top", y=-0.3, xanchor="center", x=0.5)
                )
                # [Added] 차트 외부 상단에 제목 배치 (절대 안 겹침)
                st.markdown("<h4 style='text-align: center;'>🛫 사전 결제 (대분류 그룹화)</h4>", unsafe_allow_html=True)
                st.plotly_chart(fig1, use_container_width=True, config={'displaylogo': False})
            
            if not ovr_df.empty:
                ovr_df['Date_Clean'] = ovr_df['Date'].str.split('(').str[0]
                # [Modified] title을 None으로 설정하여 내부 제목 제거
                fig2 = px.bar(ovr_df, x='Date_Clean', y=y_col, color='Category', title=None, color_discrete_map=color_map)
                
                fig2.update_layout(
                    barmode='stack', 
                    margin=dict(l=10, r=10, t=30, b=120), # 상단(t) 여백을 30으로 축소
                    legend=dict(orientation="h", yanchor="top", y=-0.3, xanchor="center", x=0.5)
                )
                # [Added] 차트 외부 상단에 제목 배치 (절대 안 겹침)
                st.markdown(f"<h4 style='text-align: center;'>🚶‍♂️ 현지 체류 일일 흐름 ({len(ovr_df['Date'].unique())}일차)</h4>", unsafe_allow_html=True)
                st.plotly_chart(fig2, use_container_width=True, config={'displaylogo': False})
with tab_final:
    if not ledger_df.empty and 'exp_df' in locals() and not exp_df.empty:
        total_trip_krw = exp_df['KRW_val'].sum(); total_trip_loc = exp_df['Local_val'].sum()
        dom_total_krw = exp_df[exp_df['PaymentMethod'].str.strip() == '원화계좌(한국)']['KRW_val'].sum()
        ovr_total_krw = total_trip_krw - dom_total_krw; ovr_total_loc = exp_df[exp_df['PaymentMethod'].str.strip() != '원화계좌(한국)']['Local_val'].sum()
        local_v = exp_df[(exp_df['IsSurvival'] == 1) & (exp_df['Currency'].str.strip() == TRAVEL_CURRENCY)].copy()
        avg_local_krw = local_v['KRW_val'].sum() / 7 if not local_v.empty else 0
        avg_local_loc = local_v['Local_val'].sum() / 7 if not local_v.empty else 0
        def kpi_box(title, krw, loc=None):
            loc_str = f"<div class='kpi-value-vnd'>({fmt_local.format(loc)} {LOCAL_SYM})</div>" if loc is not None else ""
            return f"<div class='kpi-box'><div class='kpi-title'>{title}</div><div class='kpi-value-krw'>{krw:,.0f} 원</div>{loc_str}</div>"
        st.header("🏁 여행요약")
        k1, k2, k3, k4 = st.columns(4)
        with k1: st.markdown(kpi_box("여행 최종 총 지출", total_trip_krw, total_trip_loc), unsafe_allow_html=True)
        with k2: st.markdown(kpi_box("국내 지출 총액", dom_total_krw), unsafe_allow_html=True)
        with k3: st.markdown(kpi_box("현지 지출 총액", ovr_total_krw, ovr_total_loc), unsafe_allow_html=True)
        with k4: st.markdown(kpi_box(f"현지 일상/생존 1일 평균", avg_local_krw, avg_local_loc), unsafe_allow_html=True)
        
        st.subheader("🌳 지출분석 (Treemap)")
        fig_tree = px.treemap(exp_df, path=['Macro_Category', 'Category', 'Description'], values='KRW_val', color='KRW_val', color_continuous_scale='Greens')
        fig_tree.update_traces(texttemplate="<b>%{label}</b><br>%{value:,.0f}원<br>%{percentRoot:.1%}")
        fig_tree.update_layout(margin=dict(l=0, r=0, t=10, b=0), font=dict(size=14))
        st.plotly_chart(fig_tree, use_container_width=True)
        
        st.subheader("🍕 지출비중")
        cat_pie = exp_df.groupby('Macro_Category')['KRW_val'].sum().reset_index().sort_values(by='KRW_val', ascending=False)
        fig_donut = px.pie(cat_pie, values='KRW_val', names='Macro_Category', hole=0.5, color_discrete_sequence=px.colors.qualitative.Set3)
        fig_donut.update_traces(textposition='inside', textinfo='label+value+percent', texttemplate='%{label}<br>%{value:,.0f}원<br>%{percent:.1%}')
        until_day = exp_df['Date'].max().split('(')[0]
        fig_donut.add_annotation(text=f"<b>총 지출</b><br>{total_trip_krw:,.0f} 원<br><span style='font-size:10px'>Until {until_day}</span>", showarrow=False, font=dict(size=16))
        fig_donut.update_layout(height=600, margin=dict(l=10, r=10, t=50, b=100), legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5), uniformtext_minsize=11, uniformtext_mode='hide')
        st.plotly_chart(fig_donut, use_container_width=True)

st.caption(f"GTL Platform v26.05.04.002 | Volume Guard: 65.1 KB | Sync: {datetime.now(st.session_state.current_tz).strftime('%Y-%m-%d %H:%M:%S')} | Strategic Partner Gem")
