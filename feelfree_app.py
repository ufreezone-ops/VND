## [v26.05.20.003]
## - **Date:** 2026-05-20
## - **Update Log:**
## - [Fixed] Data Engine과 URDI Engine 간의 인벤토리 차감 평가 기준 불일치로 인한 '사이드바 잔액 미차감 버그(Phantom Balance)' 완전 해결.
## - [Modified] `get_inventory_status` 로직을 `recalculate_entire_ledger`와 구조적으로 100% 동일하게 동기화하여, 데이터 타입 강제 변환 오류로부터 독립적인 실시간 평가(Dynamic Evaluation) 구조 적용.     

# ==============================================================================
# [Module 1.00.00] System Core & Configuration Engine (환경 및 관제탑 설정)
# ==============================================================================

# ------------------------------------------------------------------------------
# 1.01.00 | Global Setup (라이브러리 임포트, 페이지 및 시간대 설정)
# ------------------------------------------------------------------------------
# 1.01.01 | Page Config & Viewport Initialization
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

### ⚙️ [Logic: Global Config] 기본 환경 및 시간대 설정
st.set_page_config(page_title="Feelfree: 글로벌 여행 가계부", page_icon="🌏", layout="wide", initial_sidebar_state="expanded")

# 1.01.02 | Timezone Constants Setup
TZ_KST = timezone(timedelta(hours=9))

# ------------------------------------------------------------------------------
# 1.02.00 | Metadata & Constants Registry (매크로, 스키마, 시스템 상수)
# ------------------------------------------------------------------------------
### ⚙️[Logic: System Variable] 여행지 설정, 환율 및 매크로 매핑 데이터

# 1.02.01 | Macro Mapping Matrix (버스, 트램, 기차 교통 카테고리 완벽 매핑)
MACRO_MAP = {
    "Grab": "🚗 교통", "VinBus": "🚗 교통", "DiDi": "🚗 교통", "지하철": "🚗 교통", 
    "택시": "🚗 교통", "버스": "🚗 교통", "트램": "🚗 교통", "기차": "🚗 교통", "렌트카": "🚗 교통", "교통": "🚗 교통",
    "식사": "🍔 식음료", "간식": "🍔 식음료", "마트": "🍔 식음료",
    "마사지": "🏄 액티비티", "투어": "🏄 액티비티", "입장료": "🏄 액티비티",
    "선물": "🎁 쇼핑", "통신": "📱 통신/기타", "수수료": "📱 통신/기타", "팁": "📱 통신/기타",
    "항공권": "✈️ 항공권", "호텔": "🏨 숙박", "보험": "🛡️ 보험", 
    "보증금": "🏦 자산이동", "재환전": "🏦 자산이동", "상환": "🏦 자산이동", "개인지출": "🏦 자산이동"
}
VERSION = "v26.05.27.003"

# 1.02.02 | Schema Column Definitions
CORE_COLUMNS =['Date', 'Country', 'Category', 'Description', 'Currency', 'Amount', 'PaymentMethod', 'Receipt_URL']
SYSTEM_LOGIC_COLUMNS =['IsExpense', 'AppliedRate', 'Cum_Budget_KRW', 'Cum_Card_Local', 'Cum_Cash_Local', 'Note']
FINAL_COLUMNS = CORE_COLUMNS + SYSTEM_LOGIC_COLUMNS

# 1.02.03 | Third-party Keys & Nominal Bills Configuration
IMGBB_API_KEY = "81181bf834001b6191aaa90fa772c6f9"
BILLS =[500000, 200000, 100000, 50000, 20000, 10000, 5000, 2000, 1000]

CONFIG_SHEET = "_GTL_CONFIG_"

UPDATE_LOG_TEXT = """* `[Added]` 🚌 **교통 카테고리 '버스/트램/기차' 전역 지원**: 지출 입력 및 SPI 물가비교, 트리맵 차트에 버스 교통비 자동 분류 탑재."""

conn = st.connection("gsheets", type=GSheetsConnection)

# ------------------------------------------------------------------------------
# 1.03.00 | Cloud Version Control System (구글 시트 버전 로그 갱신)
# ------------------------------------------------------------------------------
# 1.03.01 | Google Sheets Auto Version Logger
def auto_update_log_to_gsheets():
    for attempt in range(3):
        try:
            log_df = conn.read(worksheet="version_log", ttl="10m") 
            if log_df is None or log_df.empty: log_df = pd.DataFrame(columns=["Version", "Date", "Log"])
            if VERSION not in log_df['Version'].values:
                new_log = pd.DataFrame([{"Version": VERSION, "Date": datetime.now(TZ_KST).strftime("%Y-%m-%d %H:%M:%S"), "Log": UPDATE_LOG_TEXT}])
                log_df = pd.concat([new_log, log_df], ignore_index=True)
                conn.update(worksheet="version_log", data=log_df)
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
# 1.04.01 | Control Tower Config Loader & Node Assembler
# [Modified] 다중 국가 지원(Stay_Mapping 파싱 로직 추가)이 적용된 동적 로더
@st.cache_data(ttl=600)
def get_trip_configs():
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
            st.info("💡 단기간에 많은 접속으로 구글 시트 요청 한도에 도달했습니다. 약 10초 후 새로고침 해주세요.")
            st.stop()
            
    if cfg_df is None or cfg_df.empty:
        st.error(f"🚨 **관제탑 설정('{CONFIG_SHEET}')이 비어있습니다.**")
        st.stop()
        
    # 1.04.02 | Multi-Country Node Financial Parser (국가명에 따른 현지 통화 자동 추론 헬퍼)
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
        
        # ➔ 🚀 [Added] 사이프러스 및 이스라엘 기항지 금융 정보 동적 해석 룰 주입
        if any(k in c_upper for k in ["이스라엘", "ISRAEL"]): return "ILS", "₪", 2, 1
        if any(k in c_upper for k in ["사이프러스", "CYPRUS", "키프로스"]): return "EUR", "€", 2, 1
        
        return def_c, def_s, def_t, def_m
    
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
        
        # 1. Base Node 설정
        nodes = {main_country: {
            "currency": main_curr,
            "symbol": main_sym, 
            "timezone": main_tz, 
            "multiplier": main_mult
        }}
        
        # [Added] 2. Stay_Mapping을 분석하여 경유하는 다중 국가(Multi-Node) 동적 생성
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
    return dynamic_configs

TRIP_CONFIGS = get_trip_configs()

# ------------------------------------------------------------------------------
# 1.05.00 | GUI Design System (커스텀 다크/화이트 듀얼 테마 엔진)
# ------------------------------------------------------------------------------

# 1.05.01 | Base Layout & Slim KPI Box CSS (모바일 제목 줄바꿈 방지 탑재)
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
    /* 본문 상단 여백 & 메인 배경 */
    .block-container {{ padding-top: 3.5rem !important; padding-bottom: 2rem !important; padding-left: 0.8rem !important; padding-right: 0.8rem !important; }}
    div[data-testid="stSelectbox"] {{ margin-top: 0px !important; margin-bottom: 0px !important; }}
    hr {{ margin: 0.4rem 0 0.6rem 0 !important; }}
    
    /* 📱 [모바일 메인 제목 줄바꿈 절대 방지: 후쿠오카/발칸 1줄 고정] */
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

    /* 슬림 KPI 카드 */
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


# 1.05.03 | Tab Navigation CSS (단정하고 선명한 뱃지 탭)
tab_bg_unselected = "#18202E" if is_dark else "#E2E8F0"
tab_text_unselected = "#38BDF8" if is_dark else "#0284C7"

