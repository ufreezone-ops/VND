# ==============================================================================
# [Module 1.00.00] System Core & Configuration Engine (환경 및 관제탑 설정)
# ==============================================================================

# ------------------------------------------------------------------------------
# 1.01.00 | Global Setup (라이브러리 임포트, 페이지 및 시간대 설정)
# ------------------------------------------------------------------------------
# 1.01.01 | Page Config, Timezone & Core Libraries (Latency Timer Started)
import time
t_render_start = time.perf_counter()  # ⏱️ 렌더링 속도 정밀 측정 시작점

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, timezone, date as dt_date
from streamlit_gsheets import GSheetsConnection
from streamlit_option_menu import option_menu
import requests
import base64
import re

# ⚙️ [Logic: Global Config] 기본 환경 및 KST 시간대 설정
st.set_page_config(page_title="Feelfree: 글로벌 여행 가계부", page_icon="🌏", layout="wide", initial_sidebar_state="expanded")
TZ_KST = timezone(timedelta(hours=9))

# ------------------------------------------------------------------------------
# 1.02.00 | Metadata & Constants Registry (매크로, 스키마, 시스템 상수)
# ------------------------------------------------------------------------------
# 1.02.01 | Macro Mapping Matrix (전역 교통/식음료/숙박/쇼핑 매핑)
MACRO_MAP = {
    "Grab": "🚗 교통", "VinBus": "🚗 교통", "DiDi": "🚗 교통", "지하철": "🚗 교통", 
    "택시": "🚗 교통", "버스": "🚗 교통", "트램": "🚗 교통", "기차": "🚗 교통", "렌트카": "🚗 교통", "교통": "🚗 교통",
    "식사": "🍔 식음료", "간식": "🍔 식음료", "마트": "🍔 식음료",
    "마사지": "🏄 액티비티", "투어": "🏄 액티비티", "입장료": "🏄 액티비티",
    "선물": "🎁 쇼핑", "통신": "📱 통신/기타", "수수료": "📱 통신/기타", "팁": "📱 통신/기타",
    "항공권": "✈️ 항공권", "호텔": "🏨 숙박", "보험": "🛡️ 보험", 
    "보증금": "🏦 자산이동", "재환전": "🏦 자산이동", "상환": "🏦 자산이동", "개인지출": "🏦 자산이동"
}
VERSION = "v26.05.28.005"

# 1.02.02 | Schema Column Definitions
CORE_COLUMNS = ['Date', 'Country', 'Category', 'Description', 'Currency', 'Amount', 'PaymentMethod', 'Receipt_URL']
SYSTEM_LOGIC_COLUMNS = ['IsExpense', 'AppliedRate', 'Cum_Budget_KRW', 'Cum_Card_Local', 'Cum_Cash_Local', 'Note']
FINAL_COLUMNS = CORE_COLUMNS + SYSTEM_LOGIC_COLUMNS

# 1.02.03 | Third-party Keys & Nominal Bills Configuration
IMGBB_API_KEY = "81181bf834001b6191aaa90fa772c6f9"
BILLS = [500000, 200000, 100000, 50000, 20000, 10000, 5000, 2000, 1000]

CONFIG_SHEET = "_GTL_CONFIG_"
CASH_SHEET = "_CASH_INVENTORY_"

UPDATE_LOG_TEXT = """* `[Refactored]` 🏛️ **x.yy.zz 블록 계층 구조 정밀 리팩토링**: 비대/미세 블록 분리 및 넘버링 무결성 전면 개편."""

conn = st.connection("gsheets", type=GSheetsConnection)

# ------------------------------------------------------------------------------
# 1.03.00 | Cloud Version Control System (구글 시트 버전 로그 갱신)
# ------------------------------------------------------------------------------
# 1.03.01 | Google Sheets Auto Version Logger (Session 1-Time Guard)
def auto_update_log_to_gsheets():
    # ⚡ 세션 중 이미 체크했다면 구글 시트 통신 즉시 건너뜀 (0ms)
    if st.session_state.get('v_logged') == VERSION:
        return
    for attempt in range(3):
        try:
            log_df = conn.read(worksheet="version_log", ttl="10m") 
            if log_df is None or log_df.empty: 
                log_df = pd.DataFrame(columns=["Version", "Date", "Log"])
            if VERSION not in log_df['Version'].values:
                new_log = pd.DataFrame([{
                    "Version": VERSION, 
                    "Date": datetime.now(TZ_KST).strftime("%Y-%m-%d %H:%M:%S"), 
                    "Log": UPDATE_LOG_TEXT
                }])
                log_df = pd.concat([new_log, log_df], ignore_index=True)
                conn.update(worksheet="version_log", data=log_df)
            st.session_state['v_logged'] = VERSION
            break
        except Exception as e:
            if attempt < 2 and ("429" in str(e) or "Quota" in str(e)):
                time.sleep(2)
                continue
            break

auto_update_log_to_gsheets()

# ------------------------------------------------------------------------------
# 1.04.00 | Dynamic Multi-Node Provisioning (관제탑 로드 및 다중 국가 동적 설정)
# ------------------------------------------------------------------------------
# 1.04.01 | Multi-Country Node Financial Parser (현지 통화 자동 추론 헬퍼)
def infer_node_info(c_name, def_c, def_s, def_t, def_m):
    c_upper = c_name.upper().replace(" ", "")
    if any(k in c_upper for k in ["튀르키예", "터키"]): return "TRY", "₺", 3, 1
    if any(k in c_upper for k in ["튀니지"]): return "TND", "د.ت", 1, 1
    if any(k in c_upper for k in ["그리스", "크루즈", "몬테네그로", "크로아티아", "이탈리아", "프랑스", "스페인", "독일"]): return "EUR", "€", def_t, 1
    if any(k in c_upper for k in ["세르비아"]): return "RSD", "din", 1, 1
    if any(k in c_upper for k in ["헝가리"]): return "HUF", "Ft", 1, 1
    if any(k in c_upper for k in ["싱가폴", "싱가포르"]): return "SGD", "S$", 8, 1
    if any(k in c_upper for k in ["인천", "한국", "KOREA"]): return "KRW", "₩", 9, 1
    if any(k in c_upper for k in ["중국", "CHINA"]): return "CNY", "¥", 8, 1
    if any(k in c_upper for k in ["필리핀", "CEBU"]): return "PHP", "₱", 8, 1
    if any(k in c_upper for k in ["베트남", "다낭", "푸꾸옥", "나트랑"]): return "VND", "₫", 7, 100
    if any(k in c_upper for k in ["미국", "달러", "글로벌"]): return "USD", "$", def_t, 1
    if any(k in c_upper for k in ["이스라엘", "ISRAEL"]): return "ILS", "₪", 2, 1
    if any(k in c_upper for k in ["사이프러스", "CYPRUS", "키프로스"]): return "EUR", "€", 2, 1
    return def_c, def_s, def_t, def_m

# 1.04.02 | Control Tower Config Loader & Node Assembler (Zero-Network Session Isolated)
def get_trip_configs():
    # ⚡ 세션 메모리에 이미 관제탑 설정이 있다면 구글 통신 완전 건너뜀 (0ms)
    if 'cached_trip_configs' in st.session_state and st.session_state.cached_trip_configs:
        return st.session_state.cached_trip_configs

    cfg_df = None
    for attempt in range(3):
        try:
            cfg_df = conn.read(worksheet=CONFIG_SHEET, ttl="10m")
            if cfg_df is not None and not cfg_df.empty:
                break
        except Exception as e:
            if attempt < 2 and ("429" in str(e) or "Quota" in str(e)):
                time.sleep(2.5)
                continue
            st.error(f"🚨 **관제탑 설정('{CONFIG_SHEET}') 로드 실패 (API 과부하).**")
            st.stop()
            
    if cfg_df is None or cfg_df.empty:
        st.error(f"🚨 **관제탑 설정('{CONFIG_SHEET}')이 비어있습니다.**")
        st.stop()
        
    dynamic_configs = {}
    for _, row in cfg_df.iterrows():
        raw_cats = str(row['Categories']).replace("，", ",").split(",") 
        cats = [c.strip() for c in raw_cats if c.strip()]
        
        travelers = int(row['Travelers']) if 'Travelers' in row and pd.notna(row['Travelers']) else 2
        stay_mapping = str(row['Stay_Mapping']).strip() if 'Stay_Mapping' in row and pd.notna(row['Stay_Mapping']) else ""
        
        main_country = str(row['MainCountry']).strip()
        main_curr = str(row['Currency']).strip().upper()
        main_sym = str(row['Symbol']).strip()
        main_tz = int(row['Timezone']) if pd.notna(row['Timezone']) else 9
        main_mult = int(row['Multiplier']) if pd.notna(row['Multiplier']) else 1
        
        nodes = {main_country: {
            "currency": main_curr,
            "symbol": main_sym, 
            "timezone": main_tz, 
            "multiplier": main_mult
        }}
        
        if stay_mapping:
            parts = stay_mapping.replace(" ", "").split(",")
            for p in parts:
                if ":" in p:
                    c_name = p.split(":")[0].strip()
                    if c_name and c_name not in nodes:
                        inf_c, inf_s, inf_t, inf_m = infer_node_info(c_name, main_curr, main_sym, main_tz, main_mult)
                        nodes[c_name] = {
                            "currency": inf_c,
                            "symbol": inf_s,
                            "timezone": inf_t,
                            "multiplier": inf_m
                        }
        
        dynamic_configs[str(row['TripName'])] = {
            "sheet": str(row['SheetName']),
            "nodes": nodes,
            "cats": cats,
            "travelers": travelers,
            "stay_mapping": stay_mapping
        }
    
    st.session_state.cached_trip_configs = dynamic_configs
    return dynamic_configs

TRIP_CONFIGS = get_trip_configs()

# ------------------------------------------------------------------------------
# 1.05.00 | GUI Design System (커스텀 다크/화이트 듀얼 테마 엔진)
# ------------------------------------------------------------------------------
# 1.05.01 | Base Layout & Slim KPI Box CSS
if 'app_theme' not in st.session_state:
    st.session_state.app_theme = "🌙 다크"

current_theme = st.session_state.app_theme
is_dark = (current_theme == "🌙 다크")

bg_main = "#0e1117" if is_dark else "#F8FAFC"
color_main = "#ffffff" if is_dark else "#0F172A"
kpi_bg = "#1e2130" if is_dark else "#FFFFFF"
kpi_border = "#FF8C00" if is_dark else "#F59E0B"
kpi_title_c = "#cccccc" if is_dark else "#64748B"
kpi_val_c = "#ffffff" if is_dark else "#0F172A"
kpi_vnd_c = "#FFA500" if is_dark else "#D97706"

st.markdown(f"""
    <script>var link=document.createElement('link'); link.rel='apple-touch-icon'; link.href='https://img.icons8.com/color/512/globe--v1.png'; document.getElementsByTagName('head')[0].appendChild(link);</script>
    <style>
    .block-container {{ padding-top: 3.5rem !important; padding-bottom: 2rem !important; padding-left: 0.8rem !important; padding-right: 0.8rem !important; }}
    div[data-testid="stSelectbox"] {{ margin-top: 0px !important; margin-bottom: 0px !important; }}
    hr {{ margin: 0.4rem 0 0.6rem 0 !important; }}
    
    h1 {{ 
        font-size: 26px !important; 
        white-space: nowrap !important; 
        overflow: hidden !important; 
        text-overflow: ellipsis !important;
        line-height: 1.2 !important;
        padding-top: 0rem !important; 
        margin-top: 0rem !important; 
        padding-bottom: 0.2rem !important; 
        margin-bottom: 0.8rem !important; 
    }}
    .main {{ background-color: {bg_main}; color: {color_main}; }}

    .kpi-box {{ background-color: {kpi_bg}; padding: 12px 14px; border-radius: 12px; border-left: 6px solid {kpi_border}; margin-bottom: 10px; min-height: 78px; box-shadow: 2px 4px 10px rgba(0,0,0,0.2); }}
    .kpi-title {{ font-size: 13px; color: {kpi_title_c}; margin-bottom: 3px; font-weight: 600; }}
    .kpi-value-krw {{ font-size: 20px; font-weight: bold; color: {kpi_val_c}; line-height: 1.15; }}
    .kpi-value-vnd {{ font-size: 14px; color: {kpi_vnd_c}; margin-top: 3px; font-family: 'Courier New', monospace; font-weight: 500; }}
    div[data-testid="stTable"] {{ border: 1px solid #444; border-radius: 10px; overflow: hidden; }}
    </style>
""", unsafe_allow_html=True)

# 1.05.02 | Sidebar & Form Controls CSS
sb_bg = "#1e2130" if is_dark else "#F1F5F9"
inp_bg = "#1e2130" if is_dark else "#FFFFFF"
inp_color = "#FFFFFF" if is_dark else "#0F172A"

st.markdown(f"""
    <style>
    div[data-testid="stSidebar"] div[data-baseweb="select"] > div {{ border: 2px solid #FFA500 !important; background-color: {sb_bg} !important; border-radius: 10px !important; }}
    div[data-testid="stSidebar"] .stSelectbox label {{ color: #FFA500 !important; font-weight: bold !important; }}
    div[data-baseweb="input"] {{ background-color: {inp_bg} !important; border: 1px solid #4B5563 !important; border-radius: 8px !important; }}
    div[data-baseweb="input"] input {{ color: {inp_color} !important; font-size: 14px !important; }}
    div[data-testid="stNumberInput"] button {{ display: none !important; }}
    div[data-testid="stNumberInput"] input {{ padding-right: 10px !important; }}
    section[data-testid="stSidebar"] > div:first-child {{ padding-top: 1rem !important; }}
    div[data-testid="stSidebarHeader"] {{ height: 35px !important; min-height: 35px !important; padding-top: 0px !important; }}
    </style>
""", unsafe_allow_html=True)

# 1.05.03 | Tab Navigation CSS (클릭 직관성 극대화: 슬레이트 뱃지 & 오렌지 활성 탭)
tab_bg_unselected = "#1E293B" if is_dark else "#E2E8F0"
tab_border_unselected = "#475569" if is_dark else "#CBD5E1"
tab_text_unselected = "#38BDF8" if is_dark else "#0284C7"

