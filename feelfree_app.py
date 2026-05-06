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
        "sheet": "PQ_2026",
        "nodes": {"베트남": {"currency": "VND", "symbol": "₫", "timezone": 7, "multiplier": 100}},
        "cats":["식사", "간식", "Grab", "VinBus", "마사지", "팁", "마트", "선물", "투어", "입장료", "통신", "수수료", "택시", "지하철", "항공권", "호텔", "보험"]
    },
    "🇨🇳 칭다오 (2025)": {
        "sheet": "QD_2025",
        "nodes": {"중국": {"currency": "CNY", "symbol": "¥", "timezone": 8, "multiplier": 1}},
        "cats":["식사", "간식", "DiDi", "지하철", "마사지", "팁", "마트", "선물", "투어", "입장료", "통신", "수수료", "택시", "항공권", "호텔", "보험", "보증금"]
    },
    "🗺️발칸6국(2024)": {
        "sheet": "BK_2024",
        "nodes": {
            "튀르키예": {"currency": "TRY", "symbol": "₺", "timezone": 3, "multiplier": 1},
            "세르비아": {"currency": "RSD", "symbol": "din", "timezone": 1, "multiplier": 1},
            "몬테네그로": {"currency": "EUR", "symbol": "€", "timezone": 1, "multiplier": 1},
            "크로아티아": {"currency": "EUR", "symbol": "€", "timezone": 1, "multiplier": 1},
            "헝가리": {"currency": "HUF", "symbol": "Ft", "timezone": 1, "multiplier": 100},
            "중국(상하이)": {"currency": "CNY", "symbol": "¥", "timezone": 8, "multiplier": 1},
            "글로벌(달러)": {"currency": "USD", "symbol": "$", "timezone": 1, "multiplier": 1}
        },
        # [Modified] 발칸 지출 카테고리에 '렌트카' 추가
        "cats":["식사", "간식", "교통", "렌트카", "마사지", "팁", "마트", "선물", "투어", "입장료", "통신", "수수료", "택시", "항공권", "호텔", "보험", "보증금", "기타"]
    }
}

# [Modified] MACRO_MAP에 재환전, 렌트카 추가
MACRO_MAP = {
    "Grab": "🚗 교통", "VinBus": "🚗 교통", "DiDi": "🚗 교통", "지하철": "🚗 교통", "택시": "🚗 교통", "렌트카": "🚗 교통",
    "식사": "🍔 식음료", "간식": "🍔 식음료", "마트": "🍔 식음료",
    "마사지": "🏄 액티비티", "투어": "🏄 액티비티", "입장료": "🏄 액티비티",
    "선물": "🎁 쇼핑", "통신": "📱 통신/기타", "수수료": "📱 통신/기타", "팁": "📱 통신/기타",
    "항공권": "✈️ 항공권", "호텔": "🏨 숙박", "보험": "🛡️ 보험", "보증금": "🏦 자산이동", "재환전": "🏦 자산이동"
}

CORE_COLUMNS =['Date', 'Country', 'Category', 'Description', 'Currency', 'Amount', 'PaymentMethod', 'Receipt_URL']
SYSTEM_LOGIC_COLUMNS =['IsExpense', 'AppliedRate', 'Cum_Budget_KRW', 'Cum_Card_Local', 'Cum_Cash_Local', 'Note']
FINAL_COLUMNS = CORE_COLUMNS + SYSTEM_LOGIC_COLUMNS

IMGBB_API_KEY = "81181bf834001b6191aaa90fa772c6f9"
BILLS =[500000, 200000, 100000, 50000, 20000, 10000, 5000, 2000, 1000]