st.markdown(f"""
    <style>
    .stTabs [data-baseweb="tab-list"] {{ display: flex !important; width: 100% !important; gap: 6px !important; padding: 4px !important; background: transparent !important; margin-bottom: 16px !important; }}
    .stTabs [data-baseweb="tab"] {{ flex: 1 1 0% !important; height: 42px !important; background-color: {tab_bg_unselected} !important; border-radius: 10px !important; border: 1px solid #334155 !important; display: flex !important; align-items: center !important; justify-content: center !important; }}
    .stTabs [data-baseweb="tab"] p {{ font-size: 15.5px !important; font-weight: 600 !important; color: {tab_text_unselected} !important; margin: 0px !important; }}
    .stTabs [aria-selected="true"] {{ background: linear-gradient(135deg, #FF9E00 0%, #EA580C 100%) !important; border: 1px solid #FFA500 !important; }}
    .stTabs [aria-selected="true"] p {{ color: #FFFFFF !important; font-size: 16px !important; font-weight: 800 !important; }}
    .stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {{ display: none !important; }}
    </style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# 1.06.00 | Session State Orchestrator (동적 세션 상태 및 URL 파라미터 안전 복원)
# ------------------------------------------------------------------------------
# 1.06.01 | Dynamic Session Context & Initializer
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
SURVIVAL_CATS =["간식", "Grab", "DiDi", "VinBus", "지하철", "마사지", "팁", "식사", "교통"]
FIXED_COST_CATS =["항공권", "호텔", "보험"]
DOMESTIC_CATS =["항공권", "호텔", "보험", "지하철", "택시"]

# [에러 방어] 하위 호환성을 위한 current_tz 안전 등록
if 'current_tz' not in st.session_state: st.session_state.current_tz = TZ_KST
if 'last_cat_name' not in st.session_state: st.session_state.last_cat_name = "식사"


# ==============================================================================
# [Module 2.00.00] Data Engine & Cloud Ledger Synchronizer (원장 연산 및 AI 엔진)
# ==============================================================================

# ------------------------------------------------------------------------------
# 2.01.00 | Classification & Fallback Utilities (자산 성격 분류 및 환율 보정)
# ------------------------------------------------------------------------------
# 2.01.01 | Asset Class Classifier
### ⚙️ [Logic: Data Parsing] 텍스트 기반 자산 분류기

# [Module A] Data Engine (Modified)

def get_asset_class(text):    
    """결제 수단 명칭을 분석하여 자산 성격(CASH/PREPAID/CREDIT/DOMESTIC) 분류"""
    txt = str(text).replace(" ", "").upper()
    
    # [Modified] "카드", "PAY" 등 범용 단어 제거 (현대카드, 네이버페이가 PREPAID로 오인되는 치명적 버그 해결)
    if any(k in txt for k in ["트래블", "로그", "월렛", "선불", "외화통장"]): 
        return "PREPAID"
    
    if any(k in txt for k in ["현금", "지폐", "CASH", "환전"]): 
        return "CASH"
    
    if any(k in txt for k in ["외상", "부채", "CREDIT"]):
        return "CREDIT" 
        
    return "DOMESTIC"

# 2.01.02 | Dynamic Default FX-Rate Estimator
### ⚙️[Logic: Rate Fallback] 평균 환율 동적 추론
def get_default_rate(curr):
    if curr == "KRW": return 1.0
    try:
        if 'ledger_df' in globals() and not ledger_df.empty:
            df_curr = ledger_df[(ledger_df['Currency'].str.strip() == curr) & (ledger_df['AppliedRate'] > 0)]
            if not df_curr.empty: return df_curr['AppliedRate'].mean()
    except: pass
    
    # [Modified] TRY(리라), TND(디나르), SGD(싱가폴달러) 추가 지원 (2023-2024년 기준 대략치)
    fallback_rates = {"VND": 0.056, "CNY": 190.0, "USD": 1350.0, "EUR": 1480.0, "TRY": 45.0, "TND": 430.0, "SGD": 1000.0, "RSD": 12.6, "HUF": 3.8}
    return fallback_rates.get(curr, 1.0)

# ------------------------------------------------------------------------------
# 2.02.00 | Media & Vision AI Subsystem (안전한 멀티모달 & 바우처 파서)
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

# 2.02.03 | Gemini Multimodal Direct Runner (실시간 가용 모델 자동 조회 & 대용량 전송 최적화 엔진)
def call_gemini_multimodal(contents, prompt_text=""):
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if not api_key:
        return "", "Streamlit Secrets에 GEMINI_API_KEY가 없습니다."

    # 1단계: 구글 서버에서 내 API 키로 실제 호출 가능한 모델 목록을 실시간 자동 조회 (404 방어)
    available_models = []
    for ver in ['v1', 'v1beta']:
        try:
            list_url = f"https://generativelanguage.googleapis.com/{ver}/models?key={api_key}"
            l_resp = requests.get(list_url, timeout=4)
            if l_resp.status_code == 200:
                m_list = l_resp.json().get('models', [])
                for m in m_list:
                    methods = m.get('supportedGenerationMethods', [])
                    if 'generateContent' in methods:
                        clean_name = m['name'].replace('models/', '')
                        if (ver, clean_name) not in available_models:
                            available_models.append((ver, clean_name))
        except Exception:
            pass

    # flash 계열 최우선 정렬
    def model_priority(item):
        v, name = item
        if '2.5-flash' in name: return 1
        if '2.0-flash' in name: return 2
        if '1.5-flash' in name: return 3
        if 'flash' in name: return 4
        if 'pro' in name: return 5
        return 6

    available_models.sort(key=model_priority)

    if not available_models:
        available_models = [
            ('v1', 'gemini-1.5-flash'),
            ('v1beta', 'gemini-1.5-flash'),
            ('v1beta', 'gemini-2.0-flash-exp'),
            ('v1', 'gemini-2.5-flash'),
            ('v1beta', 'gemini-2.5-flash')
        ]

    # 2단계: 이미지 리사이징 헬퍼 (3.5MB -> 150KB 이하로 0.05초 만에 초경량화하여 20초 병목 제거)
    def resize_image_if_large(raw_bytes):
        try:
            if len(raw_bytes) > 800 * 1024:  # 800KB 이상인 사진만 대상
                from PIL import Image
                import io
                img = Image.open(io.BytesIO(raw_bytes))
                max_dim = 1200
                if max(img.size) > max_dim:
                    scale = max_dim / float(max(img.size))
                    new_size = (int(img.size[0] * scale), int(img.size[1] * scale))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                buf = io.BytesIO()
                img.convert('RGB').save(buf, format='JPEG', quality=80, optimize=True)
                return buf.getvalue()
        except Exception:
            pass
        return raw_bytes

    # 전송 페이로드 구성
    rest_parts = []
    for item in contents:
        if isinstance(item, str):
            rest_parts.append({"text": item})
        elif isinstance(item, dict) and "data" in item:
            m_type = item.get("mime_type", "image/jpeg")
            b_data = item["data"]
            # PDF가 아닌 큰 이미지는 0.05초 압축 적용
            if not m_type.endswith("pdf") and not b_data.startswith(b"%PDF"):
                b_data = resize_image_if_large(b_data)
                m_type = "image/jpeg"

            b64_str = base64.b64encode(b_data).decode("utf-8")
            rest_parts.append({
                "inline_data": {
                    "mime_type": m_type,
                    "data": b64_str
                }
            })
    if prompt_text:
        rest_parts.append({"text": prompt_text})

    payload = {"contents": [{"parts": rest_parts}]}
    last_err = ""

    # 3단계: 가용 모델로 순차 호출
    for api_ver, m_name in available_models:
        try:
            url = f"https://generativelanguage.googleapis.com/{api_ver}/models/{m_name}:generateContent?key={api_key}"
            resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                cand = data.get("candidates", [])
                if cand:
                    parts = cand[0].get("content", {}).get("parts", [])
                    if parts and "text" in parts[0]:
                        return parts[0]["text"].strip(), ""
            else:
                last_err = f"[{api_ver}/{m_name}] {resp.status_code}: {resp.text[:100]}"
        except Exception as e:
            last_err = f"[{api_ver}/{m_name}] 통신에러: {e}"
            continue

    return "", last_err

# 2.02.04 | Gemini LLM Multi-Lingual Receipt Parser (호텔 엔진과 100% 동일 규격 완결형)
def summarize_receipt_files_with_gemini(uploaded_files):
    if not uploaded_files: 
        return "", "", 0.0

    prompt = """너는 다국어 영수증 전문 분석 AI야. 첨부된 영수증 사진/문서를 분석하여 아래 규칙대로 정확히 출력해줘.

[출력 형식 지침]:
1. 첫 번째 줄에는 영수증에 인쇄된 결제일(승인일시)을 반드시 '[결제일: YYYY-MM-DD]' 형식으로 적어줘. (예: Ngày: 28/09/2026 -> [결제일: 2026-09-28]). 없으면 적지 마.
2. 두 번째 줄에는 영수증 맨 아래 실제 총 결제 금액을 반드시 '[총액: 155,000 VND]' 형식으로 적어줘. (예: Tổng tiền: 155,000 đ -> [총액: 155,000 VND]). 없으면 적지 마.
3. 세 번째 줄부터는 소비한 품목들을 한 줄씩 번역해서 나열해줘:
   - 한국어 품목명(원문) (특징) 가격 통화 형태로 출력 (예: 핀홀릭 블랙커피(PHINHOLIC 1 đen) 32,000 VND).
   - 깨강정(Kẹo mè xửng) 32,000 VND
   - 오색 디저트(Ngũ Sắc) 59,000 VND
4. 인사말이나 마크다운 백틱 없이 위 내용만 있는 그대로 출력해.
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

    raw_res, _ = call_gemini_multimodal(contents, prompt)
    if not raw_res:
        return "", "", 0.0

    cleaned = raw_res.strip()
    extracted_date = ""
    extracted_total = 0.0

    # 1. 결제일 추출
    m_date = re.search(r'\[결제일:\s*(\d{4}-\d{2}-\d{2})\]', cleaned)
    if m_date:
        extracted_date = m_date.group(1)
        cleaned = re.sub(r'\[결제일:[^\]]+\]\s*', '', cleaned).strip()

    # 2. 총액 추출
    m_tot = re.search(r'\[총액:\s*([\d,]+)', cleaned)
    if m_tot:
        try:
            extracted_total = float(m_tot.group(1).replace(',', ''))
            cleaned = re.sub(r'\[총액:[^\]]+\]\s*', '', cleaned).strip()
        except Exception:
            pass

    # 3. 총액 태그 누락 시 각 행 금액 합산
    if extracted_total <= 0:
        sum_calc = 0.0
        for line in cleaned.split("\n"):
            nums = re.findall(r'(\d{1,3}(?:,\d{3})+|\d+)', line)
            if nums:
                try: sum_calc += float(nums[-1].replace(',', ''))
                except Exception: pass
        if sum_calc > 0:
            extracted_total = sum_calc

    return cleaned, extracted_date, extracted_total

# 2.02.05 | Gemini Hotel Voucher Parser (면적/발코니/성급/부분취소율 다차원 분석 완결형)
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

    # call_gemini_multimodal의 튜플 반환값(raw_res, err) 정상 수신
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
# 2.03.01 | Date Format Normalizer
### ⚙️ [Logic: Data Formatting] 날짜 정규화 엔진
def normalize_date(d_str):
    d_str = str(d_str).strip()
    if re.match(r'^\d{4}-\d{2}-\d{2}', d_str): return d_str
    match = re.match(r'^(?:20)?(\d{2})[\.\-\/]\s*(\d{1,2})[\.\-\/]\s*(\d{1,2})\.?$', d_str)
    if match:
        y, m, d = match.groups()
        dt_obj = datetime.strptime(f"20{y}-{int(m):02d}-{int(d):02d}", "%Y-%m-%d")
        return dt_obj.strftime("%Y-%m-%d(%a)")
    return d_str

# 2.03.02 | Active Trip Ledger Loader & Normalizer
### ⚙️ [Logic: DB Load] GSheet 데이터 로드 및 클리닝
@st.cache_data(ttl=120)
def load_data(sheet_name):
    df = None
    for attempt in range(3):
        try:
            df = conn.read(worksheet=sheet_name, ttl="0s")
            break
        except Exception as e:
            if attempt < 2 and ("429" in str(e) or "Quota" in str(e)):
                time.sleep(2)
                continue
            st.error(f"🚨 **치명적 오류:** 클라우드 데이터베이스 연결에 실패했습니다. ({e})")
            st.stop()
        
    if df is None or df.empty: 
        df_init = pd.DataFrame(columns=FINAL_COLUMNS)
        try: conn.update(worksheet=ACTIVE_SHEET, data=df_init)
        except: pass 
        return df_init

    year_match = re.search(r'\((\d{4})\)', st.session_state.current_trip)
    trip_year = year_match.group(1) if year_match else "2024"

    if 'Country' not in df.columns: df.insert(1, 'Country', FIRST_NODE_NAME)
    else:
        df['Country'] = df['Country'].astype(str).str.strip().replace(['nan', 'None', ''], None)
        df['Country'] = df['Country'].fillna(FIRST_NODE_NAME)
    
    if 'Cum_Card_VND' in df.columns: df.rename(columns={'Cum_Card_VND': 'Cum_Card_Local'}, inplace=True)
    if 'Cum_Cash_VND' in df.columns: df.rename(columns={'Cum_Cash_VND': 'Cum_Cash_Local'}, inplace=True)
    if 'Receipt_URL' not in df.columns: df['Receipt_URL'] = ""
        
    df = df.dropna(subset=['Date', 'Category'], how='any')
    df['Category'] = df['Category'].astype(str).str.strip()
    
    # [Modified] 하위 호환성 보장: 과거 '트래블로그'로 기록된 명칭을 '트래블카드'로 일괄 자동 치환
    df['PaymentMethod'] = df['PaymentMethod'].astype(str).str.strip().str.replace('트래블로그', '트래블카드')
    
    df['Currency'] = df['Currency'].astype(str).str.strip().str.upper() 
    
    def fix_legacy_date(d):
        d = str(d).strip()
        if d and not re.match(r'^\d{4}', d): return f"{trip_year}-{d.replace('/', '-')}"
        return d

    df['Date'] = df['Date'].apply(fix_legacy_date)
    df['Date'] = df['Date'].apply(normalize_date)
    
    df = df.reindex(columns=FINAL_COLUMNS)
    
    numeric_cols = ['Amount', 'AppliedRate', 'Cum_Budget_KRW', 'Cum_Card_Local', 'Cum_Cash_Local']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
    
    df['IsExpense'] = pd.to_numeric(df['IsExpense'], errors='coerce').fillna(0).astype(int)
    df['Note'] = df['Note'].fillna("").astype(str)
    df['Receipt_URL'] = df['Receipt_URL'].fillna("").astype(str)
    return df

# 2.03.03 | Multi-Trip Global Ledger Consolidator
### ⚙️[Logic: DB Load All] 모든 여행 가계부 로드 (조회 전용)
@st.cache_data(ttl=600)
def load_all_trips_data():
    all_dfs =[]
    with st.spinner("🌍 모든 여행 기록을 불러오는 중... (한 번 불러오면 10분간 보관됩니다)"):
        for trip_name, config in TRIP_CONFIGS.items():
            for attempt in range(3):
                try:
                    # [Modified] 과거 기록은 10분 캐싱을 적용해 429 API 폭탄 원천 차단
                    df_t = conn.read(worksheet=config['sheet'], ttl="10m")
                    if df_t is not None and not df_t.empty:
                        df_t['TripName'] = trip_name 
                        first_node_name = list(config["nodes"].keys())[0]
                        if 'Country' not in df_t.columns: df_t.insert(1, 'Country', first_node_name)
                        else: df_t['Country'] = df_t['Country'].astype(str).str.strip().fillna(first_node_name)
                        all_dfs.append(df_t)
                    break
                except Exception as e:
                    if attempt < 2 and ("429" in str(e) or "Quota" in str(e)):
                        time.sleep(1.5)
                        continue
                    break
    if not all_dfs: return pd.DataFrame(columns=FINAL_COLUMNS + ['TripName'])
    return pd.concat(all_dfs, ignore_index=True)

# 2.03.04 | Precision Cloud Cache Cleaner
### ⚙️[Logic: Smart Cache] 429 에러 방지용 정밀 타격 캐시 클리너
def smart_cache_clear():
    try: load_data.clear(ACTIVE_SHEET)
    except: pass
    try: load_all_trips_data.clear()
    except: pass

# ------------------------------------------------------------------------------
# 2.04.00 | Core Ledger Engine (FIFO 인벤토리 배치 및 금융 재계산)
# ------------------------------------------------------------------------------
# 2.04.01 | Full Ledger FIFO / Rate / Cumulative Engine
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
        
        # ➔ 🚀 [Modified] 아래와 같이 수정 ('개인지출' 예외 및 계산식 일괄 바인딩)
        clean_expense_cats = [c.strip() for c in EXPENSE_CATS]
        # [Modified] 지출 대상에서 개인지출(IsExpense = 0) 완벽 제외
        is_exp = 1 if cat in clean_expense_cats and cat not in['환불', '보증금', '재환전', '상환', '개인지출'] else 0
        temp_df.at[i, 'IsExpense'] = is_exp
        
        is_deductible = 1 if (is_exp == 1 or cat in ['보증금', '상환']) else 0
        rate = temp_df.at[i, 'AppliedRate'] 
        asset_cls = get_asset_class(method)
        
        if cat in['충전', '환전', '입금', '직접환전', '이월잔액']: # [Modified] 이월잔액 추가
            if curr != 'KRW' and (pd.isna(rate) or rate <= 0.0 or rate == 1.0): rate = get_default_rate(curr)
            if cat == '이월잔액': final_dest_cls = "CASH" # [Added] 이월잔액은 현금유입으로 처리
            elif cat == '충전': final_dest_cls = "PREPAID"
            elif cat in ['환전', '직접환전']: final_dest_cls = "CASH"
            else: final_dest_cls = get_asset_class(desc + method)

            target = f"트래블카드({curr})" if final_dest_cls == "PREPAID" else f"현금({curr})" # [Modified]
            if curr != 'KRW': inv_batches[target].append({'rate': rate, 'qty': qty})
            if asset_cls == "DOMESTIC" or cat == '충전' or cat == '이월잔액': c_budget += qty if curr == 'KRW' else qty * rate # [Modified]
        
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
                else: rate = get_default_rate(curr)
            
            # ➔ 🚀 [Modified] 환불 자산 성격에 따라 예산 정합성 분기 수정
            is_dep = str(row['Description']).replace(" ", "").lower()
            is_deposit_refund = any(k in is_dep for k in ["보증금", "deposit"])
            
            if not is_deposit_refund:
                # 1. 일반 지출 환불(항공/호텔 취소)은 카드/현금 가리지 않고 무조건 전체 여행 예산(c_budget) 감액 (Net 정합성 반영)
                c_budget -= qty if curr == 'KRW' else qty * rate
                # 2. 외화 카드/현금 지갑으로 환불된 경우 해당 외화 지갑 인벤토리(inv_batches)에 충전 처리
                if asset_cls != "DOMESTIC":
                    target = f"트래블카드({curr})" if asset_cls == "PREPAID" else f"현금({curr})"
                    if curr != 'KRW': inv_batches[target].append({'rate': rate, 'qty': qty})
            else:
                # 3. 보증금 환불은 최초 결제 시 DOMESTIC(원화신용카드 등)이었던 경우만 예산 차감 (PREPAID 보증금은 예산 변동 없음)
                if asset_cls == "DOMESTIC":
                    c_budget -= qty if curr == 'KRW' else qty * rate
                else:
                    target = f"트래블카드({curr})" if asset_cls == "PREPAID" else f"현금({curr})"
                    if curr != 'KRW': inv_batches[target].append({'rate': rate, 'qty': qty})
                
        elif cat in ['재환전', '개인지출']: # [Modified] 개인지출 시에도 동일하게 잔고 차감 및 c_budget(총예산)에서 취득원가만큼 자동 감액 처리
            if curr != 'KRW':
                target_from = f"트래블카드({curr})" if asset_cls == "PREPAID" else f"현금({curr})"
                temp_qty = qty
                if target_from in inv_batches:
                    for batch in inv_batches[target_from]:
                        if temp_qty <= 0: break
                        if batch['qty'] <= 0: continue
                        take = min(temp_qty, batch['qty']); batch['qty'] -= take; temp_qty -= take
                if pd.notna(rate) and rate > 0: c_budget -= qty * rate
                
        # [Added] 이종환전 시 외화 지갑(소스)에서 정확히 차감 (누적 예산은 변동 없음)
        elif cat == '이종환전':
            if curr != 'KRW':
                target_from = f"트래블카드({curr})" if asset_cls == "PREPAID" else f"현금({curr})"
                temp_qty = qty
                if target_from in inv_batches:
                    for batch in inv_batches[target_from]:
                        if temp_qty <= 0: break
                        if batch['qty'] <= 0: continue
                        take = min(temp_qty, batch['qty']); batch['qty'] -= take; temp_qty -= take
        
        elif cat == 'ATM출금':
            temp_qty = qty; total_inherited_krw = 0.0
            target_from = f"트래블카드({curr})"; target_to = f"현금({curr})" # [Modified]
            if target_from in inv_batches:
                for batch in inv_batches[target_from]:
                    if temp_qty <= 0: break
                    if batch['qty'] <= 0: continue
                    take = min(temp_qty, batch['qty']); batch['qty'] -= take
                    inv_batches[target_to].append({'rate': batch['rate'], 'qty': take})
                    total_inherited_krw += take * batch['rate']; temp_qty -= take
            
            if temp_qty > 0:
                fallback_r = get_WAR(curr)
                inv_batches[target_to].append({'rate': fallback_r, 'qty': temp_qty})
                total_inherited_krw += temp_qty * fallback_r
                
            if qty > 0: rate = total_inherited_krw / qty if total_inherited_krw > 0 else get_default_rate(curr)
        
        elif is_deductible == 1:
            if asset_cls == "DOMESTIC":
                if curr != 'KRW' and (pd.isna(rate) or rate <= 0.0): rate = get_default_rate(curr)
                c_budget += qty if curr == 'KRW' else qty * rate
                rate = 1.0 if curr == 'KRW' else rate
            elif curr != 'KRW':
                if asset_cls == "CREDIT":
                    rate = get_WAR(curr)
                    temp_df.at[i, 'Note'] = "Credit (Debt Generated)"
                else:
                    target = f"트래블카드({curr})" if asset_cls == "PREPAID" else f"현금({curr})" # [Modified]
                    temp_qty = qty; total_cost_krw = 0.0; decomposed =[]
                    
                    if target in inv_batches:
                        for batch in inv_batches[target]:
                            if temp_qty <= 0: break
                            if batch['qty'] <= 0: continue
                            take = min(temp_qty, batch['qty']); batch['qty'] -= take; temp_qty -= take
                            total_cost_krw += take * batch['rate']
                            r_prec = ".4f" if curr in ["VND", "HUF", "PHP"] else ".2f"
                            q_fmt = ",.0f" if curr in ["VND", "HUF"] else ",.2f"
                            decomposed.append(f"{take:{q_fmt}}@{batch['rate']:{r_prec}}")

                    if temp_qty > 0:
                        fallback_r = get_WAR(curr)
                        total_cost_krw += temp_qty * fallback_r
                        r_prec = ".4f" if curr in ["VND", "HUF", "PHP"] else ".2f"
                        q_fmt = ",.0f" if curr in ["VND", "HUF"] else ",.2f"
                        decomposed.append(f"{temp_qty:{q_fmt}}@{fallback_r:{r_prec}}(Auto-Topup?)")
                    
                    if qty > 0:
                        rate = total_cost_krw / qty 
                        if decomposed: temp_df.at[i, 'Note'] = "Decomposed: " + " + ".join(decomposed)
                    else: rate = 0.0

        row_country = temp_df.at[i, 'Country']
        nodes = TRIP_CONFIGS[st.session_state.current_trip].get("nodes", {})
        row_curr = nodes.get(row_country, FIRST_NODE)["currency"] if nodes else "USD"
        
        active_curr = curr if curr != 'KRW' else row_curr
        rnd_dec = 0 if active_curr in ["VND", "HUF", "KRW"] else 2
        
        temp_df.at[i, 'AppliedRate'] = rate
        temp_df.at[i, 'Cum_Budget_KRW'] = round(c_budget, 2)
        # [Modified] 동적으로 매핑된 active_curr를 기준으로 각 지갑 인벤토리 잔량 실시간 집계
        temp_df.at[i, 'Cum_Card_Local'] = round(sum([b['qty'] for b in inv_batches[f"트래블카드({active_curr})"]]), rnd_dec)
        temp_df.at[i, 'Cum_Cash_Local'] = round(sum([b['qty'] for b in inv_batches[f"현금({active_curr})"]]), rnd_dec)
        
    return temp_df

# ------------------------------------------------------------------------------
# 2.05.00 | Cloud Persistence & Guard (데이터 증발 차단 및 시트 커밋)
# ------------------------------------------------------------------------------
# 2.05.01 | Anti-Wipe Cloud Committer
### ⚙️[Logic: DB Save] 구글 시트 동기화
def save_data(df, metrics=None):
    if df is None or df.empty: 
        st.error("🚨 저장하려는 데이터가 비어있습니다. 데이터 보호를 위해 저장을 중단합니다.")
        return False
    
    existing_df = None
    for attempt in range(3):
        try:
            existing_df = conn.read(worksheet=ACTIVE_SHEET, ttl="0s")
            break
        except Exception as e:
            if attempt < 2 and ("429" in str(e) or "Quota" in str(e)):
                time.sleep(2)
                continue
            st.error(f"🚨 클라우드 상태 확인 실패! 덮어쓰기 참사를 막기 위해 저장을 차단합니다. ({e})")
            return False

    if existing_df is not None and len(existing_df) > 5:
        if len(df) <= 3:
            st.error(f"🚨 **치명적 데이터 증발(Wipe) 시도 차단됨!** (클라우드: {len(existing_df)}건 -> 저장시도: {len(df)}건)")
            return False

    final_df = recalculate_entire_ledger(df)
    
    for attempt in range(3):
        try:
            conn.update(worksheet=ACTIVE_SHEET, data=final_df.reindex(columns=FINAL_COLUMNS))
            smart_cache_clear() # [Fixed] 무식한 전체 캐시 삭제 대신 정밀 타격
            return True
        except Exception as e:
            if attempt < 2 and ("429" in str(e) or "Quota" in str(e)):
                time.sleep(2.5)
                continue
            st.error(f"🚨 클라우드 저장 실패: {e}")
            return False

# 2.05.02 | Atomic Ledger Appender
def append_new_data(new_rows_df):
    smart_cache_clear() # [Fixed] 
    latest_df = load_data(ACTIVE_SHEET)
    merged_df = pd.concat([latest_df, new_rows_df], ignore_index=True)
    return save_data(merged_df)
        
# [Optimistic Memory Cache] 구글 시트 재다운로드 병목 방지
if 'active_ledger_df' not in st.session_state or st.session_state.get('last_loaded_sheet') != ACTIVE_SHEET:
    st.session_state.active_ledger_df = load_data(ACTIVE_SHEET)
    st.session_state.last_loaded_sheet = ACTIVE_SHEET

ledger_df = st.session_state.active_ledger_df

# ------------------------------------------------------------------------------
# 2.05.03 | Cash Inventory Cloud Loader & Saver (지폐 실사 잔고 클라우드 동기화)
# ------------------------------------------------------------------------------

def quick_swap_and_save(df):
    try:
        # 안전 검사: 최소 건수 체크
        if df is None or len(df) < 3:
            return False
        # 사전 읽기와 금융 재계산을 건너뛰고 곧바로 구글 시트에 직결 반영
        conn.update(worksheet=ACTIVE_SHEET, data=df.reindex(columns=FINAL_COLUMNS))
        smart_cache_clear()
        return True
    except Exception as e:
        st.error(f"🚨 순서 변경 저장 실패: {e}")
        return False

CASH_SHEET = "_CASH_INVENTORY_"

def load_cash_inventory():
    for attempt in range(3):
        try:
            df = conn.read(worksheet=CASH_SHEET, ttl="0s")
            if df is not None and not df.empty:
                return df
            break
        except Exception as e:
            if attempt < 2 and ("429" in str(e) or "Quota" in str(e)):
                time.sleep(1.5)
                continue
            break
    return pd.DataFrame(columns=['TripName', 'Currency', 'Bill_Counts', 'Total_Amount', 'Updated_At'])

def save_cash_inventory(trip_name, currency, counts_dict, total_amt):
    try:
        df = load_cash_inventory()
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
        return True
    except Exception as e:
        st.error(f"🚨 지폐 실사 동기화 실패 (탭 '{CASH_SHEET}' 존재 여부 확인): {e}")
        return False

# ==============================================================================
# [Module 3.00.00] URDI Engine (Unified Real-time Deductive Inventory)
# ==============================================================================

# ------------------------------------------------------------------------------
# 3.01.00 | Real-time Inventory Audit (실시간 인벤토리 차감 및 상태 평가)
# ------------------------------------------------------------------------------
# 3.01.01 | Batch-level Multi-Wallet Inventory Evaluator
### ⚙️[Logic: URDI Engine] 인벤토리 잔고 추적
# [Modified] Data Engine과 구조적으로 100% 동일하게 동기화하여 차감 무결성 보장
def get_inventory_status(df):
    from collections import defaultdict
    temp_df = df.sort_values(by='Date', kind='mergesort', ignore_index=True) if not df.empty else df
    inv_batches = defaultdict(list)
    
    # 3.01.02 | Internal Weighted Average Rate Resolver (배치 평가용 WAR)
    def get_WAR(currency_account):
        sw_df = df[(df['Category'].str.strip().isin(['충전','환전','입금','직접환전'])) & (df['Currency'].str.strip() == currency_account)]
        if not sw_df.empty and sw_df['Amount'].sum() > 0: return (sw_df['Amount'] * sw_df['AppliedRate']).sum() / sw_df['Amount'].sum()
        return get_default_rate(currency_account)

    if temp_df.empty: return dict(inv_batches)
    
    clean_expense_cats = [c.strip() for c in EXPENSE_CATS]
    
    for _, row in temp_df.iterrows():
        qty, curr = row['Amount'], row['Currency']
        cat = str(row['Category']).strip()
        method = str(row['PaymentMethod']).strip()
        desc = str(row['Description']).strip()
        rate = row['AppliedRate']
        
        # [Added] 데이터 타입 오류 방지를 위한 동적 평가 로직 (recalculate_entire_ledger와 완전 동일)
        # [Modified] 개인지출 제외 추가
        is_exp = 1 if cat in clean_expense_cats and cat not in ['환불', '보증금', '재환전', '상환', '개인지출'] else 0
        is_deductible = 1 if (is_exp == 1 or cat in ['보증금', '상환']) else 0
        
        asset_cls = get_asset_class(method)
        
        if cat in ['충전', '환전', '입금', '직접환전', '이월잔액']: # [Modified] 이월잔액 추가
            if cat == '이월잔액': final_dest_cls = "CASH" # [Added]
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
                inv_batches[target_to].append({'rate': get_WAR(curr), 'qty': temp_qty, 'initial': temp_qty})
                
        elif cat in ['재환전', '개인지출']: # [Modified] 실시간 사이드바 잔량 계산에도 개인지출에 따른 차감 반영
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

sw_df_loc = ledger_df[(ledger_df['Category'].str.strip().isin(['충전','환전','입금','직접환전'])) & (ledger_df['Currency'].str.strip() == TRAVEL_CURRENCY)]
WAR_LOCAL = (sw_df_loc['Amount'] * sw_df_loc['AppliedRate']).sum() / sw_df_loc['Amount'].sum() if not sw_df_loc.empty and sw_df_loc['Amount'].sum() > 0 else get_default_rate(TRAVEL_CURRENCY)

# ------------------------------------------------------------------------------
# 3.02.00 | Foreign Exchange Valuation (가중 평균 환율 및 FIFO 환율 계산)
# ------------------------------------------------------------------------------
# 3.02.01 | Weighted Average Exchange Rate Engine
### ⚙️[Logic: URDI Engine] 가중 평균 환율(WAR) 및 FIFO 환율 계산
def get_WAR(curr):
    sw_df = ledger_df[(ledger_df['Category'].str.strip().isin(['충전','환전','입금','직접환전'])) & (ledger_df['Currency'].str.strip() == curr)]
    if not sw_df.empty and sw_df['Amount'].sum() > 0: return (sw_df['Amount'] * sw_df['AppliedRate']).sum() / sw_df['Amount'].sum()
    return get_default_rate(curr)

# 3.02.02 | Dynamic FIFO Cost Rate Simulator
def auto_calc_fifo_rate(amount, method, curr=TRAVEL_CURRENCY):
    asset_cls = get_asset_class(method)
    if asset_cls == "DOMESTIC": return get_WAR(curr)
    target = f"트래블카드({curr})" if asset_cls == "PREPAID" else f"현금({curr})" # [Modified]
    temp_inv = get_inventory_status(ledger_df)
    if target not in temp_inv: return get_WAR(curr)
    available_batches =[b for b in temp_inv[target] if b['qty'] > 0]
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
# 3.03.01 | Net Budget & Spent Metrics Calculator (철벽 숫자 변환 방어탑)
def calculate_summary_metrics(df):
    if df.empty: return 0.0, 0.0
    temp_df = df.sort_values(by='Date', kind='mergesort', ignore_index=True)
    
    # [Fixed] 문자열, 콤마, 결측치 등 어떤 값이 와도 무조건 순수 float로 안전 변환
    b_total = 0.0
    if 'Cum_Budget_KRW' in temp_df.columns:
        raw_b = temp_df['Cum_Budget_KRW'].iloc[-1]
        try:
            b_total = float(str(raw_b).replace(',', '').strip())
        except:
            b_total = 0.0
    if pd.isna(b_total): b_total = 0.0

    # 실지출 합산 안전 계산
    try:
        exp_sub = temp_df[temp_df['IsExpense'] == 1]
        gross_spent = exp_sub.apply(lambda r: float(r['Amount']) if str(r['Currency']).strip() == 'KRW' else float(r['Amount']) * float(r['AppliedRate']), axis=1).sum()
    except:
        gross_spent = 0.0

    # 환불액 차감 안전 계산
    try:
        expense_refunds = temp_df[
            (temp_df['Category'] == '환불') & 
            (~temp_df['Description'].str.contains("보증금|Deposit|deposit", na=False))
        ]
        refund_total = expense_refunds.apply(lambda r: float(r['Amount']) if str(r['Currency']).strip() == 'KRW' else float(r['Amount']) * float(r['AppliedRate']), axis=1).sum()
    except:
        refund_total = 0.0

    return float(b_total), float(gross_spent - refund_total)

# ==============================================================================
# [Module 4.00.00] Sidebar & Navigation Control Tower (사이드바 및 전역 라우터)
# ==============================================================================

# ------------------------------------------------------------------------------
# 4.01.00 | Sidebar Dashboard (지갑 잔고, 외상 관리, K단위 실물현금 카운터)
# ------------------------------------------------------------------------------
### 🎨 [GUI: Layout] 사이드바 영역

def cb_pull_cloud_cash(curr_c, counts_dict, b_list):
    for bill_val in b_list:
        b_id = str(bill_val).replace('.', '_')
        loaded_val = counts_dict.get(float(bill_val), 0)
        st.session_state[f"cnt_{curr_c}_{b_id}"] = int(loaded_val) if loaded_val > 0 else None

with st.sidebar:
    # --------------------------------------------------------------------------
    # [2단계] D-Day 및 취소 마감 지능형 관제탑 렌더러
    # --------------------------------------------------------------------------
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
        
        # 1. 비행 D-Day 배지 생성
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

        # 2. 호텔 취소 마감 D-Day 탐색
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

        # 관제탑 박스 출력
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

    # 4.01.01 | SPI / Provisioning Mode Context-Aware Panel
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
        # [심플한 위치 판정] 오늘이 출국일보다 이전이면 상단, 그렇지 않으면 하단!
        dep_rows_eval = ledger_df[ledger_df['Category'].str.contains('출국', na=False)]
        korea_dep_eval = ledger_df[ledger_df['Category'].str.contains('출국_한국|출국.*한국', na=False)]
        t_dep_eval = korea_dep_eval if not korea_dep_eval.empty else dep_rows_eval

        is_upcoming = False
        if not t_dep_eval.empty:
            m_eval = re.search(r'(\d{4}-\d{2})-(\d{2})', str(t_dep_eval.iloc[0]['Date']))
            if m_eval:
                dep_dt_val = datetime.strptime(m_eval.group(0), "%Y-%m-%d").date()
                today_val = datetime.now(TZ_KST).date()
                is_upcoming = (today_val < dep_dt_val)  # 👈 출국 전이면 True!

        # 출발 전(D-Day 이전)이면 사이드바 최상단에 배치
        if is_upcoming:
            render_dday_control_tower()

        # ----------------------------------------------------------------------
        # 4.01.02 | Multi-Currency Dynamic Wallet Monitor & K-Unit Physical Counter
        # ----------------------------------------------------------------------
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
        display_currs = primary_trip_currs + secondary_currs

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
        
        for c in display_currs:
            if c == "KRW": continue

            fmt = "{:,.2f}" if c not in["VND", "HUF", "PHP"] else "{:,.0f}"

            debt_amt = ledger_df[(ledger_df['Currency']==c) & (ledger_df['PaymentMethod'].str.contains("외상|부채|CREDIT", na=False))]['Amount'].sum()
            repay_amt = ledger_df[(ledger_df['Currency']==c) & (ledger_df['Category']=="상환")]['Amount'].sum()
            current_debt = debt_amt - repay_amt
            
            if current_debt > 0:
                st.markdown(f"<div style='color:#FF4B4B; font-size:13.5px; font-weight:bold;'>📌 미결제 외상: {fmt.format(current_debt)} {c}</div>", unsafe_allow_html=True)
            
            c_card = sum([b['qty'] for b in current_inventory_batches.get(f"트래블카드({c})",[])])
            c_cash = sum([b['qty'] for b in current_inventory_batches.get(f"현금({c})",[])])
            
            if c_card > 0 or c_cash > 0 or c in primary_trip_currs:
                st.markdown(f"<div style='color:#FFA500; font-weight:bold; margin-top:12px; margin-bottom:10px;'>● {c}</div>", unsafe_allow_html=True)
                st.markdown(f"💳 카드: **{fmt.format(c_card)}**")
                st.markdown(f"<div style='margin-bottom:12px;'>💵 현금: **{fmt.format(c_cash)}**</div>", unsafe_allow_html=True) 

                threshold = LOW_CASH_THRESHOLD.get(c, 1000000 if c == "VND" else 50)
                if is_trip_active and c_cash <= threshold:
                    st.markdown("""
                        <div style='color:#FFA500; font-size:12.5px; font-weight:bold; margin-top:2px; margin-bottom:14px; padding: 5px 10px; background-color: rgba(255, 165, 0, 0.12); border-radius: 6px; border-left: 3px solid #FFA500;'>
                            🚨 현금 부족 경고
                        </div>
                    """, unsafe_allow_html=True)
                
                card_batches = current_inventory_batches.get(f"트래블카드({c})", [])
                cash_batches = current_inventory_batches.get(f"현금({c})", [])
                
                if any(b['qty'] > 0 for b in (card_batches + cash_batches)):
                    with st.expander("🔍 상세 배치", expanded=is_trip_active):
                        r_fmt = ".4f" if c in ["VND", "HUF"] else ".2f"
                        if any(b['qty'] > 0 for b in card_batches):
                            st.caption("[카드]")
                            for b in card_batches:
                                if b['qty'] > 0: st.caption(f"• {fmt.format(b['qty'])} @{b['rate']:{r_fmt}}")
                        if any(b['qty'] > 0 for b in cash_batches):
                            st.caption("[현금]")
                            for b in cash_batches:
                                if b['qty'] > 0: st.caption(f"• {fmt.format(b['qty'])} @{b['rate']:{r_fmt}}")

                bills_to_count = CURR_BILLS.get(c, [])
                if bills_to_count and (c_cash > 0 or is_trip_active):
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

        # 4.01.03 | Net Financial Summary KPI Display
        st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
        st.metric("🏦 총 예산", f"{float(b_val):,.0f} 원")
        st.metric("💸 지출총액", f"{float(spent_val):,.0f} 원")

        # [2단계: 심플한 하단 배치] 출국 당일부터 여행 중/종료 후에는 지갑 아래 최하단에 렌더링!
        if not is_upcoming:
            st.divider()
            render_dday_control_tower()

        # 4.01.04 | Master Cloud Refresh (정합성 자동 재계산 일괄 실행)
        st.divider()
        st.markdown("<div style='margin-top:15px;'></div>", unsafe_allow_html=True)
        if st.button("🔄 Cloud Refresh (데이터 동기화)", use_container_width=True, type="primary"): 
            st.cache_data.clear()
            st.query_params["trip"] = st.session_state.current_trip
            if save_data(ledger_df):
                st.toast("✅ 클라우드 동기화 및 가계부 정합성 재계산 완료!", icon="🎉")
                time.sleep(0.5)
            st.rerun()

# ------------------------------------------------------------------------------
# 4.02.00 | Top Navigation Router (여행지 선택 및 관제탑 모드 스위처)
# ------------------------------------------------------------------------------
# 4.02.01 | Chronological Trip Sorter
def sort_trips(trip_names):
    return sorted(trip_names, key=lambda x: (re.search(r'\((\d{4})\)', x).group(1) if re.search(r'\((\d{4})\)', x) else '0000', x), reverse=True)

sorted_trips = sort_trips(list(TRIP_CONFIGS.keys()))

# 4.02.02 | Global Flight/SPI View Mode & Provisioning Switcher
SPECIAL_MODE_SPI = "📊 모든 여행지 물가비교"
SPECIAL_MODE_NEW = "➕ 새로운 여행지 개설"
dropdown_options = sorted_trips + [SPECIAL_MODE_SPI, SPECIAL_MODE_NEW]

if 'show_spi' not in st.session_state: 
    st.session_state.show_spi = False
if 'show_new_trip' not in st.session_state:
    st.session_state.show_new_trip = False

# 현재 선택된 여행지가 목록에 있는지 확인
if 'current_trip' not in st.session_state or st.session_state.current_trip not in sorted_trips:
    fukuoka_cands = [t for t in sorted_trips if "후쿠오카" in t or "FUKUOKA" in t.upper()]
    st.session_state.current_trip = fukuoka_cands[0] if fukuoka_cands else sorted_trips[0]

# 현재 보고 있는 인덱스 계산
if st.session_state.show_spi:
    curr_idx = len(sorted_trips)
elif st.session_state.show_new_trip:
    curr_idx = len(sorted_trips) + 1
else:
    curr_idx = sorted_trips.index(st.session_state.current_trip)

# [핵심 버그 수정] 드롭다운 변경 즉시 원장 데이터를 동기화하고 재실행(st.rerun)
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
    st.rerun() # 👈 드롭다운 선택 즉시 새 여행지 원장으로 완벽 전환!

st.selectbox(
    "✈️ 내 여행함 (Trip Selector)", 
    dropdown_options, 
    index=curr_idx, 
    key="top_nav_trip_selector", 
    on_change=on_trip_change,
    label_visibility="collapsed"
)

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

            # 실제 1박 이상 숙박(호텔 투숙)이 존재하는 정규 체류 국가만 추출
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
                
                # 5.01.03 | Horizontal Stacked Bar Chart & Display Table (확대/스크롤 고정)
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
                    
                    # [핵심] fixedrange=True, dragmode=False 로 모바일 확대 방지 및 부드러운 스크롤 보장
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
                
                # 📊 [5.02.04 | 수평 가로 막대 호텔 랭킹 차트 - 터치 스크롤 고정]
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
        # 5.03.00 | Channel 3: Flight Pricing Matrix (다구간 경유 노선 온전 추출 엔진)
        # ----------------------------------------------------------------------
        with sub_tab_flight:
            st.subheader("✈️ 항공권 요금 비교")
            st.caption("💡 각 항공권의 왕복/편도 여정을 구분하여 '1인당 왕복 환산 요금'으로 공평하게 비교합니다. 노선(Route)이 기재되지 않은 수화물/수수료 행은 해당 여행지의 메인 항공권에 자동으로 합산되며, 여행지별 설정된 인원수(Travelers)로 나누어 실질적인 '1인당 비용'을 산출합니다.")
            
            # 5.03.01 | Multi-Hop Flight Route Extractor (다구간/경유지 체인 완벽 추출)
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
            
            # 1. 1차 분류 및 수집
            for _, row in df_all.iterrows():
                cat = str(row['Category']).strip()
                desc = str(row['Description']).strip()
                amt = float(row['Amount'])
                
                if cat == '항공권' and amt > 0:
                    route = extract_airport_route(desc)
                    desc_lower = desc.lower()
                    
                    if "다구간" in desc_lower:
                        f_type = "다구간"
                    elif "왕복" in desc_lower:
                        f_type = "왕복"
                    elif "편도" in desc_lower:
                        f_type = "편도"
                    else:
                        if any(k in desc_lower for k in ["귀국", "rt", "round"]):
                            f_type = "왕복"
                        else:
                            f_type = "편도"
                    
                    fee_val = 0.0
                    match_fee = re.search(r'수수료:(\d+)원', str(row['Note']))
                    if match_fee: 
                        fee_val = float(match_fee.group(1))
                    
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
                    
                    if route:
                        primary_flights.append(flight_data)
                    else:
                        flight_surcharges.append(flight_data)
                        
                elif cat == '환불':
                    desc_lower = desc.lower()
                    if any(k in desc_lower for k in ["항공", "비행기", "페가수스", "세르비아", "항공사", "flight", "airline", "귁첸", "소피아", "베오그라드", "부다페스트", "티켓"]):
                        flight_refund_rows.append(row)

            # 5.03.02 | Surcharge/Baggage Allocation & Strict 1:1 Refund Matcher
            matched_refund_indices = set()
            
            for f in primary_flights:
                f_route = f['Route']
                f_trip = f['TripName']
                
                for s in flight_surcharges:
                    if s['TripName'] == f_trip:
                        f['Surcharge_Sum_KRW'] += s['Ticket_KRW']
                
                # 정밀 1:1 노선 매칭
                if f_route and '-' in f_route:
                    route_cities = [c.strip().lower() for c in f_route.split('-') if c.strip()]
                    dep_city, arr_city = route_cities[0], route_cities[-1]
                    
                    for r_idx, r in enumerate(flight_refund_rows):
                        if r_idx in matched_refund_indices:
                            continue
                        if r['TripName'] != f_trip:
                            continue
                            
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
                if f['Type'] == "편도":
                    f['RT_Equivalent_Per_Person_KRW'] = f['Per_Person_Net_KRW'] * 2
                else:
                    f['RT_Equivalent_Per_Person_KRW'] = f['Per_Person_Net_KRW']

            # 5.03.04 | Horizontal Flight Price Benchmark Bar Chart & Display Table (터치 스크롤 고정)
            if primary_flights:
                display_flight_rows = []
                chart_flight_data = []
                
                for f in primary_flights:
                    status_str = "정상"
                    if f['Refund_Rate'] >= 99.0: status_str = "🔴 100% 취소"
                    elif f['Refund_Rate'] > 0.0: status_str = f"🟡 부분환불 ({f['Refund_Rate']:.1f}%)"
                    
                    num_travelers = int(travelers_map.get(f['TripName'], 2))
                    
                    if f['Type'] == "편도":
                        rt_eq_str = f"{f['RT_Equivalent_Per_Person_KRW']:,.0f}원 (왕복요금으로 환산)"
                    else:
                        rt_eq_str = f"{f['RT_Equivalent_Per_Person_KRW']:,.0f}원"
                        
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
                    
                    # [2줄 라벨 적용: 온전한 다구간 노선명 <br> (여행명)]
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

# ==============================================================================
# [Module 5.04.00] Global Provisioning View (새로운 여행지 개설 단독 화면)
# ==============================================================================
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
# [Module 6.00.00] Individual Trip Manager Views (개별 여행 전용 모듈)
# ==============================================================================
else:
    st.title(f"{st.session_state.current_trip}")
    
    
    tab_main, tab_stats, tab_final = st.tabs(["가계부", "일일Data", "전체요약"])

    # --------------------------------------------------------------------------
    # 6.01.00 & 6.02.00 | Console Tab: Unified Ledger (가계부 통합 원장 & 인라인 편집)
    # --------------------------------------------------------------------------
    with tab_main:
        trip_nodes = TRIP_CONFIGS[st.session_state.current_trip].get("nodes", {})
        node_keys = list(trip_nodes.keys())
        is_single_country = len(node_keys) <= 1

        # 시차 및 날짜 컨텍스트 산출
        dep_rows_tz = ledger_df[ledger_df['Category'].str.contains('출국', na=False)]
        korea_dep_tz = ledger_df[ledger_df['Category'].str.contains('출국_한국|출국.*한국', na=False)]
        t_dep_tz = korea_dep_tz if not korea_dep_tz.empty else dep_rows_tz
        
        dep_dt_calc = None
        if not t_dep_tz.empty:
            m_d = re.search(r'(\d{4}-\d{2})-(\d{2})', str(t_dep_tz.iloc[0]['Date']))
            if m_d: dep_dt_calc = datetime.strptime(m_d.group(0), "%Y-%m-%d").date()

        arr_rows_tz = ledger_df[ledger_df['Category'].str.contains('귀국|입국', na=False)]
        korea_arr_tz = ledger_df[ledger_df['Category'].str.contains('귀국_한국|귀국.*한국|입국_한국|입국.*한국', na=False)]
        t_arr_tz = korea_arr_tz if not korea_arr_tz.empty else arr_rows_tz
        
        arr_dt_calc = None
        if not t_arr_tz.empty:
            m_a = re.search(r'(\d{4}-\d{2})-(\d{2})', str(t_arr_tz.iloc[-1]['Date']))
            if m_a: arr_dt_calc = datetime.strptime(m_a.group(0), "%Y-%m-%d").date()

        today_kst_now = datetime.now(TZ_KST).date()
        is_traveling_now = bool(dep_dt_calc and arr_dt_calc and dep_dt_calc <= today_kst_now <= arr_dt_calc)

        sel_node_default = node_keys[0] if node_keys else FIRST_NODE_NAME
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

        def clean_amount_to_float(val):
            if val is None: return 0.0
            if isinstance(val, (int, float)): return float(val)
            cleaned = re.sub(r'[^\d\.]', '', str(val).replace(',', ''))
            try: return float(cleaned) if cleaned else 0.0
            except: return 0.0

        if 'rcpt_key_idx' not in st.session_state: st.session_state.rcpt_key_idx = 0

        # ======================================================================
        # [상단부] 🚀 새 내역 등록기 (접이식 스마트 입력 카드)
        # ======================================================================
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

            # --- 1. 일반 지출 등록 폼 ---
            if mode == "일반 지출":
                clean_daily_cats = [c for c in EXPENSE_CATS if c not in ['항공권', '호텔', '보증금', '상환', '보험']]
                if not clean_daily_cats: clean_daily_cats = ["식사", "간식", "마트", "교통", "기타"]
                
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
                            with st.spinner("AI가 영수증 품목, 총금액, 결제일자를 분석 중..."):
                                smart_text, pay_date, total_amt = summarize_receipt_files_with_gemini(uploaded_files)
                                if smart_text:
                                    st.session_state['exp_desc_input'] = smart_text
                                    if total_amt > 0:
                                        st.session_state['exp_amt_int'] = int(total_amt)
                                        st.session_state['exp_amt_float'] = float(total_amt)
                                    if pay_date:
                                        parsed_dt = safe_parse_date_obj(pay_date, None)
                                        if parsed_dt: st.session_state['ai_payment_date'] = parsed_dt
                                    st.toast(f"🧾 분석 완료! 금액: {total_amt:,.0f} 자동 입력", icon="🎉")
                                    time.sleep(0.3)
                                    st.rerun()
                                else:
                                    st.error("🚨 영수증 인식을 완료하지 못했습니다.")
                                    
                with col_desc: 
                    desc = st.text_area("📝 내용 (상호명 및 다중 내역)", placeholder="예: 안바카페 - 소고기버거\n반미정식", height=120, key="exp_desc_input")

                gift_sum_amt = 0.0
                if desc and any(k in desc for k in ["VND", "KRW", "USD", "EUR", "동", "원"]):
                    lines = [line.strip() for line in desc.split("\n") if line.strip()]
                    with st.expander("🎁 선물/특산품 분리 지정 (순수 일일 체류비 왜곡 방지)", expanded=True):
                        st.caption("💡 아래 품목 중 **선물/특산품**으로 구매한 항목을 체크하시면, 일일체류비 통계에서 자동 분리 제외됩니다.")
                        selected_gifts = []
                        cols_g = st.columns(min(3, max(1, len(lines))))
                        for idx_l, line_str in enumerate(lines):
                            m_amt = re.findall(r'(\d{1,3}(?:,\d{3})+|\d+)', line_str)
                            c_box = cols_g[idx_l % len(cols_g)].checkbox(f"🎁 {line_str[:22]}..", key=f"chk_gift_{idx_l}")
                            if c_box:
                                selected_gifts.append(line_str)
                                if m_amt:
                                    try: gift_sum_amt += float(m_amt[-1].replace(',', ''))
                                    except: pass
                        st.session_state.gift_items_selected = selected_gifts
                        if gift_sum_amt > 0:
                            st.info(f"선물/특산품 분리 지정액: **{gift_sum_amt:,.0f}**")

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
                    final_receipt_urls = ""
                    if uploaded_files:
                        with st.spinner("📸 영수증 클라우드 보관 중..."):
                            u_list = [upload_image_to_imgbb(f) for f in uploaded_files if upload_image_to_imgbb(f)]
                            final_receipt_urls = ",".join(u_list)
                    
                    gift_note_tag = f" [🎁선물:{gift_sum_amt:,.0f}{curr}]" if gift_sum_amt > 0 else ""
                    final_desc = f"[{final_gateway}] {desc}{gift_note_tag}" if final_gateway else f"{desc}{gift_note_tag}"
                    new_row = pd.DataFrame([{'Date': sel_date.strftime("%Y-%m-%d(%a)"), 'Country': sel_node, 'Category': cat, 'Description': final_desc, 'Currency': curr, 'Amount': amt, 'PaymentMethod': met, 'IsExpense': 1, 'AppliedRate': cr_final, 'Note': f"Gift:{gift_sum_amt}" if gift_sum_amt > 0 else "", 'Receipt_URL': final_receipt_urls}])
                    if append_new_data(new_row): 
                        st.toast("🎉 지출이 성공적으로 기록되었습니다!", icon="✅")
                        st.session_state.clear_exp_desc = True
                        if 'exp_amt_int' in st.session_state: st.session_state['exp_amt_int'] = 0
                        if 'exp_amt_float' in st.session_state: st.session_state['exp_amt_float'] = 0.0
                        time.sleep(0.5); st.rerun()

            # --- 2. 항공권(특수) 등록 폼 ---
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

                btn_label = "🚀 항공권 및 일정 동시 기록"
                if st.button(btn_label, use_container_width=True, type="primary"):
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

            # --- 3. 호텔(특수) 등록 폼 ---
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
                        hotel_pay_row = pd.DataFrame([{'Date': sel_date.strftime("%Y-%m-%d(%a)"), 'Country': sel_node, 'Category': '호텔', 'Description': full_desc, 'Currency': h_curr, 'Amount': h_amt, 'PaymentMethod': clean_asset, 'IsExpense': 1, 'AppliedRate': h_rate, 'Note': f"수수료:{h_fee}원" if h_fee > 0 else "", 'Receipt_URL': final_hotel_receipts}])
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

            # --- 4. 자산 이동 등록 폼 ---
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

            # --- 5. 환불(취소) 등록 폼 ---
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

        # ======================================================================
        # [하단부] 📋 가계부 원장 조회 & 인라인 상세 수정기 (선물 자동 분리/신설 분할 엔진 탑재)
        # ======================================================================
        st.info("💡 **표의 행(Row)을 클릭(터치)하시면 상세 내역 수정, 순서 변경(🔼/🔽), 선물(🎁) 자동분리 신설, 영수증 AI 재스캔이 펼쳐집니다!**")
        viewer_placeholder = st.empty()

        initial_country = st.session_state.get('his_country', "이번 여행가계부")
        if initial_country == "모든 여행가계부": temp_display_df = load_all_trips_data()
        else:
            temp_display_df = ledger_df.copy()
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
            display_df = ledger_df.copy()
            if country_filter != "이번 여행가계부": display_df = display_df[display_df['Country'] == country_filter]

        if not display_df.empty: 
            display_df = display_df.reindex(columns=FINAL_COLUMNS)
            link_cfg = st.column_config.LinkColumn("영수증 📸", display_text="🔗 보기", disabled=True)
            
            render_df = display_df.copy()
            if cat_filter != "모든 카테고리": render_df = render_df[render_df['Category'] == cat_filter]
            if search_query.strip():
                mask = (render_df['Category'].str.contains(search_query, case=False, na=False) | render_df['Description'].str.contains(search_query, case=False, na=False) | render_df['Note'].str.contains(search_query, case=False, na=False) | render_df['Country'].str.contains(search_query, case=False, na=False))
                render_df = render_df[mask]
                
            st.write(f"🔎 검색 결과: {len(render_df)}건")

            dep_rows = ledger_df[ledger_df['Category'].str.contains('출국', na=False)]
            korea_dep = ledger_df[ledger_df['Category'].str.contains('출국_한국|출국.*한국', na=False)]
            target_dep_row = korea_dep if not korea_dep.empty else dep_rows
            dep_dt, arr_dt = None, None
            if not target_dep_row.empty:
                m_dep = re.search(r'(\d{4}-\d{2})-(\d{2})', str(target_dep_row.iloc[0]['Date']))
                if m_dep: dep_dt = datetime.strptime(m_dep.group(0), "%Y-%m-%d").date()

            arr_rows = ledger_df[ledger_df['Category'].str.contains('귀국|입국', na=False)]
            korea_arr = ledger_df[ledger_df['Category'].str.contains('귀국_한국|귀국.*한국|입국_한국|입국.*한국', na=False)]
            target_arr_row = korea_arr if not korea_arr.empty else arr_rows
            if not target_arr_row.empty:
                m_arr = re.search(r'(\d{4}-\d{2})-(\d{2})', str(target_arr_row.iloc[-1]['Date']))
                if m_arr: arr_dt = datetime.strptime(m_arr.group(0), "%Y-%m-%d").date()

            unique_dates = sorted(list(set(re.search(r'(\d{4}-\d{2})-(\d{2})', str(d)).group(0) for d in render_df['Date'] if re.search(r'(\d{4}-\d{2})-(\d{2})', str(d)))))
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
            
            df_event = st.dataframe(styled_table, use_container_width=True, column_config=col_cfg, hide_index=True, selection_mode="single-cell", on_select="rerun")
            selected_idx = None
            if getattr(df_event.selection, "cells", None) and len(df_event.selection.cells) > 0:
                selected_idx = df_event.selection.cells[0][0]
            elif getattr(df_event.selection, "rows", None) and len(df_event.selection.rows) > 0:
                selected_idx = df_event.selection.rows[0]

            # --- [인라인 상세 뷰어 & 선물 2개 행 자동 분할 수정기] ---
            if selected_idx is not None:
                real_idx = render_df.index[selected_idx] 
                row_data = display_df.loc[real_idx]
                
                with viewer_placeholder.container():
                    st.markdown("---")
                    c_info, c_edit = st.columns([1, 1.2])
                    with c_info:
                        st.subheader("🧾 상세 내역 및 영수증 뷰어")
                        c_up, c_down = st.columns(2)
                        with c_up:
                            if st.button("🔼 위로 한 칸 이동", key=f"btn_move_up_{real_idx}", use_container_width=True):
                                cur_df = st.session_state.active_ledger_df
                                if real_idx > 0:
                                    idx_above = real_idx - 1
                                    cur_df.iloc[idx_above], cur_df.iloc[real_idx] = cur_df.iloc[real_idx].copy(), cur_df.iloc[idx_above].copy()
                                    st.session_state.active_ledger_df = cur_df
                                    try: conn.update(worksheet=ACTIVE_SHEET, data=cur_df.reindex(columns=FINAL_COLUMNS))
                                    except: pass
                                    st.rerun()
                        with c_down:
                            if st.button("🔽 아래로 한 칸 이동", key=f"btn_move_down_{real_idx}", use_container_width=True):
                                cur_df = st.session_state.active_ledger_df
                                if real_idx < len(cur_df) - 1:
                                    idx_below = real_idx + 1
                                    cur_df.iloc[idx_below], cur_df.iloc[real_idx] = cur_df.iloc[real_idx].copy(), cur_df.iloc[idx_below].copy()
                                    st.session_state.active_ledger_df = cur_df
                                    try: conn.update(worksheet=ACTIVE_SHEET, data=cur_df.reindex(columns=FINAL_COLUMNS))
                                    except: pass
                                    st.rerun()

                        amt_fmt2 = "{:,.2f}" if MULTIPLIER == 1 and row_data['Currency'] != 'KRW' else "{:,.0f}"
                        krw_equivalent = row_data['Amount'] if row_data['Currency'] == 'KRW' else row_data['Amount'] * row_data['AppliedRate']
                        krw_display = f" ➔ <span style='color:#FFD700'>약 {krw_equivalent:,.0f} 원</span>" if row_data['Currency'] != 'KRW' else ""
                        st.markdown(f"### 🛒 {row_data['Category']} ({amt_fmt2.format(row_data['Amount'])} {row_data['Currency']}{krw_display})", unsafe_allow_html=True)
                        st.markdown(f"**🏦 결제수단:** `{row_data['PaymentMethod']}`")
                        
                        def smart_krw_translator(text, rate, curr):
                            if rate <= 0 or curr == 'KRW': return text
                            def replacer(match):
                                num_str = match.group(1).replace(',', '')
                                suffix = match.group(2).lower() if match.group(2) else ""
                                try:
                                    v = float(num_str)
                                    is_currency = any(c in suffix for c in ['vnd', 'usd', 'eur', 'cny', 'try', 'rsd', 'huf', 'krw', '원', '동', '달러'])
                                    is_unit = any(u in suffix for u in ['ml', 'g', 'kg', 'cm', 'mm', '개', 'x', '입', '장', '명', '박스'])
                                    if is_unit and not is_currency: return match.group(0)
                                    if is_currency or (curr in ['VND', 'HUF'] and v >= 1000) or ('.' in num_str) or (v > 100):
                                        krw_val = v * rate
                                        return f"{match.group(1)}<span style='font-size:13px;color:#FFD700;font-style:italic;'> (약 {krw_val:,.0f}원)</span>{match.group(2)}"
                                except: pass
                                return match.group(0)
                            pattern = re.compile(r'(?<![\d\.])(\d{1,3}(?:,\d{3})*(?:\.\d+)?)(?!\d)(\s*[a-zA-Z가-힣]*)')
                            return pattern.sub(replacer, text)

                        desc_full = str(row_data['Description'])
                        rate_for_calc = row_data['AppliedRate']
                        curr_for_calc = row_data['Currency']
                        if "-" in desc_full:
                            parts = desc_full.split("-", 1)
                            st.markdown(f"**🏪 상호명:** {parts[0].strip()}")
                            items = parts[1].strip().split("\n") if "\n" in parts[1] else parts[1].strip().split(",")
                            for item in items: 
                                if item.strip(): st.markdown(f"- {smart_krw_translator(item.strip(), rate_for_calc, curr_for_calc)}", unsafe_allow_html=True)
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
                                    display_df.at[real_idx, 'Receipt_URL'] = new_urls_str
                                    target_df = st.session_state.active_ledger_df if 'active_ledger_df' in st.session_state else display_df
                                    if real_idx in target_df.index: target_df.at[real_idx, 'Receipt_URL'] = new_urls_str
                                    if save_data(target_df):
                                        st.session_state.active_ledger_df = load_data(ACTIVE_SHEET)
                                        st.toast(f"사진 #{idx+1} 삭제 완료!", icon="✅"); time.sleep(0.4); st.rerun()
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
                                            st.toast("영수증 품목 분석 완료!", icon="🤖"); st.rerun()
                        with col_ai2:
                            if urls:
                                if st.button("🔄 기존 영수증 AI 재스캔", key=f"btn_ai_rescan_existing_{real_idx}", use_container_width=True):
                                    with st.spinner("기존 영수증 사진을 AI 재분석 중..."):
                                        try:
                                            img_resp = requests.get(urls[0], timeout=15)
                                            if img_resp.status_code == 200:
                                                class TempFileObj:
                                                    def __init__(self, b): self.b = b; self.name = "rescan.jpg"
                                                    def seek(self, pos): pass
                                                    def read(self): return self.b
                                                    def getvalue(self): return self.b
                                                mock_file = TempFileObj(img_resp.content)
                                                smart_text, _, tot_amt = summarize_receipt_files_with_gemini([mock_file])
                                                if smart_text:
                                                    st.session_state[desc_key] = smart_text
                                                    st.toast(f"기존 영수증 재스캔 완료! (총액: {tot_amt:,.0f})", icon="🎉")
                                                    st.rerun()
                                        except Exception as e_rescan:
                                            st.error(f"재스캔 실패: {e_rescan}")

                        new_desc = st.text_area("4. 세부 내역 (수정/추가)", height=110, key=desc_key)

                        # 💡 [핵심: 선물/일반 품목 분리 체크 및 2개 행 분할 인터페이스]
                        gift_items_split = []
                        normal_items_split = []
                        gift_amt_split = 0.0
                        
                        if new_desc and any(k in new_desc for k in ["VND", "KRW", "USD", "EUR", "동", "원"]):
                            clean_lines = [l.strip() for l in re.sub(r'\[🎁선물:[^\]]+\]', '', new_desc).split("\n") if l.strip()]
                            with st.expander("🎁 선물/특산품 분리 및 '선물' 항목 신설", expanded=True):
                                st.caption("💡 품목을 체크하시면 해당 품목들만 모아서 **'선물' 카테고리의 독립된 지출 행**으로 자동 분리 생성됩니다.")
                                cols_ge = st.columns(min(3, max(1, len(clean_lines))))
                                for idx_e, line_e in enumerate(clean_lines):
                                    m_amt_e = re.findall(r'(\d{1,3}(?:,\d{3})+|\d+)', line_e)
                                    val_e = float(m_amt_e[-1].replace(',', '')) if m_amt_e else 0.0
                                    # 기본 선택 추론 (선물, 기념품, 마그넷 등)
                                    is_already_gift = any(k in line_e for k in ["선물", "기념품", "마그넷", "팔찌", "목걸이", "자석", "캔디", "선물용"]) or (cur_cat == "선물")
                                    c_box_e = cols_ge[idx_e % len(cols_ge)].checkbox(f"🎁 {line_e[:20]}..", value=is_already_gift, key=f"chk_gift_edit_{real_idx}_{idx_e}")
                                    
                                    if c_box_e:
                                        gift_items_split.append(line_e)
                                        gift_amt_split += val_e
                                    else:
                                        normal_items_split.append(line_e)
                                
                                # 분리 상태 안내
                                total_receipt_amt = float(edit_amt)
                                remaining_normal_amt = max(0.0, total_receipt_amt - gift_amt_split)
                                
                                if gift_amt_split >= total_receipt_amt and total_receipt_amt > 0:
                                    st.info(f"✨ **100% 선물/기념품 영수증 감지**: 카테고리가 자동으로 **`선물` ({total_receipt_amt:,.0f} {row_data['Currency']})** 로 완벽 전환됩니다.")
                                elif gift_amt_split > 0 and remaining_normal_amt > 0:
                                    st.success(f"✂️ **2개 행으로 자동 분할 저장됩니다**:\n• 행 1 (`{edit_cat}`): **{remaining_normal_amt:,.0f}** {row_data['Currency']} (순수 체류비)\n• 행 2 (`선물`): **{gift_amt_split:,.0f}** {row_data['Currency']} (선물/쇼핑 통계로 신설 분리)")

                        # 💾 저장 및 2개 행 분할 실행기
                        if st.button("💾 이 내역 전체 업데이트 (선물 자동분할 동시적용)", use_container_width=True, type="primary"):
                            updated_rcpt_url = str(row_data.get('Receipt_URL', '')).strip()
                            if new_receipts:
                                with st.spinner("📸 영수증 클라우드 전송 중..."):
                                    new_urls = [upload_image_to_imgbb(f) for f in new_receipts if upload_image_to_imgbb(f)]
                                    if new_urls:
                                        existing_urls = [x.strip() for x in updated_rcpt_url.split(',') if x.strip().startswith('http')]
                                        updated_rcpt_url = ",".join(existing_urls + new_urls)

                            target_df = st.session_state.active_ledger_df if 'active_ledger_df' in st.session_state else ledger_df
                            total_receipt_amt = float(edit_amt)
                            
                            # [상황 1: 전체가 100% 선물인 경우 - 핑크성당 기념품 등]
                            if (gift_amt_split >= total_receipt_amt and total_receipt_amt > 0) or (len(gift_items_split) > 0 and len(normal_items_split) == 0):
                                target_df.at[real_idx, 'Category'] = "선물"
                                target_df.at[real_idx, 'Amount'] = total_receipt_amt
                                target_df.at[real_idx, 'PaymentMethod'] = edit_method
                                target_df.at[real_idx, 'Description'] = new_desc.strip()
                                target_df.at[real_idx, 'Receipt_URL'] = updated_rcpt_url
                                target_df.at[real_idx, 'Note'] = "100% Gift Purchase"
                                
                            # [상황 2: 일부만 선물인 경우 - 2개 행으로 자동 분할 Split!]
                            elif gift_amt_split > 0 and len(normal_items_split) > 0:
                                rem_amt = max(0.0, total_receipt_amt - gift_amt_split)
                                norm_desc = "\n".join(normal_items_split)
                                gift_desc = "\n".join(gift_items_split)
                                
                                # 기존 행 -> 일반 품목(마트 등)으로 축소 갱신
                                target_df.at[real_idx, 'Category'] = edit_cat
                                target_df.at[real_idx, 'Amount'] = rem_amt
                                target_df.at[real_idx, 'PaymentMethod'] = edit_method
                                target_df.at[real_idx, 'Description'] = norm_desc
                                target_df.at[real_idx, 'Receipt_URL'] = updated_rcpt_url
                                
                                # 신설 행 -> 선물 카테고리로 신규 생성하여 바로 아래 삽입
                                new_gift_row = pd.DataFrame([{
                                    'Date': row_data['Date'],
                                    'Country': row_data['Country'],
                                    'Category': '선물',
                                    'Description': f"[영수증분리] {gift_desc}",
                                    'Currency': row_data['Currency'],
                                    'Amount': gift_amt_split,
                                    'PaymentMethod': edit_method,
                                    'IsExpense': 1,
                                    'AppliedRate': row_data['AppliedRate'],
                                    'Note': f"Split from row {real_idx}",
                                    'Receipt_URL': updated_rcpt_url
                                }])
                                target_df = pd.concat([target_df.iloc[:real_idx + 1], new_gift_row, target_df.iloc[real_idx + 1:]], ignore_index=True)
                                
                            # [상황 3: 선물이 없는 일반 수정]
                            else:
                                target_df.at[real_idx, 'Category'] = edit_cat
                                target_df.at[real_idx, 'Amount'] = total_receipt_amt
                                target_df.at[real_idx, 'PaymentMethod'] = edit_method
                                target_df.at[real_idx, 'Description'] = new_desc.strip()
                                target_df.at[real_idx, 'Receipt_URL'] = updated_rcpt_url

                            if save_data(target_df):
                                st.session_state.active_ledger_df = load_data(ACTIVE_SHEET)
                                st.toast("🎉 선물 자동분할 및 업데이트 완료!", icon="✅")
                                time.sleep(0.4); st.rerun()
                    st.markdown("---")

    # --------------------------------------------------------------------------
    # 6.03.00 | Console Tab 3: Daily Statistics & Tree Visualizer (통계 및 일별 시각화)
    # --------------------------------------------------------------------------
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

                r_df = ledger_df[(ledger_df['Category'] == '환불') & (~ledger_df['Description'].str.contains("보증금|Deposit|deposit", na=False))].copy()
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

                # --------------------------------------------------------------
                # 6.03.00-A | 여행 라이프사이클(예정->X일차->N일간) 정밀 판별 엔진
                # --------------------------------------------------------------
                import math

                def is_korea_port(text):
                    txt = str(text).replace(" ", "")
                    return any(k in txt for k in ['한국', '인천', '부산', '김포', '대구', '제주', '청주', '귀국', 'ICN', 'PUS'])

                def is_foreign_transit(cat_str):
                    cat = str(cat_str).strip()
                    if "_" in cat:
                        sub_port = cat.split("_")[-1].strip()
                        if not is_korea_port(sub_port):
                            return True
                    return False

                # 출국일 정밀 탐색
                dep_candidates = ledger_df[
                    ledger_df['Category'].str.contains('출국', na=False) & 
                    ~ledger_df['Category'].apply(is_foreign_transit)
                ]
                korea_dep = ledger_df[ledger_df['Category'].apply(is_korea_port)]
                target_dep_row = korea_dep if not korea_dep.empty else dep_candidates

                dep_date_str = ""
                dep_dt = None
                if not target_dep_row.empty:
                    m_dep = re.search(r'(\d{4})-(\d{2})-(\d{2})', str(target_dep_row.iloc[0]['Date']))
                    if m_dep: 
                        dep_date_str = m_dep.group(0)
                        dep_dt = datetime.strptime(dep_date_str, "%Y-%m-%d").date()

                # 귀국일 정밀 탐색 (한국 귀국 행 고정)
                korea_arr = ledger_df[ledger_df['Category'].str.contains('입국|귀국', na=False) & ledger_df['Category'].apply(is_korea_port)]
                arr_candidates = ledger_df[
                    ledger_df['Category'].str.contains('입국|귀국', na=False) & 
                    ~ledger_df['Category'].apply(is_foreign_transit)
                ]
                target_arr_row = korea_arr if not korea_arr.empty else arr_candidates

                arr_date_str = ""
                arr_dt = None
                if not target_arr_row.empty:
                    m_arr = re.search(r'(\d{4})-(\d{2})-(\d{2})', str(target_arr_row.iloc[-1]['Date']))
                    if m_arr: 
                        arr_date_str = m_arr.group(0)
                        arr_dt = datetime.strptime(arr_date_str, "%Y-%m-%d").date()

                def check_is_fixed_cost(row):
                    orig_d = str(row['Date']).strip()
                    m_row = re.search(r'(\d{4})-(\d{2})-(\d{2})', orig_d)
                    pure_d = m_row.group(0) if m_row else ""
                    if dep_date_str and pure_d and pure_d < dep_date_str:
                        return True
                    cat = str(row['Category']).strip()
                    met = str(row['PaymentMethod']).strip()
                    return (met == '원화계좌(한국)') or (cat in FIXED_COST_CATS)

                exp_df['IsFixedCost'] = exp_df.apply(check_is_fixed_cost, axis=1)
                is_fixed_cost = exp_df['IsFixedCost']

                # 출국일 <= 날짜 <= 귀국일 사이의 지출 추출
                def is_in_trip_period(row):
                    orig_d = str(row['Date']).strip()
                    m_row = re.search(r'(\d{4})-(\d{2})-(\d{2})', orig_d)
                    if not m_row: return True
                    pure_d = m_row.group(0)
                    if dep_date_str and pure_d < dep_date_str: return False
                    if arr_date_str and pure_d > arr_date_str: return False
                    return True

                in_period_mask = exp_df.apply(is_in_trip_period, axis=1) if (dep_date_str or arr_date_str) else True
                ovr_df = exp_df[(~is_fixed_cost) & (~exp_df['Category'].isin(['입국','출국'])) & in_period_mask].copy()

                # [달력 기반 전체 여정 100% 보존] 출국일부터 귀국일까지 모든 날짜 생성 (이동일 0원 대기)
                day_kr_names = ['월', '화', '수', '목', '금', '토', '일']
                if dep_dt and arr_dt and dep_dt <= arr_dt:
                    total_calendar_days = (arr_dt - dep_dt).days + 1
                    all_cal_dates = [(dep_dt + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(total_calendar_days)]
                    
                    if 'Date_Clean' not in ovr_df.columns:
                        ovr_df['Date_Clean'] = ovr_df['Date'].str.extract(r'(\d{4}-\d{2}-\d{2})')[0]
                        
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
                            except:
                                d_str = md

                            dummy_rows.append({
                                'Date': d_str,
                                'Date_Clean': md,
                                'Country': last_country,
                                'Category': '기타',
                                'Description': '이동일 (지출 0원)',
                                'Currency': TRAVEL_CURRENCY,
                                'Amount': 0.0,
                                'PaymentMethod': '정보',
                                'IsExpense': 1,
                                'AppliedRate': 1.0,
                                'KRW_val': 0.0,
                                'Local_val': 0.0,
                                'IsSurvival': 0,
                                'IsFixedCost': False
                            })
                        ovr_df = pd.concat([ovr_df, pd.DataFrame(dummy_rows)], ignore_index=True)
                else:
                    total_calendar_days = ovr_df['Date'].str.extract(r'(\d{4}-\d{2}-\d{2})')[0].nunique()

                # --------------------------------------------------------------
                # 6.03.01 | Daily Local Spending Chart (4단계 라이프사이클 타이틀 적용)
                # --------------------------------------------------------------
                if not ovr_df.empty:
                    ovr_df = ovr_df.copy()
                    
                    trip_nodes = TRIP_CONFIGS.get(st.session_state.current_trip, {}).get("nodes", {})
                    is_single_country = (len(trip_nodes) <= 1) or (ovr_df['Country'].dropna().nunique() <= 1)

                    if 'Date_Clean' not in ovr_df.columns:
                        ovr_df['Date_Clean'] = ovr_df['Date'].str.extract(r'(\d{4}-\d{2}-\d{2})')[0]
                        
                    ovr_df = ovr_df.sort_values(by='Date_Clean')
                    unique_clean_dates = sorted([d for d in ovr_df['Date_Clean'].dropna().unique()])
                    num_total_days = len(unique_clean_dates)
                    
                    date_country_map = {}
                    for d in unique_clean_dates:
                        sub_c = ovr_df[ovr_df['Date_Clean'] == d]['Country'].dropna().unique()
                        date_country_map[d] = " / ".join(sub_c) if len(sub_c) > 0 else ""

                    prev_c = None
                    lane1_free_idx = -1
                    lane2_free_idx = -1
                    date_label_map = {}
                    
                    for idx, d in enumerate(unique_clean_dates):
                        m_d = re.search(r'\d{4}-(\d{2})-(\d{2})', d)
                        mm, dd = int(m_d.group(1)), int(m_d.group(2))
                        try:
                            dt_obj = datetime.strptime(d, "%Y-%m-%d").date()
                            day_kr = day_kr_names[dt_obj.weekday()]
                        except:
                            day_kr = ""
                            
                        c_val = date_country_map.get(d, "")
                        is_new_country = (not is_single_country) and bool(c_val) and (c_val != prev_c)
                        
                        country_html = ""
                        if is_new_country:
                            prev_c = c_val
                            c_display = c_val.replace(" / ", "<br>").replace("/", "<br>")
                            clean_len = max(len(s) for s in c_display.split("<br>"))
                            slots_needed = max(1, math.ceil(clean_len / 2.6))
                            
                            if idx >= lane1_free_idx:
                                lane1_free_idx = idx + slots_needed
                                country_html = f"<span style='font-size:10px; color:#A5B4FC; font-weight:600;'>{c_display}</span>"
                            elif idx >= lane2_free_idx:
                                lane2_free_idx = idx + slots_needed
                                country_html = f"<span style='font-size:9px;'>&nbsp;</span><br><span style='font-size:10px; color:#38BDF8; font-weight:600;'>{c_display}</span>"
                            else:
                                lane1_free_idx = idx + slots_needed
                                country_html = f"<span style='font-size:10px; color:#A5B4FC; font-weight:600;'>{c_display}</span>"
                                
                        c_part = f"<br>{country_html}" if country_html else ""
                        date_label_map[d] = f"{mm}/{dd}<br>({day_kr}){c_part}"

                    ovr_df['Date_Display'] = ovr_df['Date_Clean'].map(date_label_map)
                    
                    # [사용자 정의 4단계 라이프사이클 타이틀 공식]
                    today_dt_c = datetime.now(st.session_state.current_tz).date()
                    
                    if dep_dt and arr_dt:
                        if today_dt_c < dep_dt:
                            # 1. 출발 전: 'N일예정'
                            day_label_suffix = f"{total_calendar_days}일예정"
                            is_active_chart = False
                            div_days = max(1, total_calendar_days)
                            avg_text_prefix = "1일 평균"
                        elif dep_dt <= today_dt_c <= arr_dt:
                            # 2. 여행 중: 출국 당일(1일차) ~ 귀국 당일(N일차)
                            curr_day = (today_dt_c - dep_dt).days + 1
                            day_label_suffix = f"{curr_day}일차"
                            is_active_chart = True
                            div_days = max(1, curr_day)
                            avg_text_prefix = "현재 1일 평균"
                        else:
                            # 3. 귀국일 이후: 'N일간'
                            day_label_suffix = f"{total_calendar_days}일간"
                            is_active_chart = False
                            div_days = max(1, total_calendar_days)
                            avg_text_prefix = "1일 평균"
                    else:
                        day_label_suffix = f"{total_calendar_days}일간"
                        is_active_chart = False
                        div_days = max(1, total_calendar_days)
                        avg_text_prefix = "1일 평균"

                    st.markdown(f"<h4 style='text-align: center;'>🗺️ 여행지 일별지출({day_label_suffix})</h4>", unsafe_allow_html=True)

                    # 1일 평균선 계산
                    total_spent_val = ovr_df[y_col].sum()
                    avg_daily_val = total_spent_val / div_days if div_days > 0 else 0
                    y_unit = "원" if "원화" in c_mode else f" {LOCAL_SYM}"
                    fmt_avg = f"{avg_daily_val:,.0f}" if "원화" in c_mode or MULTIPLIER != 1 else f"{avg_daily_val:,.2f}"
                    avg_benchmark_label = f"{avg_text_prefix} {fmt_avg}{y_unit}"

                    # '전체보기' 맨 앞 배치 & 10일 구간 생성 (취소선 버그 없는 안전 기호 사용)
                    chunk_size = 10
                    chunk_options = ["🗺️ 전체보기"]
                    if num_total_days > chunk_size:
                        num_chunks = math.ceil(num_total_days / chunk_size)
                        for c_idx in range(num_chunks):
                            start_num = c_idx * chunk_size + 1
                            end_num = min((c_idx + 1) * chunk_size, num_total_days)
                            
                            d_start_raw = unique_clean_dates[start_num - 1]
                            d_end_raw = unique_clean_dates[end_num - 1]
                            
                            m1 = re.search(r'\d{4}-(\d{2})-(\d{2})', d_start_raw)
                            m2 = re.search(r'\d{4}-(\d{2})-(\d{2})', d_end_raw)
                            s_lbl = f"{int(m1.group(1))}/{int(m1.group(2))}" if m1 else d_start_raw
                            e_lbl = f"{int(m2.group(1))}/{int(m2.group(2))}" if m2 else d_end_raw
                            
                            if start_num == end_num:
                                chunk_options.append(f"{c_idx+1}구간 ({start_num}일 | {s_lbl})")
                            else:
                                chunk_options.append(f"{c_idx+1}구간 ({start_num}-{end_num}일 | {s_lbl} - {e_lbl})")
                        
                        sel_chunk = st.radio("📅 일정 구간 선택", chunk_options, index=0, horizontal=True, key="daily_chunk_sel", label_visibility="collapsed")
                        
                        if sel_chunk != "🗺️ 전체보기":
                            sel_idx = chunk_options.index(sel_chunk) - 1
                            view_dates = unique_clean_dates[sel_idx * chunk_size : min((sel_idx + 1) * chunk_size, num_total_days)]
                            chart_df = ovr_df[ovr_df['Date_Clean'].isin(view_dates)].copy()
                        else:
                            view_dates = unique_clean_dates
                            chart_df = ovr_df.copy()
                    else:
                        view_dates = unique_clean_dates
                        chart_df = ovr_df.copy()

                    fig2 = px.bar(chart_df, x='Date_Display', y=y_col, color='Category', title=None, color_discrete_map=color_map)
                    
                    if avg_daily_val > 0:
                        fig2.add_hline(
                            y=avg_daily_val,
                            line_dash="dash",
                            line_color="#FFA500",
                            line_width=1.5,
                            annotation_text=avg_benchmark_label,
                            annotation_position="top right",
                            annotation_font=dict(size=11, color="#FFA500")
                        )

                    fig2.update_layout(
                        barmode='stack', 
                        margin=dict(l=10, r=10, t=15, b=60),
                        xaxis_title=None,
                        yaxis_title=None,
                        legend_title_text="",
                        legend=dict(orientation="h", yanchor="top", y=-0.25, xanchor="center", x=0.5)
                    )
                    
                    fig2.update_xaxes(
                        categoryorder='array', 
                        categoryarray=[date_label_map[d] for d in view_dates if d in date_label_map], 
                        tickangle=0,
                        tickfont=dict(size=11),
                        fixedrange=True
                    )
                    fig2.update_yaxes(
                        fixedrange=True
                    )

                    st.plotly_chart(
                        fig2, 
                        use_container_width=True, 
                        config={'displaylogo': False, 'scrollZoom': False, 'displayModeBar': False}
                    )

                st.divider()
                
                # --------------------------------------------------------------
                # 6.03.02 | Daily Living vs Total Spent Pivot Table (전체 여정 완벽 보존)
                # --------------------------------------------------------------
                daily_set = ovr_df.groupby('Date').agg({'Country': lambda x: ' / '.join(x.unique()), 'KRW_val': 'sum', 'Local_val': 'sum'}).reset_index() if not ovr_df.empty else pd.DataFrame(columns=['Date', 'Country', 'KRW_val', 'Local_val'])
                surv_only = ovr_df[ovr_df['IsSurvival'] == 1].groupby('Date').agg({'KRW_val': 'sum', 'Local_val': 'sum'}).reset_index().rename(columns={'KRW_val': 'S_KRW', 'Local_val': 'S_Loc'}) if not ovr_df.empty else pd.DataFrame(columns=['Date', 'S_KRW', 'S_Loc'])
                daily_table = pd.merge(daily_set, surv_only, on='Date', how='left').fillna(0) if not daily_set.empty else pd.DataFrame()
                fmt_local = "{:,.2f}" if MULTIPLIER == 1 else "{:,.0f}"
                
                if not daily_table.empty:
                    def shorten_table_date(d_str):
                        d_str = str(d_str).strip()
                        m = re.search(r'(\d{4})-(\d{2})-(\d{2})', d_str)
                        if m:
                            pure_date = m.group(0)
                            mm, dd = int(m.group(2)), int(m.group(3))
                            try:
                                dt_obj = datetime.strptime(pure_date, "%Y-%m-%d").date()
                                day_kr = day_kr_names[dt_obj.weekday()]
                                return f"{mm:02d}/{dd:02d}({day_kr})"
                            except:
                                return f"{mm:02d}/{dd:02d}"
                        return d_str

                    daily_table['Date_Short'] = daily_table['Date'].apply(shorten_table_date)
                    
                    daily_table['Sort_Key'] = daily_table['Date'].str.extract(r'(\d{4}-\d{2}-\d{2})')[0]
                    daily_table = daily_table.sort_values(by='Sort_Key').drop(columns=['Sort_Key'])

                    if is_single_country:
                        display_table = daily_table[['Date_Short', 'KRW_val', 'Local_val', 'S_KRW', 'S_Loc']].rename(
                            columns={'Date_Short':'날짜', 'KRW_val':'총(원)', 'Local_val':f'총({LOCAL_SYM})', 'S_KRW':'일상(원)', 'S_Loc':f'일상({LOCAL_SYM})'}
                        )
                    else:
                        display_table = daily_table[['Country', 'Date_Short', 'KRW_val', 'Local_val', 'S_KRW', 'S_Loc']].rename(
                            columns={'Country':'국가', 'Date_Short':'날짜', 'KRW_val':'총(원)', 'Local_val':f'총({LOCAL_SYM})', 'S_KRW':'일상(원)', 'S_Loc':f'일상({LOCAL_SYM})'}
                        )

                    col_cfg_daily = {
                        "날짜": st.column_config.TextColumn("날짜", width="small")
                    }
                    st.dataframe(
                        display_table.style.format({'총(원)': '{:,.0f}', f'총({LOCAL_SYM})': fmt_local, '일상(원)': '{:,.0f}', f'일상({LOCAL_SYM})': fmt_local}),
                        use_container_width=True, 
                        hide_index=True,
                        column_config=col_cfg_daily
                    )
                else: 
                    st.info("현지 지출 데이터가 없습니다.")

                # --------------------------------------------------------------
                # 6.03.03 | Pre-Departure Domestic Cost Treemap (0원 결측치 완전방어형 트리맵)
                # --------------------------------------------------------------
                dom_df = exp_df[is_fixed_cost & (~exp_df['Category'].isin(['입국','출국']))]
                if not dom_df.empty:
                    # [핵심 버그 해결] 금액이 0원보다 큰 유효 지출(y_col > 0)만 추출하여 Plotly 백지 렌더링 오류 원천 차단
                    dom_chart_df = dom_df[dom_df[y_col] > 0].copy()
                    
                    if not dom_chart_df.empty:
                        st.divider()
                        st.markdown("<h4 style='text-align: center;'>🛫 사전결제 분석 (스마트 트리맵)</h4>", unsafe_allow_html=True)
                        
                        total_dom_sum = dom_chart_df[y_col].sum() if dom_chart_df[y_col].sum() > 0 else 1
                        
                        smart_macro_list = []
                        smart_tile_list = []
                        
                        # 호텔명 친화적 한글 정제 헬퍼
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

                        # 1. 금액 크기(비중)에 따른 절대 폰트 계층 부여
                        for idx, r in dom_chart_df.iterrows():
                            cat = str(r['Category']).strip()
                            desc = str(r['Description']).strip()
                            amt = float(r[y_col])
                            pct = (amt / total_dom_sum) * 100
                            
                            # (1) 분류 및 명칭 정리
                            if cat == '항공권':
                                if any(k in desc for k in ['부산', '인천', '김포', '대구', '제주', '청주', '왕복', '출국', '귀국', 'BX', 'VJ']):
                                    macro_lbl = "🛫 IN/OUT 항공권"
                                else:
                                    macro_lbl = "✈️ 구간/국내선"
                                clean_d = re.sub(r'\[.*?\]\s*', '', desc).split('|')[0].strip()
                                name_lbl = clean_d if len(clean_d) <= 16 else clean_d[:15] + ".."
                                is_small = False
                                
                            elif cat in ['호텔', '숙박']:
                                macro_lbl = "🏨 숙박"
                                name_lbl = clean_hotel_label(desc)
                                is_small = False
                                
                            elif cat == '보험':
                                macro_lbl = "🛡️ 보험"
                                name_lbl = "여행자보험"
                                is_small = True
                            elif cat in ['기차', '교통', '지하철', '택시']:
                                macro_lbl = "🚗 현지교통(사전)"
                                name_lbl = desc.split('(')[0].strip()
                                is_small = True
                            else:
                                macro_lbl = "📱 기타/통신"
                                name_lbl = desc[:10].strip()
                                is_small = True

                            # (2) 비중에 따른 절대 폰트 크기 계산
                            if is_small or pct < 5.5:
                                tile_html = f"<span style='font-size:11.5px; font-weight:bold;'>{name_lbl} ({amt:,.0f}원)</span>"
                            elif pct >= 35.0:
                                tile_html = f"<span style='font-size:18.5px; font-weight:bold;'>{name_lbl}</span><br><span style='font-size:15.5px; font-weight:600;'>{amt:,.0f}원</span><br><span style='font-size:12px; opacity:0.85;'>({pct:.1f}%)</span>"
                            elif pct >= 18.0:
                                tile_html = f"<span style='font-size:15.5px; font-weight:bold;'>{name_lbl}</span><br><span style='font-size:13px; font-weight:600;'>{amt:,.0f}원</span><br><span style='font-size:11px; opacity:0.85;'>({pct:.1f}%)</span>"
                            elif pct >= 11.0:
                                tile_html = f"<span style='font-size:13.5px; font-weight:bold;'>{name_lbl}</span><br><span style='font-size:11.5px; font-weight:600;'>{amt:,.0f}원</span><br><span style='font-size:10px; opacity:0.85;'>({pct:.1f}%)</span>"
                            else:
                                tile_html = f"<span style='font-size:12px; font-weight:bold;'>{name_lbl}</span><br><span style='font-size:10.5px; font-weight:600;'>{amt:,.0f}원</span><br><span style='font-size:9.5px; opacity:0.85;'>({pct:.1f}%)</span>"
                                
                            smart_macro_list.append(macro_lbl)
                            smart_tile_list.append(tile_html)
                            
                        dom_chart_df['Smart_Macro'] = smart_macro_list
                        dom_chart_df['Smart_Tile'] = smart_tile_list

                        # 컬러 팔레트
                        treemap_color_map = {
                            "🛫 IN/OUT 항공권": "#C62828",
                            "✈️ 구간/국내선": "#E53935",
                            "🏨 숙박": "#1565C0",
                            "🛡️ 보험": "#F9A825",
                            "🚗 현지교통(사전)": "#00838F",
                            "📱 기타/통신": "#6A1B9A"
                        }

                        # 2. 트리맵 렌더링
                        fig1 = px.treemap(
                            dom_chart_df, 
                            path=['Smart_Macro', 'Smart_Tile'], 
                            values=y_col, 
                            color='Smart_Macro', 
                            color_discrete_map=treemap_color_map
                        )
                        
                        # 3. HTML 인라인 폰트 그대로 표출 (%{label} 호출)
                        fig1.update_traces(
                            texttemplate="%{label}",
                            hovertemplate="<b>%{label}</b><br>금액: %{value:,.0f}원<extra></extra>",
                            textposition='middle center',
                            tiling=dict(packing='squarify', pad=4)
                        )
                        
                        fig1.update_layout(
                            margin=dict(l=10, r=10, t=10, b=10), 
                            height=560
                        )
                        
                        st.plotly_chart(fig1, use_container_width=True, config={'displaylogo': False})

                # --------------------------------------------------------------
                # 6.03.04 | Multi-Node Local Expense Treemap (결측치 & 0원 완전 방어형)
                # --------------------------------------------------------------
                if len(TRIP_CONFIGS[st.session_state.current_trip]["nodes"]) > 1 and not ovr_df.empty:
                    # [핵심] 실제 지출(y_col > 0)만 추출하고 결측치를 완벽히 메워 ValueError 원천 차단
                    country_chart_df = ovr_df[ovr_df[y_col] > 0].copy()
                    
                    if not country_chart_df.empty:
                        st.divider()
                        st.markdown("<h4 style='text-align: center;'>🌍 국가별 현지지출(Treemap)</h4>", unsafe_allow_html=True)
                        
                        country_chart_df['Macro_Category'] = country_chart_df['Category'].map(MACRO_MAP).fillna("기타")
                        country_chart_df['Country'] = country_chart_df['Country'].fillna("기타")
                        country_chart_df['Category'] = country_chart_df['Category'].fillna("기타")
                        
                        fig_country = px.treemap(
                            country_chart_df, 
                            path=['Country', 'Macro_Category', 'Category'], 
                            values=y_col, 
                            color='Country', 
                            color_discrete_sequence=px.colors.qualitative.Pastel
                        )
                        fig_country.update_traces(
                            texttemplate="<b>%{label}</b><br>%{value:,.0f}", 
                            hovertemplate="<b>%{label}</b><br>금액: %{value:,.0f}<extra></extra>",
                            textposition='middle center'
                        )
                        fig_country.update_layout(
                            margin=dict(l=10, r=10, t=10, b=20), 
                            height=520
                        )
                        st.plotly_chart(fig_country, use_container_width=True, config={'displaylogo': False})

                # 6.03.05 | Net Settlement & Refund Breakdown Card
                st.divider()
                st.subheader("🏁 여행 비용 요약 (Net)")
                c1, c2 = st.columns(2)
                
                refund_df = ledger_df[ledger_df['Category'] == '환불']
                dom_refunds = refund_df[refund_df['PaymentMethod'].apply(get_asset_class) == 'DOMESTIC']
                dom_refund_total = dom_refunds.apply(lambda r: r['Amount'] if str(r['Currency']).strip() == 'KRW' else r['Amount'] * r['AppliedRate'], axis=1).sum() if not dom_refunds.empty else 0
                
                with c1:
                    st.info("🇰🇷 사전 결제")
                    st.metric("순지출액", f"{dom_df['KRW_val'].sum():,.0f} 원")
                    with st.expander("상세내역", expanded=False):
                        dg = dom_df.groupby('Category').agg({'KRW_val':'sum', 'Date':'count'}).sort_values(by='KRW_val', ascending=False)
                        for cat_name, row_data in dg.iterrows(): st.write(f"• {cat_name}({int(row_data['Date'])}회): {row_data['KRW_val']:,.0f} 원")
                with c2:
                    st.success(f"🌏 여행지 지출")
                    st.metric("총액", f"{ovr_df['KRW_val'].sum():,.0f} 원")
                    with st.expander("상세내역", expanded=False):
                        og = ovr_df.groupby('Category').agg({'KRW_val':'sum', 'Date':'count'}).sort_values(by='KRW_val', ascending=False)
                        for cat_name, row_data in og.iterrows(): st.write(f"• {cat_name}({int(row_data['Date'])}회): {row_data['KRW_val']:,.0f} 원")

                if not refund_df.empty:
                    st.divider()
                    st.subheader("🛡️ 손실과 보상 (환불 목록)")
                    r_krw = refund_df.apply(lambda r: r['Amount'] if str(r['Currency']).strip() == 'KRW' else r['Amount'] * r['AppliedRate'], axis=1).sum()
                    st.warning(f"**환불총액:** {r_krw:,.0f} 원")
                    with st.expander("상세내역", expanded=False):
                        st.dataframe(refund_df[['Date', 'Country', 'Description', 'Amount', 'Currency', 'PaymentMethod']], use_container_width=True)

    # --------------------------------------------------------------------------
    # 6.04.00 | Console Tab 4: Final Settlement Dashboard (최종 정산 대시보드)
    # --------------------------------------------------------------------------
    with tab_final:
        if not ledger_df.empty and 'exp_df' in locals() and not exp_df.empty:
            # 6.04.01 | Executive Macro KPI Summary Cards
            total_trip_krw = exp_df['KRW_val'].sum()
            total_trip_loc = exp_df['Local_val'].sum()
            
            trip_cfg = TRIP_CONFIGS.get(st.session_state.current_trip, {})
            travelers = trip_cfg.get("travelers", 2)
            mapping_str = trip_cfg.get("stay_mapping", "")
            nights_match = re.findall(r'(\d+(?:\.\d+)?)', mapping_str)
            total_nights = sum(float(n) for n in nights_match) if nights_match else 7
            if total_nights == 0: total_nights = 7 

            # 6.04.00-A | 스마트 사전결제 판별 플래그 상속
            is_fixed_cost_final = exp_df['IsFixedCost'] if 'IsFixedCost' in exp_df.columns else exp_df.apply(check_is_fixed_cost, axis=1)
            dom_total_krw = exp_df[is_fixed_cost_final]['KRW_val'].sum()
            ovr_total_krw = total_trip_krw - dom_total_krw
            ovr_total_loc = exp_df[~is_fixed_cost_final]['Local_val'].sum()

            # [순서 재배치] 출국일/귀국일 파싱 로직을 KPI 박스 생성 전으로 선행 배치하여 NameError 원천 차단
            korea_dep_rows = ledger_df[ledger_df['Category'].str.contains('출국_한국|출국.*한국', na=False)]
            dep_rows_all = ledger_df[ledger_df['Category'].str.contains('출국', na=False)]
            t_dep = korea_dep_rows if not korea_dep_rows.empty else (dep_rows_all[~dep_rows_all['Category'].str.contains('_', na=False)] if not dep_rows_all.empty else dep_rows_all)
            
            dep_dt_f = None
            if not t_dep.empty:
                m_df = re.search(r'(\d{4})-(\d{2})-(\d{2})', str(t_dep.iloc[0]['Date']))
                if m_df: dep_dt_f = datetime.strptime(m_df.group(0), "%Y-%m-%d").date()

            korea_arr_rows = ledger_df[ledger_df['Category'].str.contains('입국_한국|입국.*한국', na=False)]
            arr_rows_all = ledger_df[ledger_df['Category'].str.contains('입국|귀국', na=False)]
            t_arr = korea_arr_rows if not korea_arr_rows.empty else (arr_rows_all[~arr_rows_all['Category'].str.contains('_', na=False)] if not arr_rows_all.empty else arr_rows_all)
            
            arr_dt_f = None
            if not t_arr.empty:
                m_af = re.search(r'(\d{4})-(\d{2})-(\d{2})', str(t_arr.iloc[-1]['Date']))
                if m_af: arr_dt_f = datetime.strptime(m_af.group(0), "%Y-%m-%d").date()

            # [정합성 동기화] 일일Data 탭과 동일하게 실제 여행 일수(9일) 기준으로 1일 평균 산출
            if dep_dt_f and arr_dt_f:
                trip_days_count = max(1, (arr_dt_f - dep_dt_f).days + 1)
            else:
                trip_days_count = max(1, int(total_nights))

            avg_local_krw = ovr_total_krw / trip_days_count if trip_days_count > 0 else 0
            avg_local_loc = ovr_total_loc / trip_days_count if trip_days_count > 0 else 0
            
            fmt_local = "{:,.2f}" if MULTIPLIER == 1 else "{:,.0f}"
            def kpi_box(title, krw, loc=None):
                loc_str = f"<div class='kpi-value-vnd'>({fmt_local.format(loc)} {LOCAL_SYM})</div>" if loc is not None else ""
                return f"<div class='kpi-box'><div class='kpi-title'>{title}</div><div class='kpi-value-krw'>{krw:,.0f} 원</div>{loc_str}</div>"
                
            st.markdown("<h3 style='margin-top: 0px; margin-bottom: 8px;'>🏁 여행요약</h3>", unsafe_allow_html=True)
            k1, k2, k3, k4 = st.columns(4)
            with k1: st.markdown(kpi_box("최종 지출", total_trip_krw, total_trip_loc), unsafe_allow_html=True)
            with k2: st.markdown(kpi_box("국내 지출", dom_total_krw), unsafe_allow_html=True)
            with k3: st.markdown(kpi_box("현지 지출", ovr_total_krw, ovr_total_loc), unsafe_allow_html=True)
            with k4: st.markdown(kpi_box("여행중 1일 평균지출", avg_local_krw, avg_local_loc), unsafe_allow_html=True)
            # ------------------------------------------------------------------
            # 6.04.02 | Comprehensive Expense Treemap Matrix
            # ------------------------------------------------------------------
            st.markdown("<h4 style='margin-top: 15px; margin-bottom: 5px;'>🌳 지출분석 (Treemap)</h4>", unsafe_allow_html=True)
            chart_df = exp_df[exp_df['KRW_val'] > 0].copy()
            if not chart_df.empty:
                chart_df['Short_Desc'] = chart_df['Description'].apply(lambda x: str(x)[:15] + ".." if len(str(x)) > 15 else x)
                chart_df['Macro_Category'] = chart_df['Category'].map(MACRO_MAP).fillna("기타")
                
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
                    insidetextfont=dict(size=16)
                )
                fig_tree.update_layout(
                    margin=dict(l=0, r=0, t=10, b=10), 
                    height=580,
                    coloraxis_showscale=False
                )
                st.plotly_chart(fig_tree, use_container_width=True, config={'displaylogo': False})
            
            # ------------------------------------------------------------------
            # 6.04.03 | Donut Category Distribution Chart
            # ------------------------------------------------------------------
            st.markdown("<h4 style='margin-top: 12px; margin-bottom: 0px;'>🍕 지출비중</h4>", unsafe_allow_html=True)
            cat_pie = exp_df.groupby('Macro_Category')['KRW_val'].sum().reset_index().sort_values(by='KRW_val', ascending=False)
            
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

            # 여행 상태 연동 중앙 텍스트 산출
            korea_dep_rows = ledger_df[ledger_df['Category'].str.contains('출국_한국|출국.*한국', na=False)]
            dep_rows_all = ledger_df[ledger_df['Category'].str.contains('출국', na=False)]
            t_dep = korea_dep_rows if not korea_dep_rows.empty else (dep_rows_all[~dep_rows_all['Category'].str.contains('_', na=False)] if not dep_rows_all.empty else dep_rows_all)
            
            dep_dt_f = None
            if not t_dep.empty:
                m_df = re.search(r'(\d{4})-(\d{2})-(\d{2})', str(t_dep.iloc[0]['Date']))
                if m_df: dep_dt_f = datetime.strptime(m_df.group(0), "%Y-%m-%d").date()

            korea_arr_rows = ledger_df[ledger_df['Category'].str.contains('입국_한국|입국.*한국', na=False)]
            arr_rows_all = ledger_df[ledger_df['Category'].str.contains('입국|귀국', na=False)]
            t_arr = korea_arr_rows if not korea_arr_rows.empty else (arr_rows_all[~arr_rows_all['Category'].str.contains('_', na=False)] if not arr_rows_all.empty else arr_rows_all)
            
            arr_dt_f = None
            if not t_arr.empty:
                m_af = re.search(r'(\d{4})-(\d{2})-(\d{2})', str(t_arr.iloc[-1]['Date']))
                if m_af: arr_dt_f = datetime.strptime(m_af.group(0), "%Y-%m-%d").date()

            today_f = datetime.now(TZ_KST).date()

            if dep_dt_f and arr_dt_f:
                cal_days_f = (arr_dt_f - dep_dt_f).days + 1
                if today_f < dep_dt_f:
                    center_sub_text = f"({cal_days_f}일예정)"
                elif dep_dt_f <= today_f <= arr_dt_f:
                    curr_k = (today_f - dep_dt_f).days + 1
                    center_sub_text = f"({curr_k}일차)"
                else:
                    center_sub_text = f"({cal_days_f}일간)"
            else:
                center_sub_text = f"({total_nights}일간)"

            center_annotation_html = f"<b>{total_trip_krw:,.0f}원</b><br><span style='font-size:12px; color:#A0AEC0;'>{center_sub_text}</span>"
            
            fig_donut.add_annotation(
                text=center_annotation_html, 
                showarrow=False, 
                align="center",
                font=dict(size=16)
            )
            
            fig_donut.update_layout(
                height=440, 
                margin=dict(l=10, r=10, t=5, b=20), 
                legend=dict(orientation="h", yanchor="top", y=-0.05, xanchor="center", x=0.5)
            )
            st.plotly_chart(fig_donut, use_container_width=True)

# 6.04.04 | Build Version & Sync Timestamp Footer
st.caption(f"GTL Platform {VERSION} | Volume Guard: ~ 70 KB | Sync: {datetime.now(TZ_KST).strftime('%Y-%m-%d %H:%M:%S')} | Strategic Partner Gem")