st.markdown(f"""
    <style>
    /* 1. 탭 리스트 컨테이너 */
    [data-baseweb="tab-list"] {{ 
        display: flex !important; 
        gap: 8px !important; 
        padding: 4px 2px !important; 
        background: transparent !important; 
        margin-bottom: 16px !important; 
        border: none !important;
        width: 100% !important;
    }}
    
    /* 2. 비활성 탭 버튼: 누를 수 있는 명확한 독립 슬레이트 뱃지 형태 */
    button[data-baseweb="tab"],
    [data-baseweb="tab"] {{ 
        flex: 1 1 0% !important; 
        height: 44px !important; 
        min-height: 44px !important;
        background-color: {tab_bg_unselected} !important; 
        border-radius: 10px !important; 
        border: 1.5px solid {tab_border_unselected} !important; 
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.25) !important;
        display: inline-flex !important; 
        align-items: center !important; 
        justify-content: center !important; 
        box-sizing: border-box !important;
        margin: 0px !important;
        cursor: pointer !important;
        padding: 0px !important;
        transition: all 0.2s ease-in-out !important;
    }}

    /* 3. 비활성 탭 마우스/터치 호버 반응 (클릭 가능한 버튼 피드백) */
    button[data-baseweb="tab"]:hover,
    [data-baseweb="tab"]:hover {{
        background-color: #334155 !important;
        border-color: #38BDF8 !important;
        box-shadow: 0 3px 8px rgba(56, 189, 248, 0.2) !important;
    }}
    
    /* 4. 비활성 탭 텍스트 폰트 & 컬러 */
    button[data-baseweb="tab"] p,
    [data-baseweb="tab"] p {{ 
        font-size: 15px !important; 
        font-weight: 600 !important; 
        color: {tab_text_unselected} !important; 
        margin: 0px !important; 
        letter-spacing: 0.2px !important;
        white-space: nowrap !important;
        transition: color 0.2s ease !important;
    }}
    button[data-baseweb="tab"]:hover p,
    [data-baseweb="tab"]:hover p {{
        color: #FFFFFF !important;
    }}
    
    /* 5. 선택된 활성 탭 (선명한 오렌지 뱃지) */
    button[data-baseweb="tab"][aria-selected="true"],
    [data-baseweb="tab"][aria-selected="true"],
    [aria-selected="true"] {{ 
        background: linear-gradient(135deg, #FF9E00 0%, #EA580C 100%) !important; 
        border: 1.5px solid #FFA500 !important; 
        box-shadow: 0 4px 14px rgba(255, 158, 0, 0.35) !important;
    }}
    button[data-baseweb="tab"][aria-selected="true"] p,
    [data-baseweb="tab"][aria-selected="true"] p,
    [aria-selected="true"] p {{ 
        color: #FFFFFF !important; 
        font-size: 15.5px !important; 
        font-weight: 800 !important; 
    }}
    
    /* 6. BaseWeb 기본 밑줄 제거 */
    [data-baseweb="tab-highlight"], 
    [data-baseweb="tab-border"] {{ 
        display: none !important; 
    }}

    /* 📱 7. 모바일 반응형 미디어 쿼리 (화면 폭 600px 이하 1줄 완벽 고정) */
    @media (max-width: 600px) {{
        [data-baseweb="tab-list"] {{ 
            gap: 4px !important; 
            padding: 0px !important;
            margin-bottom: 12px !important;
        }}
        button[data-baseweb="tab"],
        [data-baseweb="tab"] {{ 
            height: 38px !important; 
            min-height: 38px !important;
            border-radius: 8px !important;
            border-width: 1px !important;
            padding: 0px !important;
        }}
        button[data-baseweb="tab"] p,
        [data-baseweb="tab"] p {{ 
            font-size: 13.5px !important; 
            letter-spacing: -0.2px !important;
        }}
        button[data-baseweb="tab"][aria-selected="true"] p,
        [data-baseweb="tab"][aria-selected="true"] p,
        [aria-selected="true"] p {{ 
            font-size: 14px !important; 
        }}
    }}
    </style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# 1.06.00 | Session State Orchestrator (세션 상태 및 URL 파라미터 안전 복원)
# ------------------------------------------------------------------------------
# 1.06.01 | Chronological Sorter & Matcher Helper
def sort_trips(trip_names):
    return sorted(trip_names, key=lambda x: (re.search(r'\((\d{4})\)', x).group(1) if re.search(r'\((\d{4})\)', x) else '0000', x), reverse=True)

sorted_trips_initial = sort_trips(list(TRIP_CONFIGS.keys()))

def find_matching_trip(target_name):
    if not target_name: return None
    target_clean = str(target_name).replace("+", " ").strip()
    for k in TRIP_CONFIGS.keys():
        if k == target_clean or k.replace(" ", "") == target_clean.replace(" ", ""):
            return k
    return None

# 1.06.02 | Session Context Initialization
raw_query_trip = st.query_params.get("trip", None)
matched_query_trip = find_matching_trip(raw_query_trip)

if 'current_trip' not in st.session_state or st.session_state.current_trip not in TRIP_CONFIGS:
    if matched_query_trip:
        st.session_state.current_trip = matched_query_trip
    else:
        fukuoka_candidates = [t for t in sorted_trips_initial if "후쿠오카" in t or "FUKUOKA" in t.upper()]
        if fukuoka_candidates:
            st.session_state.current_trip = fukuoka_candidates[0]
        else:
            st.session_state.current_trip = sorted_trips_initial[0]
    st.query_params["trip"] = st.session_state.current_trip

ACTIVE_SHEET = TRIP_CONFIGS[st.session_state.current_trip]["sheet"]
FIRST_NODE_NAME = list(TRIP_CONFIGS[st.session_state.current_trip]["nodes"].keys())[0]
FIRST_NODE = TRIP_CONFIGS[st.session_state.current_trip]["nodes"][FIRST_NODE_NAME]
TRAVEL_CURRENCY = FIRST_NODE["currency"]
LOCAL_SYM = FIRST_NODE["symbol"]
MULTIPLIER = FIRST_NODE["multiplier"]
EXPENSE_CATS = TRIP_CONFIGS[st.session_state.current_trip]["cats"]
SURVIVAL_CATS = ["간식", "Grab", "DiDi", "VinBus", "지하철", "마사지", "팁", "식사", "교통"]
FIXED_COST_CATS = ["항공권", "호텔", "보험"]
DOMESTIC_CATS = ["항공권", "호텔", "보험", "지하철", "택시"]

if 'current_tz' not in st.session_state: st.session_state.current_tz = TZ_KST
if 'last_cat_name' not in st.session_state: st.session_state.last_cat_name = "식사"


# ==============================================================================
# [Module 2.00.00] Data Engine & Cloud Ledger Synchronizer (원장 연산 및 AI 엔진)
# ==============================================================================

# ------------------------------------------------------------------------------
# 2.01.00 | Classification & Fallback Utilities (자산 분류 및 기본 환율)
# ------------------------------------------------------------------------------
# 2.01.01 | Asset Class Classifier
def get_asset_class(text):    
    """결제 수단 명칭을 분석하여 자산 성격(CASH/PREPAID/CREDIT/DOMESTIC) 분류"""
    txt = str(text).replace(" ", "").upper()
    if any(k in txt for k in ["트래블", "로그", "월렛", "선불", "외화통장"]): 
        return "PREPAID"
    if any(k in txt for k in ["현금", "지폐", "CASH", "환전"]): 
        return "CASH"
    if any(k in txt for k in ["외상", "부채", "CREDIT"]):
        return "CREDIT" 
    return "DOMESTIC"

# 2.01.02 | Dynamic Default FX-Rate Estimator
def get_default_rate(curr):
    if curr == "KRW": return 1.0
    try:
        if 'ledger_df' in globals() and not ledger_df.empty:
            df_curr = ledger_df[(ledger_df['Currency'].str.strip() == curr) & (ledger_df['AppliedRate'] > 0)]
            if not df_curr.empty: return df_curr['AppliedRate'].mean()
    except: pass
    
    fallback_rates = {
        "VND": 0.056, "CNY": 190.0, "USD": 1350.0, "EUR": 1480.0, 
        "TRY": 45.0, "TND": 430.0, "SGD": 1000.0, "RSD": 12.6, "HUF": 3.8
    }
    return fallback_rates.get(curr, 1.0)

# ------------------------------------------------------------------------------
# 2.02.00 | Media & Vision AI Subsystem (멀티모달 및 바우처/영수증 파서)
# ------------------------------------------------------------------------------
# 2.02.01 | ImgBB Cloud Media Uploader
def upload_image_to_imgbb(image_file):
    try:
        if hasattr(image_file, "seek"):
            image_file.seek(0)
        img_bytes = image_file.getvalue() if hasattr(image_file, "getvalue") else image_file.read()
        if not img_bytes: return ""
        
        f_name = getattr(image_file, 'name', '').lower()
        if f_name.endswith('.pdf') or img_bytes.startswith(b"%PDF"):
            try:
                import fitz
                doc = fitz.open(stream=img_bytes, filetype="pdf")
                if len(doc) > 0:
                    pix = doc[0].get_pixmap(dpi=150)
                    img_bytes = pix.tobytes("png")
            except: pass
            
        payload = {"key": IMGBB_API_KEY, "image": base64.b64encode(img_bytes).decode("utf-8")}
        res = requests.post("https://api.imgbb.com/1/upload", data=payload, timeout=15)
        if res.status_code == 200: 
            time.sleep(0.2)
            return res.json()['data']['url']
    except: pass
    return ""

# 2.02.02 | PDF Text & Image Fallback Extractor
def extract_pdf_first_page_image(pdf_bytes):
    try:
        import fitz
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if len(doc) > 0:
            pix = doc[0].get_pixmap(dpi=150)
            return pix.tobytes("png")
    except: pass
    return None

def extract_full_text_from_pdf(pdf_bytes):
    text_content = ""
    try:
        import pypdf, io
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        pages_text = [page.extract_text() for page in reader.pages if page.extract_text()]
        text_content = "\n".join(pages_text).strip()
        if len(text_content) > 30: return text_content
    except: pass
    
    try:
        import fitz
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages_text = [page.get_text() for page in doc if page.get_text()]
        text_content = "\n".join(pages_text).strip()
    except: pass
    return text_content

# 2.02.03 | Gemini Multimodal Direct Runner
@st.cache_data(ttl=3600)
def get_cached_gemini_models(api_key):
    active_endpoints = []
    for ver in ['v1beta', 'v1']:
        try:
            list_url = f"https://generativelanguage.googleapis.com/{ver}/models?key={api_key}"
            resp_l = requests.get(list_url, timeout=3)
            if resp_l.status_code == 200:
                for m in resp_l.json().get('models', []):
                    if 'generateContent' in m.get('supportedGenerationMethods', []):
                        m_clean = m['name'].replace('models/', '')
                        if 'flash' in m_clean and 'exp' not in m_clean and 'preview' not in m_clean:
                            active_endpoints.append((ver, m_clean))
        except Exception:
            pass

    def sort_prio(item):
        v, name = item
        if name == 'gemini-1.5-flash' and v == 'v1beta': return 1
        if name == 'gemini-1.5-flash' and v == 'v1': return 2
        return 3

    active_endpoints.sort(key=sort_prio)
    return active_endpoints if active_endpoints else [('v1beta', 'gemini-1.5-flash')]

def call_gemini_multimodal(contents, prompt_text=""):
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if not api_key:
        return "", "Streamlit Secrets에 GEMINI_API_KEY가 없습니다."

    def compress_img_to_grayscale(b_data):
        try:
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(b_data))
            max_dim = 1000
            if max(img.size) > max_dim:
                ratio = max_dim / float(max(img.size))
                new_dim = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                img = img.resize(new_dim, Image.Resampling.LANCZOS)
            gray_img = img.convert('L')
            buf = io.BytesIO()
            gray_img.save(buf, format='JPEG', quality=70, optimize=True)
            return buf.getvalue()
        except Exception:
            pass
        return b_data

    rest_parts = []
    for item in contents:
        if isinstance(item, str):
            rest_parts.append({"text": item})
        elif isinstance(item, dict) and "data" in item:
            mime = item.get("mime_type", "image/jpeg")
            raw_b = item["data"]
            if not mime.endswith("pdf") and not raw_b.startswith(b"%PDF"):
                raw_b = compress_img_to_grayscale(raw_b)
                mime = "image/jpeg"
                
            b64_str = base64.b64encode(raw_b).decode("utf-8")
            rest_parts.append({"inline_data": {"mime_type": mime, "data": b64_str}})

    if prompt_text:
        rest_parts.append({"text": prompt_text})

    payload = {"contents": [{"parts": rest_parts}]}
    active_endpoints = get_cached_gemini_models(api_key)
    last_err = ""

    for api_ver, m_name in active_endpoints:
        try:
            url = f"https://generativelanguage.googleapis.com/{api_ver}/models/{m_name}:generateContent?key={api_key}"
            resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                cand = data.get("candidates", [])
                if cand:
                    parts = cand[0].get("content", {}).get("parts", [])
                    if parts and "text" in parts[0]:
                        return parts[0]["text"].strip(), ""
            else:
                last_err = f"[{m_name}] {resp.status_code}: {resp.text[:80]}"
        except Exception as e:
            last_err = f"[{m_name}] 에러: {e}"
            continue

    return "", last_err if last_err else "AI 서버 응답 없음"

# 2.02.04 | Gemini LLM Multi-Lingual Receipt Parser
def summarize_receipt_files_with_gemini(uploaded_files):
    import json
    if not uploaded_files: return "", "", 0.0

    prompt = """너는 다국어 영수증 전문 분석 AI야. 첨부된 영수증 사진/문서들을 분석하여 아래 JSON 포맷으로만 응답해.

[응답 JSON 스키마]:
{
    "store_name": "졸리마트 (Jolymart)",
    "payment_date": "2026-09-22",
    "total_amount": 478000,
    "items_text": "- 아치카페 연유 커피(Cà Phê Sữa Đặc Archcafe) 216g (1개) 76,000 VND\\n- 밀리케 쌀국수 면(Mì Giấy Miliket) 60g (1개) 5,000 VND\\n- 두리안 녹두 케이크(Bánh Đậu Xanh Sầu Riêng) 150g (1개) 52,000 VND"
}

[🔥 엄격한 추출 지침]:
1. store_name: 영수증 맨 위 상호명을 한글발음(원문) 형태로 추출해. (예: 졸리마트 (Jolymart), 카페 웃띡 (Út Tịch))
2. payment_date: 영수증의 실제 결제일/승인일자를 찾아 반드시 'YYYY-MM-DD'(예: 2026-09-22) 형식으로 출력해. 없으면 "".
3. total_amount: 영수증 맨 아래 실제 지불한 '최종 총 결제 금액(합계, Tổng cộng)'을 콤마 없는 순수 숫자로 추출해 (예: 478000). 품목들을 절대 임의로 더하지 말고 영수증에 인쇄된 총액 숫자를 그대로 적어.
4. items_text:
   - 영수증을 여러 장 나눠 찍어 겹치는 중복 품목은 1개만 남기고 중복을 반드시 제거해.
   - 품목명은 무조건 '자연스러운 한국어'가 맨 앞이어야 해. (예: - 한국어품목명(원문) 규격 수량 가격 통화)
   - 품목들을 줄바꿈(\\n)하여 나열해.
5. 다른 부연 설명이나 마크다운 백틱 없이 오직 '{' 로 시작해서 '}' 로 끝나는 순수 JSON 하나만 출력해.
"""
    contents = []
    for f in uploaded_files:
        try:
            if hasattr(f, "seek"): f.seek(0)
            f_bytes = f.getvalue() if hasattr(f, "getvalue") else f.read()
            if not f_bytes: continue
            f_name = getattr(f, "name", "").lower()
            mime = "application/pdf" if (f_name.endswith(".pdf") or f_bytes.startswith(b"%PDF")) else "image/jpeg"
            contents.append({"mime_type": mime, "data": f_bytes})
        except Exception:
            continue
            
    if not contents:
        return "", "", 0.0

    raw_res, err = call_gemini_multimodal(contents, prompt)
    if not raw_res:
        return "", "", 0.0

    try:
        cleaned = re.sub(r'```(?:json)?', '', raw_res).strip('` \n')
        first_brace = cleaned.find('{')
        last_brace = cleaned.rfind('}')
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            data = json.loads(cleaned[first_brace:last_brace + 1])
            store = data.get("store_name", "").strip()
            items = data.get("items_text", "").strip()
            full_desc = f"{store}\n{items}".strip() if store else items
            
            p_date = str(data.get("payment_date", "")).strip()
            tot_amt = clean_amount_to_float(data.get("total_amount", 0.0))
            return full_desc, p_date, tot_amt
    except Exception:
        pass

    return raw_res.strip(), "", 0.0

# 2.02.05 | Gemini Hotel Voucher Parser
def parse_hotel_voucher_files_with_gemini(uploaded_files):
    import json
    if not uploaded_files: 
        return {}, "첨부된 파일이 없습니다."
        
    prompt = """너는 아고다(Agoda), 부킹닷컴, 네이버페이 현금영수증 등 호텔 바우처 및 결제 영수증 전문 분석 AI야.
첨부된 문서(PDF/이미지)들을 종합 분석하여 아래 JSON 포맷으로만 응답해:

[응답 JSON 스키마]:
{
    "platform": "Agoda",
    "hotel_name": "호텔 이름 (예: 사누바 다낭 호텔 / Sanouva Danang Hotel)",
    "star_rating": "4성급",
    "room_area": 28,
    "has_balcony": "유",
    "cancel_deadline": "2026-09-25",
    "cancel_rate": 100,
    "payment_date": "2026-08-09",
    "checkin_date": "2026-09-21",
    "checkout_date": "2026-09-23",
    "nights": 2,
    "room_detail": "디럭스 트윈 시티뷰, 데일리 애프터눈티 포함",
    "payment_method": "네이버페이(원화고정)",
    "currency": "KRW",
    "amount": 118716
}

[🔥 엄격한 다차원 스펙 추출 지침]:
1. star_rating: 호텔 성급(예: 3성급, 4성급, 5성급, 부티크 등). 명시가 없으면 이름/숙소 특성으로 합리적 추론.
2. room_area: 객실 면적(㎡ 단위 숫자만. 예: 28㎡ -> 28, 35sqm -> 35). 문서에 없으면 0.
3. has_balcony: 발코니/테라스 유무 ('유' 또는 '무').
4. cancel_deadline: 무료 또는 부분 취소 마감 날짜 (반드시 YYYY-MM-DD 형식). 없으면 "".
5. cancel_rate: 위 마감일까지 취소 시 환불 비율 (숫자만. 100, 50, 60 등. 전액무료취소는 100, 환불불가는 0).
6. payment_date, checkin_date, checkout_date: 영문 월 표기라도 반드시 'YYYY-MM-DD' 숫자로 변환.
7. 확정 원화 우선: USD와 KRW가 병기되어 있거나 네이버페이 영수증이 있다면 확정 원화(KRW) 금액을 최우선 선택.
8. room_detail: '데일리 애프터눈티', '조식', '룸타입' 특징 요약.
9. 다른 설명 없이 오직 '{' 로 시작해서 '}' 로 끝나는 순수 JSON 하나만 출력해.
"""
    contents = []
    for f in uploaded_files:
        try:
            if hasattr(f, "seek"): f.seek(0)
            f_bytes = f.getvalue() if hasattr(f, "getvalue") else f.read()
            if not f_bytes: continue
            f_name = getattr(f, "name", "").lower()
            mime = "application/pdf" if (f_name.endswith(".pdf") or f_bytes.startswith(b"%PDF")) else "image/jpeg"
            contents.append({"mime_type": mime, "data": f_bytes})
        except: continue

    if not contents:
        return {}, "파일 바이트를 읽어들이지 못했습니다."

    raw_res, err = call_gemini_multimodal(contents, prompt)
    if not raw_res:
        return {}, err if err else "AI로부터 응답을 받지 못했습니다."

    try:
        cleaned = re.sub(r'```(?:json)?', '', raw_res).strip('` \n')
        first_brace = cleaned.find('{')
        last_brace = cleaned.rfind('}')
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            json_str = cleaned[first_brace:last_brace + 1]
            return json.loads(json_str), ""
    except Exception as parse_e:
        return {}, f"JSON 파싱 실패: {parse_e} | 원문: {raw_res[:80]}"

    return {}, f"유효한 JSON을 찾을 수 없습니다: {raw_res[:80]}"

# 2.02.06 | Gemini Flight e-Ticket Intelligent Structure Parser
def parse_flight_ticket_files_with_gemini(uploaded_files):
    import json
    if not uploaded_files: return {}
    prompt = """너는 항공권 e-티켓 및 결제 영수증 전문 분석 AI야.
첨부된 문서(PDF 또는 이미지) 전체를 종합 분석하여 다음 JSON 형식으로만 응답해:
{
    "platform": "예약처 (예: 트립닷컴, 네이버항공, 마이리얼트립 등)",
    "carrier": "항공사 이름 (예: 비엣젯항공, 에어부산 등)",
    "route": "노선 도시명 (예: 부산-다낭, 인천-싱가폴-이스탄불)",
    "trip_type": "왕복 또는 편도",
    "payment_date": "결제일 또는 발권일 (YYYY-MM-DD 형식. 예: 2026-08-09)",
    "dep_info": "출국/탑승 편명 및 시각 (예: VJ969, 07:45 - 11:10)",
    "dep_date": "출국/탑승 날짜 (YYYY-MM-DD 형식)",
    "ret_info": "귀국 편명 및 시각 (예: VJ968, 23:10 - 06:40)",
    "ret_date": "귀국 날짜 (YYYY-MM-DD 형식)",
    "baggage": "위탁수화물 (포함, 미포함, 일부포함 중 선택)",
    "bag_memo": "수화물 무게 상세 (예: 20kg 무료)",
    "payment_method": "결제수단 추론 (네이버페이, 원화계좌, 트래블카드 등)",
    "currency": "실제 결제된 통화 코드 (KRW, USD, EUR 등)",
    "amount": "결제 총 금액 (콤마 없는 순수 숫자)"
}
지침:
1. 네이버페이/카드 영수증이 있다면 실제 결제된 확정 원화(KRW) 금액을 우선 채워.
2. 부연 설명 없이 오직 순수 JSON 텍스트 하나만 출력해.
"""
    contents = []
    for f in uploaded_files:
        try:
            if hasattr(f, "seek"): f.seek(0)
            f_bytes = f.getvalue() if hasattr(f, "getvalue") else f.read()
            if not f_bytes: continue
            f_name = getattr(f, "name", "").lower()
            mime = "application/pdf" if (f_name.endswith(".pdf") or f_bytes.startswith(b"%PDF")) else "image/jpeg"
            contents.append({"mime_type": mime, "data": f_bytes})
        except Exception:
            continue
            
    if not contents:
        return {}

    raw_res, err = call_gemini_multimodal(contents, prompt)
    if raw_res:
        cleaned = re.sub(r'```(?:json)?\s*', '', raw_res).strip('` \n')
        first_brace = cleaned.find('{')
        last_brace = cleaned.rfind('}')
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            try:
                return json.loads(cleaned[first_brace:last_brace + 1])
            except Exception:
                pass
    return {}

# ------------------------------------------------------------------------------
# 2.03.00 | Data Cleansing & ETL Pipeline (데이터 정규화, 로드, 캐시 제어)
# ------------------------------------------------------------------------------
# 2.03.01 | Date Format Normalizer & Clean Utilities
def normalize_date(d_str):
    d_str = str(d_str).strip()
    if re.match(r'^\d{4}-\d{2}-\d{2}', d_str): return d_str
    match = re.match(r'^(?:20)?(\d{2})[\.\-\/]\s*(\d{1,2})[\.\-\/]\s*(\d{1,2})\.?$', d_str)
    if match:
        y, m, d = match.groups()
        dt_obj = datetime.strptime(f"20{y}-{int(m):02d}-{int(d):02d}", "%Y-%m-%d")
        return dt_obj.strftime("%Y-%m-%d(%a)")
    return d_str

def clean_amount_to_float(val):
    if val is None: return 0.0
    if isinstance(val, (int, float)): return float(val)
    cleaned = re.sub(r'[^\d\.]', '', str(val).replace(',', ''))
    try: return float(cleaned) if cleaned else 0.0
    except: return 0.0

# 2.03.02 | Active Trip Ledger Loader (Zero-Network Pure Memory First)
def load_data(sheet_name, force_cloud=False):
    # ⚡ 세션 메모리에 해당 시트 데이터가 이미 존재하면 구글 통신 0회 즉시 반환
    if not force_cloud and 'active_ledger_df' in st.session_state and st.session_state.get('last_loaded_sheet') == sheet_name:
        if st.session_state.active_ledger_df is not None and not st.session_state.active_ledger_df.empty:
            return st.session_state.active_ledger_df

    df = None
    for attempt in range(3):
        try:
            df = conn.read(worksheet=sheet_name, ttl="10m")
            break
        except Exception as e:
            if attempt < 2 and ("429" in str(e) or "Quota" in str(e)):
                time.sleep(2)
                continue
            st.error(f"🚨 **치명적 오류:** 클라우드 데이터베이스 연결에 실패했습니다. ({e})")
            st.stop()

    if df is None or df.empty:
        df_init = pd.DataFrame(columns=FINAL_COLUMNS)
        try:
            conn.update(worksheet=ACTIVE_SHEET, data=df_init)
        except:
            pass
        return df_init

    year_match = re.search(r'\((\d{4})\)', st.session_state.get('current_trip', ''))
    trip_year = year_match.group(1) if year_match else "2026"

    first_node_curr = FIRST_NODE_NAME if 'FIRST_NODE_NAME' in globals() else "베트남"

    if 'Country' not in df.columns:
        df.insert(1, 'Country', first_node_curr)
    else:
        df['Country'] = df['Country'].astype(str).str.strip().replace(['nan', 'None', ''], None)
        df['Country'] = df['Country'].fillna(first_node_curr)

    if 'Cum_Card_VND' in df.columns:
        df.rename(columns={'Cum_Card_VND': 'Cum_Card_Local'}, inplace=True)

    if 'Cum_Cash_VND' in df.columns:
        df.rename(columns={'Cum_Cash_VND': 'Cum_Cash_Local'}, inplace=True)

    if 'Receipt_URL' not in df.columns:
        df['Receipt_URL'] = ""

    df = df.dropna(subset=['Date', 'Category'], how='any')
    df['Category'] = df['Category'].astype(str).str.strip()
    df['PaymentMethod'] = df['PaymentMethod'].astype(str).str.strip().str.replace('트래블로그', '트래블카드')
    df['Currency'] = df['Currency'].astype(str).str.strip().str.upper()

    def fix_legacy_date(d):
        d = str(d).strip()
        if d and not re.match(r'^\d{4}', d):
            return f"{trip_year}-{d.replace('/', '-')}"
        return d

    df['Date'] = df['Date'].apply(fix_legacy_date)
    df['Date'] = df['Date'].apply(normalize_date)
    df = df.reindex(columns=FINAL_COLUMNS)

    numeric_cols = [
        'Amount',
        'AppliedRate',
        'Cum_Budget_KRW',
        'Cum_Card_Local',
        'Cum_Cash_Local'
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

    # ------------------------------------------------------------------
    # 🛡️ IsExpense 판정
    # - 실제 결제가 발생한 일반 지출은 1
    # - 호텔외상(CREDIT)은 아직 실제 결제가 아니므로 0
    # - 상환은 실제 결제가 발생한 것이므로 1
    # ------------------------------------------------------------------
    clean_expense_cats = list(
        set([c.strip() for c in EXPENSE_CATS] + ['선물', '상환'])
    ) if 'EXPENSE_CATS' in globals() else ['식사', '간식', '마트', '선물', '상환']

    def evaluate_is_expense(r):
        cat = str(r['Category']).strip()
        method = str(r['PaymentMethod']).strip()

        # 호텔외상/외상 등 신용성 결제는 실제 지출 시점이 아니므로 제외
        if get_asset_class(method) == "CREDIT":
            return 0

        # 실제 결제된 지출
        if cat in clean_expense_cats and cat not in ['환불', '보증금', '재환전', '개인지출']:
            return 1

        return 0

    df['IsExpense'] = df.apply(evaluate_is_expense, axis=1)

    df['Note'] = df['Note'].fillna("").astype(str)
    df['Receipt_URL'] = df['Receipt_URL'].fillna("").astype(str)

    st.session_state.active_ledger_df = df
    st.session_state.last_loaded_sheet = sheet_name

    return df

# 2.03.03 | Multi-Trip Global Ledger Consolidator
@st.cache_data(ttl=600, show_spinner=False)
def _load_all_trips_data_cloud():
    """
    🌍 모든 여행가계부 원본 데이터의 Streamlit 캐시 계층.
    - Google Sheets 접근은 여기에서만 수행
    - 동일 프로세스 내 반복 조회는 cache_data가 흡수
    """
    all_dfs = []

    for trip_name, config in TRIP_CONFIGS.items():
        for attempt in range(3):
            try:
                df_t = conn.read(
                    worksheet=config['sheet'],
                    ttl="10m"
                )

                if df_t is not None and not df_t.empty:
                    df_t = df_t.copy()
                    df_t['TripName'] = trip_name

                    first_node_name = list(config["nodes"].keys())[0]

                    if 'Country' not in df_t.columns:
                        df_t.insert(1, 'Country', first_node_name)
                    else:
                        df_t['Country'] = (
                            df_t['Country']
                            .astype(str)
                            .str.strip()
                            .fillna(first_node_name)
                        )

                    all_dfs.append(df_t)

                break

            except Exception as e:
                if attempt < 2 and ("429" in str(e) or "Quota" in str(e)):
                    time.sleep(1.5)
                    continue

                break

    if not all_dfs:
        return pd.DataFrame(columns=FINAL_COLUMNS + ['TripName'])

    return pd.concat(all_dfs, ignore_index=True)


def load_all_trips_data(force_cloud=False):
    """
    🌍 모든 여행가계부 조회 전용 메모리 캐시.

    조회 순서:
        1. session_state
        2. Streamlit cache_data
        3. Google Sheets

    일반적인 화면 조회에서는 Google Sheets를 직접 읽지 않는다.
    """

    cache_key = 'all_trips_lookup_df'

    # ① 세션 메모리 우선
    if not force_cloud:
        cached_df = st.session_state.get(cache_key)

        if cached_df is not None:
            return cached_df

    # ② Streamlit cache_data
    df = _load_all_trips_data_cloud()

    if df is None:
        df = pd.DataFrame(columns=FINAL_COLUMNS + ['TripName'])

    # ③ 세션 메모리에 바인딩
    st.session_state[cache_key] = df

    return df


# 2.03.04 | Precision Cloud Cache Cleaner
def smart_cache_clear():
    """
    🔄 저장/수정 이후 조회 캐시를 정확하게 무효화한다.

    주의:
    일반 조회에서는 절대로 호출하지 않는다.
    데이터가 실제로 변경된 경우에만 호출한다.
    """

    # 현재 여행가계부 메모리 캐시
    if 'active_ledger_df' in st.session_state:
        del st.session_state['active_ledger_df']

    # 현금 재고 캐시
    if 'cached_cash_df' in st.session_state:
        del st.session_state['cached_cash_df']

    # 전체 여행 조회 캐시
    if 'all_trips_lookup_df' in st.session_state:
        del st.session_state['all_trips_lookup_df']

    # Streamlit의 전체 여행 원본 캐시
    try:
        _load_all_trips_data_cloud.clear()
    except Exception:
        pass


# ------------------------------------------------------------------------------
# 2.04.00 | Core Ledger Engine (FIFO 인벤토리 배치 및 금융 재계산)
# ------------------------------------------------------------------------------
# 2.04.01 | Full Ledger FIFO / Rate / Cumulative Engine
def recalculate_entire_ledger(df):
    temp_df = df.copy()
    temp_df = temp_df.sort_values(by='Date', kind='mergesort', ignore_index=True)

    clean_expense_cats = list(
        set([c.strip() for c in EXPENSE_CATS] + ['선물', '상환'])
    )

    for i, row in temp_df.iterrows():
        cat = str(row['Category']).strip()
        method = str(row['PaymentMethod']).strip()
        asset_cls = get_asset_class(method)

        if (
            cat in clean_expense_cats
            and cat not in ['보증금', '재환전', '개인지출']
            and asset_cls != "DOMESTIC"
        ):
            temp_df.at[i, 'AppliedRate'] = 0.0

        temp_df.at[i, 'Note'] = ""
        temp_df.at[i, 'Cum_Budget_KRW'] = 0.0
        temp_df.at[i, 'Cum_Card_Local'] = 0.0
        temp_df.at[i, 'Cum_Cash_Local'] = 0.0

    from collections import defaultdict

    inv_batches = defaultdict(list)
    c_budget = 0.0

    for i, row in temp_df.iterrows():
        qty, curr = row['Amount'], row['Currency']
        cat = str(row['Category']).strip()
        method = str(row['PaymentMethod']).strip()
        desc = str(row['Description']).strip()

        asset_cls = get_asset_class(method)

        # ------------------------------------------------------------------
        # 🛡️ IsExpense 판정
        # 호텔외상(CREDIT)은 실제 결제가 아니므로 0
        # 상환은 실제 결제가 발생하므로 1
        # ------------------------------------------------------------------
        if asset_cls == "CREDIT":
            is_exp = 0
        elif cat in clean_expense_cats and cat not in [
            '환불',
            '보증금',
            '재환전',
            '개인지출'
        ]:
            is_exp = 1
        else:
            is_exp = 0

        temp_df.at[i, 'IsExpense'] = is_exp

        is_deductible = 1 if (is_exp == 1 or cat in ['보증금']) else 0

        rate = temp_df.at[i, 'AppliedRate']

        if cat in ['충전', '환전', '입금', '직접환전', '이월잔액']:
            if curr != 'KRW' and (pd.isna(rate) or rate <= 0.0 or rate == 1.0):
                rate = get_default_rate(curr)

            if cat == '이월잔액':
                final_dest_cls = "CASH"
            elif cat == '충전':
                final_dest_cls = "PREPAID"
            elif cat in ['환전', '직접환전']:
                final_dest_cls = "CASH"
            else:
                final_dest_cls = get_asset_class(desc + method)

            target = f"트래블카드({curr})" if final_dest_cls == "PREPAID" else f"현금({curr})"

            if curr != 'KRW':
                inv_batches[target].append({'rate': rate, 'qty': qty})

            if asset_cls == "DOMESTIC" or cat == '충전' or cat == '이월잔액':
                c_budget += qty if curr == 'KRW' else qty * rate

        elif cat == '환불':
            if curr != 'KRW' and (pd.isna(rate) or rate <= 1.0):
                inherited_rate = None

                for j in range(i - 1, -1, -1):
                    prev_cat = str(temp_df.at[j, 'Category']).strip()
                    prev_curr = str(temp_df.at[j, 'Currency']).strip()

                    if prev_cat == '보증금' and prev_curr == curr:
                        inherited_rate = temp_df.at[j, 'AppliedRate']
                        break

                if inherited_rate and inherited_rate > 0:
                    rate = inherited_rate
                    temp_df.at[i, 'Note'] = f"Inherited Deposit Rate: {rate:.9f}"
                else:
                    rate = get_default_rate(curr)

            is_dep = str(row['Description']).replace(" ", "").lower()
            is_deposit_refund = any(
                k in is_dep for k in ["보증금", "deposit"]
            )

            if not is_deposit_refund:
                c_budget -= qty if curr == 'KRW' else qty * rate

                if asset_cls != "DOMESTIC":
                    target = (
                        f"트래블카드({curr})"
                        if asset_cls == "PREPAID"
                        else f"현금({curr})"
                    )

                    if curr != 'KRW':
                        inv_batches[target].append({
                            'rate': rate,
                            'qty': qty
                        })
            else:
                if asset_cls == "DOMESTIC":
                    c_budget -= qty if curr == 'KRW' else qty * rate
                else:
                    target = (
                        f"트래블카드({curr})"
                        if asset_cls == "PREPAID"
                        else f"현금({curr})"
                    )

                    if curr != 'KRW':
                        inv_batches[target].append({
                            'rate': rate,
                            'qty': qty
                        })

        elif cat in ['재환전', '개인지출']:
            if curr != 'KRW':
                target_from = (
                    f"트래블카드({curr})"
                    if asset_cls == "PREPAID"
                    else f"현금({curr})"
                )

                temp_qty = qty

                if target_from in inv_batches:
                    for batch in inv_batches[target_from]:
                        if temp_qty <= 0:
                            break
                        if batch['qty'] <= 0:
                            continue

                        take = min(temp_qty, batch['qty'])
                        batch['qty'] -= take
                        temp_qty -= take

                if pd.notna(rate) and rate > 0:
                    c_budget -= qty * rate

        elif cat == '이종환전':
            if curr != 'KRW':
                target_from = (
                    f"트래블카드({curr})"
                    if asset_cls == "PREPAID"
                    else f"현금({curr})"
                )

                temp_qty = qty

                if target_from in inv_batches:
                    for batch in inv_batches[target_from]:
                        if temp_qty <= 0:
                            break
                        if batch['qty'] <= 0:
                            continue

                        take = min(temp_qty, batch['qty'])
                        batch['qty'] -= take
                        temp_qty -= take

        elif cat == 'ATM출금':
            temp_qty = qty
            total_inherited_krw = 0.0

            target_from = f"트래블카드({curr})"
            target_to = f"현금({curr})"

            if target_from in inv_batches:
                for batch in inv_batches[target_from]:
                    if temp_qty <= 0:
                        break
                    if batch['qty'] <= 0:
                        continue

                    take = min(temp_qty, batch['qty'])
                    batch['qty'] -= take

                    inv_batches[target_to].append({
                        'rate': batch['rate'],
                        'qty': take
                    })

                    total_inherited_krw += take * batch['rate']
                    temp_qty -= take

            if temp_qty > 0:
                fallback_r = get_WAR(curr)

                inv_batches[target_to].append({
                    'rate': fallback_r,
                    'qty': temp_qty
                })

                total_inherited_krw += temp_qty * fallback_r

            if qty > 0:
                rate = (
                    total_inherited_krw / qty
                    if total_inherited_krw > 0
                    else get_default_rate(curr)
                )

        elif is_deductible == 1 or cat == '상환':
            if asset_cls == "DOMESTIC":
                if curr != 'KRW' and (pd.isna(rate) or rate <= 0.0):
                    rate = get_default_rate(curr)

                c_budget += qty if curr == 'KRW' else qty * rate
                rate = 1.0 if curr == 'KRW' else rate

            elif curr != 'KRW':
                if asset_cls == "CREDIT":
                    rate = get_WAR(curr)
                    temp_df.at[i, 'Note'] = "Credit (Debt Generated)"

                else:
                    target = (
                        f"트래블카드({curr})"
                        if asset_cls == "PREPAID"
                        else f"현금({curr})"
                    )

                    temp_qty = qty
                    total_cost_krw = 0.0
                    decomposed = []

                    if target in inv_batches:
                        for batch in inv_batches[target]:
                            if temp_qty <= 0:
                                break
                            if batch['qty'] <= 0:
                                continue

                            take = min(temp_qty, batch['qty'])
                            batch['qty'] -= take
                            temp_qty -= take

                            total_cost_krw += take * batch['rate']

                            r_prec = ".4f" if curr in ["VND", "HUF", "PHP"] else ".2f"
                            q_fmt = ",.0f" if curr in ["VND", "HUF"] else ",.2f"

                            decomposed.append(
                                f"{take:{q_fmt}}@{batch['rate']:{r_prec}}"
                            )

                    if temp_qty > 0:
                        fallback_r = get_WAR(curr)
                        total_cost_krw += temp_qty * fallback_r

                        r_prec = ".4f" if curr in ["VND", "HUF", "PHP"] else ".2f"
                        q_fmt = ",.0f" if curr in ["VND", "HUF"] else ",.2f"

                        decomposed.append(
                            f"{temp_qty:{q_fmt}}@{fallback_r:{r_prec}}(Auto-Topup?)"
                        )

                    if qty > 0:
                        rate = total_cost_krw / qty

                        if decomposed:
                            temp_df.at[i, 'Note'] = (
                                "Decomposed: " + " + ".join(decomposed)
                            )
                    else:
                        rate = 0.0

        row_country = temp_df.at[i, 'Country']
        nodes = TRIP_CONFIGS[
            st.session_state.current_trip
        ].get("nodes", {})

        row_curr = (
            nodes.get(row_country, FIRST_NODE)["currency"]
            if nodes
            else "USD"
        )

        active_curr = curr if curr != 'KRW' else row_curr

        rnd_dec = (
            0
            if active_curr in ["VND", "HUF", "KRW"]
            else 2
        )

        temp_df.at[i, 'AppliedRate'] = rate
        temp_df.at[i, 'Cum_Budget_KRW'] = round(c_budget, 2)

        temp_df.at[i, 'Cum_Card_Local'] = round(
            sum(
                [b['qty'] for b in inv_batches[
                    f"트래블카드({active_curr})"
                ]]
            ),
            rnd_dec
        )

        temp_df.at[i, 'Cum_Cash_Local'] = round(
            sum(
                [b['qty'] for b in inv_batches[
                    f"현금({active_curr})"
                ]]
            ),
            rnd_dec
        )

    return temp_df

# ------------------------------------------------------------------------------
# 2.05.00 | Cloud Persistence & Inventory Synchronization (클라우드 동기화 및 가드)
# ------------------------------------------------------------------------------
# 2.05.01 | Memory Mutation & Dirty-State Manager
LEDGER_BACKUP_INTERVAL_SECONDS = 180  # 3분

def mark_ledger_dirty():
    """원장 변경을 메모리에만 반영했음을 표시한다. Google Sheets에는 접근하지 않는다."""
    st.session_state['ledger_dirty'] = True
    st.session_state['ledger_mutation_count'] = int(st.session_state.get('ledger_mutation_count', 0)) + 1
    st.session_state['ledger_order_dirty'] = True


def _invalidate_post_commit_lookup_caches():
    """정식 저장 후 다른 화면의 조회 캐시만 무효화한다. active_ledger_df는 유지한다."""
    st.session_state.pop('all_trips_lookup_df', None)
    for fn_name in ['_load_all_trips_data_cloud', 'load_all_trips_data']:
        try:
            fn = globals().get(fn_name)
            if fn is not None and hasattr(fn, 'clear'):
                fn.clear()
        except Exception:
            pass


def save_data(df, metrics=None):
    """
    기존 save_data의 이름은 유지하되, 이제는 '메모리 저장'만 담당한다.
    Google Sheets 저장은 commit_ledger_to_cloud()에서 한 번에 수행한다.
    """
    if df is None or df.empty:
        st.error("🚨 저장하려는 데이터가 비어있습니다. 데이터 보호를 위해 저장을 중단합니다.")
        return False

    final_df = recalculate_entire_ledger(df)
    st.session_state.active_ledger_df = final_df
    st.session_state.last_loaded_sheet = ACTIVE_SHEET
    mark_ledger_dirty()
    return True


# 2.05.02 | Atomic Ledger Appender (Memory-First)
def append_new_data(new_rows_df):
    """새 내역을 active_ledger_df에 추가하고 전체 정합성을 메모리에서 계산한다."""
    if new_rows_df is None or new_rows_df.empty:
        return False

    latest_df = st.session_state.get('active_ledger_df')
    if latest_df is None:
        latest_df = load_data(ACTIVE_SHEET)

    merged_df = pd.concat([latest_df, new_rows_df], ignore_index=True)
    final_df = recalculate_entire_ledger(merged_df)
    st.session_state.active_ledger_df = final_df
    st.session_state.last_loaded_sheet = ACTIVE_SHEET
    mark_ledger_dirty()
    return True


# 2.05.03 | Quick Order Swap Committer (Memory-First)
def quick_swap_and_save(df):
    """기존 호출부 호환용. 실제 클라우드 저장은 하지 않고 메모리만 갱신한다."""
    try:
        if df is None or len(df) < 1:
            return False
        final_df = recalculate_entire_ledger(df)
        st.session_state.active_ledger_df = final_df
        st.session_state.last_loaded_sheet = ACTIVE_SHEET
        mark_ledger_dirty()
        return True
    except Exception as e:
        st.error(f"🚨 메모리 순서 변경 실패: {e}")
        return False


# 2.05.03A | Explicit Cloud Committer (Single Final Save)
def commit_ledger_to_cloud():
    """현재 메모리 원장을 최종 계산한 뒤 Google Sheets에 단 한 번 확정 저장한다."""
    df = st.session_state.get('active_ledger_df')
    if df is None or df.empty:
        st.error("🚨 저장할 원장 데이터가 없습니다.")
        return False

    # 기존 Anti-Wipe 보호장치는 '최종 저장'에서만 실행한다.
    existing_df = None
    for attempt in range(3):
        try:
            existing_df = conn.read(worksheet=ACTIVE_SHEET, ttl="0s")
            break
        except Exception as e:
            if attempt < 2 and ("429" in str(e) or "Quota" in str(e)):
                time.sleep(2)
                continue
            st.error(f"🚨 클라우드 상태 확인 실패! 안전을 위해 최종 저장을 중단합니다. ({e})")
            return False

    if existing_df is not None and len(existing_df) > 5 and len(df) <= 3:
        st.error(
            f"🚨 **치명적 데이터 증발(Wipe) 시도 차단됨!** "
            f"(클라우드: {len(existing_df)}건 -> 저장시도: {len(df)}건)"
        )
        return False

    final_df = recalculate_entire_ledger(df).reindex(columns=FINAL_COLUMNS).copy()

    for attempt in range(3):
        try:
            conn.update(worksheet=ACTIVE_SHEET, data=final_df)
            st.session_state.active_ledger_df = final_df
            st.session_state.last_loaded_sheet = ACTIVE_SHEET
            st.session_state['ledger_dirty'] = False
            st.session_state['ledger_order_dirty'] = False
            st.session_state['ledger_mutation_count'] = 0
            st.session_state['last_cloud_commit_at'] = datetime.now(TZ_KST).strftime("%Y-%m-%d %H:%M:%S")
            _invalidate_post_commit_lookup_caches()
            return True
        except Exception as e:
            if attempt < 2 and ("429" in str(e) or "Quota" in str(e)):
                time.sleep(2.5)
                continue
            st.error(f"🚨 Google Sheets 최종 저장 실패: {e}")
            return False


# 2.05.04 | Cash Inventory Cloud Loader & Saver (Memory-First)
# 2.05.04 | Cash Inventory Cloud Loader & Saver (Memory-First)
def load_cash_inventory(force_cloud=False):
    # ⚡ 세션 메모리에 이미 있으면 구글 통신 0회 즉시 반환
    if not force_cloud and 'cached_cash_df' in st.session_state and st.session_state.cached_cash_df is not None:
        return st.session_state.cached_cash_df

    for attempt in range(3):
        try:
            df = conn.read(worksheet=CASH_SHEET, ttl="10m")
            if df is not None and not df.empty:
                st.session_state.cached_cash_df = df
                return df
            break
        except Exception as e:
            if attempt < 2 and ("429" in str(e) or "Quota" in str(e)):
                time.sleep(1.5)
                continue
            break
    empty_df = pd.DataFrame(columns=['TripName', 'Currency', 'Bill_Counts', 'Total_Amount', 'Updated_At'])
    st.session_state.cached_cash_df = empty_df
    return empty_df

def save_cash_inventory(trip_name, currency, counts_dict, total_amt):
    try:
        df = load_cash_inventory(force_cloud=True)
        if df is None or df.empty:
            df = pd.DataFrame(columns=['TripName', 'Currency', 'Bill_Counts', 'Total_Amount', 'Updated_At'])
            
        counts_str = ";".join([f"{k}:{v}" for k, v in counts_dict.items()])
        now_str = datetime.now(TZ_KST).strftime("%Y-%m-%d %H:%M:%S")
        
        mask = (df['TripName'] == trip_name) & (df['Currency'] == currency)
        if mask.any():
            idx = df[mask].index[0]
            df.at[idx, 'Bill_Counts'] = counts_str
            df.at[idx, 'Total_Amount'] = total_amt
            df.at[idx, 'Updated_At'] = now_str
        else:
            new_row = pd.DataFrame([{
                'TripName': trip_name,
                'Currency': currency,
                'Bill_Counts': counts_str,
                'Total_Amount': total_amt,
                'Updated_At': now_str
            }])
            df = pd.concat([df, new_row], ignore_index=True)
            
        conn.update(worksheet=CASH_SHEET, data=df)
        st.session_state.cached_cash_df = df
        return True
    except Exception as e:
        st.error(f"🚨 지폐 실사 동기화 실패: {e}")
        return False


# 2.05.05 | Ledger Auto-Backup & Recovery Guard
AUTO_BACKUP_PREFIX = "AUTO_BACKUP_"


def _backup_sheet_name(sheet_name):
    safe = re.sub(r"[^0-9A-Za-z가-힣_-]+", "_", str(sheet_name)).strip("_")
    return (AUTO_BACKUP_PREFIX + safe)[:90]


def _trip_name_for_sheet(sheet_name):
    for trip_name, config in TRIP_CONFIGS.items():
        if str(config.get('sheet')) == str(sheet_name):
            return trip_name
    return str(sheet_name)


def _write_auto_backup_snapshot(df, sheet_name=None, trip_name=None):
    """현재 메모리 원장을 별도 AUTO_BACKUP worksheet에 스냅샷으로 저장한다."""
    if df is None or df.empty:
        return False

    target_sheet = str(sheet_name or ACTIVE_SHEET)
    target_trip = str(trip_name or _trip_name_for_sheet(target_sheet))
    backup_sheet = _backup_sheet_name(target_sheet)
    backup_time = datetime.now(TZ_KST).strftime("%Y-%m-%d %H:%M:%S")

    snapshot = df.reindex(columns=FINAL_COLUMNS).copy()
    snapshot.insert(0, 'BackupTime', backup_time)
    snapshot.insert(1, 'ActiveSheet', target_sheet)
    snapshot.insert(2, 'TripName', target_trip)
    snapshot.insert(3, 'RowCount', len(df))

    try:
        try:
            conn.update(worksheet=backup_sheet, data=snapshot)
        except Exception as e_update:
            msg = str(e_update).lower()
            if 'not found' in msg or 'worksheet' in msg and ('404' in msg or 'does not exist' in msg):
                conn.create(worksheet=backup_sheet, data=snapshot)
            else:
                raise
        return True
    except Exception as e:
        st.session_state['last_auto_backup_error'] = str(e)
        return False


def backup_active_ledger_to_cloud():
    """현재 메모리 원장의 자동 백업을 즉시 실행한다. 정식 원장은 변경하지 않는다."""
    df = st.session_state.get('active_ledger_df')
    if df is None or df.empty:
        return False

    ok = _write_auto_backup_snapshot(df)
    if ok:
        now_str = datetime.now(TZ_KST).strftime("%Y-%m-%d %H:%M:%S")
        st.session_state['last_auto_backup_at'] = now_str
        st.session_state['last_auto_backup_sheet'] = ACTIVE_SHEET
        st.session_state['last_auto_backup_error'] = ''
    return ok


def restore_auto_backup_from_cloud():
    """현재 여행의 AUTO_BACKUP 스냅샷을 메모리로 복원한다. 복원 후에는 다시 최종 저장이 필요하다."""
    backup_sheet = _backup_sheet_name(ACTIVE_SHEET)
    try:
        backup_df = conn.read(worksheet=backup_sheet, ttl="0s")
        if backup_df is None or backup_df.empty:
            st.error("🛡️ 복원할 자동 백업이 없습니다.")
            return False

        backup_df = backup_df[backup_df['ActiveSheet'].astype(str) == str(ACTIVE_SHEET)].copy() if 'ActiveSheet' in backup_df.columns else backup_df
        if backup_df.empty:
            st.error("🛡️ 현재 여행가계부와 일치하는 자동 백업이 없습니다.")
            return False

        data_df = backup_df.reindex(columns=FINAL_COLUMNS).copy()
        data_df = data_df.dropna(how='all').reset_index(drop=True)
        if data_df.empty:
            st.error("🛡️ 자동 백업 데이터가 비어 있습니다.")
            return False

        final_df = recalculate_entire_ledger(data_df)
        st.session_state.active_ledger_df = final_df
        st.session_state.last_loaded_sheet = ACTIVE_SHEET
        st.session_state['ledger_dirty'] = True
        st.session_state['ledger_order_dirty'] = True
        st.session_state['ledger_mutation_count'] = int(st.session_state.get('ledger_mutation_count', 0)) + 1
        st.toast("🛡️ 자동 백업을 메모리로 복원했습니다. 확인 후 '변경사항 일괄 저장'을 눌러주세요.", icon="🔄")
        return True
    except Exception as e:
        st.error(f"🚨 자동 백업 복원 실패: {e}")
        return False


@st.fragment(run_every="3m")
def _ledger_auto_backup_fragment():
    """3분마다 메모리 변경사항을 별도 백업 시트에 저장한다."""
    if not st.session_state.get('ledger_dirty', False):
        return

    backup_active_ledger_to_cloud()


# 2.05.06 | Pure Memory Cache Binder + Safe Trip Context
if 'ledger_dirty' not in st.session_state:
    st.session_state['ledger_dirty'] = False
if 'ledger_mutation_count' not in st.session_state:
    st.session_state['ledger_mutation_count'] = 0

_previous_working_sheet = st.session_state.get('ledger_working_sheet')
if _previous_working_sheet and _previous_working_sheet != ACTIVE_SHEET and st.session_state.get('ledger_dirty', False):
    # 여행가계부를 바꾸기 전에 현재 메모리 작업본을 먼저 안전 백업한다.
    _write_auto_backup_snapshot(
        st.session_state.get('active_ledger_df'),
        sheet_name=_previous_working_sheet,
        trip_name=_trip_name_for_sheet(_previous_working_sheet),
    )

if 'active_ledger_df' not in st.session_state or st.session_state.get('last_loaded_sheet') != ACTIVE_SHEET:
    st.session_state.active_ledger_df = load_data(ACTIVE_SHEET, force_cloud=False)
    st.session_state.last_loaded_sheet = ACTIVE_SHEET
    st.session_state['ledger_dirty'] = False
    st.session_state['ledger_order_dirty'] = False
    st.session_state['ledger_mutation_count'] = 0

st.session_state['ledger_working_sheet'] = ACTIVE_SHEET
ledger_df = st.session_state.active_ledger_df

# 자동 백업은 현재 화면과 독립적으로 3분마다 동작한다.
_ledger_auto_backup_fragment()



# ==============================================================================
# [Module 3.00.00] URDI Engine (Unified Real-time Deductive Inventory)
# ==============================================================================

# ------------------------------------------------------------------------------
# 3.01.00 | Real-time Inventory Audit (실시간 인벤토리 차감 및 상태 평가)
# ------------------------------------------------------------------------------
# 3.01.01 | Batch-level Multi-Wallet Inventory Evaluator
def get_inventory_status(df):
    from collections import defaultdict
    temp_df = df.sort_values(by='Date', kind='mergesort', ignore_index=True) if not df.empty else df
    inv_batches = defaultdict(list)
    
    def get_local_WAR(currency_account):
        sw_df = df[(df['Category'].str.strip().isin(['충전','환전','입금','직접환전'])) & (df['Currency'].str.strip() == currency_account)]
        if not sw_df.empty and sw_df['Amount'].sum() > 0: 
            return (sw_df['Amount'] * sw_df['AppliedRate']).sum() / sw_df['Amount'].sum()
        return get_default_rate(currency_account)

    if temp_df.empty: return dict(inv_batches)
    clean_expense_cats = list(set([c.strip() for c in EXPENSE_CATS] + ['선물']))
    
    for _, row in temp_df.iterrows():
        qty, curr = row['Amount'], row['Currency']
        cat = str(row['Category']).strip()
        method = str(row['PaymentMethod']).strip()
        desc = str(row['Description']).strip()
        rate = row['AppliedRate']
        
        is_exp = 1 if cat in clean_expense_cats and cat not in ['환불', '보증금', '재환전', '상환', '개인지출'] else 0
        is_deductible = 1 if (is_exp == 1 or cat in ['보증금', '상환']) else 0
        asset_cls = get_asset_class(method)
        
        if cat in ['충전', '환전', '입금', '직접환전', '이월잔액']:
            if cat == '이월잔액': final_dest_cls = "CASH"
            elif cat == '충전': final_dest_cls = "PREPAID"
            elif cat in ['환전', '직접환전']: final_dest_cls = "CASH"
            else: final_dest_cls = get_asset_class(desc + method)
            
            target = f"트래블카드({curr})" if final_dest_cls == "PREPAID" else f"현금({curr})"
            if curr != 'KRW': inv_batches[target].append({'rate': rate, 'qty': qty, 'initial': qty})
            
        elif cat == '환불':
            if asset_cls != "DOMESTIC":
                target = f"트래블카드({curr})" if asset_cls == "PREPAID" else f"현금({curr})"
                if curr != 'KRW': inv_batches[target].append({'rate': rate, 'qty': qty, 'initial': qty})
                
        elif cat == 'ATM출금':
            temp_qty = qty; target_from = f"트래블카드({curr})"; target_to = f"현금({curr})"
            if target_from in inv_batches:
                for batch in inv_batches[target_from]:
                    if temp_qty <= 0: break
                    if batch['qty'] <= 0: continue
                    take = min(temp_qty, batch['qty']); batch['qty'] -= take
                    inv_batches[target_to].append({'rate': batch['rate'], 'qty': take, 'initial': take}); temp_qty -= take
            if temp_qty > 0:
                inv_batches[target_to].append({'rate': get_local_WAR(curr), 'qty': temp_qty, 'initial': temp_qty})
                
        elif cat in ['재환전', '개인지출']:
            if curr != 'KRW':
                target_from = f"트래블카드({curr})" if asset_cls == "PREPAID" else f"현금({curr})"
                temp_qty = qty
                if target_from in inv_batches:
                    for batch in inv_batches[target_from]:
                        if temp_qty <= 0: break
                        if batch['qty'] <= 0: continue
                        take = min(temp_qty, batch['qty']); batch['qty'] -= take; temp_qty -= take
                        
        elif cat == '이종환전':
            if curr != 'KRW':
                target_from = f"트래블카드({curr})" if asset_cls == "PREPAID" else f"현금({curr})"
                temp_qty = qty
                if target_from in inv_batches:
                    for batch in inv_batches[target_from]:
                        if temp_qty <= 0: break
                        if batch['qty'] <= 0: continue
                        take = min(temp_qty, batch['qty']); batch['qty'] -= take; temp_qty -= take
                        
        elif is_deductible == 1:
            if asset_cls != "DOMESTIC" and asset_cls != "CREDIT" and curr != 'KRW':
                target = f"트래블카드({curr})" if asset_cls == "PREPAID" else f"현금({curr})"
                temp_qty = qty
                if target in inv_batches:
                    for batch in inv_batches[target]:
                        if temp_qty <= 0: break
                        if batch['qty'] <= 0: continue
                        take = min(temp_qty, batch['qty']); batch['qty'] -= take; temp_qty -= take
                        
    return dict(inv_batches)

current_inventory_batches = get_inventory_status(ledger_df)

# ------------------------------------------------------------------------------
# 3.02.00 | Foreign Exchange Valuation (가중 평균 환율 및 FIFO 비용 계산)
# ------------------------------------------------------------------------------
# 3.02.01 | Weighted Average Exchange Rate Engine
def get_WAR(curr):
    sw_df = ledger_df[(ledger_df['Category'].str.strip().isin(['충전','환전','입금','직접환전'])) & (ledger_df['Currency'].str.strip() == curr)]
    if not sw_df.empty and sw_df['Amount'].sum() > 0: 
        return (sw_df['Amount'] * sw_df['AppliedRate']).sum() / sw_df['Amount'].sum()
    return get_default_rate(curr)

sw_df_loc = ledger_df[(ledger_df['Category'].str.strip().isin(['충전','환전','입금','직접환전'])) & (ledger_df['Currency'].str.strip() == TRAVEL_CURRENCY)]
WAR_LOCAL = (sw_df_loc['Amount'] * sw_df_loc['AppliedRate']).sum() / sw_df_loc['Amount'].sum() if not sw_df_loc.empty and sw_df_loc['Amount'].sum() > 0 else get_default_rate(TRAVEL_CURRENCY)

# 3.02.02 | Dynamic FIFO Cost Rate Simulator
def auto_calc_fifo_rate(amount, method, curr=TRAVEL_CURRENCY):
    asset_cls = get_asset_class(method)
    if asset_cls == "DOMESTIC": return get_WAR(curr)
    target = f"트래블카드({curr})" if asset_cls == "PREPAID" else f"현금({curr})"
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

# ------------------------------------------------------------------------------
# 3.03.00 | Financial Summary Aggregator (예산 및 실지출 요약 집계)
# ------------------------------------------------------------------------------
# 3.03.01 | Net Budget & Spent Metrics Calculator
def calculate_summary_metrics(df):
    if df.empty: return 0.0, 0.0
    temp_df = df.sort_values(by='Date', kind='mergesort', ignore_index=True)
    
    b_total = 0.0
    if 'Cum_Budget_KRW' in temp_df.columns:
        raw_b = temp_df['Cum_Budget_KRW'].iloc[-1]
        try: b_total = float(str(raw_b).replace(',', '').strip())
        except: b_total = 0.0
    if pd.isna(b_total): b_total = 0.0

    try:
        exp_sub = temp_df[temp_df['IsExpense'] == 1]
        gross_spent = exp_sub.apply(lambda r: float(r['Amount']) if str(r['Currency']).strip() == 'KRW' else float(r['Amount']) * float(r['AppliedRate']), axis=1).sum()
    except:
        gross_spent = 0.0

    try:
        expense_refunds = temp_df[
            (temp_df['Category'] == '환불') & 
            (~temp_df['Description'].str.contains("보증금|Deposit|deposit", na=False))
        ]
        refund_total = expense_refunds.apply(lambda r: float(r['Amount']) if str(r['Currency']).strip() == 'KRW' else float(r['Amount']) * float(r['AppliedRate']), axis=1).sum()
    except:
        refund_total = 0.0

    return float(b_total), float(gross_spent - refund_total)

# ------------------------------------------------------------------------------
# 4.01.00 | Sidebar Dashboard (지갑 잔고, 여정 관제탑, 실물현금 카운터, 보조통화 최하단)
# ------------------------------------------------------------------------------
# 4.01.01 | Physical Cash Cloud Pull Callback
def cb_pull_cloud_cash(curr_c, counts_dict, b_list):
    for bill_val in b_list:
        b_id = str(bill_val).replace('.', '_')
        loaded_val = counts_dict.get(float(bill_val), 0)
        st.session_state[f"cnt_{curr_c}_{b_id}"] = int(loaded_val) if loaded_val > 0 else None

with st.sidebar:
    # 4.01.02 | D-Day & Hotel Cancellation Control Tower Renderer
    def render_dday_control_tower():
        dep_rows_sb = ledger_df[ledger_df['Category'].str.contains('출국', na=False)]
        korea_dep_sb = ledger_df[ledger_df['Category'].str.contains('출국_한국|출국.*한국', na=False)]
        t_dep_sb = korea_dep_sb if not korea_dep_sb.empty else dep_rows_sb
        
        sb_dep_dt = None
        if not t_dep_sb.empty:
            m_dsb = re.search(r'(\d{4}-\d{2})-(\d{2})', str(t_dep_sb.iloc[0]['Date']))
            if m_dsb: sb_dep_dt = datetime.strptime(m_dsb.group(0), "%Y-%m-%d").date()

        arr_rows_sb = ledger_df[ledger_df['Category'].str.contains('귀국|입국', na=False)]
        korea_arr_sb = ledger_df[ledger_df['Category'].str.contains('귀국_한국|귀국.*한국|입국_한국|입국.*한국', na=False)]
        t_arr_sb = korea_arr_sb if not korea_arr_sb.empty else arr_rows_sb
        
        sb_arr_dt = None
        if not t_arr_sb.empty:
            m_asb = re.search(r'(\d{4}-\d{2})-(\d{2})', str(t_arr_sb.iloc[-1]['Date']))
            if m_asb: sb_arr_dt = datetime.strptime(m_asb.group(0), "%Y-%m-%d").date()

        today_sb = datetime.now(TZ_KST).date()
        
        if sb_dep_dt:
            diff_dep = (sb_dep_dt - today_sb).days
            if diff_dep > 0:
                flight_badge = f"<span style='background-color:#0284C7; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; font-size:12px;'>🛫 출국 D-{diff_dep}일</span>"
            elif diff_dep == 0:
                flight_badge = f"<span style='background-color:#EA580C; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; font-size:12px;'>🔥 오늘 출국! D-Day</span>"
            else:
                if sb_arr_dt and today_sb <= sb_arr_dt:
                    traveling_day = (today_sb - sb_dep_dt).days + 1
                    flight_badge = f"<span style='background-color:#16A34A; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; font-size:12px;'>📍 여행 {traveling_day}일차</span>"
                else:
                    flight_badge = f"<span style='background-color:#475569; color:white; padding:3px 8px; border-radius:6px; font-weight:bold; font-size:12px;'>🏁 여행 완료</span>"
        else:
            flight_badge = "<span style='color:#94A3B8; font-size:12px;'>🛫 출국 일정 미정</span>"

        hotel_rows = ledger_df[ledger_df['Category'] == '호텔']
        cancel_alerts = []
        for _, h_r in hotel_rows.iterrows():
            desc_h = str(h_r['Description'])
            m_c = re.search(r'취소마감:(\d{2}/\d{2})\((\d+)%환불\)', desc_h)
            if m_c:
                c_mmdd, c_rate = m_c.group(1), m_c.group(2)
                c_year = sb_dep_dt.year if sb_dep_dt else today_sb.year
                try:
                    c_target_dt = datetime.strptime(f"{c_year}/{c_mmdd}", "%Y/%m/%d").date()
                    diff_c = (c_target_dt - today_sb).days
                    h_short_name = re.sub(r'\[.*?\]\s*', '', desc_h).split('|')[0].strip()[:9]
                    
                    if diff_c > 0:
                        c_color = "#EF4444" if diff_c <= 3 else "#F59E0B"
                        cancel_alerts.append(f"<div style='font-size:11.5px; color:{c_color}; margin-top:2px;'>🚨 {h_short_name} 취소 D-{diff_c}일 ({c_rate}%환불)</div>")
                    elif diff_c == 0:
                        cancel_alerts.append(f"<div style='font-size:11.5px; color:#EF4444; font-weight:bold; margin-top:2px;'>🚨 {h_short_name} 오늘 취소 마감! ({c_rate}%환불)</div>")
                except: pass

        alerts_html = "".join(cancel_alerts) if cancel_alerts else "<div style='font-size:11px; color:#64748B;'>예정된 호텔 취소 마감 없음</div>"

        st.markdown(f"""
            <div style='background: rgba(30, 41, 59, 0.7); border: 1px solid #334155; border-radius: 10px; padding: 10px 12px; margin-bottom: 14px;'>
                <div style='display:flex; justify-content:space-between; align-items:center;'>
                    <span style='font-size:12px; font-weight:bold; color:#E2E8F0;'>🧭 여정 관제탑</span>
                    {flight_badge}
                </div>
                <div style='margin-top:6px; border-top:1px dashed #475569; padding-top:6px;'>
                    {alerts_html}
                </div>
            </div>
        """, unsafe_allow_html=True)

    # 4.01.03 | SPI / Provisioning Mode Context Panel
    if st.session_state.get('show_spi', False) or st.session_state.get('show_new_trip', False):
        st.subheader("🧭 GTL 관제탑 모드")
        if st.session_state.get('show_spi', False):
            st.info("💡 **글로벌 물가 지표(SPI) 비교 분석 중**\n\n특정 여행의 지출 내역이나 잔고를 보시려면 상단의 '내 여행함'에서 여행지를 선택해 주세요.")
        else:
            st.info("➕ **새로운 여행지 개설 모드**\n\n새 여행지를 등록하거나 기존 여행지를 보시려면 상단 '내 여행함'에서 여행지를 선택해 주세요.")
        
        st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
        if st.button("🔄 Cloud Refresh (데이터 동기화)", use_container_width=True): 
            st.cache_data.clear()
            st.query_params["trip"] = st.session_state.current_trip
            st.rerun()
    else:
        dep_rows_eval = ledger_df[ledger_df['Category'].str.contains('출국', na=False)]
        korea_dep_eval = ledger_df[ledger_df['Category'].str.contains('출국_한국|출국.*한국', na=False)]
        t_dep_eval = korea_dep_eval if not korea_dep_eval.empty else dep_rows_eval

        is_upcoming = False
        if not t_dep_eval.empty:
            m_eval = re.search(r'(\d{4}-\d{2})-(\d{2})', str(t_dep_eval.iloc[0]['Date']))
            if m_eval:
                dep_dt_val = datetime.strptime(m_eval.group(0), "%Y-%m-%d").date()
                today_val = datetime.now(TZ_KST).date()
                is_upcoming = (today_val < dep_dt_val)

        if is_upcoming:
            render_dday_control_tower()

        # 4.01.04 | 지갑 카드 렌더러 정의
        st.subheader("💰 지갑 잔고")
        b_val, spent_val = calculate_summary_metrics(ledger_df)
        
        korea_arr = ledger_df[ledger_df['Category'].str.contains('귀국|입국_한국|입국.*한국|귀국.*한국', na=False)]
        arr_rows = ledger_df[ledger_df['Category'].str.contains('귀국|입국', na=False)]
        target_arr_row = korea_arr if not korea_arr.empty else arr_rows

        is_trip_active = True
        if not target_arr_row.empty:
            m_arr = re.search(r'(\d{4}-\d{2})-(\d{2})', str(target_arr_row.iloc[-1]['Date']))
            if m_arr:
                arr_dt = datetime.strptime(m_arr.group(0), "%Y-%m-%d").date()
                today_dt = datetime.now(TZ_KST).date()
                is_trip_active = (today_dt <= arr_dt)

        active_currs = set([k.split('(')[1].replace(')','') for k in current_inventory_batches.keys() if len(current_inventory_batches[k]) > 0 and sum(b['qty'] for b in current_inventory_batches[k]) > 0])
        trip_currs_ordered = [node['currency'] for node in TRIP_CONFIGS[st.session_state.current_trip]["nodes"].values()]
        
        primary_trip_currs = []
        for c in trip_currs_ordered:
            if c not in primary_trip_currs and c != "KRW":
                primary_trip_currs.append(c)

        secondary_currs = sorted([c for c in active_currs if c not in primary_trip_currs and c != "KRW"])

        CURR_BILLS = {
            "VND": BILLS,
            "EUR": [100, 50, 20, 10, 5, 2, 1, 0.5, 0.2, 0.1],
            "USD": [100, 50, 20, 10, 5, 2, 1, 0.25, 0.1],
            "TRY": [200, 100, 50, 20, 10, 5, 1, 0.5],
            "JPY": [10000, 5000, 2000, 1000, 500, 100, 50, 10],
            "PHP": [1000, 500, 200, 100, 50, 20, 10, 5, 1],
            "CNY": [100, 50, 20, 10, 5, 1, 0.5, 0.1]
        }

        LOW_CASH_THRESHOLD = {
            "VND": 1000000, "USD": 50, "EUR": 50, "TRY": 1000, "JPY": 5000, "CNY": 300, "PHP": 2000
        }

        def render_currency_card(c, is_secondary=False):
            fmt = "{:,.2f}" if c not in ["VND", "HUF", "PHP"] else "{:,.0f}"
            c_card = sum([b['qty'] for b in current_inventory_batches.get(f"트래블카드({c})",[])])
            c_cash = sum([b['qty'] for b in current_inventory_batches.get(f"현금({c})",[])])

            debt_amt = ledger_df[(ledger_df['Currency']==c) & (ledger_df['PaymentMethod'].str.contains("외상|부채|CREDIT", na=False))]['Amount'].sum()
            repay_amt = ledger_df[(ledger_df['Currency']==c) & (ledger_df['Category']=="상환")]['Amount'].sum()
            current_debt = debt_amt - repay_amt
            if current_debt > 0:
                st.markdown(f"<div style='color:#FF4B4B; font-size:13.5px; font-weight:bold;'>📌 미결제 외상: {fmt.format(current_debt)} {c}</div>", unsafe_allow_html=True)

            header_color = "#38BDF8" if is_secondary else "#FFA500"
            st.markdown(f"<div style='color:{header_color}; font-weight:bold; margin-top:12px; margin-bottom:10px;'>● {c}</div>", unsafe_allow_html=True)
            st.markdown(f"💳 카드: **{fmt.format(c_card)}**")
            st.markdown(f"<div style='margin-bottom:12px;'>💵 현금: **{fmt.format(c_cash)}**</div>", unsafe_allow_html=True) 

            threshold = LOW_CASH_THRESHOLD.get(c, 1000000 if c == "VND" else 50)
            if not is_secondary and is_trip_active and c_cash <= threshold:
                st.markdown("""
                    <div style='color:#FFA500; font-size:12.5px; font-weight:bold; margin-top:2px; margin-bottom:14px; padding: 5px 10px; background-color: rgba(255, 165, 0, 0.12); border-radius: 6px; border-left: 3px solid #FFA500;'>
                        🚨 현금 부족 경고
                    </div>
                """, unsafe_allow_html=True)

            card_batches = current_inventory_batches.get(f"트래블카드({c})", [])
            cash_batches = current_inventory_batches.get(f"현금({c})", [])

            if any(b['qty'] > 0 for b in (card_batches + cash_batches)):
                with st.expander("🔍 상세 배치", expanded=(is_trip_active and not is_secondary)):
                    r_prec = ".4f" if c in ["VND", "HUF"] else ".2f"
                    if any(b['qty'] > 0 for b in card_batches):
                        st.caption("[카드]")
                        for b in card_batches:
                            if b['qty'] > 0: st.caption(f"• {fmt.format(b['qty'])} @{b['rate']:{r_prec}}")
                    if any(b['qty'] > 0 for b in cash_batches):
                        st.caption("[현금]")
                        for b in cash_batches:
                            if b['qty'] > 0: st.caption(f"• {fmt.format(b['qty'])} @{b['rate']:{r_prec}}")

            bills_to_count = CURR_BILLS.get(c, [])
            if bills_to_count and (c_cash > 0 or (is_trip_active and not is_secondary)):
                with st.expander("🪙 실물현금 카운터", expanded=False):
                    cash_df = load_cash_inventory()
                    cloud_total, cloud_time, cloud_counts = 0.0, "", {}
                    
                    if not cash_df.empty:
                        m_sync = (cash_df['TripName'] == st.session_state.current_trip) & (cash_df['Currency'] == c)
                        if m_sync.any():
                            row_sync = cash_df[m_sync].iloc[0]
                            cloud_total = float(row_sync.get('Total_Amount', 0))
                            raw_t = str(row_sync.get('Updated_At', '')).strip()
                            m_t = re.search(r'\d{4}-(\d{2}-\d{2})\s+(\d{1,2}):(\d{2})', raw_t)
                            if m_t: cloud_time = f"{m_t.group(1)} {int(m_t.group(2)):02d}:{m_t.group(3)}"
                            else: cloud_time = raw_t[5:16].rstrip(':')
                                
                            for item in str(row_sync.get('Bill_Counts', '')).split(";"):
                                if ":" in item:
                                    b_v, b_c = item.split(":")
                                    try: cloud_counts[float(b_v)] = int(b_c)
                                    except: pass

                    init_key = f"init_cash_{st.session_state.current_trip}_{c}"
                    if init_key not in st.session_state:
                        for b in bills_to_count:
                            val_loaded = cloud_counts.get(float(b), 0)
                            b_key_id = str(b).replace('.', '_')
                            st.session_state[f"cnt_{c}_{b_key_id}"] = int(val_loaded) if val_loaded > 0 else None
                        st.session_state[init_key] = True

                    total_counted, cur_counts = 0.0, {}
                    for bill in bills_to_count:
                        b_flt = float(bill)
                        b_key_id = str(bill).replace('.', '_')
                        
                        if c == "VND": b_label = f"{int(bill // 1000)}K"
                        elif c == "EUR": b_label = f"{int(bill)} €" if bill >= 1 else f"{int(round(bill * 100))} c"
                        elif c == "USD": b_label = f"{int(bill)} $" if bill >= 1 else f"{int(round(bill * 100))} ¢"
                        elif c == "TRY": b_label = f"{int(bill)} ₺" if bill >= 1 else f"{int(round(bill * 100))} kr"
                        elif c == "JPY": b_label = f"{int(bill)} ¥"
                        elif c == "PHP": b_label = f"{int(bill)} ₱"
                        else: b_label = f"{bill} {c}"
                            
                        c_col1, c_col2 = st.columns([1, 1.4])
                        with c_col1:
                            st.markdown(f"<div style='font-size:13px; font-weight:bold; white-space:nowrap; text-align:right; height:30px; line-height:30px; display:flex; align-items:center; justify-content:flex-end;'>{b_label}</div>", unsafe_allow_html=True)
                        with c_col2:
                            raw_val = st.session_state.get(f"cnt_{c}_{b_key_id}", None)
                            cnt = st.number_input(
                                label=f"{c}_{b_key_id}",
                                min_value=0,
                                step=1,
                                value=int(raw_val) if raw_val and raw_val > 0 else None,
                                placeholder="0",
                                key=f"cnt_{c}_{b_key_id}",
                                label_visibility="collapsed"
                            )
                        final_cnt = int(cnt) if cnt is not None else 0
                        cur_counts[b_flt] = final_cnt
                        total_counted += bill * final_cnt
                        
                    total_counted = round(total_counted, 2) if c not in ["VND", "HUF", "JPY"] else round(total_counted)
                    
                    st.markdown(f"""
                        <div style='margin-top: 14px; margin-bottom: 8px; padding: 6px 10px; background-color: rgba(255, 255, 255, 0.05); border-radius: 8px; text-align: center; border: 1px solid rgba(255, 255, 255, 0.1);'>
                            <span style='font-size:11.5px; color:#A0AEC0;'>🧮 실물현금 합계 (지폐+동전)</span><br>
                            <span style='font-size:15px; font-weight:bold; color:#4EFEB3;'>{fmt.format(total_counted)} {c}</span>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    diff_val = round(total_counted - c_cash, 2) if c not in ["VND", "HUF", "JPY"] else round(total_counted - c_cash)
                    if total_counted > 0:
                        if abs(diff_val) < 0.001: st.success("✅ 장부/실물 일치!")
                        elif diff_val < 0: st.error(f"🚨 실물 **{fmt.format(abs(diff_val))} {c}** 부족!")
                        else: st.warning(f"⚠️ 실물 **+{fmt.format(diff_val)} {c}** 초과!")

                    has_conflict = bool(cloud_counts) and (cur_counts != cloud_counts)
                    if has_conflict:
                        st.markdown(f"""
                            <div style='background-color: rgba(255, 165, 0, 0.12); border-left: 3px solid #FFA500; border-radius: 6px; padding: 8px 10px; margin-top: 10px; margin-bottom: 10px;'>
                                <div style='color: #FFA500; font-size: 12px; font-weight: bold;'>⚠️ 기기 간 데이터 불일치!</div>
                                <div style='font-size: 11.5px; color: #E2E8F0; margin-top: 4px; line-height: 1.5;'>
                                    • 현재 화면: <b>{fmt.format(total_counted)} {c}</b><br>
                                    • 클라우드: <b>{fmt.format(cloud_total)} {c}</b> <span style='color:#888;'>({cloud_time})</span>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        col_sel1, col_sel2 = st.columns(2)
                        with col_sel1:
                            st.button("📥 클라우드 가져오기", key=f"btn_pull_{c}", on_click=cb_pull_cloud_cash, args=(c, cloud_counts, bills_to_count), use_container_width=True)
                        with col_sel2:
                            if st.button("⚠️ 현재값 덮어쓰기", key=f"btn_force_push_{c}", use_container_width=True):
                                with st.spinner("클라우드 저장 중..."):
                                    if save_cash_inventory(st.session_state.current_trip, c, cur_counts, total_counted):
                                        st.success("덮어쓰기 완료!")
                                        time.sleep(0.6); st.rerun()
                    else:
                        if cloud_total > 0: st.caption(f"클라우드 동기완료 ({cloud_time})")
                        if st.button(f"💾 {c} 실물현금 저장", key=f"btn_save_normal_{c}", use_container_width=True):
                            with st.spinner("구글 시트 저장 중..."):
                                if save_cash_inventory(st.session_state.current_trip, c, cur_counts, total_counted):
                                    st.success("🎉 저장 완료!")
                                    time.sleep(0.6); st.rerun()
            st.divider()

        # 1. 🌟 메인 여행 통화 우선 상단 노출 (오렌지 헤더)
        for c in primary_trip_currs:
            render_currency_card(c, is_secondary=False)

        # 4.01.05 | Net Financial Summary KPI Display & Master Cloud Sync
        st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
        st.metric("🏦 총 예산", f"{float(b_val):,.0f} 원")
        st.metric("💸 지출총액", f"{float(spent_val):,.0f} 원")

        if not is_upcoming:
            st.divider()
            render_dday_control_tower()

        st.divider()
        st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
        # ⚡ 사용자가 수동으로 버튼을 누를 때만 구글 시트에서 강제 최신화(force_cloud=True)
        if st.button("🔄 Cloud Refresh (데이터 동기화)", use_container_width=True, type="primary"): 
            st.cache_data.clear()
            smart_cache_clear()
            if 'cached_trip_configs' in st.session_state: del st.session_state['cached_trip_configs']
            pulled_df = load_data(ACTIVE_SHEET, force_cloud=True)
            load_cash_inventory(force_cloud=True)
            re_calc_df = recalculate_entire_ledger(pulled_df)
            st.session_state.active_ledger_df = re_calc_df
            try:
                conn.update(worksheet=ACTIVE_SHEET, data=re_calc_df.reindex(columns=FINAL_COLUMNS))
                st.toast("✅ 클라우드 동기화 및 지출 정합성 복구 완료!", icon="🎉")
            except Exception as e_cr:
                st.error(f"동기화 에러: {e_cr}")
            time.sleep(0.5)
            st.rerun()

        # ⚡ 사이드바 속도 배지
        t_sb_now = (time.perf_counter() - t_render_start) * 1000
        sb_color = "#10B981" if t_sb_now < 500 else ("#38BDF8" if t_sb_now < 1500 else "#F59E0B")
        st.markdown(f"<div style='text-align:center; font-size:11.5px; color:#64748B; margin-top:8px;'>실시간 반응: <span style='color:{sb_color}; font-weight:bold;'>⚡ {t_sb_now:,.0f}ms</span></div>", unsafe_allow_html=True)

        if secondary_currs:
            st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
            st.caption("🌐 보조/기타 통화 잔고")
            for c in secondary_currs:
                render_currency_card(c, is_secondary=True)

# ------------------------------------------------------------------------------
# 4.02.00 | Top Navigation Router (여행지 선택 및 관제탑 모드 스위처)
# ------------------------------------------------------------------------------
# ==============================================================================
# 4.02.00 | Top Navigation Router (여행지 선택 및 관제탑 모드 스위처)
# ==============================================================================
# 4.02.01 | Global View Switcher & Trip Selector (상단 반응속도 뱃지 탑재)
sorted_trips = sort_trips(list(TRIP_CONFIGS.keys()))

SPECIAL_MODE_SPI = "📊 모든 여행지 물가비교"
SPECIAL_MODE_NEW = "➕ 새로운 여행지 개설"
dropdown_options = sorted_trips + [SPECIAL_MODE_SPI, SPECIAL_MODE_NEW]

if 'show_spi' not in st.session_state: 
    st.session_state.show_spi = False
if 'show_new_trip' not in st.session_state:
    st.session_state.show_new_trip = False

if 'current_trip' not in st.session_state or st.session_state.current_trip not in sorted_trips:
    fukuoka_cands = [t for t in sorted_trips if "후쿠오카" in t or "FUKUOKA" in t.upper()]
    st.session_state.current_trip = fukuoka_cands[0] if fukuoka_cands else sorted_trips[0]

if st.session_state.show_spi:
    curr_idx = len(sorted_trips)
elif st.session_state.show_new_trip:
    curr_idx = len(sorted_trips) + 1
else:
    curr_idx = sorted_trips.index(st.session_state.current_trip)

def on_trip_change():
    chosen = st.session_state.top_nav_trip_selector
    if chosen == SPECIAL_MODE_SPI:
        st.session_state.show_spi = True
        st.session_state.show_new_trip = False
        st.query_params["mode"] = "spi"
    elif chosen == SPECIAL_MODE_NEW:
        st.session_state.show_spi = False
        st.session_state.show_new_trip = True
        st.query_params["mode"] = "new"
    else:
        st.session_state.show_spi = False
        st.session_state.show_new_trip = False
        st.session_state.current_trip = chosen
        st.query_params["trip"] = chosen
        if "mode" in st.query_params:
            del st.query_params["mode"]
    st.rerun()

st.selectbox(
    "✈️ 내 여행함 (Trip Selector)", 
    dropdown_options, 
    index=curr_idx, 
    key="top_nav_trip_selector", 
    on_change=on_trip_change,
    label_visibility="collapsed"
)

# ⚡ [상단 실시간 반응속도 슬림 배지] 최상단에서 즉각 확인 가능
t_top_now = (time.perf_counter() - t_render_start) * 1000
top_color = "#10B981" if t_top_now < 500 else ("#38BDF8" if t_top_now < 1500 else "#F59E0B")
st.markdown(f"""
    <div style='display:flex; justify-content:flex-end; align-items:center; margin-top:-6px; margin-bottom:6px;'>
        <span style='font-size:12px; color:#64748B;'>반응속도: <b style='color:{top_color};'>⚡ {t_top_now:,.0f}ms</b></span>
    </div>
""", unsafe_allow_html=True)

st.divider()


# ==============================================================================
# [Module 5.00.00] Global Comparison Mode (Module F: 다국적 물가 및 단가 비교)
# ==============================================================================
if st.session_state.show_spi:
    st.title("여행지 물가비교")
    df_all = load_all_trips_data()
    
    if not df_all.empty:
        sub_tab_spi, sub_tab_hotel, sub_tab_flight = st.tabs(["1일비용", "호텔", "항공"])
      
        # ----------------------------------------------------------------------
        # 5.01.00 | Channel 1: Daily Living Cost (SPI) (수평 누적 가로막대 차트)
        # ----------------------------------------------------------------------
        with sub_tab_spi:
            # 5.01.01 | Stay Nights & Travelers Normalization Matrix
            SPI_CATS = ['식사', '간식', '마트', 'Grab', 'VinBus', 'DiDi', '지하철', '택시', '교통', '렌트카', '마사지', '팁', '통신', '수수료', '투어', '입장료', '호텔', '숙박', '체크인', '체크아웃']
            stay_nights = {}
            travelers_map = {}
            
            for trip_name, config in TRIP_CONFIGS.items():
                travelers_map[trip_name] = config.get("travelers", 2)
                mapping_str = config.get("stay_mapping", "")
                
                if ":" in mapping_str or " : " in mapping_str:
                    for p in mapping_str.replace(" ", "").split(","):
                        if ":" in p:
                            c_name, n_str = p.split(":", 1)
                            n_match = re.search(r'(\d+(?:\.\d+)?)', n_str)
                            if n_match: stay_nights[(trip_name, c_name.strip())] = float(n_match.group(1))
                else:
                    n_match = re.search(r'(\d+(?:\.\d+)?)', mapping_str)
                    if n_match:
                        for c_name in config["nodes"].keys():
                            stay_nights[(trip_name, c_name)] = float(n_match.group(1))
            
            df_all['Date_Obj'] = pd.to_datetime(df_all['Date'].str.extract(r'(\d{4}-\d{2}-\d{2})')[0], errors='coerce')
            
            for (trip, country), group in df_all.groupby(['TripName', 'Country']):
                if (trip, country) not in stay_nights:
                    extracted_nights = 0
                    cio_df = group[group['Category'].str.contains('체크인|체크아웃', na=False)]
                    if not cio_df.empty:
                        target_df = cio_df[cio_df['Category'] == '체크인'] if '체크인' in cio_df['Category'].values else cio_df
                        ext = target_df['Description'].str.extract(r'(\d+(?:\.\d+)?)\s*박')
                        extracted_nights = pd.to_numeric(ext[0], errors='coerce').fillna(0).sum()
                    if extracted_nights <= 0:
                        hotel_df = group[group['Category'].str.contains('호텔|숙박', na=False)]
                        if not hotel_df.empty:
                            ext = hotel_df['Description'].str.extract(r'(\d+(?:\.\d+)?)\s*박')
                            extracted_nights = pd.to_numeric(ext[0], errors='coerce').fillna(0).sum()
                    stay_nights[(trip, country)] = extracted_nights

            def is_valid_stay_country(r):
                t_name, c_name = str(r['TripName']), str(r['Country'])
                if any(ex in c_name for ex in ['글로벌', '경유', '환승', '크루즈', '한국', '크로아티아', '불가리아']):
                    return False
                return stay_nights.get((t_name, c_name), 0) > 0

            valid_mask = df_all.apply(is_valid_stay_country, axis=1)
            df_spi = df_all[(df_all['Category'].isin(SPI_CATS)) & valid_mask].copy()
            
            if not df_spi.empty:
                df_spi['KRW_val'] = df_spi.apply(lambda r: r['Amount'] if r['Currency'] == 'KRW' else r['Amount'] * float(r['AppliedRate']), axis=1)
                refund_df = df_all[(df_all['Category'] == '환불') & valid_mask].copy()
                if not refund_df.empty:
                    refund_df['KRW_val'] = refund_df.apply(lambda r: -(r['Amount'] if r['Currency'] == 'KRW' else r['Amount'] * float(r['AppliedRate'])), axis=1)
                    def map_refund_group(desc):
                        desc = str(desc).replace(" ", "").lower()
                        if any(k in desc for k in ["보증금", "deposit", "디파짓"]): return '제외'
                        if any(k in desc for k in ["호텔", "숙박", "인페라", "라이온", "스플랜디도", "벨몬트"]): return '🏨 숙박'
                        if any(k in desc for k in ["투어", "입장료"]): return '🏄 투어/액티비티'
                        if any(k in desc for k in ["렌트카"]): return '🚗 렌트카'
                        return '제외'
                    refund_df['SPI_Group'] = refund_df['Description'].apply(map_refund_group)
                    refund_df = refund_df[refund_df['SPI_Group'] != '제외']
                    if not refund_df.empty:
                        df_spi = pd.concat([df_spi, refund_df], ignore_index=True)

                def map_spi_group(cat):
                    if pd.isna(cat): return '📱 기타'
                    if cat in ['렌트카']: return '🚗 렌트카'
                    if cat in ['호텔', '숙박', '체크인', '체크아웃']: return '🏨 숙박'
                    if cat in ['투어', '입장료', '마사지']: return '🏄 투어/액티비티'
                    if cat in ['식사', '간식', '마트']: return '🍔 식음료'
                    if cat in ['Grab', 'VinBus', 'DiDi', '지하철', '택시', '교통']: return '🚕 로컬교통'
                    return '📱 기타'

                df_spi['SPI_Group'] = df_spi.apply(lambda r: r['SPI_Group'] if pd.notna(r.get('SPI_Group')) else map_spi_group(r['Category']), axis=1)
                agg_group = df_spi.groupby(['TripName', 'Country', 'SPI_Group'])['KRW_val'].sum().reset_index()
                agg_group['Travelers'] = agg_group['TripName'].map(travelers_map).fillna(2)
                agg_group['Nights'] = agg_group.apply(lambda r: stay_nights.get((r['TripName'], r['Country']), 1), axis=1)
                agg_group['KRW_val'] = agg_group['KRW_val'].apply(lambda x: max(0, x))
                agg_group['Nights'] = agg_group['Nights'].apply(lambda x: x if x > 0 else 1)
                agg_group['Daily_SPI'] = (agg_group['KRW_val'] / agg_group['Travelers']) / agg_group['Nights']
                
                agg_total = agg_group.groupby(['TripName', 'Country']).agg({'Daily_SPI': 'sum', 'Travelers': 'first', 'Nights': 'first'}).reset_index()

                # 5.01.02 | Spending Factor Diagnosis
                theme_notes = []
                for idx, row in agg_total.iterrows():
                    t, c, pp_nights = row['TripName'], row['Country'], row['Travelers'] * row['Nights']
                    sub_group = agg_group[(agg_group['TripName'] == t) & (agg_group['Country'] == c)]
                    hotel_v = sub_group[sub_group['SPI_Group'] == '🏨 숙박']['KRW_val'].sum()
                    rent_v = sub_group[sub_group['SPI_Group'] == '🚗 렌트카']['KRW_val'].sum()
                    tour_v = sub_group[sub_group['SPI_Group'] == '🏄 투어/액티비티']['KRW_val'].sum()
                    
                    tags = []
                    if hotel_v > 0: tags.append(f"🏨 1박평균 {hotel_v/row['Nights']/10000:.1f}만")
                    if rent_v > 0: tags.append(f"🚗 1일렌트 {rent_v/row['Nights']/10000:.1f}만")
                    if tour_v > 0: tags.append(f"🏄 투어(1인) {tour_v/pp_nights/10000:.1f}만")
                    theme_notes.append(" | ".join(tags) if tags else "-")
                    
                agg_total['Theme'] = theme_notes
                final_total_df = agg_total.sort_values(by='Daily_SPI', ascending=True)
                
                # 5.01.03 | Horizontal Stacked Bar Chart & Display Table
                if not final_total_df.empty:
                    st.markdown("### 여행지 1박비용(원)")
                    
                    def make_chart_label(r):
                        country, trip = str(r['Country']), str(r['TripName'])
                        return f"<b>{country}</b><br><span style='font-size:11px; color:#A0AEC0;'>({trip})</span>"

                    final_total_df['Chart_Label'] = final_total_df.apply(make_chart_label, axis=1)
                    
                    display_df = final_total_df.copy()
                    display_df['Daily_SPI_Fmt'] = display_df['Daily_SPI'].apply(lambda x: f"{x:,.0f} 원")
                    display_df = display_df.rename(columns={'TripName': '여행명', 'Country': '국가', 'Travelers': '인원수', 'Nights': '숙박일(박)', 'Daily_SPI_Fmt': '1박 체감물가', 'Theme': '💡 특이사항 및 요인'})
                    st.dataframe(display_df[['여행명', '국가', '인원수', '숙박일(박)', '1박 체감물가', '💡 특이사항 및 요인']], use_container_width=True, hide_index=True)
                    
                    label_map = dict(zip(zip(final_total_df['TripName'], final_total_df['Country']), final_total_df['Chart_Label']))
                    agg_group['Chart_Label'] = agg_group.apply(lambda r: label_map.get((r['TripName'], r['Country']), r['Country']), axis=1)
                    
                    category_order_y = final_total_df['Chart_Label'].tolist()
                    stack_order = ['📱 기타', '🚕 로컬교통', '🍔 식음료', '🏄 투어/액티비티', '🏨 숙박', '🚗 렌트카']
                    color_map = {'🚗 렌트카': '#D32F2F', '🏨 숙박': '#1976D2', '🏄 투어/액티비티': '#9C27B0', '🍔 식음료': '#4CAF50', '🚕 로컬교통': '#00ACC1', '📱 기타': '#795548'}
                    
                    st.markdown("<h4 style='margin-top:25px; margin-bottom: 6px;'>📊 여행지별 1박 체감물가 구성 비교</h4>", unsafe_allow_html=True)
                    
                    fig_stacked = px.bar(
                        agg_group, 
                        x='Daily_SPI', 
                        y='Chart_Label', 
                        orientation='h',
                        color='SPI_Group', 
                        color_discrete_map=color_map, 
                        category_orders={"Chart_Label": category_order_y, "SPI_Group": stack_order},
                        title=None
                    )
                    
                    dynamic_spi_height = max(480, len(final_total_df) * 44 + 100)
                    
                    fig_stacked.update_layout(
                        barmode='stack', 
                        xaxis=dict(fixedrange=True, title="1박 체감비용 (원)"),
                        yaxis=dict(fixedrange=True, autorange="reversed", title=None),
                        dragmode=False,
                        margin=dict(l=10, r=40, t=10, b=30), 
                        height=dynamic_spi_height,
                        legend=dict(
                            orientation="h", 
                            yanchor="bottom", 
                            y=1.02, 
                            xanchor="center", 
                            x=0.5, 
                            title=None
                        )
                    )
                    st.plotly_chart(fig_stacked, use_container_width=True, config={'displaylogo': False, 'scrollZoom': False, 'displayModeBar': False})

        # ----------------------------------------------------------------------
        # 5.02.00 | Channel 2: Hotel Unit Cost Analytics (수평 가로 막대 차트)
        # ----------------------------------------------------------------------
        with sub_tab_hotel:
            st.subheader("🏨 호텔 1박 요금 비교")
            st.caption("💡 실제 지출이 발생한 호텔 결제 정보(Category='호텔', Amount > 0)만 수집하며, 단순 일정인 체크인은 제외합니다. 동일 호텔명으로 기록된 여러 결제 건 중 '가장 금액이 큰 건'을 기본숙박비로 지정하여 투숙일수를 추출하고, '그 외 금액이 작은 결제 건'은 일수 증가 없이 기타추가비용(업그레이드/세금 등)으로 자동 분류하여 정합성을 보장합니다.")
            
            def clean_hotel_name(desc):
                s = str(desc)
                s = re.sub(r'^\[.*?\]\s*', '', s)
                parts = re.split(r'[,|]', s)
                name = parts[0].strip()
                name = re.sub(r'\s*\d+\s*박.*$', '', name)
                return name.strip()
            
            raw_hotel_rows = []
            refund_rows = []
            
            for _, row in df_all.iterrows():
                cat = str(row['Category']).strip()
                desc = str(row['Description']).strip()
                amt = float(row['Amount'])
                is_exp = int(row['IsExpense']) if 'IsExpense' in row else 1
                
                if cat == '환불':
                    desc_lower = desc.lower()
                    if any(k in desc_lower for k in ["호텔", "숙박", "인페라", "라이온", "스플랜디도", "벨몬트", "센터호텔", "agoda", "아고다", "booking", "소피아", "코럴베이", "파노라마"]):
                        refund_rows.append(row)
                        continue
                
                if cat in ['호텔', '숙박'] and is_exp == 1 and amt > 0:
                    h_name = clean_hotel_name(desc)
                    match_nights = re.search(r'(\d+)\s*박', desc)
                    nights = int(match_nights.group(1)) if match_nights else 0
                    
                    raw_hotel_rows.append({
                        'TripName': row['TripName'],
                        'Country': row['Country'],
                        'Date': row['Date'],
                        'Original_Desc': desc,
                        'Clean_Name': h_name if h_name else "알 수 없는 호텔",
                        'Nights': nights,
                        'Currency': row['Currency'],
                        'Amount': amt,
                        'AppliedRate': row['AppliedRate'],
                        'Cost_KRW': amt if row['Currency'] == 'KRW' else amt * row['AppliedRate'],
                        'Type': 'HOTEL_ROW'
                    })
                    
                elif cat in ['수수료', '기타'] and is_exp == 1 and amt > 0:
                    desc_lower = desc.lower()
                    if any(k in desc_lower for k in ["도시세", "시티택스", "시티 택스", "citytax", "city tax", "tourist tax"]):
                        h_name = clean_hotel_name(desc)
                        raw_hotel_rows.append({
                            'TripName': row['TripName'],
                            'Country': row['Country'],
                            'Date': row['Date'],
                            'Original_Desc': desc,
                            'Clean_Name': h_name if h_name else "알 수 없는 호텔",
                            'Nights': 0,
                            'Currency': row['Currency'],
                            'Amount': amt,
                            'AppliedRate': row['AppliedRate'],
                            'Cost_KRW': amt if row['Currency'] == 'KRW' else amt * row['AppliedRate'],
                            'Type': 'SURCHARGE_ROW'
                        })
            
            from collections import defaultdict
            grouped_hotels = defaultdict(list)
            for r in raw_hotel_rows:
                key = (r['TripName'], r['Country'], r['Clean_Name'])
                grouped_hotels[key].append(r)
                
            consolidated_hotels = []
            for key, rows in grouped_hotels.items():
                trip_name, country, clean_name = key
                
                rows_sorted = sorted(rows, key=lambda x: x['Cost_KRW'], reverse=True)
                primary_stay = rows_sorted[0]
                base_cost = primary_stay['Cost_KRW']
                nights = primary_stay['Nights']
                
                if nights == 0:
                    for r in rows_sorted[1:]:
                        if r['Nights'] > 0:
                            nights = r['Nights']
                            break
                
                if nights == 0:
                    continue
                
                extra_fees = sum(r['Cost_KRW'] for r in rows_sorted[1:])
                
                total_refund = 0.0
                total_refund_foreign = 0.0
                total_fx_loss = 0.0
                
                for r in refund_rows:
                    if r['TripName'] == trip_name:
                        r_desc = str(r['Description']).lower()
                        if clean_name.lower() in r_desc or any(k in r_desc for k in clean_name.lower().split()):
                            r_cost_krw = r['Amount'] if r['Currency'] == 'KRW' else r['Amount'] * r['AppliedRate']
                            total_refund += r_cost_krw
                            total_refund_foreign += r['Amount']
                            
                            expected_refund_krw = r['Amount'] * primary_stay['AppliedRate']
                            total_fx_loss += (r_cost_krw - expected_refund_krw)
                
                cancellation_rate = min(100.0, (total_refund_foreign / primary_stay['Amount']) * 100.0) if primary_stay['Amount'] > 0 else 0.0
                
                consolidated_hotels.append({
                    'TripName': trip_name,
                    'Country': country,
                    'Clean_Name': clean_name,
                    'Nights': nights,
                    'Cost_KRW': base_cost,
                    'Upgrade_Cost_KRW': extra_fees,
                    'Refund_KRW': total_refund,
                    'Cancellation_Rate': cancellation_rate,
                    'FX_GainLoss': total_fx_loss
                })

            if consolidated_hotels:
                display_hotel_rows = []
                chart_data = []
                
                for h in consolidated_hotels:
                    net_cost = h['Cost_KRW'] + h['Upgrade_Cost_KRW'] - h['Refund_KRW']
                    nights = h['Nights']
                    avg_rate = net_cost / nights if nights > 0 and h['Cancellation_Rate'] < 100.0 else 0.0
                    
                    status_str = "정상 투숙"
                    if h['Cancellation_Rate'] >= 100.0: status_str = "🔴 100% 취소"
                    elif h['Cancellation_Rate'] > 0.0: status_str = f"🟡 부분취소 ({h['Cancellation_Rate']:.1f}%)"
                    
                    fx_diff = h['FX_GainLoss']
                    fx_loss_str = f"{fx_diff:+,.0f}원" if fx_diff != 0 else "-"
                    base_price = h['Cost_KRW'] + h['Upgrade_Cost_KRW']
                    
                    display_hotel_rows.append({
                        '여행명': h['TripName'],
                        '국가': h['Country'],
                        '호텔명': h['Clean_Name'],
                        '숙박일수': f"{nights}박",
                        '기본숙박비(업글포함)': f"{base_price:,.0f}원",
                        '환불액': f"{h['Refund_KRW']:,.0f}원" if h['Refund_KRW'] > 0 else "-",
                        '실지불 순액(Net)': f"{max(0, net_cost):,.0f}원",
                        '1박당 평균': f"{avg_rate:,.0f}원" if avg_rate > 0 else "-",
                        '상태': status_str,
                        '환차손익(환율차이)': fx_loss_str
                    })
                    
                    if h['Cancellation_Rate'] < 100.0 and avg_rate > 0:
                        chart_data.append({
                            'Hotel_Label': f"<b>{h['Clean_Name']}</b><br><span style='font-size:11px; color:#A0AEC0;'>({h['TripName']})</span>",
                            '1박당 요금(원)': avg_rate
                        })
                
                st.dataframe(pd.DataFrame(display_hotel_rows), use_container_width=True, hide_index=True)
                
                if chart_data:
                    chart_df = pd.DataFrame(chart_data).sort_values(by='1박당 요금(원)', ascending=True)
                    
                    fig_hotel = px.bar(
                        chart_df, 
                        x='1박당 요금(원)', 
                        y='Hotel_Label', 
                        orientation='h',
                        color='1박당 요금(원)', 
                        color_continuous_scale='Blues', 
                        title="🏨 숙소별 1박 실질 투숙 비용 비교 (도시세/업그레이드 포함 / 취소 제외)"
                    )
                    
                    fig_hotel.update_traces(
                        texttemplate=" %{x:,.0f}원",
                        textposition="outside",
                        cliponaxis=False
                    )
                    
                    dynamic_hotel_height = max(450, len(chart_df) * 44 + 100)
                    
                    fig_hotel.update_layout(
                        xaxis=dict(fixedrange=True, title=None),
                        yaxis=dict(fixedrange=True, autorange="reversed", title=None),
                        dragmode=False,
                        margin=dict(l=10, r=80, t=40, b=30),
                        height=dynamic_hotel_height,
                        coloraxis_showscale=False
                    )
                    st.plotly_chart(fig_hotel, use_container_width=True, config={'displaylogo': False, 'scrollZoom': False, 'displayModeBar': False})
            else:
                st.info("비교할 호텔 숙박 내역이 없습니다.")

        # ----------------------------------------------------------------------
        # 5.03.00 | Channel 3: Flight Pricing Matrix (다구간 경유 노선 온전 추출)
        # ----------------------------------------------------------------------
        with sub_tab_flight:
            st.subheader("✈️ 항공권 요금 비교")
            st.caption("💡 각 항공권의 왕복/편도 여정을 구분하여 '1인당 왕복 환산 요금'으로 공평하게 비교합니다. 노선(Route)이 기재되지 않은 수화물/수수료 행은 해당 여행지의 메인 항공권에 자동으로 합산되며, 여행지별 설정된 인원수(Travelers)로 나누어 실질적인 '1인당 비용'을 산출합니다.")
            
            # 5.03.01 | Multi-Hop Flight Route Extractor
            def extract_airport_route(text):
                cleaned = re.sub(r'\[.*?\]', '', str(text)).strip()
                cleaned = re.split(r'[\(\|,]', cleaned)[0].strip()
                match = re.search(r'([가-힣a-zA-Z]+(?:\s*-\s*[가-힣a-zA-Z]+)+)', cleaned)
                if match:
                    parts = [p.strip() for p in re.split(r'\s*-\s*', match.group(0)) if p.strip()]
                    if len(parts) >= 2:
                        return "-".join(parts)
                return None

            primary_flights = []
            flight_surcharges = []
            flight_refund_rows = []
            
            for _, row in df_all.iterrows():
                cat = str(row['Category']).strip()
                desc = str(row['Description']).strip()
                amt = float(row['Amount'])
                
                if cat == '항공권' and amt > 0:
                    route = extract_airport_route(desc)
                    desc_lower = desc.lower()
                    
                    if "다구간" in desc_lower: f_type = "다구간"
                    elif "왕복" in desc_lower: f_type = "왕복"
                    elif "편도" in desc_lower: f_type = "편도"
                    else:
                        if any(k in desc_lower for k in ["귀국", "rt", "round"]): f_type = "왕복"
                        else: f_type = "편도"
                    
                    fee_val = 0.0
                    match_fee = re.search(r'수수료:(\d+)원', str(row['Note']))
                    if match_fee: fee_val = float(match_fee.group(1))
                    
                    flight_data = {
                        'TripName': row['TripName'],
                        'Country': row['Country'],
                        'Date': row['Date'],
                        'Original_Desc': desc,
                        'Route': route,
                        'Type': f_type,
                        'Currency': row['Currency'],
                        'Amount': amt,
                        'AppliedRate': row['AppliedRate'],
                        'Ticket_KRW': amt if row['Currency'] == 'KRW' else amt * row['AppliedRate'],
                        'Extra_Fee_KRW': fee_val,
                        'Surcharge_Sum_KRW': 0.0,
                        'Refund_KRW': 0.0,
                        'Refund_Foreign': 0.0,
                        'Refund_Rate': 0.0,
                        'Loss_KRW': 0.0
                    }
                    
                    if route: primary_flights.append(flight_data)
                    else: flight_surcharges.append(flight_data)
                        
                elif cat == '환불':
                    desc_lower = desc.lower()
                    if any(k in desc_lower for k in ["항공", "비행기", "페가수스", "세르비아", "항공사", "flight", "airline", "귁첸", "소피아", "베오그라드", "부다페스트", "티켓"]):
                        flight_refund_rows.append(row)

            # 5.03.02 | Surcharge Allocation & 1:1 Refund Matcher
            matched_refund_indices = set()
            
            for f in primary_flights:
                f_route = f['Route']
                f_trip = f['TripName']
                
                for s in flight_surcharges:
                    if s['TripName'] == f_trip:
                        f['Surcharge_Sum_KRW'] += s['Ticket_KRW']
                
                if f_route and '-' in f_route:
                    route_cities = [c.strip().lower() for c in f_route.split('-') if c.strip()]
                    dep_city, arr_city = route_cities[0], route_cities[-1]
                    
                    for r_idx, r in enumerate(flight_refund_rows):
                        if r_idx in matched_refund_indices: continue
                        if r['TripName'] != f_trip: continue
                            
                        r_desc = str(r['Description']).lower()
                        r_route = extract_airport_route(r['Description'])
                        is_exact_route = bool(r_route and r_route == f_route)
                        is_both_cities_in_desc = (dep_city in r_desc and arr_city in r_desc)
                        
                        if is_exact_route or is_both_cities_in_desc:
                            r_cost_krw = r['Amount'] if r['Currency'] == 'KRW' else r['Amount'] * r['AppliedRate']
                            f['Refund_KRW'] += r_cost_krw
                            f['Refund_Foreign'] += r['Amount']
                            matched_refund_indices.add(r_idx)
                
                num_travelers = travelers_map.get(f['TripName'], 2)
                total_initial = f['Ticket_KRW'] + f['Extra_Fee_KRW'] + f['Surcharge_Sum_KRW']
                f['Net_Cost_KRW'] = max(0, total_initial - f['Refund_KRW'])
                f['Refund_Rate'] = min(100.0, (f['Refund_Foreign'] / f['Amount']) * 100.0) if f['Amount'] > 0 else 0.0
                f['Loss_KRW'] = max(0, f['Ticket_KRW'] - f['Refund_KRW']) if f['Refund_KRW'] > 0 else 0.0
                
                f['Per_Person_Initial_KRW'] = total_initial / num_travelers
                f['Per_Person_Net_KRW'] = f['Net_Cost_KRW'] / num_travelers
                f['Per_Person_Loss_KRW'] = f['Loss_KRW'] / num_travelers
                f['Per_Person_Refund_KRW'] = f['Refund_KRW'] / num_travelers
                
                # 5.03.03 | Per-Person Roundtrip Equivalent Normalizer
                if f['Type'] == "편도": f['RT_Equivalent_Per_Person_KRW'] = f['Per_Person_Net_KRW'] * 2
                else: f['RT_Equivalent_Per_Person_KRW'] = f['Per_Person_Net_KRW']

            # 5.03.04 | Horizontal Flight Price Benchmark Bar Chart
            if primary_flights:
                display_flight_rows = []
                chart_flight_data = []
                
                for f in primary_flights:
                    status_str = "정상"
                    if f['Refund_Rate'] >= 99.0: status_str = "🔴 100% 취소"
                    elif f['Refund_Rate'] > 0.0: status_str = f"🟡 부분환불 ({f['Refund_Rate']:.1f}%)"
                    
                    num_travelers = int(travelers_map.get(f['TripName'], 2))
                    rt_eq_str = f"{f['RT_Equivalent_Per_Person_KRW']:,.0f}원 (왕복요금으로 환산)" if f['Type'] == "편도" else f"{f['RT_Equivalent_Per_Person_KRW']:,.0f}원"
                        
                    display_flight_rows.append({
                        '여행명': f['TripName'],
                        '노선(공항)': f['Route'],
                        '인원수': f"{num_travelers}인",
                        '구분': f['Type'],
                        '1인당 구매요금': f"{f['Per_Person_Initial_KRW']:,.0f}원",
                        '1인당 환불액': f"{f['Per_Person_Refund_KRW']:,.0f}원" if f['Per_Person_Refund_KRW'] > 0 else "-",
                        '환불율': f"{f['Refund_Rate']:.1f}%" if f['Refund_Rate'] > 0 else "-",
                        '1인당 취소손실': f"{f['Per_Person_Loss_KRW']:,.0f}원" if f['Per_Person_Loss_KRW'] > 0 else "-",
                        '1인당 실지불(Net)': f"{f['Per_Person_Net_KRW']:,.0f}원",
                        '1인당 왕복 환산 요금': rt_eq_str,
                        '상태': status_str
                    })
                    
                    if f['Refund_Rate'] == 0.0 and f['Refund_KRW'] <= 0 and f['RT_Equivalent_Per_Person_KRW'] > 0:
                        chart_flight_data.append({
                            'Flight_Label': f"<b>{f['Route']}</b><br><span style='font-size:11px; color:#A0AEC0;'>({f['TripName']})</span>",
                            '1인당 왕복 환산 요금(원)': f['RT_Equivalent_Per_Person_KRW']
                        })
                
                st.dataframe(pd.DataFrame(display_flight_rows), use_container_width=True, hide_index=True)
                
                if chart_flight_data:
                    chart_flight_df = pd.DataFrame(chart_flight_data).sort_values(by='1인당 왕복 환산 요금(원)', ascending=True)
                    
                    fig_flight = px.bar(
                        chart_flight_df, 
                        x='1인당 왕복 환산 요금(원)', 
                        y='Flight_Label', 
                        orientation='h',
                        color='1인당 왕복 환산 요금(원)', 
                        color_continuous_scale='Reds', 
                        title="✈️ 1인당 왕복 기준 항공요금 공평 비교 (편도 노선 2배 환산 적용 / 취소·환불 노선 제외)"
                    )
                    
                    fig_flight.update_traces(
                        texttemplate=" %{x:,.0f}원",
                        textposition="outside",
                        cliponaxis=False
                    )
                    
                    dynamic_chart_height = max(450, len(chart_flight_df) * 44 + 100)
                    
                    fig_flight.update_layout(
                        xaxis=dict(fixedrange=True, title=None),
                        yaxis=dict(fixedrange=True, autorange="reversed", title=None),
                        dragmode=False,
                        margin=dict(l=10, r=80, t=40, b=30),
                        height=dynamic_chart_height,
                        coloraxis_showscale=False
                    )
                    st.plotly_chart(fig_flight, use_container_width=True, config={'displaylogo': False, 'scrollZoom': False, 'displayModeBar': False})
            else:
                st.info("비교할 항공권 내역이 없습니다.")

# ------------------------------------------------------------------------------
# 5.04.00 | Global Provisioning View (새로운 여행지 개설 단독 화면)
# ------------------------------------------------------------------------------
elif st.session_state.get('show_new_trip', False):
    st.title("➕ 새로운 여행지 개설")
    st.info("💡 새로운 여행지를 개설하면 관제탑(`_GTL_CONFIG_`)에 자동 등록되고 전용 데이터베이스 시트가 생성됩니다.")
    
    with st.container():
        new_t_name = st.text_input("1. 여행 이름", placeholder="예: 🇨🇿 프라하 (2027)")
        new_s_name = st.text_input("2. 시트 이름 (영문/숫자/언더바만)", placeholder="예: PRG_2027")
        
        c_p1, c_p2, c_p3 = st.columns(3)
        with c_p1:
            new_curr = st.text_input("통화 코드", value="USD", key="prov_curr_final")
            new_sym = st.text_input("통화 기호", value="$", key="prov_sym_final")
        with c_p2:
            new_mult = st.selectbox("환율 배율", [1, 100], index=0, key="prov_mult_final")
            new_tz = st.number_input("현지 시차 (KST=9)", value=9, key="prov_tz_final")
        with c_p3:
            new_country = st.text_input("대표 국가명", value="미국", key="prov_country_final")

        default_cats = "식사,간식,마트,택시,지하철,트램,투어,입장료,마사지,팁,수수료,통신,보증금,항공권,호텔,보험,상환"
        new_cats_str = st.text_area("3. 카테고리 구성 (쉼표 구분)", value=default_cats, key="prov_cats_final")

        if st.button("🚀 서버에 새 여행지 즉시 개설", use_container_width=True, type="primary"):
            if new_t_name and new_s_name:
                cfg_df_p = conn.read(worksheet=CONFIG_SHEET, ttl="0s")
                new_entry = pd.DataFrame([{
                    "TripName": new_t_name, "SheetName": new_s_name,
                    "MainCountry": new_country, "Currency": new_curr,
                    "Symbol": new_sym, "Timezone": new_tz,
                    "Multiplier": new_mult, "Categories": new_cats_str
                }])
                conn.update(worksheet=CONFIG_SHEET, data=pd.concat([cfg_df_p, new_entry], ignore_index=True))
                
                new_sheet_df = pd.DataFrame(columns=FINAL_COLUMNS)
                try:
                    conn.update(worksheet=new_s_name, data=new_sheet_df)
                    st.success(f"🎉 '{new_t_name}' 여행지가 성공적으로 개설되었습니다!")
                    st.cache_data.clear()
                    st.session_state.show_new_trip = False
                    st.session_state.current_trip = new_t_name
                    time.sleep(1)
                    st.rerun()
                except:
                    st.warning(f"탭 '{new_s_name}'을 수동으로 생성해 주세요.")
                    st.cache_data.clear()
                    st.session_state.show_new_trip = False
                    st.session_state.current_trip = new_t_name
                    time.sleep(2)
                    st.rerun()

# ==============================================================================
# [Module 6.00.00] Main Ledger & Multi-Tab Analytics Engine
# ==============================================================================

# ------------------------------------------------------------------------------
# 6.00.01 | Common Preprocessing & Financial Calculation Engine (표준 대분류 장착)
# ------------------------------------------------------------------------------
trip_nodes = TRIP_CONFIGS[st.session_state.current_trip].get("nodes", {})
node_keys = list(trip_nodes.keys())
is_single_country = len(node_keys) <= 1
sel_node_default = node_keys[0] if node_keys else FIRST_NODE_NAME

# 여정 출국/귀국 날짜 및 시차 공통 계산
def is_korea_port_common(text):
    txt = str(text).replace(" ", "")
    return any(k in txt for k in ['한국', '인천', '부산', '김포', '대구', '제주', '청주', '귀국', 'ICN', 'PUS'])

def is_foreign_transit_common(cat_str):
    cat = str(cat_str).strip()
    if "_" in cat:
        sub_port = cat.split("_")[-1].strip()
        if not is_korea_port_common(sub_port): return True
    return False

dep_candidates = ledger_df[ledger_df['Category'].str.contains('출국', na=False) & ~ledger_df['Category'].apply(is_foreign_transit_common)]
korea_dep = ledger_df[ledger_df['Category'].apply(is_korea_port_common)]
target_dep_row = korea_dep if not korea_dep.empty else dep_candidates

dep_date_str = ""
dep_dt_calc = None
if not target_dep_row.empty:
    m_d = re.search(r'(\d{4}-\d{2})-(\d{2})', str(target_dep_row.iloc[0]['Date']))
    if m_d: 
        dep_date_str = m_d.group(0)
        dep_dt_calc = datetime.strptime(dep_date_str, "%Y-%m-%d").date()

korea_arr = ledger_df[ledger_df['Category'].str.contains('입국|귀국', na=False) & ledger_df['Category'].apply(is_korea_port_common)]
arr_candidates = ledger_df[ledger_df['Category'].str.contains('입국|귀국', na=False) & ~ledger_df['Category'].apply(is_foreign_transit_common)]
target_arr_row = korea_arr if not korea_arr.empty else arr_candidates

arr_date_str = ""
arr_dt_calc = None
if not target_arr_row.empty:
    m_a = re.search(r'(\d{4}-\d{2})-(\d{2})', str(target_arr_row.iloc[-1]['Date']))
    if m_a: 
        arr_date_str = m_a.group(0)
        arr_dt_calc = datetime.strptime(arr_date_str, "%Y-%m-%d").date()

today_kst_now = datetime.now(TZ_KST).date()
is_traveling_now = bool(dep_dt_calc and arr_dt_calc and dep_dt_calc <= today_kst_now <= arr_dt_calc)
dynamic_tz = timezone(timedelta(hours=trip_nodes.get(sel_node_default, FIRST_NODE)["timezone"])) if is_traveling_now else TZ_KST

def safe_parse_date_obj(d_str, fallback):
    if not d_str: return fallback
    s = str(d_str).strip()
    m_iso = re.search(r'(\d{4})[^\d](\d{1,2})[^\d](\d{1,2})', s)
    if m_iso:
        try: return dt_date(int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3)))
        except: pass
    month_map = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}
    m_eng = re.search(r'([a-zA-Z]+)\s*(\d{1,2}),?\s*(\d{4})', s)
    if m_eng:
        mon_str, day_str, year_str = m_eng.group(1).lower()[:3], m_eng.group(2), m_eng.group(3)
        if mon_str in month_map:
            try: return dt_date(int(year_str), month_map[mon_str], int(day_str))
            except: pass
    return fallback

if 'rcpt_key_idx' not in st.session_state: st.session_state.rcpt_key_idx = 0

# 🔥 [전역 공통 판별 함수] 고정비/사전결제 여부 판별
def check_is_fixed_cost(row):
    orig_d = str(row['Date']).strip()
    m_row = re.search(r'(\d{4})-(\d{2})-(\d{2})', orig_d)
    pure_d = m_row.group(0) if m_row else ""
    if dep_date_str and pure_d and pure_d < dep_date_str: return True
    cat = str(row['Category']).strip()
    met = str(row['PaymentMethod']).strip()
    return (met == '원화계좌(한국)') or (cat in FIXED_COST_CATS)

# 🔥 [핵심 비즈니스 규칙] 지출 원장(exp_df), 대분류(Macro_Category), 필수/고정비 완벽 일괄 생성
exp_df = ledger_df[ledger_df['IsExpense'] == 1].copy()
if not exp_df.empty:
    # 1. 원화 및 현지화 환산액 계산
    exp_df['KRW_val'] = exp_df.apply(
        lambda r: float(r['Amount']) if str(r['Currency']).strip() == 'KRW' else float(r['Amount']) * float(r['AppliedRate']),
        axis=1
    )
    exp_df['Local_val'] = exp_df.apply(
        lambda r: float(r['Amount']) if str(r['Currency']).strip() == TRAVEL_CURRENCY else (float(r['KRW_val']) / get_WAR(TRAVEL_CURRENCY) if get_WAR(TRAVEL_CURRENCY) > 0 else float(r['Amount'])),
        axis=1
    )

    # 2. 🌟 대분류(Macro_Category) 표준 컬럼 탑재 (KeyError 원천 차단)
    exp_df['Macro_Category'] = exp_df['Category'].map(MACRO_MAP).fillna("📱 기타/통신").astype(str)

    # 3. 필수지출(IsSurvival) 및 고정비(IsFixedCost) 판별
    def check_is_survival_cost(row):
        cat = str(row['Category']).strip()
        met = str(row['PaymentMethod']).strip()
        if cat in ['선물', '쇼핑', '호텔', '숙박', '항공권', '출국', '귀국', '렌트카', '보험', '통신', '수수료', '보증금', '개인지출']:
            return 0
        if met in ['원화계좌(한국)', '해외송금(한국계좌)']:
            return 0
        if cat in ['식사', '간식', '마트', 'Grab', 'VinBus', 'DiDi', '지하철', '택시', '교통', '마사지', '팁', '투어', '입장료', '기차', '상환']:
            return 1
        return 0

    exp_df['IsSurvival'] = exp_df.apply(check_is_survival_cost, axis=1)
    exp_df['IsFixedCost'] = exp_df.apply(check_is_fixed_cost, axis=1)

# ------------------------------------------------------------------------------
# 6.00.02 | Main 4-Tab Navigation Bar (Mobile 1-Line & Arrow Removal)
# ------------------------------------------------------------------------------
menu_options = ["가계부", "일일Data", "돋보기", "전체요약"]

if "current_main_tab" not in st.session_state:
    st.session_state["current_main_tab"] = "가계부"

current_tab = st.session_state["current_main_tab"]
default_idx = menu_options.index(current_tab) if current_tab in menu_options else 0

main_tab_choice = option_menu(
    menu_title=None,
    options=menu_options,
    icons=["", "", "", ""],  # 빈 문자열 4개로 ▷ 화살표 원천 차단
    default_index=default_idx,
    orientation="horizontal",
    styles={
        "container": {
            "padding": "0px !important",
            "margin": "0px auto 14px auto !important",
            "background-color": "transparent",
            "display": "flex !important",
            "flex-wrap": "nowrap !important",
            "width": "100% !important",
        },
        "icon": {
            "display": "none !important",
            "width": "0px !important",
            "margin": "0px !important",
        },
        "nav": {
            "display": "flex !important",
            "flex-wrap": "nowrap !important",
            "width": "100% !important",
        },
        "nav-link": {
            "font-size": "13px !important",
            "font-weight": "600 !important",
            "letter-spacing": "-0.5px !important",
            "text-align": "center !important",
            "padding": "8px 2px !important",
            "margin": "0px 1.5px !important",
            "white-space": "nowrap !important",
            "min-width": "0px !important",
            "flex": "1 1 0% !important",
            "border": "1px solid #334155",
            "border-radius": "6px",
            "color": "#94A3B8 !important",
            "background-color": "#1E293B",
            "--hover-color": "#334155 !important",
        },
        "nav-link-selected": {
            "background-color": "#EA580C !important",
            "color": "#FFFFFF !important",
            "font-weight": "700 !important",
            "border": "1px solid #EA580C !important",
        },
    },
    key="main_navbar_choice"
)

st.session_state["current_main_tab"] = main_tab_choice


# 6.01.00 | Unified Ledger Console (가계부 탭)
# ==============================================================================
if main_tab_choice == "가계부":
    with st.expander("➕ 새 지출 / 일정 / 바우처 등록하기", expanded=False):
        if is_single_country:
            sel_node = node_keys[0] if node_keys else FIRST_NODE_NAME
            IN_CFG = trip_nodes.get(sel_node, FIRST_NODE)
            IN_CURR = IN_CFG["currency"]
            IN_MULTI = IN_CFG["multiplier"]
            mode = st.radio("기록 모드 선택", ["일반 지출", "🛫 항공권(특수)", "🏨 호텔(특수)", "자산 이동", "환불(취소)"], horizontal=True, key="mode_radio", label_visibility="collapsed")
        else:
            c_node, c_mode = st.columns([1, 2])
            with c_node:
                sel_node = st.selectbox("🌍 국가 선택", node_keys, key="in_country")
                IN_CFG = trip_nodes[sel_node]
                IN_CURR = IN_CFG["currency"]
                IN_MULTI = IN_CFG["multiplier"]
            with c_mode:
                mode = st.radio("기록 모드 선택", ["일반 지출", "🛫 항공권(특수)", "🏨 호텔(특수)", "자산 이동", "환불(취소)"], horizontal=True, key="mode_radio", label_visibility="collapsed")

        if 'ai_payment_date' in st.session_state and st.session_state['ai_payment_date']:
            default_cal_val = st.session_state.pop('ai_payment_date')
            st.session_state['shared_date_input'] = default_cal_val
        elif 'shared_date_input' not in st.session_state:
            st.session_state['shared_date_input'] = datetime.now(dynamic_tz).date()

        sel_date = st.date_input("날짜 선택", key="shared_date_input")
        node_currs = [node["currency"] for node in trip_nodes.values()]
        available_currs = sorted(list(set(node_currs + ["KRW", "USD", "EUR"])))

        if mode == "일반 지출":
            base_daily_cats = [c for c in EXPENSE_CATS if c not in ['항공권', '호텔', '보증금', '상환', '보험']]
            if "선물" not in base_daily_cats:
                if "마트" in base_daily_cats:
                    idx_m = base_daily_cats.index("마트")
                    clean_daily_cats = base_daily_cats[:idx_m+1] + ["선물"] + base_daily_cats[idx_m+1:]
                else:
                    clean_daily_cats = ["식사", "간식", "마트", "선물", "교통", "기타"]
            else:
                clean_daily_cats = base_daily_cats

            def_index = clean_daily_cats.index(st.session_state.last_cat_name) if st.session_state.last_cat_name in clean_daily_cats else 0
            cat = st.radio("항목 선택", clean_daily_cats, index=def_index, horizontal=True, key="exp_cat")
            st.session_state.last_cat_name = cat
            
            if st.session_state.get('clear_exp_desc', False):
                st.session_state.exp_desc_input = ""
                st.session_state.clear_exp_desc = False
                st.session_state.gift_items_selected = []
                
            col_desc, col_receipt = st.columns([3, 1.2])
            with col_receipt: 
                uploaded_files = st.file_uploader("📸 영수증 첨부 (사진/PDF)", type=['png', 'jpg', 'jpeg', 'pdf'], key="exp_direct_uploader", accept_multiple_files=True)
                if uploaded_files:
                    if st.button("🤖 영수증 AI 스캔 (통합 번역)", key="btn_ai_exp_direct", use_container_width=True, type="primary"):
                        with st.spinner("AI가 영수증 품목, 총금액, 결제일자를 정밀 분석 중..."):
                            smart_text, pay_date, total_amt = summarize_receipt_files_with_gemini(uploaded_files)
                            if smart_text:
                                st.session_state['exp_desc_input'] = smart_text
                                if total_amt > 0:
                                    st.session_state['exp_amt_int'] = int(total_amt)
                                    st.session_state['exp_amt_float'] = float(total_amt)
                                if pay_date:
                                    parsed_dt = safe_parse_date_obj(pay_date, None)
                                    if parsed_dt: 
                                        st.session_state['ai_payment_date'] = parsed_dt
                                st.toast(f"🎉 영수증 분석 완료! 금액: {total_amt:,.0f} 자동 입력", icon="✅")
                                time.sleep(0.3)
                                st.rerun()
                            else:
                                st.error("🚨 영수증 인식을 완료하지 못했습니다.")
                                
            with col_desc: 
                desc = st.text_area("📝 내용 (상호명 및 다중 내역)", placeholder="예: 안바카페 - 소고기버거\n반미정식", height=120, key="exp_desc_input")

            def parse_amount_from_line(line_text):
                m_k = re.search(r'(\d+(?:\.\d+)?)\s*[kK]', line_text)
                if m_k: return float(m_k.group(1)) * 1000
                nums = re.findall(r'(\d{1,3}(?:,\d{3})+|\d+)', line_text)
                if nums:
                    try: return float(nums[-1].replace(',', ''))
                    except: pass
                return 0.0

            gift_sum_amt = 0.0
            candidate_item_lines = []
            store_header_in = ""
            
            if desc and any(ch.isdigit() for ch in desc):
                raw_lines = [l.strip() for l in desc.split("\n") if l.strip()]
                for idx_l, l_text in enumerate(raw_lines):
                    val_chk = parse_amount_from_line(l_text)
                    if idx_l == 0 and val_chk == 0 and not l_text.startswith("-"):
                        store_header_in = l_text
                    elif val_chk > 0 or l_text.startswith("-"):
                        candidate_item_lines.append(l_text)

                if cat != "선물" and candidate_item_lines:
                    with st.expander("🎁 선물/특산품 분리 지정 (순수 일일 체류비 왜곡 방지)", expanded=True):
                        st.caption("💡 마트/간식 중 **선물/기념품**을 체크하시면 해당 품목만 '선물' 항목으로 자동 분리됩니다.")
                        selected_gifts = []
                        cols_g = st.columns(min(3, max(1, len(candidate_item_lines))))
                        for idx_l, line_str in enumerate(candidate_item_lines):
                            val_l = parse_amount_from_line(line_str)
                            disp_l = re.sub(r'^[\-\*•\s]+', '', line_str)
                            c_box = cols_g[idx_l % len(cols_g)].checkbox(f"🎁 {disp_l[:20]}..", key=f"chk_gift_new_{idx_l}")
                            if c_box:
                                selected_gifts.append(line_str)
                                gift_sum_amt += val_l
                        st.session_state.gift_items_selected = selected_gifts
                        if gift_sum_amt > 0:
                            st.info(f"선물/특산품 분리 지정액: **{gift_sum_amt:,.0f}**")
                elif cat == "선물":
                    st.caption("✨ 현재 선택된 카테고리가 **'선물'**이므로, 전체 금액이 선물 지출로 자동 기록됩니다.")

            col_m1, col_m2, col_m3 = st.columns([1, 1, 1])
            with col_m1: 
                primary_currs = [IN_CURR, "KRW", "USD", "EUR"]
                curr_opts = [c for i, c in enumerate(primary_currs) if c not in primary_currs[:i]] + [c for c in available_currs if c not in primary_currs]
                curr = st.selectbox("통화", curr_opts, key="exp_curr")
            with col_m2:
                if curr != "KRW": met_options = [f"현금({curr})", f"트래블카드({curr})", f"호텔외상({curr})", "원화계좌(한국)", "해외송금(한국계좌)", "원화계좌(현지)"]
                else: met_options = ["원화계좌(한국)", "원화계좌(현지)"]
                met = st.selectbox("결제 자산(Asset)", met_options, index=0, key="exp_met")
            with col_m3:
                harvested_tags = set()
                if not ledger_df.empty:
                    extracted = ledger_df['Description'].str.extractall(r'\[(.*?)\]')
                    if not extracted.empty: harvested_tags = set(extracted[0].dropna().unique())
                raw_gateways = ["알리페이", "위챗페이", "네이버페이", "카카오페이", "Apple Pay", "토스페이", "Trip.com", "Agoda", "Booking.com", "Uber", "Bolt", "Revolut"]
                other_gateways = sorted(list((set(raw_gateways) | harvested_tags) - {"선택안함 (기본)"}))
                combined_gateways = ["선택안함 (기본)"] + other_gateways + ["➕ 직접 입력하기"]
                gateway_sel = st.selectbox("결제 플랫폼 (Gateway)", combined_gateways, index=0, key="exp_gw")
                final_gateway = ""
                if gateway_sel == "➕ 직접 입력하기": final_gateway = st.text_input("새 플랫폼 이름 입력", placeholder="예: 마이리얼트립")
                elif gateway_sel != "선택안함 (기본)": final_gateway = gateway_sel

            col_a1, col_a2 = st.columns(2)
            with col_a1:
                if curr == "KRW" or (curr == IN_CURR and IN_MULTI == 100): 
                    if 'exp_amt_int' not in st.session_state: st.session_state['exp_amt_int'] = 0
                    amt = st.number_input(f"금액 ({curr})", min_value=0, step=1000 if curr != "KRW" else 1, format="%d", key="exp_amt_int")
                else: 
                    if 'exp_amt_float' not in st.session_state: st.session_state['exp_amt_float'] = 0.0
                    amt = st.number_input(f"금액 ({curr})", min_value=0.0, step=1.0, format="%.2f", key="exp_amt_float")
            with col_a2:
                if curr != "KRW" and amt > 0:
                    calc_rate = auto_calc_fifo_rate(amt, met, curr)
                    st.caption(f"💡 {curr} 계산 환율: **{calc_rate:.5f}**")
                    cr_final = st.number_input("확정 환율", value=float(calc_rate), format="%.5f", key=f"exp_cr_auto_{met}_{amt}")
                else: cr_final = st.number_input("확정 환율", value=(1.0 if curr=="KRW" else get_default_rate(curr)), format="%.5f", key=f"exp_cr_man_{curr}")
                
            if st.button("🚀 지출 기록하기", use_container_width=True, type="primary"):
                if amt <= 0:
                    st.warning("결제 금액을 0원보다 크게 입력해 주세요.")
                    st.stop()

                final_receipt_urls = ""
                if uploaded_files:
                    with st.spinner("📸 영수증 클라우드 보관 중..."):
                        u_list = [upload_image_to_imgbb(f) for f in uploaded_files if upload_image_to_imgbb(f)]
                        final_receipt_urls = ",".join(u_list)
                
                total_amt_val = float(amt)
                new_rows_to_add = []
                base_store_line = store_header_in if store_header_in else (candidate_item_lines[0] if candidate_item_lines else "상호명미기재")
                
                if cat == "선물" or (gift_sum_amt >= total_amt_val and total_amt_val > 0):
                    f_desc = f"[{final_gateway}] {desc}" if final_gateway else desc
                    new_rows_to_add.append({
                        'Date': sel_date.strftime("%Y-%m-%d(%a)"),
                        'Country': sel_node,
                        'Category': '선물',
                        'Description': f_desc.strip(),
                        'Currency': curr,
                        'Amount': total_amt_val,
                        'PaymentMethod': met,
                        'IsExpense': 1,
                        'AppliedRate': cr_final,
                        'Note': '100% Gift',
                        'Receipt_URL': final_receipt_urls
                    })
                elif gift_sum_amt > 0 and (total_amt_val - gift_sum_amt) > 0:
                    rem_amt = total_amt_val - gift_sum_amt
                    norm_lines = [l for l in candidate_item_lines if l not in st.session_state.gift_items_selected]
                    gift_lines = st.session_state.gift_items_selected
                    
                    d_norm = f"{base_store_line}\n" + "\n".join(norm_lines) if norm_lines else base_store_line
                    d_gift = f"{base_store_line}\n" + "\n".join(gift_lines) if gift_lines else base_store_line
                    f_d_norm = f"[{final_gateway}] {d_norm}" if final_gateway else d_norm
                    f_d_gift = f"[{final_gateway}] {d_gift}" if final_gateway else d_gift
                    
                    new_rows_to_add.append({'Date': sel_date.strftime("%Y-%m-%d(%a)"), 'Country': sel_node, 'Category': cat, 'Description': f_d_norm.strip(), 'Currency': curr, 'Amount': rem_amt, 'PaymentMethod': met, 'IsExpense': 1, 'AppliedRate': cr_final, 'Note': 'Normal Split', 'Receipt_URL': final_receipt_urls})
                    new_rows_to_add.append({'Date': sel_date.strftime("%Y-%m-%d(%a)"), 'Country': sel_node, 'Category': '선물', 'Description': f_d_gift.strip(), 'Currency': curr, 'Amount': gift_sum_amt, 'PaymentMethod': met, 'IsExpense': 1, 'AppliedRate': cr_final, 'Note': 'Gift Split', 'Receipt_URL': final_receipt_urls})
                else:
                    f_desc = f"[{final_gateway}] {desc}" if final_gateway else desc
                    new_rows_to_add.append({'Date': sel_date.strftime("%Y-%m-%d(%a)"), 'Country': sel_node, 'Category': cat, 'Description': f_desc.strip(), 'Currency': curr, 'Amount': total_amt_val, 'PaymentMethod': met, 'IsExpense': 1, 'AppliedRate': cr_final, 'Note': '', 'Receipt_URL': final_receipt_urls})

                new_rows_df = pd.DataFrame(new_rows_to_add)
                if append_new_data(new_rows_df):
                    st.toast("🎉 지출이 메모리에 기록되었습니다! Google Sheets는 최종 저장 시 한 번에 반영됩니다.", icon="✅")
                    st.session_state.clear_exp_desc = True
                    time.sleep(0.2)
                    st.rerun()

        elif mode == "🛫 항공권(특수)":
            st.subheader("✈️ 항공권 및 스케줄 통합 기록")
            col_f_input, col_f_rcpt = st.columns([3, 1.2])
            with col_f_rcpt:
                uploaded_flight_files = st.file_uploader("📸 e-티켓 첨부", type=['png', 'jpg', 'jpeg', 'pdf'], key=f"flight_rcpt_{st.session_state.rcpt_key_idx}", accept_multiple_files=True)
                if uploaded_flight_files:
                    if st.button("🤖 e-티켓 AI 자동분석", key="btn_ai_flight", use_container_width=True, type="primary"):
                        parsed = parse_flight_ticket_files_with_gemini(uploaded_flight_files)
                        if parsed:
                            st.session_state['f_gw_input'] = parsed.get('platform', '트립닷컴')
                            st.session_state['f_carrier_input'] = parsed.get('carrier', '')
                            st.session_state['f_route_input'] = parsed.get('route', '')
                            st.session_state['f_dep_info_input'] = parsed.get('dep_info', '')
                            st.session_state['f_ret_info_input'] = parsed.get('ret_info', '')
                            st.session_state['f_bag_memo_input'] = parsed.get('bag_memo', '')
                            st.session_state['f_amt_input'] = clean_amount_to_float(parsed.get('amount', 0.0))
                            if parsed.get('currency'): st.session_state['f_curr_select'] = str(parsed.get('currency')).upper()
                            if parsed.get('trip_type') in ["왕복", "편도"]: st.session_state['f_trip_type_radio'] = parsed.get('trip_type')
                            if parsed.get('dep_date'): st.session_state['f_dep_date_input'] = safe_parse_date_obj(parsed.get('dep_date'), datetime.now().date())
                            if parsed.get('ret_date'): st.session_state['f_ret_date_input'] = safe_parse_date_obj(parsed.get('ret_date'), datetime.now().date() + timedelta(days=7))
                            if parsed.get('payment_date'): st.session_state['ai_payment_date'] = safe_parse_date_obj(parsed.get('payment_date'), datetime.now().date())
                            st.toast("✈️ e-티켓 정보 자동 입력 완료!", icon="🎉")
                            time.sleep(0.3); st.rerun()

            with col_f_input:
                f_trip_type = st.radio("여정 구분", ["왕복", "편도"], horizontal=True, key="f_trip_type_radio")
                c1, c2, c3 = st.columns(3)
                with c1: f_gw = st.text_input("1. 결제 플랫폼", placeholder="예: 트립닷컴", key="f_gw_input")
                with c2: f_carrier = st.text_input("2. 항공사", placeholder="예: 비엣젯항공", key="f_carrier_input")
                with c3: f_route = st.text_input("3. 노선", placeholder="예: 부산-다낭", key="f_route_input")

                c4, c5 = st.columns(2)
                with c4:
                    st.info(f"🛫 {'출국' if f_trip_type == '왕복' else '탑승'} 스케줄")
                    f_dep_info = st.text_input("4. 스케줄 정보", placeholder="예: VJ969, 07:45 - 11:10", key="f_dep_info_input")
                    f_dep_date = st.date_input("5. 탑승 날짜", value=st.session_state.get('f_dep_date_input', sel_date), key="f_dep_date_input")
                with c5:
                    if f_trip_type == "왕복":
                        st.success("🛬 귀국 스케줄")
                        f_ret_info = st.text_input("6. 귀국편 정보", placeholder="예: VJ968, 23:10 - 06:40 (+1)", key="f_ret_info_input")
                        f_ret_date = st.date_input("7. 귀국 날짜", value=st.session_state.get('f_ret_date_input', sel_date + timedelta(days=7)), key="f_ret_date_input")
                    else: f_ret_info, f_ret_date = "", None

                c6, c7, c8 = st.columns([1, 1, 1])
                with c6: f_baggage = st.selectbox("8. 위탁수화물", ["포함", "미포함", "일부포함"], key="f_baggage_select")
                with c7: f_bag_memo = st.text_input("9. 수화물 상세", placeholder="예: 20kg 무료", key="f_bag_memo_input")
                with c8: f_asset = st.selectbox("10. 결제 수단", ["네이버페이(원화고정)", "원화계좌(한국)", "해외송금(한국계좌)", "트래블카드(외화)", "신용카드(원화결제)", "기타"], key="f_asset_select")
                f_memo = st.text_input("📝 비고/메모", key="f_memo_input")

            st.divider()
            c9, c10, c11, c12 = st.columns([1, 2, 1, 1])
            with c9: 
                curr_opts_flight = ["KRW", "USD", "EUR"] + [c for c in available_currs if c not in ["KRW", "USD", "EUR"]]
                f_curr = st.selectbox("11. 통화", curr_opts_flight, key="f_curr_select")
            with c10: 
                f_amt_val = clean_amount_to_float(st.session_state.get('f_amt_input', 0.0))
                f_amt = st.number_input(f"12. 결제 금액({f_curr})", min_value=0.0, value=f_amt_val, step=1.0, key="f_amt_input")
            with c11: f_rate = st.number_input("13. 환율", value=1.0 if f_curr=="KRW" or "네이버" in f_asset else get_default_rate(f_curr), format="%.4f")
            with c12: f_fee = st.number_input("14. 수수료(원)", min_value=0)

            if st.button("🚀 항공권 및 일정 동시 기록", use_container_width=True, type="primary"):
                if not f_gw or not f_route: st.warning("결제 플랫폼과 노선 정보는 필수입니다."); st.stop()
                clean_asset = f_asset.split('(')[0].strip()
                if "트래블카드" in f_asset: clean_asset = f"트래블카드({f_curr})"
                u_list = [upload_image_to_imgbb(f) for f in uploaded_flight_files if upload_image_to_imgbb(f)] if uploaded_flight_files else []
                final_flight_receipts = ",".join(u_list)

                route_str = f" | 출국:{f_dep_info}" if f_dep_info else ""
                ret_str = f" | 귀국:{f_ret_info}" if f_trip_type == "왕복" and f_ret_info else ""
                memo_str = f" | 메모:{f_memo}" if f_memo else ""
                full_desc = f"[{f_gw}+{clean_asset}] {f_route}({f_carrier}){route_str}{ret_str} | 수화물:{f_baggage}({f_bag_memo}){memo_str}"
                flight_row = pd.DataFrame([{'Date': sel_date.strftime("%Y-%m-%d(%a)"), 'Country': sel_node, 'Category': '항공권', 'Description': full_desc, 'Currency': f_curr, 'Amount': f_amt, 'PaymentMethod': clean_asset, 'IsExpense': 1, 'AppliedRate': f_rate, 'Note': f"수수료:{f_fee}원" if f_fee > 0 else "", 'Receipt_URL': final_flight_receipts}])
                
                new_rows = [flight_row]
                if f_dep_info:
                    dep_row = pd.DataFrame([{'Date': f_dep_date.strftime("%Y-%m-%d(%a)"), 'Country': sel_node, 'Category': '출국' if f_trip_type == '왕복' else '항공스케줄', 'Description': f"🛫 {f_route} 출국 ({f_dep_info})", 'Currency': 'KRW', 'Amount': 0, 'PaymentMethod': '정보', 'IsExpense': 0, 'AppliedRate': 1.0, 'Note': 'Auto-created', 'Receipt_URL': ''}])
                    new_rows.append(dep_row)
                if f_trip_type == "왕복" and f_ret_info:
                    arr_row = pd.DataFrame([{'Date': f_ret_date.strftime("%Y-%m-%d(%a)"), 'Country': sel_node, 'Category': '귀국', 'Description': f"🛬 {f_route} 귀국 ({f_ret_info})", 'Currency': 'KRW', 'Amount': 0, 'PaymentMethod': '정보', 'IsExpense': 0, 'AppliedRate': 1.0, 'Note': 'Auto-created', 'Receipt_URL': ''}])
                    new_rows.append(arr_row)
                
                if append_new_data(pd.concat(new_rows, ignore_index=True)):
                    st.toast("🎉 항공권과 일정이 모두 기록되었습니다!", icon="✅")
                    for k in ['f_gw_input', 'f_carrier_input', 'f_route_input', 'f_dep_info_input', 'f_ret_info_input', 'f_bag_memo_input', 'f_amt_input', 'f_memo_input']:
                        if k in st.session_state: del st.session_state[k]
                    time.sleep(0.5); st.rerun()

        elif mode == "🏨 호텔(특수)":
            st.subheader("🏨 호텔 4대 통합 관리")
            hotel_sub_mode = st.radio("호텔 업무 선택", ["🏨 호텔 예약/결제 (체크인·아웃 자동생성)", "🏷️ 체크인 보증금 결제 (Deposit)", "🔙 체크아웃 보증금 환급 (Deposit Return)", "💳 체크아웃 외상 청산"], horizontal=True, key="hotel_sub_mode_radio")
            st.divider()

            if "호텔 예약/결제" in hotel_sub_mode:
                col_h_input, col_h_rcpt = st.columns([3, 1.2])
                with col_h_rcpt:
                    uploaded_hotel_files = st.file_uploader("📸 호텔 바우처 첨부", type=['png', 'jpg', 'jpeg', 'pdf'], key="hotel_direct_uploader", accept_multiple_files=True)
                    if uploaded_hotel_files:
                        if st.button("🤖 바우처 AI 자동분석 & 폼 채우기", key="btn_ai_hotel_direct", use_container_width=True, type="primary"):
                            with st.spinner("AI가 호텔 바우처/스펙을 분석 중..."):
                                parsed, err = parse_hotel_voucher_files_with_gemini(uploaded_hotel_files)
                                if parsed:
                                    st.session_state['h_gw_input'] = parsed.get('platform', 'Agoda')
                                    st.session_state['h_name_input'] = parsed.get('hotel_name', '')
                                    st.session_state['h_detail_input'] = parsed.get('room_detail', '')
                                    st.session_state['h_nights_input'] = max(1, int(parsed.get('nights', 1)))
                                    st.session_state['h_amt_input'] = clean_amount_to_float(parsed.get('amount', 0.0))
                                    st.session_state['h_star_select'] = parsed.get('star_rating', '4성급')
                                    st.session_state['h_area_input'] = int(parsed.get('room_area', 0))
                                    st.session_state['h_balcony_select'] = "유" if parsed.get('has_balcony') == "유" else "무"
                                    st.session_state['h_cancel_rate_input'] = int(parsed.get('cancel_rate', 100))
                                    if parsed.get('cancel_deadline'): st.session_state['h_cancel_date_input'] = safe_parse_date_obj(parsed.get('cancel_deadline'), None)
                                    if parsed.get('currency'): st.session_state['h_curr_select'] = str(parsed.get('currency')).upper()
                                    if parsed.get('payment_method'):
                                        pm = str(parsed.get('payment_method'))
                                        for cand in ["네이버페이(원화고정)", "원화계좌(한국)", "해외송금(한국계좌)", "트래블카드(외화)", "신용카드(원화결제)"]:
                                            if any(k in pm for k in ["네이버", "원화계좌", "트래블", "신용카드"]):
                                                st.session_state['h_asset_select'] = cand; break
                                    if parsed.get('checkin_date'): st.session_state['h_checkin_input'] = safe_parse_date_obj(parsed.get('checkin_date'), datetime.now().date())
                                    if parsed.get('payment_date'): st.session_state['ai_payment_date'] = safe_parse_date_obj(parsed.get('payment_date'), datetime.now().date())
                                    st.toast("🎉 호텔 바우처 스펙 및 결제정보 자동 입력 완료!", icon="✅")
                                    time.sleep(0.3); st.rerun()
                                else: st.error(f"🚨 분석 실패 사유: {err}")

                with col_h_input:
                    c1, c2 = st.columns(2)
                    with c1:
                        h_gw = st.text_input("1. 결제 플랫폼", placeholder="예: Agoda", key="h_gw_input")
                        h_name = st.text_input("2. 호텔명", placeholder="예: 사누바 다낭 호텔", key="h_name_input")
                        if 'h_checkin_input' not in st.session_state: st.session_state['h_checkin_input'] = sel_date
                        h_checkin = st.date_input("3. 체크인 날짜", key="h_checkin_input")
                        hotel_assets = ["네이버페이(원화고정)", "원화계좌(한국)", "해외송금(한국계좌)", "트래블카드(외화)", "신용카드(원화결제)", "기타"]
                        if 'h_asset_select' not in st.session_state: st.session_state['h_asset_select'] = hotel_assets[0]
                        h_asset = st.selectbox("4. 결제 수단", hotel_assets, key="h_asset_select")
                    with c2:
                        if 'h_nights_input' not in st.session_state: st.session_state['h_nights_input'] = 1
                        h_nights = st.number_input("5. 숙박 일수", min_value=1, step=1, key="h_nights_input")
                        h_checkout_calc = h_checkin + timedelta(days=int(h_nights))
                        st.info(f"📅 체크아웃 예정일: **{h_checkout_calc.strftime('%Y-%m-%d')}** ({h_nights}박)")
                        h_detail = st.text_area("6. 내용 (룸타입/혜택)", placeholder="예: 디럭스 트윈 시티뷰, 데일리 애프터눈티", height=68, key="h_detail_input")
                        h_curr_opts = ["KRW", "USD", "EUR", "VND", "PHP", "CNY", "TRY"]
                        if 'h_curr_select' not in st.session_state: st.session_state['h_curr_select'] = "KRW"
                        h_curr = st.selectbox("7. 결제 통화", h_curr_opts, key="h_curr_select")

                st.markdown("<div style='font-size: 13px; font-weight: bold; color: #38BDF8;'>🏷️ 호텔 상세 스펙 및 취소 정책</div>", unsafe_allow_html=True)
                cs1, cs2, cs3, cs4, cs5 = st.columns([1.2, 1, 1, 1.4, 1.2])
                with cs1:
                    star_opts = ["5성급", "4성급", "3성급", "2성급 이하", "리조트/풀빌라", "기타"]
                    cur_star = st.session_state.get('h_star_select', '4성급')
                    h_star = st.selectbox("성급(Star)", star_opts, index=star_opts.index(cur_star) if cur_star in star_opts else 1, key="h_star_select")
                with cs2: h_area = st.number_input("면적(㎡)", min_value=0, max_value=500, value=int(st.session_state.get('h_area_input', 0)), step=1, key="h_area_input")
                with cs3:
                    cur_bal = st.session_state.get('h_balcony_select', '무')
                    h_balcony = st.selectbox("발코니", ["유", "무"], index=0 if cur_bal=="유" else 1, key="h_balcony_select")
                with cs4: h_cancel_date = st.date_input("취소 마감일", value=st.session_state.get('h_cancel_date_input', None), key="h_cancel_date_input")
                with cs5: h_cancel_rate = st.number_input("환불율(%)", min_value=0, max_value=100, value=int(st.session_state.get('h_cancel_rate_input', 100)), step=10, key="h_cancel_rate_input")

                c3, c4, c5 = st.columns(3)
                with c3: 
                    if 'h_amt_input' not in st.session_state: st.session_state['h_amt_input'] = 0.0
                    h_amt = st.number_input(f"8. 결제 금액({h_curr})", min_value=0.0, step=1.0, key="h_amt_input")
                with c4: h_rate = st.number_input("9. 적용 환율", value=1.0 if h_curr=="KRW" or "네이버" in h_asset else get_default_rate(h_curr), format="%.4f")
                with c5: h_fee = st.number_input("10. 환율 수수료(원)", min_value=0)

                if st.button("🚀 호텔 예약 및 체크인·체크아웃 동시 저장", use_container_width=True, type="primary"):
                    if not h_gw or not h_name: st.warning("결제 플랫폼과 호텔명을 입력하세요."); st.stop()
                    clean_asset = f"트래블카드({h_curr})" if "트래블카드" in h_asset else h_asset.split('(')[0].strip()
                    u_list = [upload_image_to_imgbb(f) for f in uploaded_hotel_files if upload_image_to_imgbb(f)] if uploaded_hotel_files else []
                    final_hotel_receipts = ",".join(u_list)

                    spec_tags = []
                    if h_star: spec_tags.append(f"{h_star}")
                    if h_area > 0: spec_tags.append(f"{h_area}㎡")
                    if h_balcony == "유": spec_tags.append("발코니")
                    if h_cancel_date: spec_tags.append(f"취소마감:{h_cancel_date.strftime('%m/%d')}({h_cancel_rate}%환불)")
                    spec_str = f" | [{' · '.join(spec_tags)}]" if spec_tags else ""

                    full_desc = f"[{h_gw}+{clean_asset}] {h_name} | {h_nights}박({h_checkin.strftime('%m/%d')}~{h_checkout_calc.strftime('%m/%d')}) | {h_detail.replace(chr(10), ' ')}{spec_str}"
                    hotel_pay_row = pd.DataFrame([{'Date': sel_date.strftime("%Y-%m-%d(%a)"), 'Country': sel_node, 'Category': '호텔', 'Description': full_desc, 'Currency': h_curr, 'Amount': h_amt, 'PaymentMethod': clean_asset, 'IsExpense': 1, 'AppliedRate': h_rate, 'Note': f"수수료:{f_fee}원" if h_fee > 0 else "", 'Receipt_URL': final_hotel_receipts}])
                    checkin_row = pd.DataFrame([{'Date': h_checkin.strftime("%Y-%m-%d(%a)"), 'Country': sel_node, 'Category': '체크인', 'Description': f"체크인 🏨 {h_name} ({h_nights}박)", 'Currency': h_curr, 'Amount': 0, 'PaymentMethod': '정보', 'IsExpense': 0, 'AppliedRate': 1.0, 'Note': 'Auto-Checkin', 'Receipt_URL': ''}])
                    checkout_row = pd.DataFrame([{'Date': h_checkout_calc.strftime("%Y-%m-%d(%a)"), 'Country': sel_node, 'Category': '체크아웃', 'Description': f"체크아웃 🏨 {h_name}", 'Currency': h_curr, 'Amount': 0, 'PaymentMethod': '정보', 'IsExpense': 0, 'AppliedRate': 1.0, 'Note': 'Auto-Checkout', 'Receipt_URL': ''}])
                    
                    if append_new_data(pd.concat([hotel_pay_row, checkin_row, checkout_row], ignore_index=True)):
                        st.toast(f"🎉 '{h_name}' 예약 및 체크인/아웃 일정이 자동 생성되었습니다!", icon="✅")
                        for k in ['h_gw_input', 'h_name_input', 'h_checkin_input', 'h_nights_input', 'h_detail_input', 'h_amt_input']:
                            if k in st.session_state: del st.session_state[k]
                        time.sleep(0.5); st.rerun()

            elif "체크인 보증금 결제" in hotel_sub_mode:
                c_d1, c_d2 = st.columns(2)
                with c_d1:
                    dep_h_name = st.text_input("호텔명", placeholder="예: 사누바 다낭 호텔")
                    dep_curr = st.selectbox("보증금 통화", available_currs, index=available_currs.index(IN_CURR) if IN_CURR in available_currs else 0)
                    dep_amt = st.number_input(f"금액 ({dep_curr})", min_value=0.0, step=1000.0 if dep_curr=="VND" else 10.0)
                with c_d2:
                    dep_pay_source = st.selectbox("결제 수단", [f"트래블카드({dep_curr})", f"현금({dep_curr})", "신용카드(원화결제)"])
                    dep_desc = st.text_input("메모", value=f"[{dep_h_name}] 체크인 보증금(Deposit)" if dep_h_name else "호텔 체크인 보증금(Deposit)")
                if st.button("🚀 보증금 결제 기록 (지출 제외 / 지갑 차감)", use_container_width=True, type="primary"):
                    dep_rate = auto_calc_fifo_rate(dep_amt, dep_pay_source, dep_curr)
                    new_row = pd.DataFrame([{'Date': sel_date.strftime("%Y-%m-%d(%a)"), 'Country': sel_node, 'Category': '보증금', 'Description': dep_desc, 'Currency': dep_curr, 'Amount': dep_amt, 'PaymentMethod': dep_pay_source, 'IsExpense': 0, 'AppliedRate': dep_rate, 'Note': 'Hotel Deposit Paid', 'Receipt_URL': ''}])
                    if append_new_data(new_row): st.toast("✅ 보증금 기록 완료!", icon="🎉"); st.rerun()

            elif "체크아웃 보증금 환급" in hotel_sub_mode:
                c_r1, c_r2 = st.columns(2)
                with c_r1:
                    rf_h_name = st.text_input("호텔명", placeholder="예: 사누바 다낭 호텔")
                    rf_curr = st.selectbox("환급 통화", available_currs, index=available_currs.index(IN_CURR) if IN_CURR in available_currs else 0)
                    rf_amt = st.number_input(f"환급액 ({rf_curr})", min_value=0.0, step=1000.0 if rf_curr=="VND" else 10.0)
                with c_r2:
                    rf_dest = st.selectbox("입금 지갑", [f"현금({rf_curr})", f"트래블카드({rf_curr})", "원화계좌(한국)"])
                    rf_desc = st.text_input("환급 메모", value=f"[{rf_h_name}] 체크아웃 보증금 반환" if rf_h_name else "호텔 체크아웃 보증금 반환")
                if st.button("🚀 보증금 지갑 복구 (Rollback)", use_container_width=True, type="primary"):
                    new_row = pd.DataFrame([{'Date': sel_date.strftime("%Y-%m-%d(%a)"), 'Country': sel_node, 'Category': '환불', 'Description': f"[보증금반환] {rf_desc}", 'Currency': rf_curr, 'Amount': rf_amt, 'PaymentMethod': rf_dest, 'IsExpense': 0, 'AppliedRate': get_default_rate(rf_curr), 'Note': 'Hotel Deposit Returned', 'Receipt_URL': ''}])
                    if append_new_data(new_row): st.toast("✅ 보증금 환급 복구 완료!", icon="🎉"); st.rerun()

            else:
                c_c1, c_c2 = st.columns(2)
                with c_c1:
                    clear_curr = st.selectbox("청산 통화", available_currs, index=available_currs.index(IN_CURR) if IN_CURR in available_currs else 0)
                    clear_amt = st.number_input(f"청산 금액 ({clear_curr})", min_value=0.0, step=1000.0 if clear_curr=="VND" else 1.0)
                with c_c2:
                    clear_pay_source = st.selectbox("정산 지불 수단", [f"트래블카드({clear_curr})", f"현금({clear_curr})", "원화계좌(한국)"])
                    clear_desc = st.text_input("상환 메모", value="호텔 체크아웃 외상 청산 (룸차지)")
                if st.button("🚀 외상 청산 완료", use_container_width=True, type="primary"):
                    clear_rate = auto_calc_fifo_rate(clear_amt, clear_pay_source, clear_curr)
                    new_row = pd.DataFrame([{'Date': sel_date.strftime("%Y-%m-%d(%a)"), 'Country': sel_node, 'Category': '상환', 'Description': clear_desc, 'Currency': clear_curr, 'Amount': clear_amt, 'PaymentMethod': clear_pay_source, 'IsExpense': 0, 'AppliedRate': clear_rate, 'Note': 'Hotel Credit Cleared', 'Receipt_URL': ''}])
                    if append_new_data(new_row): st.toast(f"✅ 호텔 외상 청산 완료!", icon="🎉"); st.rerun()

        elif mode == "자산 이동":
            ty = st.selectbox("유형", ["충전 (원화계좌 -> 트래블카드)", "직접환전 (원화계좌 -> 로컬현금)", "이종환전 (외화 -> 타국 외화)", "ATM출금 (카드 -> 로컬현금)", "재환전 (외화 -> 원화계좌)", "이월잔액 (지난여행 -> 현금잔액)", "개인지출 (외화잔액 -> 여행외 소비)"], key="tr_type")
            c1, c2 = st.columns(2)
            if "이종환전" in ty:
                with c1:
                    curr_tr = st.selectbox("타깃 외화", [c for c in available_currs if c != "KRW"], key="tr_target_curr")
                    tr_target_met = st.selectbox("보관 자산", [f"트래블카드({curr_tr})", f"현금({curr_tr})"], key="tr_target_met")
                    t_amt = st.number_input(f"얻은 금액 ({curr_tr})", min_value=0.0, step=10.0, key="tr_target_flt")
                with c2:
                    curr_src = st.selectbox("지불 외화", [c for c in available_currs if c not in ["KRW", curr_tr]], key="tr_source_curr")
                    src_met = st.selectbox("출처", [f"트래블카드({curr_src})", f"현금({curr_src})"], key="tr_source_met")
                    s_amt = st.number_input(f"지불 금액 ({curr_src})", min_value=0.0, step=10.0, key="tr_source_flt")
                if st.button("🔄 이종환전 실행", use_container_width=True, type="primary"):
                    fifo_rate = auto_calc_fifo_rate(s_amt, src_met, curr_src)
                    target_rate = (s_amt * fifo_rate) / t_amt if t_amt > 0 else 0
                    row_src = pd.DataFrame([{'Date': sel_date.strftime("%Y-%m-%d(%a)"), 'Country': sel_node, 'Category': '이종환전', 'Description': f"이종환전 지불 (-> {curr_tr} {t_amt})", 'Currency': curr_src, 'Amount': s_amt, 'PaymentMethod': src_met, 'IsExpense': 0, 'AppliedRate': fifo_rate, 'Note': '', 'Receipt_URL': ''}])
                    row_tgt = pd.DataFrame([{'Date': sel_date.strftime("%Y-%m-%d(%a)"), 'Country': sel_node, 'Category': "충전" if "트래블카드" in tr_target_met else "직접환전", 'Description': f"이종환전 획득 (<- {curr_src} {s_amt})", 'Currency': curr_tr, 'Amount': t_amt, 'PaymentMethod': src_met, 'IsExpense': 0, 'AppliedRate': target_rate, 'Note': '', 'Receipt_URL': ''}])
                    if append_new_data(pd.concat([row_src, row_tgt], ignore_index=True)): st.toast("이종환전 완료!", icon="✅"); st.rerun()

            elif "개인지출" in ty:
                with c1:
                    curr_tr = st.selectbox("통화", [c for c in available_currs if c != "KRW"], key="tr_curr")
                    s_amt = st.number_input(f"금액 ({curr_tr})", min_value=0.0, step=1.0, key="tr_sell_flt")
                    source_met = st.selectbox("출처", [f"트래블카드({curr_tr})", f"현금({curr_tr})"], key="tr_sell_met")
                with c2:
                    s_desc = st.text_input("상세 용도", placeholder="예: 개인 쇼핑 등", key="tr_sell_desc")
                if st.button("🚀 개인지출 기록하기", use_container_width=True):
                    fifo_rate = auto_calc_fifo_rate(s_amt, source_met, curr_tr)
                    new_row = pd.DataFrame([{'Date': sel_date.strftime("%Y-%m-%d(%a)"), 'Country': sel_node, 'Category': '개인지출', 'Description': f"[개인지출] {s_desc}", 'Currency': curr_tr, 'Amount': s_amt, 'PaymentMethod': source_met, 'IsExpense': 0, 'AppliedRate': fifo_rate, 'Note': 'Exclude from Travel', 'Receipt_URL': ''}])
                    if append_new_data(new_row): st.toast("개인지출 완료!", icon="✅"); st.rerun()
            else:
                with c1:
                    curr_tr = st.selectbox("통화", available_currs, key="tr_curr")
                    t_amt = st.number_input(f"금액 ({curr_tr})", min_value=0.0, step=10.0, key="tr_target_flt")
                    if "ATM" in ty: applied_tr_rate = auto_calc_fifo_rate(t_amt, f"트래블카드({curr_tr})", curr_tr)
                    else:
                        s_cost = st.number_input("원금 (KRW)", min_value=0, step=1, format="%d", key="tr_source_swap")
                        applied_tr_rate = s_cost / t_amt if t_amt > 0 else 0
                with c2: fee_amt = st.number_input(f"수수료 ({curr_tr})", min_value=0.0, step=1.0, key="tr_fee_flt")
                if st.button("🔄 자산 이동 실행", use_container_width=True):
                    dest = f"트래블카드({curr_tr})" if "충전" in ty else f"현금({curr_tr})"
                    source = "원화계좌(한국)" if "원화계좌" in ty else f"트래블카드({curr_tr})"
                    main_row = pd.DataFrame([{'Date': sel_date.strftime("%Y-%m-%d(%a)"), 'Country': sel_node, 'Category': ty.split(" ")[0], 'Description': f"{ty.split(' ')[0]} (-> {dest})", 'Currency': curr_tr, 'Amount': t_amt, 'PaymentMethod': source, 'IsExpense': 0, 'AppliedRate': applied_tr_rate, 'Note': '', 'Receipt_URL': ''}])
                    new_rows = [main_row]
                    if fee_amt > 0:
                        fee_rate = auto_calc_fifo_rate(fee_amt, f"트래블카드({curr_tr})", curr_tr)
                        fee_row = pd.DataFrame([{'Date': sel_date.strftime("%Y-%m-%d(%a)"), 'Country': sel_node, 'Category': "수수료", 'Description': f"{ty.split(' ')[0]} 수수료", 'Currency': curr_tr, 'Amount': fee_amt, 'PaymentMethod': f"트래블카드({curr_tr})", 'IsExpense': 1, 'AppliedRate': fee_rate, 'Note': '', 'Receipt_URL': ''}])
                        new_rows.append(fee_row)
                    if append_new_data(pd.concat(new_rows, ignore_index=True)): st.toast("이동 완료!", icon="✅"); st.rerun()

        elif mode == "환불(취소)":
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                r_curr = st.selectbox("통화", available_currs, key="rf_curr")
                r_met = st.selectbox("입금 지갑", [f"현금({r_curr})", f"트래블카드({r_curr})", "원화계좌(한국)"], key="rf_met")
                r_amt = st.number_input("환불 금액", min_value=0.0, step=1.0, format="%.2f", key="rf_amt_flt")
            with col_r2:
                r_rate = st.number_input("당시 환율", value=(1.0 if r_curr=="KRW" else get_default_rate(r_curr)), format="%.5f", key="rf_rate")
                r_desc = st.text_input("메모", placeholder="예: 투어 예약 취소 환불", key="rf_desc")
            if st.button("🔙 환불 인벤토리 롤백 실행", use_container_width=True):
                new_row = pd.DataFrame([{'Date': sel_date.strftime("%Y-%m-%d(%a)"), 'Country': sel_node, 'Category': '환불', 'Description': f"취소: {r_desc}", 'Currency': r_curr, 'Amount': r_amt, 'PaymentMethod': r_met, 'IsExpense': 0, 'AppliedRate': r_rate, 'Note': 'Rollback', 'Receipt_URL': ''}])
                if append_new_data(new_row): st.toast("환불 롤백 완료!", icon="✅"); st.rerun()



            # 교체 범위: 6.01.03 ~ 6.01.06 전체
# 기존 6.01.03 ~ 6.01.06을 위에서 아래까지 통째로 교체하세요.
# 검색결과 영역과 상세 내역 영역을 독립 Fragment로 분리합니다.
    # 6.01.03 | Filter & Ledger Table Engine
    @st.fragment
    def _render_ledger_table_fragment():
        st.info("💡 **표의 행(Row)을 클릭(터치)하시면 상세 내역 수정, 순서 변경(🔼/🔽), 선물(🎁) 자동분리 신설, 영수증 AI 재스캔이 펼쳐집니다!**")

        # ☁️ 원장 저장은 이제 여기 하나로 통합한다. 모든 편집은 먼저 메모리에 반영된다.
        if st.session_state.get('ledger_dirty', False):
            c_save, c_backup = st.columns([3, 2])
            with c_save:
                st.warning("📝 **저장되지 않은 변경사항이 있습니다.** 현재 작업은 메모리에 안전하게 반영되어 있습니다.")
                if st.button("☁️ 변경사항 일괄 저장", key="btn_commit_ledger_global", use_container_width=True, type="primary"):
                    if commit_ledger_to_cloud():
                        st.toast("☁️ 변경사항을 Google Sheets에 일괄 저장했습니다!", icon="✅")
                        st.rerun(scope="fragment")
            with c_backup:
                backup_at = st.session_state.get('last_auto_backup_at')
                backup_text = backup_at if backup_at else "아직 없음"
                st.caption(f"🛡️ 자동 백업: 3분 간격\n\n마지막 백업: **{backup_text}**")
            if st.button("🛡️ 지금 백업", key="btn_manual_ledger_backup", use_container_width=True):
                if backup_active_ledger_to_cloud():
                    st.toast("🛡️ 현재 메모리 원장을 자동 백업했습니다.", icon="✅")
                    st.rerun(scope="fragment")

        # 🔥 검색결과 표와 행 이동의 단일 메모리 원본
        # 이동 버튼을 누를 때마다 Google Sheets를 읽지 않고, active_ledger_df를 즉시 화면에 반영한다.
        active_memory_df = st.session_state.get('active_ledger_df')
        if active_memory_df is None or active_memory_df.empty:
            active_memory_df = ledger_df.copy()
            st.session_state.active_ledger_df = active_memory_df.copy()
        else:
            active_memory_df = active_memory_df.copy()

        initial_country = st.session_state.get('his_country', "이번 여행가계부")
        if initial_country == "모든 여행가계부": temp_display_df = load_all_trips_data()
        else:
            temp_display_df = active_memory_df
            if initial_country != "이번 여행가계부": temp_display_df = temp_display_df[temp_display_df['Country'] == initial_country]

        cat_options = ["모든 카테고리"] + sorted(list(temp_display_df['Category'].dropna().unique())) if not temp_display_df.empty else ["모든 카테고리"]

        c_filter, c_cat, c_search = st.columns([3, 3, 5])
        with c_filter:
            filter_options = ["모든 여행가계부", "이번 여행가계부"] + list(TRIP_CONFIGS[st.session_state.current_trip]["nodes"].keys())
            country_filter = st.selectbox("🌍 국가 필터", filter_options, index=filter_options.index(initial_country) if initial_country in filter_options else 1, key="his_country")
        with c_cat: 
            cat_filter = st.selectbox("📂 카테고리 필터", cat_options, index=0, key="his_cat")
        with c_search: 
            search_query = st.text_input("🔎 검색어 입력", placeholder="상호명, 메모 등 검색", key="his_search")

        if country_filter == "모든 여행가계부":
            st.warning("⚠️ '모든 여행가계부' 모드에서는 내역 조회만 가능합니다.")
            display_df = load_all_trips_data()
        else:
            # 일반 조회는 항상 메모리 원본(active_ledger_df)을 사용한다.
            display_df = active_memory_df
            if country_filter != "이번 여행가계부": display_df = display_df[display_df['Country'] == country_filter]

        if not display_df.empty: 
            display_df = display_df.reindex(columns=FINAL_COLUMNS)
            link_cfg = st.column_config.LinkColumn("영수증 📸", display_text="🔗 보기", disabled=True)
            
            render_df = display_df
            if cat_filter != "모든 카테고리": render_df = render_df[render_df['Category'] == cat_filter]
            if search_query.strip():
                mask = (render_df['Category'].str.contains(search_query, case=False, na=False) | render_df['Description'].str.contains(search_query, case=False, na=False) | render_df['Note'].str.contains(search_query, case=False, na=False) | render_df['Country'].str.contains(search_query, case=False, na=False))
                render_df = render_df[mask]
                
            st.write(f"🔎 검색 결과: {len(render_df)}건")

            dep_rows = active_memory_df[active_memory_df['Category'].str.contains('출국', na=False)]
            korea_dep = active_memory_df[active_memory_df['Category'].str.contains('출국_한국|출국.*한국', na=False)]
            target_dep_row = korea_dep if not korea_dep.empty else dep_rows
            dep_dt, arr_dt = None, None
            if not target_dep_row.empty:
                m_dep = re.search(r'(\d{4}-\d{2})-(\d{2})', str(target_dep_row.iloc[0]['Date']))
                if m_dep: dep_dt = datetime.strptime(m_dep.group(0), "%Y-%m-%d").date()

            arr_rows = active_memory_df[active_memory_df['Category'].str.contains('귀국|입국', na=False)]
            korea_arr = active_memory_df[active_memory_df['Category'].str.contains('귀국_한국|귀국.*한국|입국_한국|입국.*한국', na=False)]
            target_arr_row = korea_arr if not korea_arr.empty else arr_rows
            if not target_arr_row.empty:
                m_arr = re.search(r'(\d{4}-\d{2})-(\d{2})', str(target_arr_row.iloc[-1]['Date']))
                if m_arr: arr_dt = datetime.strptime(m_arr.group(0), "%Y-%m-%d").date()

            unique_date_series = render_df['Date'].astype(str).str.extract(r'(\d{4}-\d{2}-\d{2})', expand=False).dropna()
            unique_dates = sorted(unique_date_series.unique().tolist())
            date_to_group = {d: i % 2 for i, d in enumerate(unique_dates)}

            day_kr_names = ['월', '화', '수', '목', '금', '토', '일']
            def format_display_date_se(row):
                orig_d, cat = str(row['Date']).strip(), str(row['Category']).strip()
                m_full = re.search(r'(\d{4})-(\d{2})-(\d{2})', orig_d)
                if m_full: pure_date, mm, dd = m_full.group(0), m_full.group(2), m_full.group(3)
                else: return orig_d
                try:
                    cur_d = datetime.strptime(pure_date, "%Y-%m-%d").date()
                    day_kr = day_kr_names[cur_d.weekday()]
                except: cur_d, day_kr = None, ""
                short_d = f"{mm}/{dd}({day_kr})" if day_kr else f"{mm}/{dd}"

                if cur_d and dep_dt and cur_d == dep_dt: return f"{short_d} 🛫Day1"
                if cur_d and arr_dt and cur_d == arr_dt: return f"{short_d} 🛬귀국"
                if not dep_dt or not cur_d: return short_d
                diff = (cur_d - dep_dt).days
                if diff < 0: return f"{short_d} 🏷️사전"
                return f"{short_d} 📍D-{diff + 1}"

            styled_render_df = render_df.copy()
            styled_render_df['Date'] = styled_render_df.apply(format_display_date_se, axis=1)
            if is_single_country and 'Country' in styled_render_df.columns:
                styled_render_df = styled_render_df.drop(columns=['Country'])

            def style_journey_rows_se(row):
                orig_d = str(render_df.loc[row.name, 'Date'])
                m = re.search(r'(\d{4})-(\d{2})-(\d{2})', orig_d)
                if not m: return [''] * len(row)
                pure_date = m.group(0)
                cur_d = datetime.strptime(pure_date, "%Y-%m-%d").date()
                if dep_dt and cur_d == dep_dt: return ['background-color: rgba(245, 158, 11, 0.28); font-weight: bold; color: #F59E0B;'] * len(row)
                if arr_dt and cur_d == arr_dt: return ['background-color: rgba(16, 185, 129, 0.28); font-weight: bold; color: #10B981;'] * len(row)
                if dep_dt and (cur_d - dep_dt).days < 0: return ['opacity: 0.7; font-style: italic;'] * len(row)
                if date_to_group.get(pure_date, 0) == 1: return ['background-color: rgba(249, 115, 22, 0.12); color: #0284C7;'] * len(row)
                return ['background-color: transparent;'] * len(row)

            styled_table = styled_render_df.style.apply(style_journey_rows_se, axis=1)
            def smart_num_fmt(v):
                if pd.isna(v) or not isinstance(v, (int, float)): return v
                if v == 0: return "0"
                if abs(v) >= 1 and v == int(v): return f"{int(v):,}"
                return f"{v:,.2f}"

            num_cols = ['Amount', 'AppliedRate', 'Cum_Budget_KRW', 'Cum_Card_Local', 'Cum_Cash_Local']
            styled_table = styled_table.format(smart_num_fmt, subset=[c for c in num_cols if c in styled_render_df.columns])
            col_cfg = {"Date": st.column_config.TextColumn("날짜", width=120), "Category": st.column_config.TextColumn("항목", width="small"), "Receipt_URL": link_cfg}
            
            df_event = st.dataframe(styled_table, use_container_width=True, column_config=col_cfg, hide_index=True, selection_mode="single-cell", on_select="rerun", key="ledger_result_table")

            # 6.01.04 | 선택 행 상태 관리
            # 선택 행은 "표시 위치"가 아니라 실제 ledger index로 기억한다.
            # 행 이동 직후에는 dataframe selection이 이전 화면 위치를 다시 보내올 수 있으므로
            # 한 번만 무시하고, 방금 이동한 행을 계속 선택 상태로 유지한다.
            selected_idx = None
            saved_real_idx = st.session_state.get('ledger_selected_real_idx')
            ignore_stale_selection = bool(st.session_state.pop('ledger_ignore_selection_once', False))

            if ignore_stale_selection and saved_real_idx is not None:
                try:
                    selected_idx = render_df.index.get_loc(saved_real_idx)
                except (KeyError, TypeError, IndexError):
                    selected_idx = None
            else:
                event_real_idx = None
                if getattr(df_event.selection, "cells", None) and len(df_event.selection.cells) > 0:
                    event_row_idx = df_event.selection.cells[0][0]
                    if 0 <= event_row_idx < len(render_df):
                        event_real_idx = render_df.index[event_row_idx]
                elif getattr(df_event.selection, "rows", None) and len(df_event.selection.rows) > 0:
                    event_row_idx = df_event.selection.rows[0]
                    if 0 <= event_row_idx < len(render_df):
                        event_real_idx = render_df.index[event_row_idx]

                if event_real_idx is not None:
                    selected_idx = render_df.index.get_loc(event_real_idx)
                    event_real_idx = int(event_real_idx)
                    st.session_state['ledger_selected_real_idx'] = event_real_idx
                    previous_detail_idx = st.session_state.get('ledger_detail_selected_real_idx')
                    if previous_detail_idx != event_real_idx:
                        st.session_state['ledger_detail_selected_real_idx'] = event_real_idx
                        st.rerun()
                elif saved_real_idx is not None:
                    try:
                        selected_idx = render_df.index.get_loc(saved_real_idx)
                    except (KeyError, TypeError, IndexError):
                        selected_idx = None


            # 6.01.03 | 검색결과 바로 아래 행 순서 조정판
            # 이동은 active_ledger_df 메모리만 변경하고, 이 검색결과 fragment만 다시 그린다.
            selected_real_idx_for_move = st.session_state.get('ledger_selected_real_idx')
            if selected_real_idx_for_move is not None:
                try:
                    _move_pos = active_memory_df.index.get_loc(selected_real_idx_for_move)
                    if isinstance(_move_pos, slice):
                        _move_pos = _move_pos.start
                    _move_pos = int(_move_pos)
                except (KeyError, TypeError, IndexError):
                    _move_pos = None

                if _move_pos is not None:
                    st.markdown("**↕️ 선택 행 순서 조정**")
                    c_up5, c_up1, c_down1, c_down5 = st.columns(4)

                    def _move_ledger_row_from_search(delta):
                        cur_df = st.session_state.get('active_ledger_df')
                        if cur_df is None or cur_df.empty:
                            return False

                        current_real_idx = st.session_state.get('ledger_selected_real_idx')
                        try:
                            current_pos = cur_df.index.get_loc(current_real_idx)
                            if isinstance(current_pos, slice):
                                current_pos = current_pos.start
                            current_pos = int(current_pos)
                        except (KeyError, TypeError, IndexError):
                            return False

                        new_pos = max(0, min(len(cur_df) - 1, current_pos + delta))
                        if new_pos == current_pos:
                            return False

                        cur_df = cur_df.copy()
                        row_a = cur_df.iloc[current_pos].copy()
                        row_b = cur_df.iloc[new_pos].copy()
                        cur_df.iloc[current_pos] = row_b
                        cur_df.iloc[new_pos] = row_a
                        cur_df = recalculate_entire_ledger(cur_df)

                        st.session_state.active_ledger_df = cur_df
                        st.session_state['ledger_selected_real_idx'] = cur_df.index[new_pos]
                        mark_ledger_dirty()
                        st.session_state['ledger_ignore_selection_once'] = True
                        return True

                    with c_up5:
                        if st.button("⏫ 5칸", key=f"btn_move_up5_search_{selected_real_idx_for_move}", use_container_width=True):
                            if _move_ledger_row_from_search(-5):
                                st.rerun(scope="fragment")
                    with c_up1:
                        if st.button("🔼 1칸", key=f"btn_move_up1_search_{selected_real_idx_for_move}", use_container_width=True):
                            if _move_ledger_row_from_search(-1):
                                st.rerun(scope="fragment")
                    with c_down1:
                        if st.button("🔽 1칸", key=f"btn_move_down1_search_{selected_real_idx_for_move}", use_container_width=True):
                            if _move_ledger_row_from_search(1):
                                st.rerun(scope="fragment")
                    with c_down5:
                        if st.button("⏬ 5칸", key=f"btn_move_down5_search_{selected_real_idx_for_move}", use_container_width=True):
                            if _move_ledger_row_from_search(5):
                                st.rerun(scope="fragment")


    # 6.01.05 | Detail Viewer & Inline Editor Fragment
    @st.fragment
    def _render_ledger_detail_fragment():
        # 상세 영역은 검색결과 fragment와 독립적으로 동작한다.
        selected_real_idx = st.session_state.get('ledger_detail_selected_real_idx')
        if selected_real_idx is None:
            selected_real_idx = st.session_state.get('ledger_selected_real_idx')
        active_df = st.session_state.get('active_ledger_df')
        if active_df is None or active_df.empty or selected_real_idx is None:
            st.info("💡 위 검색결과에서 행을 클릭하면 상세 내역이 여기에 표시됩니다.")
            return

        try:
            if selected_real_idx not in active_df.index:
                st.info("💡 선택된 내역을 찾을 수 없습니다. 위 검색결과에서 다시 선택해 주세요.")
                return
            real_idx = selected_real_idx
            row_data = active_df.loc[real_idx]
        except (KeyError, TypeError, IndexError):
            st.info("💡 선택된 내역을 찾을 수 없습니다. 위 검색결과에서 다시 선택해 주세요.")
            return

        st.markdown("---")
        c_info, c_edit = st.columns([1, 1.2])
        
        with c_info:
            st.subheader("🧾 상세 내역 및 영수증 뷰어")
            amt_fmt2 = "{:,.2f}" if MULTIPLIER == 1 and row_data['Currency'] != 'KRW' else "{:,.0f}"
            krw_equivalent = row_data['Amount'] if row_data['Currency'] == 'KRW' else row_data['Amount'] * row_data['AppliedRate']
            krw_display = f" ➔ <span style='color:#FFD700'>약 {krw_equivalent:,.0f} 원</span>" if row_data['Currency'] != 'KRW' else ""
            st.markdown(f"### 🛒 {row_data['Category']} ({amt_fmt2.format(row_data['Amount'])} {row_data['Currency']}{krw_display})", unsafe_allow_html=True)
            st.markdown(f"**🏦 결제수단:** `{row_data['PaymentMethod']}`")
            
            def smart_krw_translator(text, rate, curr):
                if rate <= 0 or curr == 'KRW': return text
                def replacer(match):
                    raw_num = match.group(1).strip()
                    suffix = match.group(2).lower() if match.group(2) else ""
                    
                    if curr in ['VND', 'HUF', 'KRW'] or re.search(r'\.\d{3}(?!\d)', raw_num):
                        clean_num_str = raw_num.replace('.', '').replace(',', '')
                    else:
                        clean_num_str = raw_num.replace(',', '')

                    try:
                        v = float(clean_num_str)
                        if 'k' in suffix: return match.group(0)
                        is_currency = any(c in suffix for c in ['vnd', 'usd', 'eur', 'cny', 'try', 'rsd', 'huf', 'krw', '원', '동', '달러', 'đ'])
                        is_unit = any(u in suffix for u in ['ml', 'g', 'kg', 'cm', 'mm', '개', 'x', '입', '장', '명', '박스', 'p', 'l'])
                        if is_unit and not is_currency: return match.group(0)
                        if is_currency or (curr in ['VND', 'HUF'] and v >= 1000) or (v > 100) or ('.' in raw_num and curr not in ['VND', 'HUF']):
                            krw_val = v * rate
                            return f"{match.group(1)}<span style='font-size:13px;color:#FFD700;font-style:italic;'> (약 {krw_val:,.0f}원)</span>{match.group(2)}"
                    except: pass
                    return match.group(0)
                
                pattern = re.compile(r'(?<![\d\.])(\d{1,3}(?:[,\.]\d{3})*(?:\.\d+)?|\d+)(?!\d)(\s*[a-zA-Z가-힣đĐ]*)')
                return pattern.sub(replacer, text)

            desc_full = str(row_data['Description'])
            rate_for_calc = row_data['AppliedRate']
            curr_for_calc = row_data['Currency']
            if "-" in desc_full:
                parts = desc_full.split("-", 1)
                st.markdown(f"**🏪 상호명:** {parts[0].strip()}")
                items = parts[1].strip().split("\n") if "\n" in parts[1] else parts[1].strip().split(",")
                for item in items: 
                    item_clean = item.strip()
                    if item_clean:
                        item_clean = re.sub(r'^[\-\*•\s]+', '', item_clean)
                        translated_item = smart_krw_translator(item_clean, rate_for_calc, curr_for_calc)
                        st.markdown(f"- {translated_item}", unsafe_allow_html=True)
            else:
                trans_item = smart_krw_translator(desc_full, rate_for_calc, curr_for_calc)
                st.markdown(f"**📝 내역:** {trans_item}", unsafe_allow_html=True)
                
            receipt_data = str(row_data['Receipt_URL']).strip()
            urls = [u.strip() for u in receipt_data.split(",") if u.strip().startswith("http")]
            if urls:
                for idx, url in enumerate(urls):
                    st.image(url, use_container_width=True, caption=f"영수증 사진 #{idx+1}")
                    if st.button(f"🗑️ 사진 #{idx+1} 삭제", key=f"btn_del_rcpt_{real_idx}_{idx}", use_container_width=True):
                        remaining_urls = [u for i, u in enumerate(urls) if i != idx]
                        new_urls_str = ",".join(remaining_urls)
                        active_df.at[real_idx, 'Receipt_URL'] = new_urls_str
                        target_df = st.session_state.active_ledger_df if 'active_ledger_df' in st.session_state else active_df
                        if real_idx in target_df.index: target_df.at[real_idx, 'Receipt_URL'] = new_urls_str
                        if save_data(target_df):
                            st.toast(f"사진 #{idx+1} 삭제 완료! (메모리 반영)", icon="✅"); time.sleep(0.2); st.rerun(scope="fragment")
            else: st.info("첨부된 영수증 사진이 없습니다.")
                
        with c_edit:
            st.subheader("✏️ 상세 내역 & 결제정보 수정")
            all_cats_avail = list(dict.fromkeys(EXPENSE_CATS + ['선물', '상환', '충전', '환전', '입금', '직접환전', '이월잔액', '환불', '개인지출', '재환전', '출국', '귀국', '체크인', '체크아웃']))
            cur_cat = str(row_data['Category']).strip()
            cat_idx_sel = all_cats_avail.index(cur_cat) if cur_cat in all_cats_avail else 0
            
            ec1, ec2 = st.columns(2)
            with ec1: edit_cat = st.selectbox("1. 항목(카테고리)", all_cats_avail, index=cat_idx_sel, key=f"edit_cat_sel_{real_idx}")
            with ec2: edit_amt = st.number_input("2. 결제 금액", value=float(row_data['Amount']), step=1000.0 if row_data['Currency']=="VND" else 1.0, format="%.2f" if row_data['Currency']!="VND" else "%.0f", key=f"edit_amt_val_{real_idx}")
                
            cur_method = str(row_data['PaymentMethod']).strip()
            avail_methods = list(dict.fromkeys([cur_method, f"트래블카드({row_data['Currency']})", f"현금({row_data['Currency']})", f"호텔외상({row_data['Currency']})", "원화계좌(한국)", "해외송금(한국계좌)", "정보"]))
            method_idx_sel = avail_methods.index(cur_method) if cur_method in avail_methods else 0
            edit_method = st.selectbox("3. 결제 수단(자산)", avail_methods, index=method_idx_sel, key=f"edit_met_sel_{real_idx}")
            
            desc_key = f"edit_desc_{real_idx}"
            if st.session_state.get('current_edit_idx') != real_idx:
                st.session_state[desc_key] = str(row_data['Description'])
                st.session_state['current_edit_idx'] = real_idx

            new_receipts = st.file_uploader("📸 영수증 사후 업로드 (사진/PDF)", type=['png', 'jpg', 'jpeg', 'pdf'], key=f"inline_receipt_{real_idx}", accept_multiple_files=True)
            
            col_ai1, col_ai2 = st.columns(2)
            with col_ai1:
                if new_receipts:
                    if st.button("🤖 새 영수증 AI 스캔 & 추가", key=f"btn_ai_scan_inline_{real_idx}", use_container_width=True, type="primary"):
                        with st.spinner("AI가 새 영수증을 분석 중..."):
                            smart_text, _, _ = summarize_receipt_files_with_gemini(new_receipts)
                            if smart_text:
                                cur_val = st.session_state.get(desc_key, '').strip()
                                st.session_state[desc_key] = f"{cur_val}\n{smart_text}".strip() if cur_val else smart_text
                                st.toast("영수증 품목 분석 완료!", icon="🤖"); st.rerun(scope="fragment")
            with col_ai2:
                if urls:
                    if st.button("🔄 기존 영수증 AI 재스캔", key=f"btn_ai_rescan_existing_{real_idx}", use_container_width=True):
                        with st.spinner("기존 영수증 사진을 AI 재분석 중..."):
                            img_bytes = None
                            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                            for attempt in range(2):
                                try:
                                    img_resp = requests.get(urls[0], headers=headers, timeout=25)
                                    if img_resp.status_code == 200 and len(img_resp.content) > 1000:
                                        img_bytes = img_resp.content
                                        break
                                except Exception:
                                    time.sleep(1)

                            if img_bytes:
                                class TempFileObj:
                                    def __init__(self, b): self.b = b; self.name = "rescan.jpg"
                                    def seek(self, pos): pass
                                    def read(self): return self.b
                                    def getvalue(self): return self.b
                                mock_file = TempFileObj(img_bytes)
                                smart_text, _, tot_amt = summarize_receipt_files_with_gemini([mock_file])
                                if smart_text:
                                    st.session_state[desc_key] = smart_text
                                    st.toast(f"기존 영수증 재스캔 완료! (총액: {tot_amt:,.0f})", icon="🎉")
                                    st.rerun(scope="fragment")

            new_desc = st.text_area("4. 세부 내역 (수정/추가)", height=110, key=desc_key)

            gift_items_split = []
            normal_items_split = []
            gift_amt_split = 0.0
            
            if new_desc and any(ch.isdigit() for ch in new_desc):
                all_lines = [l.strip() for l in re.sub(r'\[🎁선물:[^\]]+\]', '', new_desc).split("\n") if l.strip()]
                store_header = ""
                candidate_item_lines = []
                
                if all_lines:
                    store_header = all_lines[0]
                    raw_candidates = all_lines[1:]
                else:
                    raw_candidates = []

                for l_text in raw_candidates:
                    val_chk = parse_amount_from_line(l_text)
                    if l_text.startswith("-") or l_text.startswith("*") or l_text.startswith("•") or val_chk > 0:
                        candidate_item_lines.append(l_text)
                    else:
                        if not store_header: store_header = l_text

                if candidate_item_lines:
                    with st.expander("🎁 선물/특산품 분리 및 '선물' 항목 신설", expanded=True):
                        st.caption("💡 아래 품목 중 **선물/특산품**을 체크하시면 해당 품목만 '선물' 항목으로 분리됩니다.")
                        cols_ge = st.columns(min(3, max(1, len(candidate_item_lines))))
                        for idx_e, line_e in enumerate(candidate_item_lines):
                            val_e = parse_amount_from_line(line_e)
                            disp_name = re.sub(r'^[\-\*•\s]+', '', line_e)
                            is_already_gift = any(k in line_e for k in ["선물", "기념품", "마그넷", "팔찌", "목걸이", "자석", "캔디", "선물용", "옷", "원피스", "스카프"]) or (cur_cat == "선물")
                            c_box_e = cols_ge[idx_e % len(cols_ge)].checkbox(f"🎁 {disp_name[:18]}..", value=is_already_gift, key=f"chk_gift_edit_{real_idx}_{idx_e}")
                            
                            if c_box_e:
                                gift_items_split.append(line_e)
                                gift_amt_split += val_e
                            else:
                                normal_items_split.append(line_e)
                        
                        total_receipt_amt = float(edit_amt)
                        remaining_normal_amt = max(0.0, total_receipt_amt - gift_amt_split)
                        
                        if gift_amt_split >= total_receipt_amt and total_receipt_amt > 0:
                            st.info(f"✨ **100% 선물 지출**: 카테고리가 **`선물` ({total_receipt_amt:,.0f} {row_data['Currency']})** 로 전환됩니다.")
                        elif gift_amt_split > 0 and remaining_normal_amt > 0:
                            st.success(f"✂️ **2개 행 분할**:\n• 기존 (`{edit_cat}`): **{remaining_normal_amt:,.0f}** {row_data['Currency']}\n• 신설 (`선물`): **{gift_amt_split:,.0f}** {row_data['Currency']}")

            if st.button("💾 이 내역 변경사항 적용 (선물 자동분할 동시적용)", use_container_width=True, type="primary"):
                updated_rcpt_url = str(row_data.get('Receipt_URL', '')).strip()
                if new_receipts:
                    with st.spinner("📸 영수증 클라우드 전송 중..."):
                        new_urls = []
                        for f in new_receipts:
                            _uploaded_url = upload_image_to_imgbb(f)
                            if _uploaded_url:
                                new_urls.append(_uploaded_url)
                        if new_urls:
                            existing_urls = [x.strip() for x in updated_rcpt_url.split(',') if x.strip().startswith('http')]
                            updated_rcpt_url = ",".join(existing_urls + new_urls)

                target_df = st.session_state.active_ledger_df if 'active_ledger_df' in st.session_state else ledger_df
                total_receipt_amt = float(edit_amt)
                
                if (gift_amt_split >= total_receipt_amt and total_receipt_amt > 0) or (len(gift_items_split) > 0 and len(normal_items_split) == 0):
                    target_df.at[real_idx, 'Category'] = "선물"
                    target_df.at[real_idx, 'Amount'] = total_receipt_amt
                    target_df.at[real_idx, 'PaymentMethod'] = edit_method
                    target_df.at[real_idx, 'Description'] = new_desc.strip()
                    target_df.at[real_idx, 'Receipt_URL'] = updated_rcpt_url
                    target_df.at[real_idx, 'Note'] = "100% Gift Purchase"
                    
                elif gift_amt_split > 0 and len(normal_items_split) > 0:
                    rem_amt = max(0.0, total_receipt_amt - gift_amt_split)
                    lines_all = [l.strip() for l in new_desc.split('\n') if l.strip()]
                    store_hdr = lines_all[0] if lines_all else "상호명미기재"
                    
                    norm_desc = f"{store_hdr}\n" + "\n".join(normal_items_split)
                    gift_desc = f"{store_hdr}\n" + "\n".join(gift_items_split)
                    
                    base_cat = edit_cat if edit_cat != "선물" else row_data.get('Category', '마트')
                    if base_cat == "선물": base_cat = "마트"
                    
                    target_df.at[real_idx, 'Category'] = base_cat
                    target_df.at[real_idx, 'Amount'] = rem_amt
                    target_df.at[real_idx, 'PaymentMethod'] = edit_method
                    target_df.at[real_idx, 'Description'] = norm_desc.strip()
                    target_df.at[real_idx, 'Receipt_URL'] = updated_rcpt_url
                    
                    new_gift_row = pd.DataFrame([{
                        'Date': row_data['Date'],
                        'Country': row_data['Country'],
                        'Category': '선물',
                        'Description': gift_desc.strip(),
                        'Currency': row_data['Currency'],
                        'Amount': gift_amt_split,
                        'PaymentMethod': edit_method,
                        'IsExpense': 1,
                        'AppliedRate': row_data['AppliedRate'],
                        'Note': 'Gift Split',
                        'Receipt_URL': updated_rcpt_url
                    }])
                    target_df = pd.concat([target_df.iloc[:real_idx + 1], new_gift_row, target_df.iloc[real_idx + 1:]], ignore_index=True)
                    
                else:
                    target_df.at[real_idx, 'Category'] = edit_cat
                    target_df.at[real_idx, 'Amount'] = total_receipt_amt
                    target_df.at[real_idx, 'PaymentMethod'] = edit_method
                    target_df.at[real_idx, 'Description'] = new_desc.strip()
                    target_df.at[real_idx, 'Receipt_URL'] = updated_rcpt_url

                final_calc_df = recalculate_entire_ledger(target_df)
                st.session_state.active_ledger_df = final_calc_df
                if real_idx in final_calc_df.index:
                    st.session_state['ledger_detail_selected_real_idx'] = real_idx
                    st.session_state['ledger_selected_real_idx'] = real_idx
                elif not final_calc_df.empty:
                    nearest_idx = min(max(int(real_idx), 0), len(final_calc_df) - 1)
                    st.session_state['ledger_detail_selected_real_idx'] = final_calc_df.index[nearest_idx]
                    st.session_state['ledger_selected_real_idx'] = final_calc_df.index[nearest_idx]
                mark_ledger_dirty()

                st.toast("🎉 선물 분할 및 정합성 원샷 업데이트 완료! (메모리 반영)", icon="✅")
                time.sleep(0.2)
                st.rerun(scope="fragment")

            st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
            if st.button("🚨 이 지출 내역 영구 삭제하기", key=f"btn_delete_row_{real_idx}", use_container_width=True):
                target_df = st.session_state.active_ledger_df if 'active_ledger_df' in st.session_state else ledger_df
                target_df = target_df.drop(real_idx).reset_index(drop=True)
                final_calc_df = recalculate_entire_ledger(target_df)
                st.session_state.active_ledger_df = final_calc_df
                mark_ledger_dirty()

                st.toast("🗑️ 해당 지출 내역을 메모리에서 삭제했습니다. (최종 저장 전까지 복구 가능)", icon="🗑️")
                time.sleep(0.2)
                st.rerun(scope="fragment")

        st.markdown("---")

    # 6.01.06 | Search Result + Detail Entry
    _render_ledger_table_fragment()
    _render_ledger_detail_fragment()



# ==============================================================================
# [Module 6.02.00] Daily Statistics & Time-Series Engine (일일Data 탭)
# ==============================================================================
elif main_tab_choice == "일일Data":
    if not exp_df.empty:
        # 카테고리 컬러 팔레트 및 스택 순서
        color_map = {
            "식사": "#26A69A", "간식": "#66BB6A", "마트": "#EC407A",
            "Grab": "#29B6F6", "VinBus": "#26C6DA", "DiDi": "#29B6F6", "지하철": "#42A5F5",
            "택시": "#5C6BC0", "교통": "#5C6BC0", "마사지": "#FF7043", "투어": "#7E57C2",
            "입장료": "#AB47BC", "통신": "#FFA726", "수수료": "#8D6E63", "팁": "#26A69A",
            "항공권": "#EF5350", "호텔": "#42A5F5", "보험": "#FFEE58",
            "선물": "#FACC15", "기타": "#9E9E9E"
        }
        category_stack_order = [
            "식사", "간식", "마트", "Grab", "VinBus", "DiDi", "지하철", "택시", "교통", 
            "마사지", "투어", "입장료", "통신", "수수료", "팁", "항공권", "호텔", "보험", "선물", "기타"
        ]

        # 통화 선택 라디오
        c_mode = st.radio(
            "통화 선택", 
            [f"현지화({TRAVEL_CURRENCY})", "원화(KRW)"], 
            index=0, 
            horizontal=True, 
            key="st_curr_top", 
            label_visibility="collapsed"
        )
        y_col = 'KRW_val' if "원화" in c_mode else 'Local_val'

        dep_dt = dep_dt_calc
        arr_dt = arr_dt_calc
        is_fixed_cost = exp_df['IsFixedCost']

        # 1. 🛡️ 표준 YYYY-MM-DD 단일 정밀 파서
        def extract_pure_ymd(d_val):
            s = str(d_val).strip()
            m = re.search(r'(\d{4})[^\d](\d{1,2})[^\d](\d{1,2})', s)
            if m:
                return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
            return s

        def is_in_trip_period(row):
            pure_d = extract_pure_ymd(row['Date'])
            if dep_date_str and pure_d < dep_date_str: return False
            if arr_date_str and pure_d > arr_date_str: return False
            return True

        in_period_mask = exp_df.apply(is_in_trip_period, axis=1) if (dep_date_str or arr_date_str) else True
        ovr_df = exp_df[(~is_fixed_cost) & (~exp_df['Category'].isin(['입국','출국'])) & in_period_mask].copy()

        day_kr_names = ['월', '화', '수', '목', '금', '토', '일']
        ovr_df['Date_Clean'] = ovr_df['Date'].apply(extract_pure_ymd)

        # 2. 🛡️ 이동일 더미 행 중복 원천 방지
        if dep_dt and arr_dt and dep_dt <= arr_dt:
            total_calendar_days = (arr_dt - dep_dt).days + 1
            all_cal_dates = [(dep_dt + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(total_calendar_days)]
            existing_clean_dates = set(ovr_df['Date_Clean'].dropna().unique())
            missing_dates = [d for d in all_cal_dates if d not in existing_clean_dates]
            
            if missing_dates:
                dummy_rows = []
                for md in missing_dates:
                    prev_part = ovr_df[ovr_df['Date_Clean'] < md]
                    last_country = prev_part.iloc[-1]['Country'] if not prev_part.empty else (list(TRIP_CONFIGS[st.session_state.current_trip]["nodes"].keys())[0])
                    try:
                        dt_md = datetime.strptime(md, "%Y-%m-%d").date()
                        w_kr = day_kr_names[dt_md.weekday()]
                        d_str = f"{md}({w_kr})"
                    except: d_str = md

                    dummy_rows.append({
                        'Date': d_str, 'Date_Clean': md, 'Country': last_country, 'Category': '기타',
                        'Description': '이동일 (지출 0원)', 'Currency': TRAVEL_CURRENCY, 'Amount': 0.0,
                        'PaymentMethod': '정보', 'IsExpense': 1, 'AppliedRate': 1.0, 'KRW_val': 0.0,
                        'Local_val': 0.0, 'IsSurvival': 0, 'IsFixedCost': False, 'Macro_Category': '📱 기타/통신'
                    })
                ovr_df = pd.concat([ovr_df, pd.DataFrame(dummy_rows)], ignore_index=True)
        else:
            total_calendar_days = ovr_df['Date_Clean'].nunique()

        if not ovr_df.empty:
            ovr_df = ovr_df.sort_values(by='Date_Clean', kind='mergesort')
            unique_clean_dates = sorted([str(d) for d in ovr_df['Date_Clean'].dropna().unique() if str(d).strip()])
            
            # 3. 🛡️ X축 독립 날짜 라벨 1:1 매핑 생성
            date_label_map = {}
            for d in unique_clean_dates:
                m_d = re.search(r'(\d{4})-(\d{2})-(\d{2})', d)
                if m_d:
                    yyyy_val, mm_val, dd_val = m_d.group(1), int(m_d.group(2)), int(m_d.group(3))
                    try:
                        dt_obj = datetime.strptime(f"{yyyy_val}-{mm_val:02d}-{dd_val:02d}", "%Y-%m-%d").date()
                        day_kr = day_kr_names[dt_obj.weekday()]
                    except:
                        day_kr = ""
                    date_label_map[d] = f"{mm_val}/{dd_val}<br>({day_kr})"
                else:
                    date_label_map[d] = d

            ordered_x_labels = [date_label_map[d] for d in unique_clean_dates]

            today_dt_c = datetime.now(st.session_state.current_tz).date()
            if dep_dt and arr_dt:
                if today_dt_c < dep_dt:
                    day_label_suffix = f"{total_calendar_days}일예정"; div_days = max(1, total_calendar_days)
                elif dep_dt <= today_dt_c <= arr_dt:
                    curr_day = (today_dt_c - dep_dt).days + 1
                    day_label_suffix = f"{curr_day}일차"; div_days = max(1, curr_day)
                else:
                    day_label_suffix = f"{total_calendar_days}일간"; div_days = max(1, total_calendar_days)
            else:
                day_label_suffix = f"{total_calendar_days}일간"; div_days = max(1, total_calendar_days)

            total_spent_val = ovr_df[y_col].sum()
            surv_spent_val = ovr_df[ovr_df['IsSurvival'] == 1][y_col].sum()
            
            avg_daily_total = total_spent_val / div_days if div_days > 0 else 0
            avg_daily_surv = surv_spent_val / div_days if div_days > 0 else 0
            
            y_unit = "원" if "원화" in c_mode else f" {LOCAL_SYM}"
            fmt_tot = f"{avg_daily_total:,.0f}" if "원화" in c_mode or MULTIPLIER != 1 else f"{avg_daily_total:,.2f}"
            fmt_surv = f"{avg_daily_surv:,.0f}" if "원화" in c_mode or MULTIPLIER != 1 else f"{avg_daily_surv:,.2f}"

            rem_cash = sum([b['qty'] for b in current_inventory_batches.get(f"현금({TRAVEL_CURRENCY})", [])])
            war_curr = get_WAR(TRAVEL_CURRENCY)
            
            if "원화" in c_mode:
                rem_cash_val = rem_cash * war_curr if war_curr > 0 else 0
                surv_krw_sum = ovr_df[ovr_df['IsSurvival'] == 1]['KRW_val'].sum()
                avg_surv_val_for_calc = (surv_krw_sum / div_days) if div_days > 0 else 1
            else:
                rem_cash_val = rem_cash
                surv_loc_sum = ovr_df[ovr_df['IsSurvival'] == 1]['Local_val'].sum()
                avg_surv_val_for_calc = (surv_loc_sum / div_days) if div_days > 0 else 1

            days_survivable = (rem_cash_val / avg_surv_val_for_calc) if avg_surv_val_for_calc > 0 else 999.0
            remaining_trip_days = max(0, (arr_dt - today_dt_c).days) if arr_dt and today_dt_c <= arr_dt else 0
            
            if remaining_trip_days > 0:
                if days_survivable >= remaining_trip_days:
                    status_badge = f"<span style='color:#10B981; font-weight:800; font-size:16px;'>🟢 안전 (약 {days_survivable:.1f}일분 여유)</span>"
                else:
                    shortfall = remaining_trip_days - days_survivable
                    status_badge = f"<span style='color:#EF4444; font-weight:800; font-size:16px;'>🚨 경고 (약 {days_survivable:.1f}일 뒤 소진, 추가 현금화 필요)</span>"
            else:
                status_badge = f"<span style='color:#38BDF8; font-weight:800; font-size:16px;'>🪙 약 {days_survivable:.1f}일 체류 가능</span>"

            st.markdown(f"""
                <div style='background: rgba(30, 41, 59, 0.7); border: 1px solid #334155; border-radius: 10px; padding: 12px 14px; margin-bottom: 15px;'>
                    <div style='display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;'>
                        <div>
                            <span style='font-size:15px; font-weight:600; color:#94A3B8;'>💳 현금 잔고: </span>
                            <span style='font-size:17px; font-weight:800; color:#4EFEB3;'>{rem_cash:,.0f} {LOCAL_SYM} (카드 제외 현금기준)</span>
                        </div>
                        <div>
                            <span style='font-size:15px; font-weight:600; color:#94A3B8;'>⏳ 현금 2일치 수명 관제: </span>
                            {status_badge}
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            # ------------------------------------------------------------------
            # [Module 6.02.01] 필수지출 차트 (이모티콘/범례명 삭제 & 9개 막대 분리)
            # ------------------------------------------------------------------
            st.markdown(f"<h4 style='text-align: center; margin-bottom:4px;'>필수지출 ({day_label_suffix})</h4>", unsafe_allow_html=True)
            surv_chart_df = ovr_df[ovr_df['IsSurvival'] == 1].copy()
            if not surv_chart_df.empty:
                surv_chart_df['Date_Display'] = surv_chart_df['Date_Clean'].map(date_label_map).astype(str)
                fig_surv = px.bar(
                    surv_chart_df, x='Date_Display', y=y_col, color='Category',
                    barmode='stack', color_discrete_map=color_map, title=None,
                    category_orders={"Date_Display": ordered_x_labels, "Category": category_stack_order}
                )
                if avg_daily_surv > 0:
                    fig_surv.add_hline(
                        y=avg_daily_surv, line_dash="dash", line_color="#0284C7", line_width=3.6,
                        annotation_text=f" 평균 {fmt_surv}{y_unit} ", annotation_position="top right",
                        annotation_font=dict(size=16, color="#FFFFFF", family="sans-serif"),
                        annotation_bgcolor="rgba(3, 105, 161, 0.78)",
                        annotation_bordercolor="rgba(2, 132, 199, 0.9)",
                        annotation_borderwidth=1.5, annotation_borderpad=6,
                        annotation_yshift=14
                    )
                fig_surv.update_layout(
                    margin=dict(l=10, r=10, t=20, b=50), 
                    xaxis_title=None, 
                    yaxis_title=None,
                    legend_title_text="",  # 범례 Category 삭제
                    legend=dict(orientation="h", yanchor="top", y=-0.25, xanchor="center", x=0.5, title=None), 
                    height=390
                )
                # 🌟 X축을 category형으로 강제 지정하여 날짜 뭉개짐 방지
                fig_surv.update_xaxes(type='category', fixedrange=True, tickfont=dict(size=12), categoryorder='array', categoryarray=ordered_x_labels)
                fig_surv.update_yaxes(fixedrange=True, tickfont=dict(size=16, color="#CBD5E1"))
                st.plotly_chart(fig_surv, use_container_width=True, config={'displaylogo': False, 'scrollZoom': False, 'displayModeBar': False})
            else:
                st.info("해당 기간 내 필수지출 항목이 없습니다.")

            st.markdown("<div style='margin: 25px 0px; border-top: 1px dashed #475569;'></div>", unsafe_allow_html=True)

            # ------------------------------------------------------------------
            # [Module 6.02.02] 일별 총지출 차트 (이모티콘/범례명 삭제 & 9개 막대 분리)
            # ------------------------------------------------------------------
            st.markdown(f"<h4 style='text-align: center; margin-bottom:4px;'>일별 총지출 ({day_label_suffix})</h4>", unsafe_allow_html=True)
            total_chart_df = ovr_df.copy()
            total_chart_df['Date_Display'] = total_chart_df['Date_Clean'].map(date_label_map).astype(str)

            fig_tot = px.bar(
                total_chart_df, x='Date_Display', y=y_col, color='Category',
                barmode='stack', color_discrete_map=color_map, title=None,
                category_orders={"Date_Display": ordered_x_labels, "Category": category_stack_order}
            )
            if avg_daily_total > 0:
                fig_tot.add_hline(
                    y=avg_daily_total, line_dash="dash", line_color="#F59E0B", line_width=3.6,
                    annotation_text=f" 평균 {fmt_tot}{y_unit} ", annotation_position="top right",
                    annotation_font=dict(size=16, color="#FFFFFF", family="sans-serif"),
                    annotation_bgcolor="rgba(180, 83, 9, 0.78)",
                    annotation_bordercolor="rgba(245, 158, 11, 0.9)",
                    annotation_borderwidth=1.5, annotation_borderpad=6,
                    annotation_yshift=14
                )
            fig_tot.update_layout(
                margin=dict(l=10, r=10, t=20, b=50), 
                xaxis_title=None, 
                yaxis_title=None,
                legend_title_text="",  # 범례 Category 삭제
                legend=dict(orientation="h", yanchor="top", y=-0.25, xanchor="center", x=0.5, title=None), 
                height=390
            )
            # 🌟 X축을 category형으로 강제 지정하여 날짜 뭉개짐 방지
            fig_tot.update_xaxes(type='category', fixedrange=True, tickfont=dict(size=12), categoryorder='array', categoryarray=ordered_x_labels)
            fig_tot.update_yaxes(fixedrange=True, tickfont=dict(size=16, color="#CBD5E1"))
            st.plotly_chart(fig_tot, use_container_width=True, config={'displaylogo': False, 'scrollZoom': False, 'displayModeBar': False})

        st.divider()
        
        # ----------------------------------------------------------------------
        # [Module 6.02.03] 일별 피벗 매트릭스 테이블 (중복 없는 정렬 & 요약행 배경색)
        # ----------------------------------------------------------------------
        daily_set = ovr_df.groupby('Date_Clean').agg({'Country': lambda x: ' / '.join(x.unique()), 'KRW_val': 'sum', 'Local_val': 'sum'}).reset_index() if not ovr_df.empty else pd.DataFrame(columns=['Date_Clean', 'Country', 'KRW_val', 'Local_val'])
        surv_only = ovr_df[ovr_df['IsSurvival'] == 1].groupby('Date_Clean').agg({'KRW_val': 'sum', 'Local_val': 'sum'}).reset_index().rename(columns={'KRW_val': 'S_KRW', 'Local_val': 'S_Loc'}) if not ovr_df.empty else pd.DataFrame(columns=['Date_Clean', 'S_KRW', 'S_Loc'])
        daily_table = pd.merge(daily_set, surv_only, on='Date_Clean', how='left').fillna(0) if not daily_set.empty else pd.DataFrame()
        fmt_local = "{:,.2f}" if MULTIPLIER == 1 else "{:,.0f}"
        
        if not daily_table.empty:
            def format_table_date_header(d_clean):
                m = re.search(r'(\d{4})-(\d{2})-(\d{2})', str(d_clean))
                if m:
                    mm, dd = int(m.group(2)), int(m.group(3))
                    try:
                        dt_obj = datetime.strptime(d_clean, "%Y-%m-%d").date()
                        day_kr = day_kr_names[dt_obj.weekday()]
                        return f"{mm:02d}/{dd:02d}({day_kr})"
                    except:
                        return f"{mm:02d}/{dd:02d}"
                return str(d_clean)

            daily_table['Date_Short'] = daily_table['Date_Clean'].apply(format_table_date_header)
            daily_table = daily_table.sort_values(by='Date_Clean', kind='mergesort')

            sum_tot_krw = daily_table['KRW_val'].sum()
            sum_tot_loc = daily_table['Local_val'].sum()
            sum_surv_krw = daily_table['S_KRW'].sum()
            sum_surv_loc = daily_table['S_Loc'].sum()
            
            row_count = max(1, len(daily_table))
            avg_tot_krw = sum_tot_krw / row_count
            avg_tot_loc = sum_tot_loc / row_count
            avg_surv_krw = sum_surv_krw / row_count
            avg_surv_loc = sum_surv_loc / row_count

            summary_rows = pd.DataFrame([
                {
                    'Country': '📊 총합계', 'Date_Short': '합계(Sum)', 
                    'Local_val': sum_tot_loc, 'KRW_val': sum_tot_krw, 
                    'S_Loc': sum_surv_loc, 'S_KRW': sum_surv_krw
                },
                {
                    'Country': '📈 1일 평균', 'Date_Short': '일평균(Avg)', 
                    'Local_val': avg_tot_loc, 'KRW_val': avg_tot_krw, 
                    'S_Loc': avg_surv_loc, 'S_KRW': avg_surv_krw
                }
            ])
            
            if is_single_country:
                display_table = daily_table[['Date_Short', 'Local_val', 'KRW_val', 'S_Loc', 'S_KRW']].rename(columns={'Date_Short':'날짜', 'Local_val':f'총({LOCAL_SYM})', 'KRW_val':'총(원)', 'S_Loc':f'필수({LOCAL_SYM})', 'S_KRW':'필수(원)'})
                summary_display = summary_rows[['Date_Short', 'Local_val', 'KRW_val', 'S_Loc', 'S_KRW']].rename(columns={'Date_Short':'날짜', 'Local_val':f'총({LOCAL_SYM})', 'KRW_val':'총(원)', 'S_Loc':f'필수({LOCAL_SYM})', 'S_KRW':'필수(원)'})
            else:
                display_table = daily_table[['Country', 'Date_Short', 'Local_val', 'KRW_val', 'S_Loc', 'S_KRW']].rename(columns={'Country':'국가', 'Date_Short':'날짜', 'Local_val':f'총({LOCAL_SYM})', 'KRW_val':'총(원)', 'S_Loc':f'필수({LOCAL_SYM})', 'S_KRW':'필수(원)'})
                summary_display = summary_rows[['Country', 'Date_Short', 'Local_val', 'KRW_val', 'S_Loc', 'S_KRW']].rename(columns={'Country':'국가', 'Date_Short':'날짜', 'Local_val':f'총({LOCAL_SYM})', 'KRW_val':'총(원)', 'S_Loc':f'필수({LOCAL_SYM})', 'S_KRW':'필수(원)'})

            final_table_with_summary = pd.concat([display_table, summary_display], ignore_index=True)
            
            # 🌟 폰트는 유지하고 요약 2개 행에 배경색(Highlight)만 주입
            def style_daily_pivot_table(df_display):
                styles = pd.DataFrame('', index=df_display.index, columns=df_display.columns)
                loc_cols = [c for c in df_display.columns if f"({LOCAL_SYM})" in c]
                for col in loc_cols:
                    styles[col] = 'background-color: rgba(2, 132, 199, 0.12);'

                for idx in df_display.index:
                    row_date = str(df_display.loc[idx, '날짜'])
                    if row_date in ['합계(Sum)', '일평균(Avg)']:
                        for col in df_display.columns:
                            styles.loc[idx, col] = 'background-color: rgba(245, 158, 11, 0.22);'
                return styles

            styled_daily_table = final_table_with_summary.style.apply(style_daily_pivot_table, axis=None).format({
                f'총({LOCAL_SYM})': fmt_local, '총(원)': '{:,.0f}', f'필수({LOCAL_SYM})': fmt_local, '필수(원)': '{:,.0f}'
            })

            col_cfg_daily = {"날짜": st.column_config.TextColumn("날짜", width="small"), "국가": st.column_config.TextColumn("국가", width="small")}
            st.dataframe(styled_daily_table, use_container_width=True, hide_index=True, column_config=col_cfg_daily)
        else: 
            st.info("현지 지출 데이터가 없습니다.")
    else:
        st.info("기록된 지출 데이터가 없습니다.")


# ==============================================================================
# [Module 6.03.00] Unified Magnifier Hub (Memory-Cached Regex Optimizer)
# ==============================================================================
elif main_tab_choice == "돋보기":
    @st.fragment(key="magnifier_hub")
    def render_magnifier_fragment():
        st.subheader("🔍 여행 소비 돋보기")
        
        def auto_fit_header_label(text, amount, total_amount):
            if not text: return ""
            s = str(text).strip()
            s = re.sub(r'\[.*?\]\s*', '', s)
            s = re.sub(r'\s+to\s+', ' ➔ ', s, flags=re.IGNORECASE)
            s = re.sub(r'[\d,\.]+\s*[kK원동\$]+.*$', '', s).strip(' -*•()[]/_')
            if not s: return ""
            pct = (amount / total_amount * 100) if total_amount > 0 else 0
            dynamic_max_len = int(min(28, max(10, 10 + pct * 0.6)))
            return s[:dynamic_max_len] + ".." if len(s) > dynamic_max_len else s

        def smart_wrap_multiline(text, max_line_len=10):
            if not text: return ""
            s = str(text).strip()
            s = re.sub(r'\[.*?\]\s*', '', s)
            s = re.sub(r'\s+to\s+', ' ➔ ', s, flags=re.IGNORECASE)
            s = re.sub(r'[\d,\.]+\s*[kK원동\$]+.*$', '', s).strip(' -*•()[]/_')
            s = re.sub(r'\b\d+(?:\.\d+)?\s*(?:km|분|초|시간)\b', '', s, flags=re.IGNORECASE).strip(' ,-')
            if not s: return ""

            lines = []
            parts = re.split(r'(\(.*?\))', s)
            for part in parts:
                part = part.strip()
                if not part: continue
                if part.startswith('(') and part.endswith(')'):
                    if len(part) > max_line_len + 4:
                        sub_words = part[1:-1].split()
                        cur = "("
                        for sw in sub_words:
                            if len(cur + " " + sw) <= max_line_len:
                                cur = (cur + " " + sw).strip() if cur != "(" else "(" + sw
                            else:
                                lines.append(cur)
                                cur = sw
                        if cur: lines.append(cur + ")")
                    else:
                        lines.append(part)
                else:
                    words = part.split()
                    cur_line = ""
                    for w in words:
                        if len(cur_line + " " + w) <= max_line_len:
                            cur_line = (cur_line + " " + w).strip()
                        else:
                            if cur_line: lines.append(cur_line)
                            cur_line = w
                    if cur_line: lines.append(cur_line)

            if len(lines) > 3: lines = lines[:3]
            return "<br>".join(lines)

        # ⚡ [고속화 캐시 엔진] 돋보기 3대 데이터셋 전처리 메모이제이션
        @st.cache_data(ttl=600)
        def parse_cached_market_items(df_records, travel_curr, war_rate):
            df_src = pd.DataFrame(df_records)
            market_keywords = ['마트', '시장', 'market', 'lotte', 'big c', 'go!', 'vinmart', 'winmart', 'coop', '야시장', '면세점', '파마씨티', 'pharmacity', '약국', '졸리', '성물', '기념품', '헬로', '한시장', '동바시장', '편의점']
            exclude_keywords_m = ['마사지', '발마사지', '그랩', 'grab', '미터기', '택시', '교통', '콜택시', '식사', '카페', '레스토랑', '호텔']
            
            def is_market(r):
                cat, desc = str(r['Category']).strip(), str(r['Description']).strip().lower()
                if cat in ['마트', '시장', '선물']: return True
                if cat in ['마사지', '택시', '교통', 'Grab', 'VinBus', 'DiDi', '지하철', '버스', '트램', '기차', '식사', '간식', '호텔', '항공권', '보험', '투어', '입장료', '통신', '수수료', '팁', '상환', '보증금']: return False
                if any(ek in desc for ek in exclude_keywords_m): return False
                return any(mk in desc for mk in market_keywords) or any(mk in cat for mk in market_keywords)

            m_df = df_src[df_src.apply(is_market, axis=1) & (df_src['IsExpense'] == 1)].copy()
            if m_df.empty: return pd.DataFrame()

            tot_market_raw = m_df['Amount'].sum()
            parsed_items = []
            for _, r in m_df.iterrows():
                desc_raw = str(r['Description'])
                r_curr, r_amt = str(r['Currency']).strip().upper(), float(r['Amount'])
                lines = [l.strip() for l in desc_raw.split('\n') if l.strip()]
                store_name = lines[0] if lines else "기타 마트/선물"
                store_clean = auto_fit_header_label(store_name.split('|')[0], r_amt, tot_market_raw) or "마트/시장"
                store_lower = store_name.lower()

                if '한시장' in store_lower: bazaar_group = '🧺 한시장 통합'
                elif '동바시장' in store_lower: bazaar_group = '🧺 동바시장 통합'
                elif '약국' in store_lower or 'pharmacity' in store_lower or '파마씨티' in store_lower: bazaar_group = '💊 약국 통합'
                elif any(k in store_lower for k in ['마트', '슈퍼', '편의점', 'lotte', 'big c', '7-eleven', 'circle k', 'jolymart', '졸리']): bazaar_group = '🛒 마트/슈퍼 통합'
                elif '시장' in store_lower or '야시장' in store_lower: bazaar_group = '🛍️ 기타 전통시장'
                else: bazaar_group = '🎁 기타 쇼핑/선물샵'

                item_lines = lines[1:] if len(lines) > 1 else lines
                trash = ['địa chỉ', 'hdon', 'ngay', 'gio', 'hdban', 'mastercard', 'vietcombank', 'tid', 'mid', 'cls', 'toan', 'so lo', 'tên', 'đại lý', 'tổng cộng', 'tổng', 'tiền', 'mã', 'hóa đơn', 'đt:', 'mst:', 'tp.', 'đường', 'phường', 'quận']
                valid_items = []

                for il in item_lines:
                    il_low = il.lower()
                    if any(tk in il_low for tk in trash) or len(il) < 2 or '---' in il or '===' in il: continue
                    is_bullet = il.startswith('-') or il.startswith('*') or il.startswith('•')
                    if not is_bullet and not (re.search(r'(\d+(?:\.\d+)?)\s*[kK]\b', il) or re.search(r'\d{2,}', il)): continue

                    price_val = 0.0
                    m_k = re.search(r'(\d+(?:\.\d+)?)\s*[kK]\b', il)
                    if m_k: price_val = float(m_k.group(1)) * 1000
                    else:
                        comma_nums = re.findall(r'(\d{1,3}(?:,\d{3})+)', il)
                        if comma_nums:
                            try: price_val = float(comma_nums[-1].replace(',', ''))
                            except: pass
                        else:
                            plain_nums = re.findall(r'(\d+)', il)
                            if plain_nums:
                                try:
                                    for p_str in reversed(plain_nums):
                                        p_val = float(p_str)
                                        if p_val > 500: price_val = p_val; break
                                except: pass

                    clean_name = smart_wrap_multiline(il, max_line_len=10)
                    if clean_name and len(clean_name) >= 2 and not clean_name.startswith('로 잘못'):
                        valid_items.append({'raw_line': il, 'name': clean_name, 'price': price_val})

                if not valid_items or (len(valid_items) == 1 and valid_items[0]['price'] == 0):
                    parsed_items.append({'Bazaar_Group': bazaar_group, 'Store': store_clean, 'Item': store_clean, 'Local_val': r_amt, 'Curr': r_curr})
                else:
                    sum_p = sum(it['price'] for it in valid_items if it['price'] > 0)
                    scale = (r_amt / sum_p) if (sum_p > 0 and r_amt > 0 and abs(sum_p - r_amt) > 1.0) else 1.0
                    for it in valid_items:
                        fp = it['price'] if it['price'] > 0 else (r_amt / max(1, len(valid_items)))
                        fp = round(fp * scale, -2)
                        parsed_items.append({'Bazaar_Group': bazaar_group, 'Store': store_clean, 'Item': it['name'], 'Local_val': fp, 'Curr': r_curr})

            res_df = pd.DataFrame(parsed_items)
            if not res_df.empty:
                res_df = res_df[res_df['Local_val'] > 0].copy()
                res_df['KRW_str'] = res_df['Local_val'].apply(lambda v: f"약 {round(v * war_rate, -2):,.0f}원") if (war_rate > 0) else ""
            return res_df

        @st.cache_data(ttl=600)
        def parse_cached_food_items(df_records, travel_curr, war_rate):
            df_src = pd.DataFrame(df_records)
            def is_food(r):
                cat, desc, met = str(r['Category']).strip(), str(r['Description']).strip().lower(), str(r['PaymentMethod']).strip().lower()
                if cat in ['식사', '간식']: return True
                if '외상' in met or 'credit' in met or '호텔외상' in met:
                    if any(k in desc for k in ['맥주', '와인', '음료', '칵테일', '수영장', '조식', '식사', '룸서비스', '카페', '커피', 'bar', 'pool']): return True
                return False

            f_df = df_src[df_src.apply(is_food, axis=1) & (df_src['IsExpense'] == 1)].copy()
            if f_df.empty: return pd.DataFrame()

            tot_f_raw = f_df['Amount'].sum()
            parsed_food = []
            for _, r in f_df.iterrows():
                desc_raw, r_curr, r_amt = str(r['Description']), str(r['Currency']).strip().upper(), float(r['Amount'])
                lines = [l.strip() for l in desc_raw.split('\n') if l.strip()]
                place_name = lines[0] if lines else "기타 식당/카페"
                place_clean = auto_fit_header_label(place_name.split('|')[0], r_amt, tot_f_raw) or "식당/카페"
                place_lower = place_name.lower()

                if any(k in place_lower for k in ['카페', '커피', 'coffee', '티', '브런치', '디저트', '반미']): f_group = '☕ 카페/디저트'
                elif any(k in place_lower for k in ['맥주', 'bar', '펍', 'pub', '라운지', '루프탑']): f_group = '🍻 주류/바(Bar)'
                else: f_group = '🍽️ 레스토랑/식당'

                item_lines = lines[1:] if len(lines) > 1 else lines
                valid_items = []
                for il in item_lines:
                    if len(il) < 1 or '---' in il: continue
                    price_val = 0.0
                    m_k = re.search(r'(\d+(?:\.\d+)?)\s*[kK]\b', il)
                    if m_k: price_val = float(m_k.group(1)) * 1000
                    else:
                        comma_nums = re.findall(r'(\d{1,3}(?:,\d{3})+)', il)
                        if comma_nums:
                            try: price_val = float(comma_nums[-1].replace(',', ''))
                            except: pass
                        else:
                            plain_nums = re.findall(r'(\d+)', il)
                            if plain_nums:
                                try:
                                    for p_str in reversed(plain_nums):
                                        p_val = float(p_str)
                                        if p_val > 500: price_val = p_val; break
                                except: pass
                    clean_iname = smart_wrap_multiline(il, max_line_len=10)
                    if clean_iname and (len(clean_iname) >= 1 or price_val > 0): valid_items.append({'name': clean_iname, 'price': price_val})

                if not valid_items or (len(valid_items) == 1 and valid_items[0]['price'] == 0):
                    parsed_food.append({'Food_Group': f_group, 'Place': place_clean, 'Item': place_clean, 'Local_val': r_amt, 'Curr': r_curr})
                else:
                    sum_fp = sum(it['price'] for it in valid_items if it['price'] > 0)
                    f_scale = (r_amt / sum_fp) if (sum_fp > 0 and r_amt > 0 and abs(sum_fp - r_amt) > 1.0) else 1.0
                    for it in valid_items:
                        fp = it['price'] if it['price'] > 0 else (r_amt / max(1, len(valid_items)))
                        fp = round(fp * f_scale, -2)
                        parsed_food.append({'Food_Group': f_group, 'Place': place_clean, 'Item': it['name'], 'Local_val': fp, 'Curr': r_curr})

            res_df = pd.DataFrame(parsed_food)
            if not res_df.empty:
                res_df = res_df[res_df['Local_val'] > 0].copy()
                res_df['KRW_str'] = res_df['Local_val'].apply(lambda v: f"약 {round(v * war_rate, -2):,.0f}원") if (war_rate > 0) else ""
            return res_df

        @st.cache_data(ttl=600)
        def parse_cached_traffic_items(df_records, travel_curr, war_rate):
            df_src = pd.DataFrame(df_records)
            def is_traffic(r):
                cat, desc, met = str(r['Category']).strip(), str(r['Description']).strip().lower(), str(r['PaymentMethod']).strip()
                if met in ['원화계좌(한국)', '해외송금(한국계좌)']: return False
                if cat == '버스': return not any(k in desc for k in ['시외', '고속', '장거리', '슬리핑', 'limousine', 'intercity'])
                if cat in ['기차', '열차'] or any(k in desc for k in ['헤리티지열차', '헤리티지', 'railway', 'vnr']): return False
                return cat in ['Grab', 'VinBus', 'DiDi', '택시', '블랙택시', '지하철', '트램']

            t_df = df_src[df_src.apply(is_traffic, axis=1) & (df_src['IsExpense'] == 1)].copy()
            if t_df.empty: return pd.DataFrame()

            tot_t_raw = t_df['Amount'].sum()
            parsed_t = []
            for _, r in t_df.iterrows():
                cat_r, desc_raw, r_amt = str(r['Category']).strip(), str(r['Description']), float(r['Amount'])
                r_curr = str(r['Currency']).strip().upper() or travel_curr
                clean_desc = re.sub(r'\[.*?\]\s*', '', desc_raw).strip()
                lines_t = [l.strip() for l in clean_desc.split('\n') if l.strip()]
                first_line = lines_t[0] if lines_t else clean_desc
                first_line = re.sub(r'[\d,\.]+\s*(?:vnd|동|원|\$|[kK])\b.*$', '', first_line, flags=re.IGNORECASE)
                first_line = re.sub(r'\b\d+(?:\.\d+)?\s*(?:km|분|초|시간)\b.*$', '', first_line, flags=re.IGNORECASE).strip(' ,-')

                p_provider = cat_r if cat_r in ['Grab', 'VinBus', 'DiDi', '택시', '블랙택시'] else "로컬교통"
                p_prov_clean = auto_fit_header_label(p_provider, r_amt, tot_t_raw) or "이동 수단"
                p_item_clean = smart_wrap_multiline(first_line, max_line_len=11) or "이동 요금"
                parsed_t.append({'Traffic_Group': '그랩 및 로컬교통', 'Provider': p_prov_clean, 'Item': p_item_clean, 'Local_val': r_amt, 'Curr': r_curr})

            res_df = pd.DataFrame(parsed_t)
            if not res_df.empty:
                res_df = res_df[res_df['Local_val'] > 0].copy()
                res_df['KRW_str'] = res_df['Local_val'].apply(lambda v: f"약 {round(v * war_rate, -2):,.0f}원") if (war_rate > 0) else ""
            return res_df

        @st.cache_data(ttl=600)
        def parse_cached_massage_items(df_records, travel_curr, war_rate):
            df_src = pd.DataFrame(df_records)
            m_df = df_src[(df_src['Category'] == '마사지') & (df_src['IsExpense'] == 1)].copy()
            if m_df.empty: return pd.DataFrame()

            tot_m_raw = m_df['Amount'].sum()
            parsed_m = []
            for _, r in m_df.iterrows():
                desc_raw, r_amt = str(r['Description']), float(r['Amount'])
                r_curr = str(r['Currency']).strip().upper() or travel_curr
                clean_desc = re.sub(r'\[.*?\]\s*', '', desc_raw).strip()
                p_provider, p_item = clean_desc.split('-', 1) if '-' in clean_desc else (clean_desc, clean_desc)
                p_prov_clean = auto_fit_header_label(p_provider.strip(), r_amt, tot_m_raw) or "마사지 샵"
                p_item_clean = smart_wrap_multiline(p_item.strip(), max_line_len=10) or "힐링 마사지"
                parsed_m.append({'Massage_Group': '마사지', 'Provider': p_prov_clean, 'Item': p_item_clean, 'Local_val': r_amt, 'Curr': r_curr})

            res_df = pd.DataFrame(parsed_m)
            if not res_df.empty:
                res_df = res_df[res_df['Local_val'] > 0].copy()
                res_df['KRW_str'] = res_df['Local_val'].apply(lambda v: f"약 {round(v * war_rate, -2):,.0f}원") if (war_rate > 0) else ""
            return res_df

        # 돋보기 서브 3대 탭 메뉴
        sub_tab_choice = option_menu(
            menu_title=None,
            options=["장바구니", "식당·카페", "마사지·교통"],
            icons=["cart3", "cup-hot", "car-front"],
            default_index=0,
            orientation="horizontal",
            styles={
                "container": {"padding": "0px !important", "background-color": "transparent", "margin-bottom": "12px", "gap": "6px"},
                "icon": {"color": "#38BDF8", "font-size": "13px", "margin-right": "2px"},
                "nav-link": {
                    "font-size": "13.5px", "font-weight": "600", "text-align": "center", "margin": "0px",
                    "padding": "8px 6px", "white-space": "nowrap", "background-color": "#1E293B", "color": "#38BDF8",
                    "border-radius": "8px", "border": "1.5px solid #475569", "--hover-color": "#334155"
                },
                "nav-link-selected": {
                    "background-color": "#FF9E00", "background-image": "linear-gradient(135deg, #FF9E00 0%, #EA580C 100%)",
                    "color": "#FFFFFF", "font-size": "14px", "font-weight": "800", "border": "1.5px solid #FFA500"
                }
            }
        )

        if not ledger_df.empty:
            raw_records = ledger_df[['Date', 'Category', 'Description', 'Currency', 'Amount', 'PaymentMethod', 'IsExpense']].to_dict('records')
            war_val = get_WAR(TRAVEL_CURRENCY)

            # 1. 🌟 장바구니 트리맵 (캐시 적용)
            if sub_tab_choice == "장바구니":
                item_df = parse_cached_market_items(raw_records, TRAVEL_CURRENCY, war_val)
                if not item_df.empty:
                    base_curr = item_df['Curr'].iloc[0] if 'Curr' in item_df.columns else TRAVEL_CURRENCY
                    tot_market_local = item_df['Local_val'].sum()
                    st.metric(f"장바구니 총 지출액 ({base_curr} 기준)", f"{tot_market_local:,.0f} {base_curr}")
                    fig_market = px.treemap(
                        item_df, path=['Bazaar_Group', 'Store', 'Item'], values='Local_val', color='Local_val',
                        color_continuous_scale='Tealgrn', custom_data=['KRW_str'], title=None
                    )
                    cart_tt = "<b>%{label}</b><br>%{value:,.0f} " + base_curr + "<br><span style='font-size:12px; opacity:0.9;'>%{customdata[0]}</span>" if base_curr != 'KRW' else "<b>%{label}</b><br>%{value:,.0f} KRW"
                    fig_market.update_traces(texttemplate=cart_tt, hovertemplate=f"<b>분류/상호/품목:</b> %{{label}}<br><b>지출액:</b> %{{value:,.0f}} {base_curr}<br><b>비중:</b> %{{percentRoot:.1%}}<extra></extra>", textposition='middle center', insidetextfont=dict(size=16), pathbar=dict(thickness=24, visible=True), tiling=dict(pad=5))
                    fig_market.update_layout(margin=dict(l=0, r=0, t=10, b=10), height=580, coloraxis_showscale=False)
                    st.plotly_chart(fig_market, use_container_width=True, config={'displaylogo': False})
                else:
                    st.info("기록된 마트, 시장 또는 선물 지출 내역이 없습니다.")

            # 2. 🌟 식당·카페 트리맵 (캐시 적용)
            elif sub_tab_choice == "식당·카페":
                food_df = parse_cached_food_items(raw_records, TRAVEL_CURRENCY, war_val)
                if not food_df.empty:
                    f_base_curr = food_df['Curr'].iloc[0] if 'Curr' in food_df.columns else TRAVEL_CURRENCY
                    tot_food_local = food_df['Local_val'].sum()
                    st.metric(f"식당·카페 총 지출액 ({f_base_curr} 기준)", f"{tot_food_local:,.0f} {f_base_curr}")
                    fig_food = px.treemap(
                        food_df, path=['Food_Group', 'Place', 'Item'], values='Local_val', color='Local_val',
                        color_continuous_scale='YlOrBr', custom_data=['KRW_str'], title=None
                    )
                    food_tt = "<b>%{label}</b><br>%{value:,.0f} " + f_base_curr + "<br><span style='font-size:12px; opacity:0.9;'>%{customdata[0]}</span>" if f_base_curr != 'KRW' else "<b>%{label}</b><br>%{value:,.0f} KRW"
                    fig_food.update_traces(texttemplate=food_tt, hovertemplate=f"<b>분류/장소/메뉴:</b> %{{label}}<br><b>지출액:</b> %{{value:,.0f}} {f_base_curr}<br><b>비중:</b> %{{percentRoot:.1%}}<extra></extra>", textposition='middle center', insidetextfont=dict(size=16), pathbar=dict(thickness=24, visible=True), tiling=dict(pad=5))
                    fig_food.update_layout(margin=dict(l=0, r=0, t=10, b=10), height=580, coloraxis_showscale=False)
                    st.plotly_chart(fig_food, use_container_width=True, config={'displaylogo': False})
                else:
                    st.info("기록된 식사 또는 간식 지출 내역이 없습니다.")

            # 3. 🌟 마사지·교통 듀얼 트리맵 (캐시 적용)
            elif sub_tab_choice == "마사지·교통":
                st.markdown("<h4 style='margin-bottom: 2px;'>그랩 및 로컬교통</h4>", unsafe_allow_html=True)
                traffic_df_final = parse_cached_traffic_items(raw_records, TRAVEL_CURRENCY, war_val)
                if not traffic_df_final.empty:
                    t_base_curr = TRAVEL_CURRENCY
                    tot_traffic_local = traffic_df_final['Local_val'].sum()
                    st.markdown(f"<div style='font-size: 22px; font-weight: bold; color: #4EFEB3; margin-bottom: 8px;'>{tot_traffic_local:,.0f} {t_base_curr}</div>", unsafe_allow_html=True)
                    fig_traffic = px.treemap(traffic_df_final, path=['Traffic_Group', 'Provider', 'Item'], values='Local_val', color='Local_val', color_continuous_scale='Tealgrn', custom_data=['KRW_str'], title=None)
                    traffic_tt = "<b>%{label}</b><br>%{value:,.0f} " + t_base_curr + "<br><span style='font-size:12px; opacity:0.9;'>%{customdata[0]}</span>" if t_base_curr != 'KRW' else "<b>%{label}</b><br>%{value:,.0f} KRW"
                    fig_traffic.update_traces(texttemplate=traffic_tt, hovertemplate=f"<b>분류/이동수단/내역:</b> %{{label}}<br><b>지출액:</b> %{{value:,.0f}} {t_base_curr}<br><b>비중:</b> %{{percentRoot:.1%}}<extra></extra>", textposition='middle center', insidetextfont=dict(size=16), pathbar=dict(thickness=24, visible=True), tiling=dict(pad=5))
                    fig_traffic.update_layout(margin=dict(l=0, r=0, t=10, b=10), height=460, coloraxis_showscale=False)
                    st.plotly_chart(fig_traffic, use_container_width=True, config={'displaylogo': False})
                else:
                    st.info("기록된 로컬 교통 지출 내역이 없습니다.")

                st.markdown("<div style='margin: 30px 0px; border-top: 1px dashed #475569;'></div>", unsafe_allow_html=True)

                st.markdown("<h4 style='margin-bottom: 2px;'>마사지</h4>", unsafe_allow_html=True)
                massage_df_final = parse_cached_massage_items(raw_records, TRAVEL_CURRENCY, war_val)
                if not massage_df_final.empty:
                    m_base_curr = TRAVEL_CURRENCY
                    tot_massage_local = massage_df_final['Local_val'].sum()
                    st.markdown(f"<div style='font-size: 22px; font-weight: bold; color: #4EFEB3; margin-bottom: 8px;'>{tot_massage_local:,.0f} {m_base_curr}</div>", unsafe_allow_html=True)
                    fig_massage = px.treemap(massage_df_final, path=['Massage_Group', 'Provider', 'Item'], values='Local_val', color='Local_val', color_continuous_scale='Tealgrn', custom_data=['KRW_str'], title=None)
                    massage_tt = "<b>%{label}</b><br>%{value:,.0f} " + m_base_curr + "<br><span style='font-size:12px; opacity:0.9;'>%{customdata[0]}</span>" if m_base_curr != 'KRW' else "<b>%{label}</b><br>%{value:,.0f} KRW"
                    fig_massage.update_traces(texttemplate=massage_tt, hovertemplate=f"<b>분류/업체/코스:</b> %{{label}}<br><b>지출액:</b> %{{value:,.0f}} {m_base_curr}<br><b>비중:</b> %{{percentRoot:.1%}}<extra></extra>", textposition='middle center', insidetextfont=dict(size=16), pathbar=dict(thickness=24, visible=True), tiling=dict(pad=5))
                    fig_massage.update_layout(margin=dict(l=0, r=0, t=10, b=10), height=460, coloraxis_showscale=False)
                    st.plotly_chart(fig_massage, use_container_width=True, config={'displaylogo': False})
                else:
                    st.info("기록된 마사지 지출 내역이 없습니다.")
    render_magnifier_fragment()

# ==============================================================================



# ==============================================================================
# 6.04.00 | Final Settlement Dashboard (전체요약 탭 - 원스톱 정산 / No Emoji)
# ==============================================================================
elif main_tab_choice == "전체요약":
    if not exp_df.empty:
        total_trip_krw = exp_df['KRW_val'].sum()
        total_trip_loc = exp_df['Local_val'].sum()
        
        trip_cfg = TRIP_CONFIGS.get(st.session_state.current_trip, {})
        travelers = trip_cfg.get("travelers", 2)
        mapping_str = trip_cfg.get("stay_mapping", "")
        nights_match = re.findall(r'(\d+(?:\.\d+)?)', mapping_str)
        total_nights = sum(float(n) for n in nights_match) if nights_match else 7
        if total_nights == 0: total_nights = 7 

        is_fixed_cost_final = exp_df['IsFixedCost']
        dom_df = exp_df[is_fixed_cost_final & (~exp_df['Category'].isin(['입국','출국']))]
        ovr_df = exp_df[(~is_fixed_cost_final) & (~exp_df['Category'].isin(['입국','출국']))]

        dep_dt_f = dep_dt_calc
        arr_dt_f = arr_dt_calc

        # ----------------------------------------------------------------------
        # 1. 총지출 (종합 트리맵)
        # ----------------------------------------------------------------------
        st.markdown("<h3 style='margin-top: 0px; margin-bottom: 8px;'>총지출</h3>", unsafe_allow_html=True)
        chart_df = exp_df[exp_df['KRW_val'] > 0].copy()
        if not chart_df.empty:
            def sanitize_desc(row):
                d = str(row['Description']).strip()
                if not d or d.lower() == 'nan': d = row['Category']
                if d == row['Macro_Category'] or d == row['Category']: d = f"{d} (상세)"
                return d[:15] + ".." if len(d) > 15 else d

            chart_df['Short_Desc'] = chart_df.apply(sanitize_desc, axis=1)
            
            fig_tree = px.treemap(
                chart_df, 
                path=['Macro_Category', 'Category', 'Short_Desc'], 
                values='KRW_val', 
                color='KRW_val', 
                color_continuous_scale='Greens'
            )
            fig_tree.update_traces(
                texttemplate="<b>%{label}</b><br>%{value:,.0f}원", 
                hovertemplate="<b>%{label}</b><br>금액: %{value:,.0f}원<br>비중: %{percentRoot:.1%}<extra></extra>", 
                textposition='middle center', 
                insidetextfont=dict(size=16), 
                pathbar=dict(thickness=24, visible=True), 
                tiling=dict(pad=5)
            )
            fig_tree.update_layout(margin=dict(l=0, r=0, t=5, b=10), height=580, coloraxis_showscale=False)
            st.plotly_chart(fig_tree, use_container_width=True, config={'displaylogo': False})
        
        # ----------------------------------------------------------------------
        # 2. 파이 그래프 (도넛 차트 - 제목 없이 바로 렌더링)
        # ----------------------------------------------------------------------
        cat_pie = exp_df[exp_df['KRW_val'] > 0].groupby('Macro_Category')['KRW_val'].sum().reset_index().sort_values(by='KRW_val', ascending=False)
        
        if not cat_pie.empty:
            fig_donut = px.pie(
                cat_pie, 
                values='KRW_val', 
                names='Macro_Category', 
                hole=0.35, 
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig_donut.update_traces(
                textposition='inside', 
                textinfo='label+value+percent', 
                texttemplate="<b>%{label}</b><br>%{value:,.0f}원<br>(%{percent:.1%})", 
                insidetextfont=dict(size=13.5)
            )

            today_f = datetime.now(TZ_KST).date()
            if dep_dt_f and arr_dt_f:
                cal_days_f = (arr_dt_f - dep_dt_f).days + 1
                if today_f < dep_dt_f: center_sub_text = f"({cal_days_f}일예정)"
                elif dep_dt_f <= today_f <= arr_dt_f: center_sub_text = f"({(today_f - dep_dt_f).days + 1}일차)"
                else: center_sub_text = f"({cal_days_f}일간)"
            else:
                center_sub_text = f"({total_nights}일간)"

            fig_donut.add_annotation(
                text=f"<b>{total_trip_krw:,.0f}원</b><br><span style='font-size:12px; color:#A0AEC0;'>{center_sub_text}</span>", 
                showarrow=False, 
                align="center", 
                font=dict(size=16)
            )
            fig_donut.update_layout(
                height=420, 
                margin=dict(l=10, r=10, t=10, b=20), 
                legend=dict(orientation="h", yanchor="top", y=-0.05, xanchor="center", x=0.5)
            )
            st.plotly_chart(fig_donut, use_container_width=True)

        # ----------------------------------------------------------------------
        # 3. 사전결제 (스마트 트리맵)
        # ----------------------------------------------------------------------
        if not dom_df.empty:
            dom_chart_df = dom_df[dom_df['KRW_val'] > 0].copy()
            if not dom_chart_df.empty:
                st.divider()
                st.markdown("<h3 style='margin-bottom: 8px;'>사전결제</h3>", unsafe_allow_html=True)
                
                smart_macro_list = []
                smart_tile_list = []
                
                def clean_hotel_label(desc):
                    h_clean = re.sub(r'\[.*?\]\s*', '', desc)
                    h_clean = re.split(r'[,|]', h_clean)[0].strip()
                    m_nights = re.search(r'(\d+)\s*박', desc)
                    n_str = f" ({m_nights.group(1)}박)" if m_nights else ""
                    low = h_clean.lower()
                    if 'saigon' in low or 'morin' in low: short_name = "사이공 모린"
                    elif 'sanouva' in low: short_name = "사누바 다낭"
                    elif 'century' in low: short_name = "센츄리 리버"
                    elif 'coral' in low or '코럴' in low: short_name = "코럴베이"
                    elif 'impera' in low or '인페라' in low: short_name = "인페라 호텔"
                    elif 'splendido' in low or '스플랜디도' in low: short_name = "스플랜디도"
                    else:
                        short_name = re.sub(r'Hotel|호텔|리조트|Resort', '', h_clean, flags=re.IGNORECASE).strip()
                        if len(short_name) > 11: short_name = short_name[:10] + ".."
                    return f"{short_name}{n_str}"

                for idx, r in dom_chart_df.iterrows():
                    cat = str(r['Category']).strip()
                    desc = str(r['Description']).strip()
                    
                    if cat == '항공권':
                        if any(k in desc for k in ['부산', '인천', '김포', '대구', '제주', '청주', '왕복', '출국', '귀국', 'BX', 'VJ']): 
                            macro_lbl = "IN/OUT 항공권"
                        else: 
                            macro_lbl = "구간/국내선"
                        clean_d = re.sub(r'\[.*?\]\s*', '', desc).split('|')[0].strip()
                        name_lbl = clean_d if len(clean_d) <= 16 else clean_d[:15] + ".."
                    elif cat in ['호텔', '숙박']:
                        macro_lbl = "숙박"
                        name_lbl = clean_hotel_label(desc)
                    elif cat == '보험':
                        macro_lbl = "보험"
                        name_lbl = "여행자보험"
                    elif cat in ['기차', '교통', '지하철', '택시']:
                        macro_lbl = "현지교통(사전)"
                        name_lbl = desc.split('(')[0].strip()
                    else:
                        macro_lbl = "기타/통신"
                        name_lbl = desc[:12].strip()

                    smart_macro_list.append(macro_lbl)
                    smart_tile_list.append(name_lbl)
                    
                dom_chart_df['Smart_Macro'] = smart_macro_list
                dom_chart_df['Smart_Tile'] = smart_tile_list
                treemap_color_map = {
                    "IN/OUT 항공권": "#C62828", "구간/국내선": "#E53935", 
                    "숙박": "#1565C0", "보험": "#F9A825", 
                    "현지교통(사전)": "#00838F", "기타/통신": "#6A1B9A"
                }

                fig_dom = px.treemap(
                    dom_chart_df, 
                    path=['Smart_Macro', 'Smart_Tile'], 
                    values='KRW_val', 
                    color='Smart_Macro', 
                    color_discrete_map=treemap_color_map
                )
                fig_dom.update_traces(
                    texttemplate="<b>%{label}</b><br>%{value:,.0f}원", 
                    hovertemplate="<b>%{label}</b><br>금액: %{value:,.0f}원<br>비중: %{percentRoot:.1%}<extra></extra>", 
                    textposition='middle center',
                    insidetextfont=dict(size=16),
                    pathbar=dict(thickness=24, visible=True),
                    tiling=dict(pad=5)
                )
                fig_dom.update_layout(
                    margin=dict(l=0, r=0, t=5, b=10), 
                    height=520,
                    coloraxis_showscale=False
                )
                st.plotly_chart(fig_dom, use_container_width=True, config={'displaylogo': False})

        # ----------------------------------------------------------------------
        # 4. 요약 (사전결제 vs 여행지 지출 2분할 요약 박스)
        # ----------------------------------------------------------------------
        st.divider()
        st.markdown("<h3 style='margin-bottom: 8px;'>요약</h3>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.info("사전 결제")
            st.metric("순지출액", f"{dom_df['KRW_val'].sum():,.0f} 원")
            with st.expander("상세내역", expanded=False):
                dg = dom_df.groupby('Category').agg({'KRW_val':'sum', 'Date':'count'}).sort_values(by='KRW_val', ascending=False)
                for cat_name, row_data in dg.iterrows(): st.write(f"• {cat_name}({int(row_data['Date'])}회): {row_data['KRW_val']:,.0f} 원")
        with c2:
            st.success("여행지 지출")
            st.metric("총액", f"{ovr_df['KRW_val'].sum():,.0f} 원")
            with st.expander("상세내역", expanded=False):
                og = ovr_df.groupby('Category').agg({'KRW_val':'sum', 'Date':'count'}).sort_values(by='KRW_val', ascending=False)
                for cat_name, row_data in og.iterrows(): st.write(f"• {cat_name}({int(row_data['Date'])}회): {row_data['KRW_val']:,.0f} 원")

        # ----------------------------------------------------------------------
        # 5. 손실과 보상 (환불 목록)
        # ----------------------------------------------------------------------
        refund_df = ledger_df[ledger_df['Category'] == '환불']
        if not refund_df.empty:
            st.divider()
            st.markdown("<h3 style='margin-bottom: 8px;'>손실과 보상</h3>", unsafe_allow_html=True)
            r_krw = refund_df.apply(lambda r: r['Amount'] if str(r['Currency']).strip() == 'KRW' else r['Amount'] * r['AppliedRate'], axis=1).sum()
            st.warning(f"**환불총액:** {r_krw:,.0f} 원")
            with st.expander("상세내역", expanded=True):
                st.dataframe(refund_df[['Date', 'Country', 'Description', 'Amount', 'Currency', 'PaymentMethod']], use_container_width=True, hide_index=True)
    else:
        st.info("기록된 지출 데이터가 없습니다.")
# ------------------------------------------------------------------------------
# 6.05.00 | Build Version & Real-time Latency Benchmark Footer
# ------------------------------------------------------------------------------
t_render_end = time.perf_counter()
render_latency_ms = (t_render_end - t_render_start) * 1000

# ⏱️ 속도 상태별 뱃지 컬러 (500ms 미만 녹색, 1500ms 이상 경고 오렌지/레드)
if render_latency_ms < 500:
    perf_badge = f"<span style='color:#10B981; font-weight:bold;'>⚡ {render_latency_ms:,.0f}ms (초고속)</span>"
elif render_latency_ms < 1500:
    perf_badge = f"<span style='color:#38BDF8; font-weight:bold;'>⚡ {render_latency_ms:,.0f}ms (보통)</span>"
else:
    perf_badge = f"<span style='color:#F59E0B; font-weight:bold;'>🐢 {render_latency_ms:,.0f}ms (통신 지연중)</span>"

st.markdown(f"""
    <div style='display:flex; justify-content:space-between; align-items:center; font-size:12px; color:#64748B; border-top:1px solid #1E293B; padding-top:8px; margin-top:20px;'>
        <div>GTL Platform {VERSION} | Volume Guard: ~ 70 KB | Sync: {datetime.now(TZ_KST).strftime('%Y-%m-%d %H:%M:%S')}</div>
        <div>반응속도: {perf_badge}</div>
    </div>
""", unsafe_allow_html=True)