# [Modified] 버전 및 업데이트 로그 v26.05.06.002
VERSION = "v26.05.06.002"
UPDATE_LOG_TEXT = """* `[Improved]` 탭 디자인 혁신: 밋밋했던 상단 탭을 도드라지는 버튼형 디자인으로 변경하여 선택 상태의 시인성을 극대화함.
* `[Fixed]` 모바일 최적화: 차트 X축 겹침 방지 및 일별 지출 표 가로 스크롤 지원 적용 완료."""

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
    .kpi-box { background-color: #1e2130; padding: 20px; border-radius: 15px; border-left: 8px solid #FF8C00; margin-bottom: 20px; min-height: 130px; box-shadow: 4px 6px 15px rgba(0,0,0,0.5); }
    .kpi-title { font-size: 15px; color: #cccccc; margin-bottom: 10px; font-weight: 600; }
    .kpi-value-krw { font-size: 26px; font-weight: bold; color: #ffffff; line-height: 1.1; }
    .kpi-value-vnd { font-size: 18px; color: #FFA500; margin-top: 8px; font-family: 'Courier New', monospace; font-weight: 500; }
    div[data-testid="stTable"] { border: 1px solid #444; border-radius: 10px; overflow: hidden; }

    /* [Modified] 오렌지 강조형 탭 컨테이너 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 5px; 
        padding: 5px 5px;
        background-color: #161a25; 
        border-radius: 12px;
        border: 2px solid #FFA500; /* 테두리를 오렌지색으로 변경 및 두께 강화 */
        box-shadow: 0px 0px 10px rgba(255, 165, 0, 0.2); /* 은은한 오렌지 광채 추가 */
    }

    .stTabs [data-baseweb="tab"] {
        height: 40px; 
        background-color: #262b3b; /* 비활성 배경을 조금 더 밝게 조정 */
        border-radius: 8px !important;
        padding: 0px 10px !important; 
        color: #CCCCCC !important; /* 글자색을 어두운 회색에서 밝은 회색으로 변경 */
        border: 1px solid #333;
        font-size: 14px !important; 
        transition: all 0.3s ease;
    }

    .stTabs [data-baseweb="tab"]:hover {
        background-color: #3d4455; /* 마우스 올렸을 때 더 밝게 반응 */
        color: #ffffff !important;
    }

    /* [Modified] 오렌지 테마 활성 탭 */
    .stTabs [aria-selected="true"] {
        background-color: #FFA500 !important; /* 네온그린에서 오렌지로 변경 */
        color: #000000 !important; 
        font-weight: 800 !important;
        box-shadow: 0px 4px 12px rgba(255, 165, 0, 0.4) !important; 
        border: 1px solid #FFA500 !important;
    }

    /* 사이드바 및 드롭다운 스타일 (오렌지 톤 유지) */
    div[data-testid="stSidebar"] div[data-baseweb="select"] > div { border: 2px solid #FFA500 !important; background-color: #1e2130 !important; border-radius: 10px !important; }
    div[data-testid="stSidebar"] .stSelectbox label { color: #FFA500 !important; font-weight: bold !important; }
    div[data-baseweb="popover"] li[aria-selected="true"] { background-color: #FFA500 !important; color: #000000 !important; font-weight: bold !important; }
    div[data-baseweb="popover"] li:hover { background-color: #FFD700 !important; color: #000000 !important; }
    div[data-testid="stSidebar"] .stSelectbox label p { color: #FFD700 !important; }
    </style>
    """, unsafe_allow_html=True)

if 'current_trip' not in st.session_state: st.session_state.current_trip = list(TRIP_CONFIGS.keys())[0]

ACTIVE_SHEET = TRIP_CONFIGS[st.session_state.current_trip]["sheet"]
FIRST_NODE_NAME = list(TRIP_CONFIGS[st.session_state.current_trip]["nodes"].keys())[0]
FIRST_NODE = TRIP_CONFIGS[st.session_state.current_trip]["nodes"][FIRST_NODE_NAME]
TRAVEL_CURRENCY = FIRST_NODE["currency"]
LOCAL_SYM = FIRST_NODE["symbol"]
TRIP_TZ = timezone(timedelta(hours=FIRST_NODE["timezone"]))
MULTIPLIER = FIRST_NODE["multiplier"]
EXPENSE_CATS = TRIP_CONFIGS[st.session_state.current_trip]["cats"]
SURVIVAL_CATS =["간식", "Grab", "DiDi", "VinBus", "지하철", "마사지", "팁", "식사", "교통"]
FIXED_COST_CATS =["항공권", "호텔", "보험"]
DOMESTIC_CATS =["항공권", "호텔", "보험", "지하철", "택시"]

if 'current_tz' not in st.session_state: st.session_state.current_tz = TZ_KST
if 'shared_date' not in st.session_state: st.session_state.shared_date = datetime.now(st.session_state.current_tz).date()
# [Modified] 인덱스 대신 문자열로 상태 기억
if 'last_cat_name' not in st.session_state: st.session_state.last_cat_name = "식사"

# --- SECTION 2:[Module A] Data Engine ---
def get_asset_class(text):
    txt = str(text).replace(" ", "")
    if any(k in txt for k in["현금", "종이돈", "지폐"]): return "CASH" 
    if any(k in txt for k in["트래블", "월렛", "카드"]): return "PREPAID" 
    return "DOMESTIC" 

# [Modified] 하드코딩 폐기 및 가계부 내 평균 환율 동적 추론 로직으로 변경
def get_default_rate(curr):
    if curr == "KRW": return 1.0
    # 1순위: 현재 로드된 ledger_df(이번 여행)에서 해당 통화의 평균 적용 환율 찾기
    try:
        if 'ledger_df' in globals() and not ledger_df.empty:
            df_curr = ledger_df[(ledger_df['Currency'].str.strip() == curr) & (ledger_df['AppliedRate'] > 0)]
            if not df_curr.empty: return df_curr['AppliedRate'].mean()
    except: pass
    
    # 2순위: 시스템에 남겨진 안전망 (최소한의 계산 실패 방지용)
    fallback_rates = {"VND": 0.056, "CNY": 190.0, "USD": 1350.0, "EUR": 1480.0, "TRY": 45.0, "RSD": 12.6, "HUF": 3.8}
    return fallback_rates.get(curr, 1.0)

def upload_image_to_imgbb(image_file):
    try:
        payload = {"key": IMGBB_API_KEY, "image": base64.b64encode(image_file.read()).decode("utf-8")}
        res = requests.post("https://api.imgbb.com/1/upload", data=payload)
        if res.status_code == 200: return res.json()['data']['url']
    except: pass
    return ""

def normalize_date(d_str):
    d_str = str(d_str).strip()
    # 1. 이미 YYYY-MM-DD(Day) 형식이면 그대로 반환
    if re.match(r'^\d{4}-\d{2}-\d{2}', d_str):
        return d_str
    
    # 2. YY.MM.DD 또는 YYYY.MM.DD 형식을 YYYY-MM-DD(Day)로 변환
    match = re.match(r'^(?:20)?(\d{2})[\.\-\/]\s*(\d{1,2})[\.\-\/]\s*(\d{1,2})\.?$', d_str)
    if match:
        y, m, d = match.groups()
        dt_obj = datetime.strptime(f"20{y}-{int(m):02d}-{int(d):02d}", "%Y-%m-%d")
        return dt_obj.strftime("%Y-%m-%d(%a)")
    return d_str

def load_data():
    try:
        df = conn.read(worksheet=ACTIVE_SHEET, ttl="0s")
        if df is None or df.empty: return pd.DataFrame(columns=FINAL_COLUMNS)

        # [Added] 마이그레이션을 위한 현재 여행 연도 추출
        year_match = re.search(r'\((\d{4})\)', st.session_state.current_trip)
        trip_year = year_match.group(1) if year_match else "2024"

        # 1. Country 보정 로직 (유지)
        if 'Country' not in df.columns:
            df.insert(1, 'Country', FIRST_NODE_NAME)
        else:
            df['Country'] = df['Country'].astype(str).str.strip().replace(['nan', 'None', ''], None)
            df['Country'] = df['Country'].fillna(FIRST_NODE_NAME)
        
        # 2. 레거시 컬럼명 변경 (유지)
        if 'Cum_Card_VND' in df.columns: df.rename(columns={'Cum_Card_VND': 'Cum_Card_Local'}, inplace=True)
        if 'Cum_Cash_VND' in df.columns: df.rename(columns={'Cum_Cash_VND': 'Cum_Cash_Local'}, inplace=True)
        if 'Receipt_URL' not in df.columns: df['Receipt_URL'] = ""
            
        # 3. 데이터 클리닝 및 연도 결합 (Modified)
        df = df.dropna(subset=['Date', 'Category'], how='any')
        df['Category'] = df['Category'].astype(str).str.strip()
        df['PaymentMethod'] = df['PaymentMethod'].astype(str).str.strip()
        df['Currency'] = df['Currency'].astype(str).str.strip()
        
        # [Added] 구형 날짜(MM/DD)에 연도 강제 주입 로직
        def fix_legacy_date(d):
            d = str(d).strip()
            if d and not re.match(r'^\d{4}', d): # 연도로 시작하지 않는 데이터
                # "04/21(Tue)" 또는 "04/21" -> "2026-04-21"
                return f"{trip_year}-{d.replace('/', '-')}"
            return d

        df['Date'] = df['Date'].apply(fix_legacy_date)
        df['Date'] = df['Date'].apply(normalize_date)
        
        # 4. 수치형 변환 및 정규화 (유지)
        df = df.reindex(columns=FINAL_COLUMNS)
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
        df['AppliedRate'] = pd.to_numeric(df['AppliedRate'], errors='coerce').fillna(0.0)
        df['IsExpense'] = pd.to_numeric(df['IsExpense'], errors='coerce').fillna(0).astype(int)
        df['Note'] = df['Note'].fillna("").astype(str)
        df['Receipt_URL'] = df['Receipt_URL'].fillna("").astype(str)
        return df
    except Exception: return pd.DataFrame(columns=FINAL_COLUMNS)

def load_all_trips_data():
    all_dfs =[]
    with st.spinner("🌍 모든 여행 기록을 불러오는 중..."):
        for trip_name, config in TRIP_CONFIGS.items():
            try:
                df_t = conn.read(worksheet=config['sheet'], ttl="0s")
                if df_t is None or df_t.empty: continue
                
                first_node_name = list(config["nodes"].keys())[0]
                if 'Country' not in df_t.columns:
                    df_t.insert(1, 'Country', first_node_name)
                else:
                    df_t['Country'] = df_t['Country'].astype(str).str.strip().replace(['nan', 'None', ''], None)
                    df_t['Country'] = df_t['Country'].fillna(first_node_name)

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
    
    from collections import defaultdict
    inv_batches = defaultdict(list)
    c_budget = 0.0
    
    for i, row in temp_df.iterrows():
        qty, curr = row['Amount'], row['Currency']
        cat, method, desc = str(row['Category']).strip(), str(row['PaymentMethod']).strip(), str(row['Description']).strip()
        
        # [Modified] 재환전을 명시적 비지출(0) 항목으로 보호
        is_exp = 1 if cat in EXPENSE_CATS and cat not in['환불', '보증금', '재환전'] else 0
        temp_df.at[i, 'IsExpense'] = is_exp
        
        is_deductible = 1 if (is_exp == 1 or cat == '보증금') else 0
        rate = temp_df.at[i, 'AppliedRate'] 
        
        asset_cls = get_asset_class(method)
        
        if cat in['충전', '환전', '입금', '직접환전']:
            if curr != 'KRW' and (pd.isna(rate) or rate <= 0.0 or rate == 1.0): rate = get_default_rate(curr)
            dest_cls = get_asset_class(desc + method)
            target = f"트래블로그({curr})" if dest_cls == "PREPAID" else f"현금({curr})"
            
            if curr != 'KRW': inv_batches[target].append({'rate': rate, 'qty': qty})
            if asset_cls == "DOMESTIC": c_budget += qty if curr == 'KRW' else qty * rate
        
        elif cat == '환불':
            if curr != 'KRW' and (pd.isna(rate) or rate <= 0.0 or rate == 1.0): rate = get_default_rate(curr)
            if asset_cls == "DOMESTIC":
                c_budget -= qty if curr == 'KRW' else qty * rate 
            else:
                target = f"트래블로그({curr})" if asset_cls == "PREPAID" else f"현금({curr})"
                if curr != 'KRW': inv_batches[target].append({'rate': rate, 'qty': qty})
                
        # [Added] 재환전 인벤토리 차감 및 원금(Budget) 회수 로직
        elif cat == '재환전':
            if curr != 'KRW':
                target_from = f"트래블로그({curr})" if asset_cls == "PREPAID" else f"현금({curr})"
                temp_qty = qty
                if target_from in inv_batches:
                    for batch in inv_batches[target_from]:
                        if temp_qty <= 0: break
                        if batch['qty'] <= 0: continue
                        take = min(temp_qty, batch['qty'])
                        batch['qty'] -= take
                        temp_qty -= take
                if pd.notna(rate) and rate > 0:
                    c_budget -= qty * rate
        
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
            elif curr != 'KRW':
                target = f"트래블로그({curr})" if asset_cls == "PREPAID" else f"현금({curr})"
                temp_qty = qty; total_cost_krw = 0.0; decomposed =[]
                if target in inv_batches:
                    for batch in inv_batches[target]:
                        if temp_qty <= 0: break
                        if batch['qty'] <= 0: continue
                        take = min(temp_qty, batch['qty']); batch['qty'] -= take; temp_qty -= take
                        total_cost_krw += take * batch['rate']
                        take_str = f"{take:,.2f}" if curr not in["VND", "HUF"] else f"{take:,.0f}"
                        rate_str = f"{batch['rate']:.2f}" if curr not in ["VND", "HUF"] else f"{batch['rate']:.4f}"
                        decomposed.append(f"{take_str}@{rate_str}")
                if qty > 0:
                    rate = total_cost_krw / qty if total_cost_krw > 0 else get_default_rate(curr)
                    if decomposed: temp_df.at[i, 'Note'] = "Decomposed: " + " + ".join(decomposed)
                else: rate = 0.0

        row_country = temp_df.at[i, 'Country']
        nodes = TRIP_CONFIGS[st.session_state.current_trip].get("nodes", {})
        row_curr = nodes.get(row_country, FIRST_NODE)["currency"] if nodes else "USD"
        rnd_dec = 0 if row_curr in["VND", "HUF", "KRW"] else 2
        
        temp_df.at[i, 'AppliedRate'] = rate
        temp_df.at[i, 'Cum_Budget_KRW'] = round(c_budget, 2)
        temp_df.at[i, 'Cum_Card_Local'] = round(sum([b['qty'] for b in inv_batches[f"트래블로그({row_curr})"]]), rnd_dec)
        temp_df.at[i, 'Cum_Cash_Local'] = round(sum([b['qty'] for b in inv_batches[f"현금({row_curr})"]]), rnd_dec)
        
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
    from collections import defaultdict
    temp_df = df.sort_values(by='Date', kind='mergesort', ignore_index=True) if not df.empty else df
    inv_batches = defaultdict(list)
    if temp_df.empty: return dict(inv_batches)
    for _, row in temp_df.iterrows():
        qty, rate, desc, cat, method, curr = row['Amount'], row['AppliedRate'], str(row['Description']), str(row['Category']).strip(), str(row['PaymentMethod']), row['Currency']
        asset_cls = get_asset_class(method)
        
        if cat in['충전', '환전', '입금', '직접환전']:
            dest_cls = get_asset_class(desc + method)
            target = f"트래블로그({curr})" if dest_cls == "PREPAID" else f"현금({curr})"
            if curr != 'KRW': inv_batches[target].append({'rate': rate, 'qty': qty, 'initial': qty})
        elif cat == '환불':
            if asset_cls != "DOMESTIC":
                target = f"트래블로그({curr})" if asset_cls == "PREPAID" else f"현금({curr})"
                if curr != 'KRW': inv_batches[target].append({'rate': rate, 'qty': qty, 'initial': qty})
        elif cat == 'ATM출금':
            temp_qty = qty; target_from = f"트래블로그({curr})"; target_to = f"현금({curr})"
            if target_from in inv_batches:
                for batch in inv_batches[target_from]:
                    if temp_qty <= 0: break
                    if batch['qty'] <= 0: continue
                    take = min(temp_qty, batch['qty']); batch['qty'] -= take
                    inv_batches[target_to].append({'rate': batch['rate'], 'qty': take, 'initial': take}); temp_qty -= take
        # [Modified] 재환전 시에도 인벤토리(지갑)가 지출처럼 까이도록 '재환전' 추가
        elif (row['IsExpense'] == 1 or cat in ['보증금', '재환전']) and curr != 'KRW':
            if asset_cls != "DOMESTIC":
                target = f"트래블로그({curr})" if asset_cls == "PREPAID" else f"현금({curr})"
                temp_qty = qty
                if target in inv_batches:
                    for batch in inv_batches[target]:
                        if temp_qty <= 0: break
                        if batch['qty'] <= 0: continue
                        take = min(temp_qty, batch['qty']); batch['qty'] -= take; temp_qty -= take
    return dict(inv_batches)

current_inventory_batches = get_inventory_status(ledger_df)

sw_df_loc = ledger_df[(ledger_df['Category'].str.strip().isin(['충전','환전','입금','직접환전'])) & (ledger_df['Currency'].str.strip() == TRAVEL_CURRENCY)]
WAR_LOCAL = (sw_df_loc['Amount'] * sw_df_loc['AppliedRate']).sum() / sw_df_loc['Amount'].sum() if not sw_df_loc.empty and sw_df_loc['Amount'].sum() > 0 else get_default_rate(TRAVEL_CURRENCY)

def get_WAR(curr):
    sw_df = ledger_df[(ledger_df['Category'].str.strip().isin(['충전','환전','입금','직접환전'])) & (ledger_df['Currency'].str.strip() == curr)]
    if not sw_df.empty and sw_df['Amount'].sum() > 0: return (sw_df['Amount'] * sw_df['AppliedRate']).sum() / sw_df['Amount'].sum()
    return get_default_rate(curr)

def auto_calc_fifo_rate(amount, method, curr=TRAVEL_CURRENCY):
    asset_cls = get_asset_class(method)
    if asset_cls == "DOMESTIC": return get_WAR(curr)
    
    target = f"트래블로그({curr})" if asset_cls == "PREPAID" else f"현금({curr})"
    temp_inv = get_inventory_status(ledger_df)
    if target not in temp_inv: return get_WAR(curr)
    available_batches = [b for b in temp_inv[target] if b['qty'] > 0]
    if not available_batches: return get_WAR(curr)
    total_cost_krw, remaining = 0.0, amount
    for batch in available_batches:
        if remaining <= 0: break
        take = min(remaining, batch['qty']); total_cost_krw += take * batch['rate']; remaining -= take
    if remaining > 0: total_cost_krw += remaining * available_batches[-1]['rate']
    return total_cost_krw / amount if amount > 0 else 0

def calculate_summary_metrics(df):
    if df.empty: return 0.0, 0.0
    temp_df = df.sort_values(by='Date', kind='mergesort', ignore_index=True)
    b_total = temp_df['Cum_Budget_KRW'].iloc[-1] if 'Cum_Budget_KRW' in temp_df.columns else 0
    
    gross_spent = temp_df[temp_df['IsExpense'] == 1].apply(lambda r: r['Amount'] if str(r['Currency']).strip() == 'KRW' else r['Amount'] * r['AppliedRate'], axis=1).sum()
    expense_refunds = temp_df[(temp_df['Category'] == '환불') & (temp_df['PaymentMethod'].apply(get_asset_class) == 'DOMESTIC')]
    refund_total = expense_refunds.apply(lambda r: r['Amount'] if str(r['Currency']).strip() == 'KRW' else r['Amount'] * r['AppliedRate'], axis=1).sum()
    
    return b_total, gross_spent - refund_total

# --- SECTION 5:[Sidebar] ---
with st.sidebar:
    st.divider()
    st.title("💰 Wallet Status")
    b_val, spent_val = calculate_summary_metrics(ledger_df)
    
    active_currs = set([k.split('(')[1].replace(')','') for k in current_inventory_batches.keys() if len(current_inventory_batches[k]) > 0 and sum(b['qty'] for b in current_inventory_batches[k]) > 0])
    trip_currs = set(node['currency'] for node in TRIP_CONFIGS[st.session_state.current_trip]["nodes"].values())
    display_currs = sorted(list(active_currs | trip_currs))
    
    for c in display_currs:
        if c == "KRW": continue
        c_card = sum([b['qty'] for b in current_inventory_batches.get(f"트래블로그({c})", [])])
        c_cash = sum([b['qty'] for b in current_inventory_batches.get(f"현금({c})",[])])
        
        if c_card > 0 or c_cash > 0 or c in trip_currs:
            st.markdown(f"**[{c} 잔액]**")
            c1, c2 = st.columns(2)
            fmt = "{:,.2f}" if c not in["VND", "HUF"] else "{:,.0f}"
            
            c1.metric(f"💳 카드", f"{fmt.format(c_card)}")
            if current_inventory_batches.get(f"트래블로그({c})"):
                with c1.expander("카드배치", expanded=False):
                    for b in current_inventory_batches[f"트래블로그({c})"]:
                        if b['qty'] > 0: st.caption(f"• {fmt.format(b['qty'])} @ {b['rate']:.2f}원")
            
            c2.metric(f"💵 현금", f"{fmt.format(c_cash)}")
            if current_inventory_batches.get(f"현금({c})"):
                with c2.expander("현금배치", expanded=False):
                    for b in current_inventory_batches[f"현금({c})"]:
                        if b['qty'] > 0: st.caption(f"• {fmt.format(b['qty'])} @ {b['rate']:.2f}원")
            st.divider()

    st.metric("🏦 총 예산 (KRW)", f"{b_val:,.0f} 원")
    st.metric("💸 지출총액 (KRW)", f"{spent_val:,.0f} 원")

    st.divider()
    tz_sel = st.radio("📍 기준 시간 (Timezone)",["🇰🇷 한국 시간", "🌍 여행지 현지 시간"], horizontal=True, index=0 if "한국" in str(st.session_state.current_tz) else 1)
    st.session_state.current_tz = TZ_KST if "한국" in tz_sel else TRIP_TZ
    if st.button("🔄 Cloud Refresh", use_container_width=True): st.cache_data.clear(); st.rerun()
        
# --- SECTION 4:[Module C] Intelligent Input (📝 입력) ---
st.title(f"{st.session_state.current_trip}")

# [Modified] 메인 화면 상단으로 전진 배치된 여행 선택기
c_trip_top, c_empty = st.columns([2, 2])
with c_trip_top:
    sel_trip = st.selectbox("✈️ 내 여행함 (Trip Selector)", list(TRIP_CONFIGS.keys()), 
                             index=list(TRIP_CONFIGS.keys()).index(st.session_state.current_trip),
                             label_visibility="collapsed") # 제목이 이미 있으므로 라벨은 숨김
    if sel_trip != st.session_state.current_trip:
        st.session_state.current_trip = sel_trip; st.rerun()

st.divider() # 선택기 아래 구분선 추가

tab_in, tab_his, tab_stats, tab_final = st.tabs(["📝 입력", "🔍 조회", "📊 일일", "🏁 요약"])

with tab_in:
    c_node, c_mode = st.columns([1, 2])
    with c_node:
        sel_node = st.selectbox("🌍 국가 선택", list(TRIP_CONFIGS[st.session_state.current_trip]["nodes"].keys()), key="in_country")
        IN_CFG = TRIP_CONFIGS[st.session_state.current_trip]["nodes"][sel_node]
        IN_CURR = IN_CFG["currency"]
        IN_MULTI = IN_CFG["multiplier"]
    with c_mode:
        mode = st.radio("기록 모드 선택",["일반 지출", "자산 이동", "환불(취소)", "출입국"], horizontal=True, key="mode_radio", label_visibility="collapsed")
    
    dynamic_tz = timezone(timedelta(hours=IN_CFG["timezone"])) if "한국" not in str(st.session_state.current_tz) else TZ_KST
    sel_date = st.date_input("날짜 선택", value=datetime.now(dynamic_tz).date(), key="shared_date_input")

    available_currs = sorted(list(set(node["currency"] for node in TRIP_CONFIGS[st.session_state.current_trip]["nodes"].values())))

    if mode == "일반 지출":        
        # [Modified] 인덱스가 아닌 카테고리 텍스트 자체를 추적하여 버그 원천 차단
        def_index = EXPENSE_CATS.index(st.session_state.last_cat_name) if st.session_state.last_cat_name in EXPENSE_CATS else 0
        cat = st.radio("항목 선택", EXPENSE_CATS, index=def_index, horizontal=True, key="exp_cat")
        st.session_state.last_cat_name = cat
        
        col_desc, col_receipt = st.columns([3, 1])
        with col_desc: desc = st.text_input("내용 (상호명 및 상세메모)", placeholder="예: 안바카페 - 소고기버거, 반미정식", key="exp_desc")
        with col_receipt: uploaded_file = st.file_uploader("📸 영수증 첨부", type=['png', 'jpg', 'jpeg'], key="exp_receipt")
            
        col_m1, col_m2, col_m3 = st.columns([1, 1, 1])
        with col_m1: 
            curr_opts =[IN_CURR, "KRW", "USD"] + [c for c in available_currs if c not in[IN_CURR, "KRW", "USD"]]
            curr = st.selectbox("통화", curr_opts, key="exp_curr")
        with col_m2:
            met_options =[f"현금({curr})", f"트래블로그({curr})", "원화계좌(한국)", "원화계좌(현지)"] if curr != "KRW" else["원화계좌(한국)", "원화계좌(현지)"]
            met = st.selectbox("결제 자산(Asset)", met_options, index=0, key="exp_met")
        with col_m3:
            harvested_tags = set()
            if not ledger_df.empty:
                extracted = ledger_df['Description'].str.extractall(r'\[(.*?)\]')
                if not extracted.empty: harvested_tags = set(extracted[0].dropna().unique())
            
            default_gateways =["알리페이", "위챗페이", "네이버페이", "카카오페이", "Apple Pay", "토스페이", "Trip.com", "Agoda", "Booking.com", "Uber", "Bolt", "Revolut"]
            combined_gateways =["선택안함 (기본)"] + sorted(list(set(default_gateways) | harvested_tags)) +["➕ 직접 입력하기"]
            gateway_sel = st.selectbox("결제 플랫폼 (Gateway)", combined_gateways, key="exp_gw")
            
            final_gateway = ""
            if gateway_sel == "➕ 직접 입력하기": final_gateway = st.text_input("새로운 플랫폼 이름 입력", placeholder="예: 마이리얼트립")
            elif gateway_sel != "선택안함 (기본)": final_gateway = gateway_sel

        col_a1, col_a2 = st.columns(2)
        with col_a1:
            if curr == "KRW" or (curr == IN_CURR and IN_MULTI == 100):
                amt = st.number_input(f"금액 ({curr})", min_value=0, step=1000 if curr != "KRW" else 1, format="%d", key="exp_amt_int")
            else:
                amt = st.number_input(f"금액 ({curr})", min_value=0.0, step=1.0, format="%.2f", key="exp_amt_float")
        with col_a2:
            if curr != "KRW" and amt > 0:
                calc_rate = auto_calc_fifo_rate(amt, met, curr)
                st.caption(f"💡 {curr} 인벤토리 계산 환율: **{calc_rate:.5f}**")
                cr_final = st.number_input("확정 환율", value=float(calc_rate), format="%.5f", key=f"exp_cr_auto_{met}_{amt}")
            else: cr_final = st.number_input("확정 환율", value=(1.0 if curr=="KRW" else get_default_rate(curr)), format="%.5f", key=f"exp_cr_man_{curr}")
            
        if st.button("🚀 지출 기록하기", use_container_width=True):
            receipt_url = ""
            if uploaded_file is not None:
                with st.spinner("📸 영수증 링킹 중..."):
                    receipt_url = upload_image_to_imgbb(uploaded_file)
            
            final_desc = f"[{final_gateway}] {desc}" if final_gateway else desc
            new_row = pd.DataFrame([{
                'Date': sel_date.strftime("%Y-%m-%d(%a)"),
                'Country': sel_node,
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
        # [Modified] 재환전 유형 추가
        ty = st.selectbox("유형",["직접환전 (원화계좌 -> 지폐)", "충전 (원화계좌 -> 카드)", "ATM출금 (카드 -> 지폐)", "재환전 (외화 -> 원화계좌)"], key="tr_type")
        c1, c2 = st.columns(2)
        
        # [Added] 재환전 전용 UI 및 환차손익 로직 추가
        if "재환전" in ty:
            with c1:
                curr_opts_tr =[c for c in available_currs if c not in ["KRW"]]
                curr_tr = st.selectbox("팔(Sell) 통화", curr_opts_tr, key="tr_curr")
                s_amt = st.number_input(f"팔 외화 금액 ({curr_tr})", min_value=0.0, step=10.0, format="%.2f", key="tr_sell_flt")
                source_met = st.selectbox("외화 출처",[f"트래블로그({curr_tr})", f"현금({curr_tr})"], key="tr_sell_met")
            with c2:
                rcv_krw = st.number_input("입금받은 원화 총액 (KRW)", min_value=0, step=1000, format="%d", key="tr_rcv_krw")
                if s_amt > 0:
                    fifo_rate = auto_calc_fifo_rate(s_amt, source_met, curr_tr)
                    fifo_cost = s_amt * fifo_rate
                    st.info(f"💡 시스템 내 매입 원가(FIFO): **{fifo_cost:,.0f} 원**")
                    fx_diff = rcv_krw - fifo_cost
                    if rcv_krw > 0:
                        st.caption(f"적용 매도 환율: {(rcv_krw/s_amt):.4f}")
                        if fx_diff < -1: st.error(f"📉 환차손(손해) 발생: {abs(fx_diff):,.0f} 원")
                        elif fx_diff > 1: st.success(f"📈 환차익(이익) 발생: {fx_diff:,.0f} 원")
                        else: st.success("⚖️ 환차손익 없음")
                        
            if st.button("🔄 재환전 실행 (환차손익 분할기록)", use_container_width=True):
                applied_sell_rate = rcv_krw / s_amt if s_amt > 0 else 0
                main_row = pd.DataFrame([{'Date': sel_date.strftime("%Y-%m-%d(%a)"), 'Country': sel_node, 'Category': '재환전', 'Description': f"남은 {curr_tr} 재환전 (외화매도)", 'Currency': curr_tr, 'Amount': s_amt, 'PaymentMethod': source_met, 'IsExpense': 0, 'AppliedRate': applied_sell_rate, 'Note': f"원화 {rcv_krw}원 입금", 'Receipt_URL': ''}])
                final_entry = pd.concat([ledger_df, main_row], ignore_index=True)
                
                fx_diff = rcv_krw - (s_amt * auto_calc_fifo_rate(s_amt, source_met, curr_tr)) if s_amt > 0 else 0
                if abs(fx_diff) >= 1:
                    fx_amt = -abs(fx_diff) if fx_diff > 0 else abs(fx_diff)
                    desc_fx = f"[{curr_tr} 재환전] 환차익" if fx_diff > 0 else f"[{curr_tr} 재환전] 환차손"
                    fx_row = pd.DataFrame([{'Date': sel_date.strftime("%Y-%m-%d(%a)"), 'Country': sel_node, 'Category': '수수료', 'Description': desc_fx, 'Currency': 'KRW', 'Amount': fx_amt, 'PaymentMethod': '원화계좌(한국)', 'IsExpense': 1, 'AppliedRate': 1.0, 'Note': 'Auto-FX Diff', 'Receipt_URL': ''}])
                    final_entry = pd.concat([final_entry, fx_row], ignore_index=True)
                if save_data(final_entry): st.rerun()
                
        else:
            with c1:
                curr_opts_tr =[IN_CURR, "USD"] +[c for c in available_currs if c not in[IN_CURR, "USD", "KRW"]]
                curr_tr = st.selectbox("대상 통화", curr_opts_tr, key="tr_curr")
                if curr_tr == IN_CURR and IN_MULTI == 100:
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
                if curr_tr == IN_CURR and IN_MULTI == 100:
                    fee_amt = st.number_input(f"ATM 수수료 ({curr_tr})", min_value=0, step=1000, format="%d", key="tr_fee_int")
                else:
                    fee_amt = st.number_input(f"ATM 수수료 ({curr_tr})", min_value=0.0, step=1.0, format="%.2f", key="tr_fee_flt")
                    
            if st.button("🔄 이동 실행", use_container_width=True):
                dest = f"트래블로그({curr_tr})" if "카드" in ty else f"현금({curr_tr})"
                source = "원화계좌(한국)" if "원화계좌" in ty else f"트래블로그({curr_tr})"
                main_row = pd.DataFrame([{'Date': sel_date.strftime("%Y-%m-%d(%a)"), 'Country': sel_node, 'Category': ty.split(" ")[0], 'Description': f"{ty.split(' ')[0]} (-> {dest})", 'Currency': curr_tr, 'Amount': t_amt, 'PaymentMethod': source, 'IsExpense': 0, 'AppliedRate': applied_tr_rate, 'Note': '', 'Receipt_URL': ''}])
                final_entry = pd.concat([ledger_df, main_row], ignore_index=True)
                if fee_amt > 0:
                    fee_rate = auto_calc_fifo_rate(fee_amt, f"트래블로그({curr_tr})", curr_tr)
                    fee_row = pd.DataFrame([{'Date': sel_date.strftime("%Y-%m-%d(%a)"), 'Country': sel_node, 'Category': "수수료", 'Description': f"{ty.split(' ')[0]} 수수료", 'Currency': curr_tr, 'Amount': fee_amt, 'PaymentMethod': f"트래블로그({curr_tr})", 'IsExpense': 1, 'AppliedRate': fee_rate, 'Note': '', 'Receipt_URL': ''}])
                    final_entry = pd.concat([final_entry, fee_row], ignore_index=True)
                if save_data(final_entry): st.rerun()

    elif mode == "환불(취소)":
        st.subheader("🔙 결제 취소 및 환불 (Rollback)")
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            curr_opts_rf =[IN_CURR, "KRW", "USD"] +[c for c in available_currs if c not in[IN_CURR, "KRW", "USD"]]
            r_curr = st.selectbox("취소된 통화", curr_opts_rf, key="rf_curr")
            
            r_met = st.selectbox("돌려받을 지갑",[f"현금({r_curr})", f"트래블로그({r_curr})", "원화계좌(한국)", "원화계좌(현지)"] if r_curr != "KRW" else["원화계좌(한국)", "원화계좌(현지)"], key="rf_met")
            if r_curr == "KRW" or (r_curr == IN_CURR and IN_MULTI == 100):
                r_amt = st.number_input("환불 금액", min_value=0, step=1000 if r_curr != "KRW" else 1, format="%d", key="rf_amt_int")
            else:
                r_amt = st.number_input("환불 금액", min_value=0.0, step=1.0, format="%.2f", key="rf_amt_flt")
        with col_r2:
            r_rate = st.number_input("과거 결제 시 적용됐던 환율", value=(1.0 if r_curr=="KRW" else get_default_rate(r_curr)), format="%.5f", key="rf_rate")
            r_desc = st.text_input("취소 내역 메모", placeholder="예: 호텔 보증금 반환", key="rf_desc")
        if st.button("🔙 환불 인벤토리 롤백 실행", use_container_width=True):
            new_row = pd.DataFrame([{'Date': sel_date.strftime("%Y-%m-%d(%a)"), 'Country': sel_node, 'Category': '환불', 'Description': f"취소: {r_desc}", 'Currency': r_curr, 'Amount': r_amt, 'PaymentMethod': r_met, 'IsExpense': 0, 'AppliedRate': r_rate, 'Note': 'Rollback', 'Receipt_URL': ''}])
            if save_data(pd.concat([ledger_df, new_row], ignore_index=True)): st.rerun()

    else:
        st.subheader("✈️ 출입국 일정 기록")
        io_type = st.radio("구분",["출국", "입국"], horizontal=True, key="io_radio")
        desc = st.text_input("내용 (메모)", placeholder="편명, 시간 등", key="io_desc")
        if st.button("🚀 일정 기록 완료", use_container_width=True):
            new_row = pd.DataFrame([{'Date': sel_date.strftime("%Y-%m-%d(%a)"), 'Country': sel_node, 'Category': io_type, 'Description': desc, 'Currency': 'KRW', 'Amount': 0, 'PaymentMethod': '원화계좌(한국)', 'IsExpense': 1, 'AppliedRate': 1.0, 'Note': '', 'Receipt_URL': ''}])
            if save_data(pd.concat([ledger_df, new_row], ignore_index=True)): st.rerun()

# --- SECTION 6:[Module D, E: History & Settlement] ---
with tab_his:
    st.info("💡 **표의 행(Row)을 클릭(터치)하시면 바로 아래에 상세 내역 수정과 영수증 첨부 화면이 펼쳐집니다!**")
    
    viewer_placeholder = st.empty()
    
    c_filter, c_search, c_tog = st.columns([2, 3, 1])
    with c_filter:
        filter_options =["모든 여행가계부", "이번 여행가계부"] + list(TRIP_CONFIGS[st.session_state.current_trip]["nodes"].keys())
        country_filter = st.selectbox("🌍 국가 필터", filter_options, index=1, key="his_country")
    with c_search: 
        search_query = st.text_input("🔎 검색어 입력", placeholder="상호명, 메모, 카테고리 등", key="his_search", label_visibility="collapsed")
    with c_tog: 
        edit_mode = st.toggle("✏️ 직접 수정 모드", value=False, key="his_edit_toggle")

    if country_filter == "모든 여행가계부":
        st.warning("⚠️ '모든 여행가계부' 모드에서는 내역 조회만 가능하며, 수정은 불가능합니다.")
        edit_mode = False 
        display_df = load_all_trips_data()
    else:
        display_df = ledger_df.copy()
        if country_filter != "이번 여행가계부":
            display_df = display_df[display_df['Country'] == country_filter]

    if st.button(f"🔄 '{st.session_state.current_trip}' 가계부 정합성 재계산", use_container_width=True, type="primary"):
        if save_data(ledger_df):
            st.success("데이터 정합성 복구 완료!"); time.sleep(1); st.rerun()
            
    if not display_df.empty: 
        display_df = display_df.sort_values(by='Date', kind='mergesort').reset_index(drop=True)
        display_df = display_df.reindex(columns=FINAL_COLUMNS)
        link_cfg = st.column_config.LinkColumn("영수증 📸", display_text="🔗 보기", disabled=True)
        
        if search_query.strip():
            mask = (
                display_df['Category'].str.contains(search_query, case=False, na=False) | 
                display_df['Description'].str.contains(search_query, case=False, na=False) | 
                display_df['Note'].str.contains(search_query, case=False, na=False) |
                display_df['Country'].str.contains(search_query, case=False, na=False) 
            )
            filtered_df = display_df[mask]
            st.write(f"🔎 검색 결과: {len(filtered_df)}건")
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

                        # [Added] 소나무 꿀 (Pine Honey) 에피소드 대응: KRW 즉시 환산 로직
                        krw_equivalent = row_data['Amount'] if row_data['Currency'] == 'KRW' else row_data['Amount'] * row_data['AppliedRate']
                        krw_display = f" ➔ <span style='color:#FFD700'>약 {krw_equivalent:,.0f} 원</span>" if row_data['Currency'] != 'KRW' else ""
                        
                        # [Modified] 마크다운에 원화 가치 병기 (HTML span 적용)
                        st.markdown(f"### 🛒 {row_data['Category']} ({amt_fmt2.format(row_data['Amount'])} {row_data['Currency']}{krw_display})", unsafe_allow_html=True)
                        st.markdown(f"**🏦 결제수단:** {row_data['PaymentMethod']}")
                        
                        desc_full = str(row_data['Description'])
                        if "-" in desc_full:
                            parts = desc_full.split("-", 1)
                            st.markdown(f"**🏪 상호명:** {parts[0].strip()}")
                            detail_str = parts[1].strip()
                            st.markdown("**📝 세부 구매 내역:**")
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
                return r['Amount'] * r['AppliedRate']
            exp_df['KRW_val'] = exp_df.apply(get_krw_val, axis=1)
            
            def get_local_val(r):
                c_curr = str(r['Currency']).strip()
                if c_curr == TRAVEL_CURRENCY: return r['Amount']
                krw_v = r['Amount'] if c_curr == 'KRW' else r['Amount'] * r['AppliedRate']
                war_t = get_WAR(TRAVEL_CURRENCY)
                return krw_v / war_t if war_t > 0 else 0
            exp_df['Local_val'] = exp_df.apply(get_local_val, axis=1)
            exp_df['IsSurvival'] = exp_df['Category'].apply(lambda x: 1 if x in SURVIVAL_CATS else 0)

            # [Added] Net-ifier 엔진: 환불 내역을 역산하여 지출(exp_df) 차트에서 직접 깎아냅니다.
            r_df = ledger_df[ledger_df['Category'] == '환불'].copy()
            if not r_df.empty:
                for _, r_row in r_df.iterrows():
                    desc = str(r_row['Description']).replace(" ", "")
                    t_cat = "기타"
                    if any(k in desc for k in["호텔", "숙박", "인페라", "라이온", "스플랜디도"]): t_cat = "호텔"
                    elif any(k in desc for k in["항공", "귁첸", "소피아", "베오그라드", "부다페스트"]): t_cat = "항공권"
                    
                    r_val = r_row['Amount'] if str(r_row['Currency']).strip() == 'KRW' else r_row['Amount'] * r_row['AppliedRate']
                    
                    while r_val > 0.5:
                        cands = exp_df[(exp_df['Category'] == t_cat) & (exp_df['KRW_val'] > 0)]
                        if cands.empty:
                            cands = exp_df[exp_df['KRW_val'] > 0]
                            if cands.empty: break
                        m_idx = cands['KRW_val'].idxmax()
                        take = min(r_val, exp_df.at[m_idx, 'KRW_val'])
                        exp_df.at[m_idx, 'KRW_val'] -= take
                        r_val -= take

            color_map = {"식사": "#2E7D32", "간식": "#4CAF50", "마트": "#E91E63", "Grab": "#00897B", "VinBus": "#00ACC1", "DiDi": "#00897B", "지하철": "#00ACC1", "택시": "#009688", "교통": "#009688", "렌트카": "#009688", "마사지": "#0288D1", "투어": "#673AB7", "입장료": "#3F51B5", "선물": "#9C27B0", "통신": "#FF9800", "수수료": "#795548", "팁": "#03A9F4", "항공권": "#D32F2F", "호텔": "#1976D2", "보험": "#FBC02D"}
            macro_color_map = {"🍔 식음료": "#4CAF50", "🚗 교통": "#00ACC1", "🏄 액티비티": "#0288D1", "🎁 쇼핑": "#9C27B0", "📱 통신/기타": "#FF9800", "✈️ 항공권": "#D32F2F", "🏨 숙박": "#1976D2", "🛡️ 보험": "#FBC02D", "기타": "#9E9E9E"}

            c_mode = st.radio("📊 통화 선택",["원화(KRW)", f"현지화({TRAVEL_CURRENCY})"], horizontal=True, key="st_curr_top")
            y_col = 'KRW_val' if "원화" in c_mode else 'Local_val'

            is_fixed_cost = (exp_df['PaymentMethod'].str.strip() == '원화계좌(한국)') | (exp_df['Category'].isin(FIXED_COST_CATS))

            ovr_df = exp_df[(~is_fixed_cost) & (~exp_df['Category'].isin(['입국','출국']))]
            if not ovr_df.empty:
                ovr_df = ovr_df.copy()
                ovr_df['Date_Clean'] = ovr_df['Date'].str.split('(').str[0]
                ovr_df = ovr_df.sort_values(by='Date_Clean')
                
                # [Added] 국가별 정보를 x축 라벨에 HTML로 병기하여 시각적 분리감 확보
                ovr_df['Date_Country'] = ovr_df['Date_Clean'] + "<br><span style='font-size:11px;color:#AAAAAA'>" + ovr_df['Country'] + "</span>"
                
                fig2 = px.bar(ovr_df, x='Date_Country', y=y_col, color='Category', title=None, color_discrete_map=color_map)
                # [Modified] X축 텍스트 겹침 방지를 위해 강제 -90도 회전 및 폰트 크기 조정, 하단 마진 증가
                fig2.update_layout(barmode='stack', margin=dict(l=10, r=10, t=30, b=150), legend=dict(orientation="h", yanchor="top", y=-0.3, xanchor="center", x=0.5))
                fig2.update_xaxes(categoryorder='array', categoryarray=ovr_df['Date_Country'].unique(), tickangle=-90, tickfont=dict(size=10))
                st.markdown(f"<h4 style='text-align: center;'>🗺️ 여행지 일별지출({len(ovr_df['Date_Clean'].unique())}일차)</h4>", unsafe_allow_html=True)
                st.plotly_chart(fig2, use_container_width=True, config={'displaylogo': False})

            st.divider()
            # [Modified] 일별 지출 테이블 GroupBy 쿼리에 '국가(Country)' 정보 묶음 연산 추가
            daily_set = ovr_df.groupby('Date').agg({'Country': lambda x: ' / '.join(x.unique()), 'KRW_val': 'sum', 'Local_val': 'sum'}).reset_index() if not ovr_df.empty else pd.DataFrame(columns=['Date', 'Country', 'KRW_val', 'Local_val'])
            surv_only = ovr_df[ovr_df['IsSurvival'] == 1].groupby('Date').agg({'KRW_val': 'sum', 'Local_val': 'sum'}).reset_index().rename(columns={'KRW_val': 'S_KRW', 'Local_val': 'S_Loc'}) if not ovr_df.empty else pd.DataFrame(columns=['Date', 'S_KRW', 'S_Loc'])
            daily_table = pd.merge(daily_set, surv_only, on='Date', how='left').fillna(0) if not daily_set.empty else pd.DataFrame()
            fmt_local = "{:,.2f}" if MULTIPLIER == 1 else "{:,.0f}"
            
            # [Added] 렌더링 시 컬럼 순서를 '국가 -> 날짜 -> 금액' 순으로 엑셀과 동일하게 배치
            if not daily_table.empty:
                display_table = daily_table[['Country', 'Date', 'KRW_val', 'Local_val', 'S_KRW', 'S_Loc']].rename(
                    columns={'Country':'국가', 'Date':'날짜', 'KRW_val':'총(원)', 'Local_val':f'총({LOCAL_SYM})', 'S_KRW':'일상(원)', 'S_Loc':f'일상({LOCAL_SYM})'}
                )
                # [Modified] 모바일에서 국가 이름 세로 늘어짐(행 높이 팽창) 방지를 위해 st.table 대신 반응형 st.dataframe 사용 및 인덱스 숨김 처리
                st.dataframe(display_table.style.format({'총(원)': '{:,.0f}', f'총({LOCAL_SYM})': fmt_local, '일상(원)': '{:,.0f}', f'일상({LOCAL_SYM})': fmt_local}), use_container_width=True, hide_index=True)
            else:
                st.info("현지 지출 데이터가 없습니다.")

            dom_df = exp_df[is_fixed_cost & (~exp_df['Category'].isin(['입국','출국']))]
            if not dom_df.empty:
                st.divider()
                fig1 = px.treemap(dom_df, path=['Macro_Category', 'Category', 'Description'], values=y_col, color='Macro_Category', color_discrete_map=macro_color_map)
                fig1.update_traces(texttemplate="<b>%{label}</b><br>%{value:,.0f}", hovertemplate="<b>%{label}</b><br>금액: %{value:,.0f}")
                fig1.update_layout(margin=dict(l=10, r=10, t=30, b=30))
                st.markdown("<h4 style='text-align: center;'>🛫 사전결제(Treemap)</h4>", unsafe_allow_html=True)
                st.plotly_chart(fig1, use_container_width=True, config={'displaylogo': False})

            if len(TRIP_CONFIGS[st.session_state.current_trip]["nodes"]) > 1 and not ovr_df.empty:
                st.divider()
                fig_country = px.treemap(ovr_df, path=['Country', 'Macro_Category', 'Category'], values=y_col, color='Country', color_discrete_sequence=px.colors.qualitative.Pastel)
                fig_country.update_traces(texttemplate="<b>%{label}</b><br>%{value:,.0f}", hovertemplate="<b>%{label}</b><br>금액: %{value:,.0f}")
                fig_country.update_layout(margin=dict(l=10, r=10, t=30, b=30))
                st.markdown("<h4 style='text-align: center;'>🌍 국가별 현지지출(Treemap)</h4>", unsafe_allow_html=True)
                st.plotly_chart(fig_country, use_container_width=True, config={'displaylogo': False})

            st.divider()
            st.subheader("🏁 여행 비용 요약 (Net)")
            c1, c2 = st.columns(2)
            
            refund_df = ledger_df[ledger_df['Category'] == '환불']
            dom_refunds = refund_df[refund_df['PaymentMethod'].apply(get_asset_class) == 'DOMESTIC']
            dom_refund_total = dom_refunds.apply(lambda r: r['Amount'] if str(r['Currency']).strip() == 'KRW' else r['Amount'] * r['AppliedRate'], axis=1).sum() if not dom_refunds.empty else 0
            
            with c1:
                st.info("🇰🇷 사전 결제")
                # [Modified] Net-ifier가 이미 차감했으므로 중복 차감 제거
                st.metric("순지출액", f"{dom_df['KRW_val'].sum():,.0f} 원")
                with st.expander("상세내역", expanded=False):
                    dg = dom_df.groupby('Category').agg({'KRW_val':'sum', 'Date':'count'}).sort_values(by='KRW_val', ascending=False)
                    for cat_name, row_data in dg.iterrows():
                        st.write(f"• {cat_name}({int(row_data['Date'])}회): {row_data['KRW_val']:,.0f} 원")
            with c2:
                st.success(f"🌏 여행지 지출")
                st.metric("총액", f"{ovr_df['KRW_val'].sum():,.0f} 원")
                with st.expander("상세내역", expanded=False):
                    og = ovr_df.groupby('Category').agg({'KRW_val':'sum', 'Date':'count'}).sort_values(by='KRW_val', ascending=False)
                    for cat_name, row_data in og.iterrows():
                        st.write(f"• {cat_name}({int(row_data['Date'])}회): {row_data['KRW_val']:,.0f} 원")

            if not refund_df.empty:
                st.divider()
                st.subheader("🛡️ 손실과 보상")
                r_krw = refund_df.apply(lambda r: r['Amount'] if str(r['Currency']).strip() == 'KRW' else r['Amount'] * r['AppliedRate'], axis=1).sum()
                st.warning(f"**환불총액:** {r_krw:,.0f} 원")
                with st.expander("상세내역", expanded=False):
                    st.dataframe(refund_df[['Date', 'Country', 'Description', 'Amount', 'Currency', 'PaymentMethod']], use_container_width=True)

with tab_final:
    if not ledger_df.empty and 'exp_df' in locals() and not exp_df.empty:
        # [Modified] Net-ifier가 exp_df 내부의 값을 이미 깎았으므로, 여기서 추가로 빼지 않음 (이중 차감 방지)
        total_trip_krw = exp_df['KRW_val'].sum()
        total_trip_loc = exp_df['Local_val'].sum()
        
        is_fixed_cost_final = (exp_df['PaymentMethod'].str.strip() == '원화계좌(한국)') | (exp_df['Category'].isin(FIXED_COST_CATS))
        dom_total_krw = exp_df[is_fixed_cost_final]['KRW_val'].sum()
        ovr_total_krw = total_trip_krw - dom_total_krw
        ovr_total_loc = exp_df[~is_fixed_cost_final]['Local_val'].sum()
        
        local_v = exp_df[(exp_df['IsSurvival'] == 1) & (exp_df['Currency'].str.strip() == TRAVEL_CURRENCY)].copy()
        avg_local_krw = local_v['KRW_val'].sum() / 7 if not local_v.empty else 0
        avg_local_loc = local_v['Local_val'].sum() / 7 if not local_v.empty else 0
        
        fmt_local = "{:,.2f}" if MULTIPLIER == 1 else "{:,.0f}"
        def kpi_box(title, krw, loc=None):
            loc_str = f"<div class='kpi-value-vnd'>({fmt_local.format(loc)} {LOCAL_SYM})</div>" if loc is not None else ""
            return f"<div class='kpi-box'><div class='kpi-title'>{title}</div><div class='kpi-value-krw'>{krw:,.0f} 원</div>{loc_str}</div>"
            
        st.header("🏁 여행요약")
        k1, k2, k3, k4 = st.columns(4)
        with k1: st.markdown(kpi_box("여행 최종 순지출", total_trip_krw, total_trip_loc), unsafe_allow_html=True)
        with k2: st.markdown(kpi_box("국내 지출 순액", dom_total_krw), unsafe_allow_html=True)
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
        fig_donut.add_annotation(text=f"<b>순지출(Net)</b><br>{total_trip_krw:,.0f} 원<br><span style='font-size:10px'>Until {until_day}</span>", showarrow=False, font=dict(size=16))
        fig_donut.update_layout(height=600, margin=dict(l=10, r=10, t=50, b=100), legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5), uniformtext_minsize=11, uniformtext_mode='hide')
        st.plotly_chart(fig_donut, use_container_width=True)

st.caption(f"GTL Platform v26.05.06.001 | Volume Guard: 69.8 KB | Sync: {datetime.now(st.session_state.current_tz).strftime('%Y-%m-%d %H:%M:%S')} | Strategic Partner Gem")
