## [v26.05.20.004] - 2026-05-20
## **Architect**: Gem
## **Focus**: Multiplier Dynamic Scaling, Date Formatting & UI View Overhaul
## * `[Refactored]` Multiplier(100배수) 적용을 통한 환율 5.67 직관적 스케일링 및 과거 데이터 Auto-Migration 탑재.
## * `[Modified]` 날짜 포맷 최적화 ('26 05/20(수)) 및 조회 탭 완벽한 숫자 포매팅 뷰어 적용.

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

# ==============================================================================
# --- SECTION 1: Configuration & Global Setup ---
# ==============================================================================
### ⚙️ [Logic: Global Config] 기본 환경 및 시간대 설정
st.set_page_config(page_title="Feelfree: 글로벌 여행 가계부", page_icon="🌏", layout="wide", initial_sidebar_state="expanded")

TZ_KST = timezone(timedelta(hours=9))

### ⚙️[Logic: System Variable] 여행지 설정, 환율 및 매크로 매핑 데이터

MACRO_MAP = {
    "Grab": "🚗 교통", "VinBus": "🚗 교통", "DiDi": "🚗 교통", "지하철": "🚗 교통", "택시": "🚗 교통", "렌트카": "🚗 교통",
    "식사": "🍔 식음료", "간식": "🍔 식음료", "마트": "🍔 식음료",
    "마사지": "🏄 액티비티", "투어": "🏄 액티비티", "입장료": "🏄 액티비티",
    "선물": "🎁 쇼핑", "통신": "📱 통신/기타", "수수료": "📱 통신/기타", "팁": "📱 통신/기타",
    "항공권": "✈️ 항공권", "호텔": "🏨 숙박", "보험": "🛡️ 보험", "보증금": "🏦 자산이동", "재환전": "🏦 자산이동", "상환": "🏦 자산이동"
}

CORE_COLUMNS =['Date', 'Country', 'Category', 'Description', 'Currency', 'Amount', 'PaymentMethod', 'Receipt_URL']
SYSTEM_LOGIC_COLUMNS =['IsExpense', 'AppliedRate', 'Cum_Budget_KRW', 'Cum_Card_Local', 'Cum_Cash_Local', 'Note']
FINAL_COLUMNS = CORE_COLUMNS + SYSTEM_LOGIC_COLUMNS

IMGBB_API_KEY = "81181bf834001b6191aaa90fa772c6f9"
BILLS =[500000, 200000, 100000, 50000, 20000, 10000, 5000, 2000, 1000]

CONFIG_SHEET = "_GTL_CONFIG_"
VERSION = "v26.05.20.004"

UPDATE_LOG_TEXT = """* `[Refactored]` Multiplier(100배수) 적용을 통한 환율 5.67 직관적 스케일링 및 과거 데이터 Auto-Migration 탑재.
* `[Modified]` 날짜 포맷 최적화 ('26 05/20(수)) 및 조회 탭 완벽한 숫자 포매팅 뷰어 적용."""

conn = st.connection("gsheets", type=GSheetsConnection)

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

@st.cache_data(ttl=600)
def get_trip_configs():
    cfg_df = None
    for attempt in range(3):
        try:
            cfg_df = conn.read(worksheet=CONFIG_SHEET, ttl="10m")
            if cfg_df is not None and not cfg_df.empty: break
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
    return dynamic_configs

TRIP_CONFIGS = get_trip_configs()

# [Added] 통화별 멀티플라이어 전역 조회 헬퍼
def get_mult(curr):
    if curr == 'KRW': return 1
    for trip, config in TRIP_CONFIGS.items():
        for node in config.get("nodes", {}).values():
            if node['currency'] == curr:
                return node['multiplier']
    return 100 if curr in ["VND", "IDR"] else 1

# [Added] 글로벌 직관적 날짜 포맷 (한국어 요일)
def format_date_korean(dt_obj):
    kr_days = ["월", "화", "수", "목", "금", "토", "일"]
    return f"'{str(dt_obj.year)[2:]} {dt_obj.month:02d}/{dt_obj.day:02d}({kr_days[dt_obj.weekday()]})"

### 🎨 [GUI: Layout] Custom CSS (화면 전반의 디자인 및 컴포넌트 스타일링)
st.markdown("""
    <script>var link=document.createElement('link'); link.rel='apple-touch-icon'; link.href='https://img.icons8.com/color/512/globe--v1.png'; document.getElementsByTagName('head')[0].appendChild(link);</script>
    <style>
    .main { background-color: #0e1117; }
    .kpi-box { background-color: #1e2130; padding: 20px; border-radius: 15px; border-left: 8px solid #FF8C00; margin-bottom: 20px; min-height: 130px; box-shadow: 4px 6px 15px rgba(0,0,0,0.5); }
    .kpi-title { font-size: 15px; color: #cccccc; margin-bottom: 10px; font-weight: 600; }
    .kpi-value-krw { font-size: 26px; font-weight: bold; color: #ffffff; line-height: 1.1; }
    .kpi-value-vnd { font-size: 18px; color: #FFA500; margin-top: 8px; font-family: 'Courier New', monospace; font-weight: 500; }
    div[data-testid="stTable"] { border: 1px solid #444; border-radius: 10px; overflow: hidden; }

    .stTabs[data-baseweb="tab-list"] { gap: 5px; padding: 5px 5px; background-color: #161a25; border-radius: 12px; border: 2px solid #FFA500; box-shadow: 0px 0px 10px rgba(255, 165, 0, 0.2); }
    .stTabs[data-baseweb="tab"] { height: 40px; background-color: #262b3b; border-radius: 8px !important; padding: 0px 10px !important; color: #CCCCCC !important; border: 1px solid #333; font-size: 14px !important; transition: all 0.3s ease; }
    .stTabs[data-baseweb="tab"]:hover { background-color: #3d4455; color: #ffffff !important; }
    .stTabs [aria-selected="true"] { background-color: #FFA500 !important; color: #000000 !important; font-weight: 800 !important; box-shadow: 0px 4px 12px rgba(255, 165, 0, 0.4) !important; border: 1px solid #FFA500 !important; }

    div[data-testid="stSidebar"] div[data-baseweb="select"] > div { border: 2px solid #FFA500 !important; background-color: #1e2130 !important; border-radius: 10px !important; }
    div[data-testid="stSidebar"] .stSelectbox label { color: #FFA500 !important; font-weight: bold !important; }
    div[data-baseweb="popover"] li[aria-selected="true"] { background-color: #FFA500 !important; color: #000000 !important; font-weight: bold !important; }
    div[data-baseweb="popover"] li:hover { background-color: #FFD700 !important; color: #000000 !important; }
    div[data-testid="stSidebar"] .stSelectbox label p { color: #FFD700 !important; }[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { padding-top: 0.5rem !important; gap: 0px !important; }
    [data-testid="stSidebar"] .stExpander div[data-testid="stVerticalBlock"] { gap: 2px !important; padding: 5px !important; }
    [data-testid="stSidebar"] hr { margin: 0.5rem 0 !important; }

    div[data-testid="stNumberInput"] button { display: none !important; }
    div[data-testid="stNumberInput"] input { padding-right: 10px !important; }
    div[data-testid="stNumberInput"] [data-baseweb="input"] { border-right-width: 1px !important; }
    </style>
    """, unsafe_allow_html=True)

### ⚙️ [Logic: Session State] 동적 세션 데이터 초기화
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
if 'last_cat_name' not in st.session_state: st.session_state.last_cat_name = "식사"

# ==============================================================================
# --- SECTION 2: [Module A] Data Engine ---
# ==============================================================================
### ⚙️ [Logic: Data Parsing] 텍스트 기반 자산 분류기
def get_asset_class(text):    
    txt = str(text).replace(" ", "").upper()
    if any(k in txt for k in ["트래블", "로그", "월렛", "선불", "외화통장"]): return "PREPAID"
    if any(k in txt for k in ["현금", "지폐", "CASH", "환전"]): return "CASH"
    if any(k in txt for k in ["외상", "부채", "CREDIT"]): return "CREDIT" 
    return "DOMESTIC"

### ⚙️[Logic: Rate Fallback] 평균 환율 동적 추론 (Scaled Rate 반환)
def get_default_rate(curr):
    if curr == "KRW": return 1.0
    try:
        if 'ledger_df' in globals() and not ledger_df.empty:
            df_curr = ledger_df[(ledger_df['Currency'].str.strip() == curr) & (ledger_df['AppliedRate'] > 0)]
            if not df_curr.empty: return df_curr['AppliedRate'].mean()
    except: pass
    
    fallback_rates = {"VND": 5.6, "CNY": 190.0, "USD": 1350.0, "EUR": 1480.0, "TRY": 45.0, "TND": 430.0, "SGD": 1000.0, "RSD": 12.6, "HUF": 3.8}
    return fallback_rates.get(curr, 1.0)

### ⚙️ [Logic: API] ImgBB 영수증 업로드
def upload_image_to_imgbb(image_file):
    try:
        payload = {"key": IMGBB_API_KEY, "image": base64.b64encode(image_file.read()).decode("utf-8")}
        res = requests.post("https://api.imgbb.com/1/upload", data=payload)
        if res.status_code == 200: return res.json()['data']['url']
    except: pass
    return ""

### ⚙️[Logic: AI OCR - Vision]
def extract_text_from_vision_api(image_bytes):
    try:
        from google.oauth2 import service_account
        from google.cloud import vision
        def find_gcp_key(d):
            try:
                if "private_key" in d and "client_email" in d: return dict(d)
                for k, v in d.items():
                    if isinstance(v, dict) or hasattr(v, 'items'):
                        res = find_gcp_key(v)
                        if res: return res
            except: pass
            return None
            
        secret_dict = find_gcp_key(st.secrets)
        if not secret_dict: return "⚠️ [설정 오류] Secrets에서 GCP 인증키를 찾지 못했습니다."
            
        if "type" not in secret_dict: secret_dict["type"] = "service_account"
        if "project_id" not in secret_dict:
            email = secret_dict.get("client_email", "")
            if "@" in email and ".iam" in email: secret_dict["project_id"] = email.split("@")[1].split(".iam")[0]
            else: secret_dict["project_id"] = "gtl-project-auto"
                
        if "\\n" in secret_dict["private_key"]: secret_dict["private_key"] = secret_dict["private_key"].replace('\\n', '\n')
            
        credentials = service_account.Credentials.from_service_account_info(secret_dict)
        client = vision.ImageAnnotatorClient(credentials=credentials)
        image = vision.Image(content=image_bytes)
        response = client.text_detection(image=image)
        
        if response.error.message: return f"⚠️ [API 에러]: {response.error.message}"
        texts = response.text_annotations
        if texts: return texts[0].description
        return ""
    except Exception as e: return f"⚠️ [에러 발생]: {e}"

### ⚙️[Logic: AI LLM - Gemini]
def summarize_receipt_with_gemini(raw_text):
    if not raw_text or "⚠️" in raw_text: return raw_text
    try:
        import google.generativeai as genai
        if "GEMINI_API_KEY" not in st.secrets: return raw_text + "\n\n(⚠️ Gemini API 키가 설정되지 않아 원본을 출력합니다.)"
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        prompt = """너는 다국어 영수증 전문 분석가야. 상호명, 세금 등은 버리고 오직 '소비한 품목'과 '가격'만 추출해.
1. 품목은 자연스러운 한국어로 번역하고 뒤에 영문을 병기해. (특징/용량 요약 포함)
2. 수량이 2개 이상일 때만 (X개) 표시. 가격은 소수점 없는 화폐는 그대로, 있는 화폐는 .2f 형식으로 화폐단위 병기.
3. 예: 타이거밤(Tiger Balm) 파스 (통증 완화, 7x10cm) (3개) 156,000 vnd"""
        models_to_try =['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-flash-latest', 'gemini-pro-latest']
        last_error = ""
        for m_name in models_to_try:
            try:
                model = genai.GenerativeModel(m_name)
                response = model.generate_content(prompt + "\n[영수증]\n" + raw_text)
                if response.text: return response.text.strip()
            except Exception as e:
                last_error = str(e)
                if "404" in str(e) or "not found" in str(e).lower(): continue
                break
        return raw_text + f"\n\n(⚠️ Gemini 요약 에러: {last_error})"
    except Exception as e: return raw_text + f"\n\n(⚠️ Gemini 요약 에러: {e})"

### ⚙️ [Logic: DB Load] GSheet 데이터 로드 및 마이그레이션
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
        df['Country'] = df['Country'].astype(str).str.strip().replace(['nan', 'None', ''], None).fillna(FIRST_NODE_NAME)
    
    if 'Cum_Card_VND' in df.columns: df.rename(columns={'Cum_Card_VND': 'Cum_Card_Local'}, inplace=True)
    if 'Cum_Cash_VND' in df.columns: df.rename(columns={'Cum_Cash_VND': 'Cum_Cash_Local'}, inplace=True)
    if 'Receipt_URL' not in df.columns: df['Receipt_URL'] = ""
        
    df = df.dropna(subset=['Date', 'Category'], how='any')
    df['Category'] = df['Category'].astype(str).str.strip()
    df['PaymentMethod'] = df['PaymentMethod'].astype(str).str.strip().str.replace('트래블로그', '트래블카드')
    df['Currency'] = df['Currency'].astype(str).str.strip().str.upper() 
    
    # [Modified] Legacy 날짜 포맷 마이그레이션
    def fix_legacy_date(d):
        d = str(d).strip()
        if re.match(r"^'\d{2}\s+\d{2}/\d{2}\([가-힣]\)$", d): return d
        match = re.search(r'(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})', d)
        if match:
            y, m, day = match.groups()
        else:
            if d and not re.match(r'^\d{4}', d):
                y, m, day = trip_year, d.split('-')[0] if '-' in d else d.split('/')[0], d.split('-')[-1] if '-' in d else d.split('/')[-1]
            else: return d
        try:
            dt_obj = datetime.strptime(f"{y}-{int(m):02d}-{int(day):02d}", "%Y-%m-%d")
            return format_date_korean(dt_obj)
        except: return d

    df['Date'] = df['Date'].apply(fix_legacy_date)
    df = df.reindex(columns=FINAL_COLUMNS)
    
    numeric_cols = ['Amount', 'AppliedRate', 'Cum_Budget_KRW', 'Cum_Card_Local', 'Cum_Cash_Local']
    for col in numeric_cols:
        if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
    
    # [Added] Legacy 환율(0.056) 오토 마이그레이션 (Multiplier 적용)
    mask = (df['AppliedRate'] > 0) & (df['AppliedRate'] < 1.0) & (df['Currency'].apply(get_mult) == 100)
    df.loc[mask, 'AppliedRate'] *= 100

    df['IsExpense'] = pd.to_numeric(df['IsExpense'], errors='coerce').fillna(0).astype(int)
    df['Note'] = df['Note'].fillna("").astype(str)
    df['Receipt_URL'] = df['Receipt_URL'].fillna("").astype(str)
    return df

@st.cache_data(ttl=600)
def load_all_trips_data():
    all_dfs =[]
    with st.spinner("🌍 모든 여행 기록을 불러오는 중... (한 번 불러오면 10분간 보관됩니다)"):
        for trip_name, config in TRIP_CONFIGS.items():
            for attempt in range(3):
                try:
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

def smart_cache_clear():
    try: load_data.clear(ACTIVE_SHEET)
    except: pass
    try: load_all_trips_data.clear()
    except: pass

### ⚙️[Logic: Core Calculation] 전체 원장 재계산 (DB 저장 전) Multiplier 엔진 적용
def recalculate_entire_ledger(df):
    temp_df = df.copy()
    temp_df = temp_df.sort_values(by='Date', kind='mergesort', ignore_index=True)
    
    for i, row in temp_df.iterrows():
        cat = str(row['Category']).strip()
        asset_cls = get_asset_class(row['PaymentMethod'])
        if cat in EXPENSE_CATS and cat != '보증금' and asset_cls != "DOMESTIC": temp_df.at[i, 'AppliedRate'] = 0.0
        temp_df.at[i, 'Note'] = ""; temp_df.at[i, 'Cum_Budget_KRW'] = 0.0; temp_df.at[i, 'Cum_Card_Local'] = 0.0; temp_df.at[i, 'Cum_Cash_Local'] = 0.0
    
    from collections import defaultdict
    inv_batches = defaultdict(list)
    c_budget = 0.0
    
    for i, row in temp_df.iterrows():
        qty, curr = row['Amount'], row['Currency']
        cat, method, desc = str(row['Category']).strip(), str(row['PaymentMethod']).strip(), str(row['Description']).strip()
        
        clean_expense_cats = [c.strip() for c in EXPENSE_CATS]
        is_exp = 1 if cat in clean_expense_cats and cat not in['환불', '보증금', '재환전', '상환'] else 0
        temp_df.at[i, 'IsExpense'] = is_exp
        
        is_deductible = 1 if (is_exp == 1 or cat in ['보증금', '상환']) else 0
        rate = temp_df.at[i, 'AppliedRate'] 
        asset_cls = get_asset_class(method)
        mult = get_mult(curr)
        
        if cat in['충전', '환전', '입금', '직접환전']:
            if curr != 'KRW' and (pd.isna(rate) or rate <= 0.0 or rate == 1.0): rate = get_default_rate(curr)
            if cat == '충전': final_dest_cls = "PREPAID"
            elif cat in ['환전', '직접환전']: final_dest_cls = "CASH"
            else: final_dest_cls = get_asset_class(desc + method)

            target = f"트래블카드({curr})" if final_dest_cls == "PREPAID" else f"현금({curr})"
            if curr != 'KRW': inv_batches[target].append({'rate': rate, 'qty': qty})
            if asset_cls == "DOMESTIC" or cat == '충전': 
                c_budget += qty if curr == 'KRW' else qty * (rate / mult)
        
        elif cat == '환불':
            if curr != 'KRW' and (pd.isna(rate) or rate <= 1.0):
                inherited_rate = None
                for j in range(i - 1, -1, -1):
                    if str(temp_df.at[j, 'Category']).strip() == '보증금' and str(temp_df.at[j, 'Currency']).strip() == curr:
                        inherited_rate = temp_df.at[j, 'AppliedRate']
                        break
                if inherited_rate and inherited_rate > 0:
                    rate = inherited_rate
                    temp_df.at[i, 'Note'] = f"Inherited Rate: {rate:.4f}"
                else: rate = get_default_rate(curr)
            
            if asset_cls == "DOMESTIC": c_budget -= qty if curr == 'KRW' else qty * (rate / mult)
            else:
                target = f"트래블카드({curr})" if asset_cls == "PREPAID" else f"현금({curr})"
                if curr != 'KRW': inv_batches[target].append({'rate': rate, 'qty': qty})
                
        elif cat == '재환전':
            if curr != 'KRW':
                target_from = f"트래블카드({curr})" if asset_cls == "PREPAID" else f"현금({curr})"
                temp_qty = qty
                if target_from in inv_batches:
                    for batch in inv_batches[target_from]:
                        if temp_qty <= 0: break
                        if batch['qty'] <= 0: continue
                        take = min(temp_qty, batch['qty']); batch['qty'] -= take; temp_qty -= take
                if pd.notna(rate) and rate > 0: c_budget -= qty * (rate / mult)
                
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
            target_from = f"트래블카드({curr})"; target_to = f"현금({curr})"
            if target_from in inv_batches:
                for batch in inv_batches[target_from]:
                    if temp_qty <= 0: break
                    if batch['qty'] <= 0: continue
                    take = min(temp_qty, batch['qty']); batch['qty'] -= take
                    inv_batches[target_to].append({'rate': batch['rate'], 'qty': take})
                    total_inherited_krw += take * (batch['rate'] / mult); temp_qty -= take
            
            if temp_qty > 0:
                fallback_r = get_WAR(curr)
                inv_batches[target_to].append({'rate': fallback_r, 'qty': temp_qty})
                total_inherited_krw += temp_qty * (fallback_r / mult)
                
            if qty > 0: rate = (total_inherited_krw / qty) * mult if total_inherited_krw > 0 else get_default_rate(curr)
        
        elif is_deductible == 1:
            if asset_cls == "DOMESTIC":
                if curr != 'KRW' and (pd.isna(rate) or rate <= 0.0): rate = get_default_rate(curr)
                c_budget += qty if curr == 'KRW' else qty * (rate / mult)
                rate = 1.0 if curr == 'KRW' else rate
            elif curr != 'KRW':
                if asset_cls == "CREDIT":
                    rate = get_WAR(curr)
                    temp_df.at[i, 'Note'] = "Credit (Debt Generated)"
                else:
                    target = f"트래블카드({curr})" if asset_cls == "PREPAID" else f"현금({curr})" 
                    temp_qty = qty; total_cost_krw = 0.0; decomposed =[]
                    
                    if target in inv_batches:
                        for batch in inv_batches[target]:
                            if temp_qty <= 0: break
                            if batch['qty'] <= 0: continue
                            take = min(temp_qty, batch['qty']); batch['qty'] -= take; temp_qty -= take
                            total_cost_krw += take * (batch['rate'] / mult)
                            r_prec = ".2f"
                            q_fmt = ",.0f" if mult == 100 else ",.2f"
                            decomposed.append(f"{take:{q_fmt}}@{batch['rate']:{r_prec}}")

                    if temp_qty > 0:
                        fallback_r = get_WAR(curr)
                        total_cost_krw += temp_qty * (fallback_r / mult)
                        r_prec = ".2f"
                        q_fmt = ",.0f" if mult == 100 else ",.2f"
                        decomposed.append(f"{temp_qty:{q_fmt}}@{fallback_r:{r_prec}}(Auto)")
                    
                    if qty > 0:
                        rate = (total_cost_krw / qty) * mult
                        if decomposed: temp_df.at[i, 'Note'] = "Decomposed: " + " + ".join(decomposed)
                    else: rate = 0.0

        row_country = temp_df.at[i, 'Country']
        nodes = TRIP_CONFIGS[st.session_state.current_trip].get("nodes", {})
        row_curr = nodes.get(row_country, FIRST_NODE)["currency"] if nodes else "USD"
        rnd_dec = 0 if row_curr in["VND", "HUF", "KRW"] else 2
        
        temp_df.at[i, 'AppliedRate'] = rate
        temp_df.at[i, 'Cum_Budget_KRW'] = round(c_budget, 2)
        temp_df.at[i, 'Cum_Card_Local'] = round(sum([b['qty'] for b in inv_batches[f"트래블카드({row_curr})"]]), rnd_dec)
        temp_df.at[i, 'Cum_Cash_Local'] = round(sum([b['qty'] for b in inv_batches[f"현금({row_curr})"]]), rnd_dec)
        
    return temp_df

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
            st.error(f"🚨 클라우드 상태 확인 실패! ({e})")
            return False

    if existing_df is not None and len(existing_df) > 5:
        if len(df) <= 3:
            st.error(f"🚨 **치명적 데이터 증발(Wipe) 시도 차단됨!** (클라우드: {len(existing_df)}건 -> 저장시도: {len(df)}건)")
            return False

    final_df = recalculate_entire_ledger(df)
    for attempt in range(3):
        try:
            conn.update(worksheet=ACTIVE_SHEET, data=final_df.reindex(columns=FINAL_COLUMNS))
            smart_cache_clear()
            return True
        except Exception as e:
            if attempt < 2 and ("429" in str(e) or "Quota" in str(e)):
                time.sleep(2.5)
                continue
            st.error(f"🚨 클라우드 저장 실패: {e}")
            return False

def append_new_data(new_rows_df):
    smart_cache_clear()
    latest_df = load_data(ACTIVE_SHEET)
    merged_df = pd.concat([latest_df, new_rows_df], ignore_index=True)
    return save_data(merged_df)
        
ledger_df = load_data(ACTIVE_SHEET)

# ==============================================================================
# --- SECTION 3:[Module B] URDI Engine ---
# ==============================================================================
def get_inventory_status(df):
    from collections import defaultdict
    temp_df = df.sort_values(by='Date', kind='mergesort', ignore_index=True) if not df.empty else df
    inv_batches = defaultdict(list)
    
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
        
        is_exp = 1 if cat in clean_expense_cats and cat not in ['환불', '보증금', '재환전', '상환'] else 0
        is_deductible = 1 if (is_exp == 1 or cat in ['보증금', '상환']) else 0
        asset_cls = get_asset_class(method)
        
        if cat in ['충전', '환전', '입금', '직접환전']:
            if cat == '충전': final_dest_cls = "PREPAID"
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
                
        elif cat == '재환전':
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

### ⚙️[Logic: URDI Engine] 가중 평균 환율(WAR) 및 FIFO 환율 계산
def get_WAR(curr):
    sw_df = ledger_df[(ledger_df['Category'].str.strip().isin(['충전','환전','입금','직접환전'])) & (ledger_df['Currency'].str.strip() == curr)]
    if not sw_df.empty and sw_df['Amount'].sum() > 0: return (sw_df['Amount'] * sw_df['AppliedRate']).sum() / sw_df['Amount'].sum()
    return get_default_rate(curr)

def auto_calc_fifo_rate(amount, method, curr=TRAVEL_CURRENCY):
    asset_cls = get_asset_class(method)
    if asset_cls == "DOMESTIC": return get_WAR(curr)
    target = f"트래블카드({curr})" if asset_cls == "PREPAID" else f"현금({curr})"
    temp_inv = get_inventory_status(ledger_df)
    if target not in temp_inv: return get_WAR(curr)
    available_batches =[b for b in temp_inv[target] if b['qty'] > 0]
    if not available_batches: return get_WAR(curr)
    
    total_cost_krw, remaining = 0.0, amount
    mult = get_mult(curr)
    for batch in available_batches:
        if remaining <= 0: break
        take = min(remaining, batch['qty'])
        total_cost_krw += take * (batch['rate'] / mult); remaining -= take
    if remaining > 0: total_cost_krw += remaining * (available_batches[-1]['rate'] / mult)
    return (total_cost_krw / amount) * mult if amount > 0 else 0

def calculate_summary_metrics(df):
    if df.empty: return 0.0, 0.0
    temp_df = df.sort_values(by='Date', kind='mergesort', ignore_index=True)
    b_total = temp_df['Cum_Budget_KRW'].iloc[-1] if 'Cum_Budget_KRW' in temp_df.columns else 0
    gross_spent = temp_df[temp_df['IsExpense'] == 1].apply(lambda r: r['Amount'] if str(r['Currency']).strip() == 'KRW' else r['Amount'] * (r['AppliedRate'] / get_mult(r['Currency'])), axis=1).sum()
    expense_refunds = temp_df[(temp_df['Category'] == '환불') & (temp_df['PaymentMethod'].apply(get_asset_class) == 'DOMESTIC')]
    refund_total = expense_refunds.apply(lambda r: r['Amount'] if str(r['Currency']).strip() == 'KRW' else r['Amount'] * (r['AppliedRate'] / get_mult(r['Currency'])), axis=1).sum()
    return b_total, gross_spent - refund_total

# ==============================================================================
# --- SECTION 4: [Sidebar] UI & Dashboard ---
# ==============================================================================
with st.sidebar:
    if st.session_state.get('show_spi', False):
        st.subheader("🧭 GTL 관제탑 모드")
        st.info("💡 **글로벌 물가 지표(SPI) 비교 분석 중**\n\n특정 여행의 지출 내역이나 잔고를 보시려면 상단의 '내 여행함'에서 여행지를 선택해 주세요.")
        st.divider()
        tz_sel = st.radio("📍 기준 시간 (Timezone)",["🇰🇷 한국 시간", "🌍 현지 시간"], horizontal=True, index=0)
        st.session_state.current_tz = TZ_KST if "한국" in tz_sel else TRIP_TZ
        st.markdown("<div style='margin-top:35px;'></div>", unsafe_allow_html=True)
        if st.button("🔄 Cloud Refresh", use_container_width=True): st.cache_data.clear(); st.rerun()
    else:
        st.subheader("💰 지갑 잔고")
        b_val, spent_val = calculate_summary_metrics(ledger_df)
        
        active_currs = set([k.split('(')[1].replace(')','') for k in current_inventory_batches.keys() if len(current_inventory_batches[k]) > 0 and sum(b['qty'] for b in current_inventory_batches[k]) > 0])
        trip_currs = set(node['currency'] for node in TRIP_CONFIGS[st.session_state.current_trip]["nodes"].values())
        display_currs = sorted(list(active_currs | trip_currs))
        
        for c in display_currs:
            if c == "KRW": continue
            m = get_mult(c)
            fmt = "{:,.2f}" if m == 1 else "{:,.0f}"

            debt_amt = ledger_df[(ledger_df['Currency']==c) & (ledger_df['PaymentMethod'].str.contains("외상|부채|CREDIT", na=False))]['Amount'].sum()
            repay_amt = ledger_df[(ledger_df['Currency']==c) & (ledger_df['Category']=="상환")]['Amount'].sum()
            current_debt = debt_amt - repay_amt
            if current_debt > 0: st.markdown(f"<div style='color:#FF4B4B; font-size:14px;'>📌 <b>미결제 외상: {fmt.format(current_debt)}</b></div>", unsafe_allow_html=True)
            
            c_card = sum([b['qty'] for b in current_inventory_batches.get(f"트래블카드({c})",[])])
            c_cash = sum([b['qty'] for b in current_inventory_batches.get(f"현금({c})",[])])
            
            if c_card > 0 or c_cash > 0 or c in trip_currs:
                st.markdown(f"<div style='color:#FFA500; font-weight:bold; margin-top:14px; margin-bottom:12px;'>● {c}</div>", unsafe_allow_html=True)
                st.markdown(f"💳 카드: **{fmt.format(c_card)}**")
                st.markdown(f"<div style='margin-bottom:18px;'>💵 현금: **{fmt.format(c_cash)}**</div>", unsafe_allow_html=True) 
                
                card_batches = current_inventory_batches.get(f"트래블카드({c})", [])
                cash_batches = current_inventory_batches.get(f"현금({c})", [])
                if any(b['qty'] > 0 for b in (card_batches + cash_batches)):
                    with st.expander("🔍 상세 배치", expanded=False):
                        r_fmt = ".2f"
                        if any(b['qty'] > 0 for b in card_batches):
                            st.caption("[카드]")
                            for b in card_batches:
                                if b['qty'] > 0: st.caption(f"• {fmt.format(b['qty'])} @{b['rate']:{r_fmt}}")
                        if any(b['qty'] > 0 for b in cash_batches):
                            st.caption("[현금]")
                            for b in cash_batches:
                                if b['qty'] > 0: st.caption(f"• {fmt.format(b['qty'])} @{b['rate']:{r_fmt}}")
                st.divider()

        st.markdown("<div style='margin-top:35px;'></div>", unsafe_allow_html=True)
        st.metric("🏦 총 예산", f"{b_val:,.0f} 원")
        st.metric("💸 지출총액", f"{spent_val:,.0f} 원")

        st.divider()
        st.markdown("<div style='margin-top:35px;'></div>", unsafe_allow_html=True)
        tz_sel = st.radio("📍 기준 시간 (Timezone)",["🇰🇷 한국 시간", "🌍 여행지 현지 시간"], horizontal=True, index=0 if "한국" in str(st.session_state.current_tz) else 1)
        st.session_state.current_tz = TZ_KST if "한국" in tz_sel else TRIP_TZ

        st.markdown("<div style='margin-top:35px;'></div>", unsafe_allow_html=True)
        if st.button("🔄 Cloud Refresh", use_container_width=True): st.cache_data.clear(); st.rerun()

# ==============================================================================
# --- SECTION 5: [Router] UI Navigation & Core Modules ---
# ==============================================================================
def sort_trips(trip_names):
    return sorted(trip_names, key=lambda x: (re.search(r'\((\d{4})\)', x).group(1) if re.search(r'\((\d{4})\)', x) else '0000', x), reverse=True)

sorted_trips = sort_trips(list(TRIP_CONFIGS.keys()))
SPECIAL_MODE = "📊 모든 여행 간 비교 (SPI)"
dropdown_options = sorted_trips + [SPECIAL_MODE]

if 'show_spi' not in st.session_state: st.session_state.show_spi = False
curr_idx = len(sorted_trips) if st.session_state.show_spi else (sorted_trips.index(st.session_state.current_trip) if st.session_state.current_trip in sorted_trips else 0)

c_trip_top, c_empty = st.columns([2, 2])
with c_trip_top:
    sel_trip = st.selectbox("✈️ 내 여행함 (Trip Selector)", dropdown_options, index=curr_idx, label_visibility="collapsed")
    if sel_trip == SPECIAL_MODE:
        if not st.session_state.show_spi:
            st.session_state.show_spi = True
            st.rerun()
    else:
        if st.session_state.show_spi or sel_trip != st.session_state.current_trip:
            st.session_state.show_spi = False
            st.session_state.current_trip = sel_trip
            st.rerun()

st.divider()

if st.session_state.show_spi:
    st.title("여행지 물가비교")
    df_all = load_all_trips_data()
    
    if not df_all.empty:
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
                    for c_name in config["nodes"].keys(): stay_nights[(trip_name, c_name)] = float(n_match.group(1))
        
        def extract_spi_date(d_str):
            match = re.search(r"'(\d{2})\s+(\d{2})/(\d{2})", str(d_str))
            if match: return f"20{match.group(1)}-{match.group(2)}-{match.group(3)}"
            match2 = re.search(r'(\d{4}-\d{2}-\d{2})', str(d_str))
            if match2: return match2.group(1)
            return None
            
        df_all['Date_Obj'] = pd.to_datetime(df_all['Date'].apply(extract_spi_date), errors='coerce')
        
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
                stay_nights[(trip, country)] = max(1, extracted_nights if extracted_nights > 0 else 1)

        df_spi = df_all[(df_all['Category'].isin(SPI_CATS)) & (~df_all['Country'].str.contains('글로벌|경유|크로아티아|불가리아', na=False))].copy()
        
        if not df_spi.empty:
            df_spi['KRW_val'] = df_spi.apply(lambda r: r['Amount'] if r['Currency'] == 'KRW' else r['Amount'] * (float(r['AppliedRate'])/get_mult(r['Currency'])), axis=1)
            refund_df = df_all[(df_all['Category'] == '환불') & (~df_all['Country'].str.contains('글로벌|경유|크로아티아|불가리아', na=False))].copy()
            if not refund_df.empty:
                refund_df['KRW_val'] = refund_df.apply(lambda r: -(r['Amount'] if r['Currency'] == 'KRW' else r['Amount'] * (float(r['AppliedRate'])/get_mult(r['Currency']))), axis=1)
                def map_refund_group(desc):
                    desc = str(desc).replace(" ", "").lower()
                    if any(k in desc for k in ["보증금", "deposit"]): return '제외'
                    if any(k in desc for k in ["호텔", "숙박"]): return '🏨 숙박'
                    if any(k in desc for k in ["투어", "입장료"]): return '🏄 투어/액티비티'
                    if any(k in desc for k in ["렌트카"]): return '🚗 렌트카'
                    return '제외'
                refund_df['SPI_Group'] = refund_df['Description'].apply(map_refund_group)
                refund_df = refund_df[refund_df['SPI_Group'] != '제외']
                if not refund_df.empty: df_spi = pd.concat([df_spi, refund_df], ignore_index=True)

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
            theme_notes =[]
            for idx, row in agg_total.iterrows():
                t, c, pp_nights = row['TripName'], row['Country'], row['Travelers'] * row['Nights']
                sub_group = agg_group[(agg_group['TripName'] == t) & (agg_group['Country'] == c)]
                hotel_v = sub_group[sub_group['SPI_Group'] == '🏨 숙박']['KRW_val'].sum()
                rent_v = sub_group[sub_group['SPI_Group'] == '🚗 렌트카']['KRW_val'].sum()
                tour_v = sub_group[sub_group['SPI_Group'] == '🏄 투어/액티비티']['KRW_val'].sum()
                
                tags =[]
                if hotel_v > 0: tags.append(f"🏨 1박평균 {hotel_v/row['Nights']/10000:.1f}만")
                if rent_v > 0: tags.append(f"🚗 1일렌트 {rent_v/row['Nights']/10000:.1f}만")
                if tour_v > 0: tags.append(f"🏄 투어(1인) {tour_v/pp_nights/10000:.1f}만")
                theme_notes.append(" | ".join(tags) if tags else "-")
            agg_total['Theme'] = theme_notes
            final_total_df = agg_total.sort_values(by='Daily_SPI', ascending=True)
            
            if not final_total_df.empty:
                st.markdown("### 여행지별 1박 체감물가 (KRW)")
                final_total_df['Chart_Label'] = final_total_df.apply(lambda r: f"{r['Country']}({re.search(r'([가-힣]+)', r['TripName']).group(1) if re.search(r'([가-힣]+)', r['TripName']) else ''})" if re.search(r'([가-힣]+)', r['TripName']) and re.search(r'([가-힣]+)', r['TripName']).group(1) not in str(r['Country']) else str(r['Country']), axis=1)
                display_df = final_total_df.rename(columns={'TripName': '여행명', 'Country': '국가', 'Travelers': '인원수', 'Nights': '숙박일(박)', 'Theme': '💡 특이사항 및 요인'})
                display_df['1박 체감물가'] = display_df['Daily_SPI'].apply(lambda x: f"{x:,.0f} 원")
                st.dataframe(display_df[['여행명', '국가', '인원수', '숙박일(박)', '1박 체감물가', '💡 특이사항 및 요인']], use_container_width=True, hide_index=True)
                
                label_map = dict(zip(zip(final_total_df['TripName'], final_total_df['Country']), final_total_df['Chart_Label']))
                agg_group['Chart_Label'] = agg_group.apply(lambda r: label_map.get((r['TripName'], r['Country']), r['Country']), axis=1)
                category_order_x = final_total_df['Chart_Label'].tolist()
                stack_order = ['📱 기타', '🚕 로컬교통', '🍔 식음료', '🏄 투어/액티비티', '🏨 숙박', '🚗 렌트카']
                color_map = {'🚗 렌트카':'#D32F2F', '🏨 숙박':'#1976D2', '🏄 투어/액티비티':'#9C27B0', '🍔 식음료':'#4CAF50', '🚕 로컬교통':'#00ACC1', '📱 기타':'#795548'}
                fig_stacked = px.bar(agg_group, x='Chart_Label', y='Daily_SPI', color='SPI_Group', color_discrete_map=color_map, category_orders={"Chart_Label": category_order_x, "SPI_Group": stack_order})
                fig_stacked.update_layout(barmode='stack', margin=dict(l=10, r=10, t=10, b=30), legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5, title=None), xaxis_title=None, yaxis_title=None)
                fig_stacked.update_traces(hovertemplate="%{x}<br><b>%{data.name}</b>: %{y:,.0f}원<extra></extra>")
                st.plotly_chart(fig_stacked, use_container_width=True, config={'displaylogo': False})
            else: st.info("비교할 SPI 데이터가 부족합니다.")
        else: st.info("SPI 기준에 부합하는 데이터가 없습니다.")

else:
    st.title(f"{st.session_state.current_trip}")
    tab_in, tab_his, tab_stats, tab_final = st.tabs(["📝 입력", "🔍 조회", "📊 일일", "🏁 요약"])

    with tab_in:
        c_node, c_mode = st.columns([1, 2])
        with c_node:
            sel_node = st.selectbox("🌍 국가 선택", list(TRIP_CONFIGS[st.session_state.current_trip]["nodes"].keys()), key="in_country")
            IN_CFG = TRIP_CONFIGS[st.session_state.current_trip]["nodes"][sel_node]
            IN_CURR = IN_CFG["currency"]
            IN_MULTI = IN_CFG["multiplier"]
        with c_mode:
            mode = st.radio("기록 모드 선택",["일반 지출", "🛫 항공권(특수)", "🏨 호텔(특수)", "자산 이동", "환불(취소)"], horizontal=True, key="mode_radio", label_visibility="collapsed")
        
        dynamic_tz = timezone(timedelta(hours=IN_CFG["timezone"])) if "한국" not in str(st.session_state.current_tz) else TZ_KST
        sel_date = st.date_input("날짜 선택", value=datetime.now(dynamic_tz).date(), key="shared_date_input")
        available_currs = sorted(list(set(node["currency"] for node in TRIP_CONFIGS[st.session_state.current_trip]["nodes"].values())))

        if mode == "일반 지출":        
            def_index = EXPENSE_CATS.index(st.session_state.last_cat_name) if st.session_state.last_cat_name in EXPENSE_CATS else 0
            cat = st.radio("항목 선택", EXPENSE_CATS, index=def_index, horizontal=True, key="exp_cat")
            st.session_state.last_cat_name = cat
            if st.session_state.get('clear_exp_desc', False):
                st.session_state.exp_desc = ""; st.session_state.clear_exp_desc = False
                
            col_desc, col_receipt = st.columns([3, 1])
            with col_receipt: 
                uploaded_files = st.file_uploader("📸 영수증 첨부 (다중 가능)", type=['png', 'jpg', 'jpeg'], key="exp_receipt", accept_multiple_files=True)
                if uploaded_files:
                    if st.button("🤖 영수증 AI 스캔", use_container_width=True):
                        with st.spinner("분석 중..."):
                            all_texts = "\n---\n".join([extract_text_from_vision_api(f.getvalue()) for f in uploaded_files])
                            smart_text = summarize_receipt_with_gemini(all_texts)
                            if smart_text:
                                st.session_state.exp_desc = st.session_state.get('exp_desc', '') + "\n" + smart_text
                                st.rerun()
                                
            with col_desc: desc = st.text_area("📝 내용 (상호명 및 다중 내역)", height=120, key="exp_desc")
                
            col_m1, col_m2, col_m3 = st.columns([1, 1, 1])
            with col_m1: 
                curr_opts =[IN_CURR, "KRW", "USD"] +[c for c in available_currs if c not in[IN_CURR, "KRW", "USD"]]
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
                combined_gateways =["선택안함 (기본)"] + sorted(list(set(["알리페이", "위챗페이", "네이버페이", "Apple Pay", "Trip.com", "Agoda", "Uber", "Bolt"]) | harvested_tags)) +["➕ 직접 입력하기"]
                gateway_sel = st.selectbox("결제 플랫폼", combined_gateways, key="exp_gw")
                final_gateway = st.text_input("새로운 플랫폼 이름 입력") if gateway_sel == "➕ 직접 입력하기" else ("" if gateway_sel == "선택안함 (기본)" else gateway_sel)

            col_a1, col_a2 = st.columns(2)
            with col_a1:
                mult = get_mult(curr)
                if curr == "KRW" or mult == 100: amt = st.number_input(f"금액 ({curr})", min_value=0, step=1000 if curr != "KRW" else 1, format="%d", key="exp_amt_int")
                else: amt = st.number_input(f"금액 ({curr})", min_value=0.0, step=1.0, format="%.2f", key="exp_amt_float")
            with col_a2:
                if curr != "KRW" and amt > 0:
                    calc_rate = auto_calc_fifo_rate(amt, met, curr)
                    st.caption(f"💡 {curr} 인벤토리 계산 환율: **{calc_rate:.2f}**")
                    cr_final = st.number_input("확정 환율", value=float(calc_rate), format="%.5f", key=f"exp_cr_auto_{met}_{amt}")
                else: cr_final = st.number_input("확정 환율", value=(1.0 if curr=="KRW" else get_default_rate(curr)), format="%.5f", key=f"exp_cr_man_{curr}")
                
            if st.button("🚀 지출 기록하기", use_container_width=True):
                url_list = [upload_image_to_imgbb(file) for file in uploaded_files] if uploaded_files else []
                new_row = pd.DataFrame([{'Date': format_date_korean(sel_date), 'Country': sel_node, 'Category': cat, 'Description': f"[{final_gateway}] {desc}" if final_gateway else desc, 'Currency': curr, 'Amount': amt, 'PaymentMethod': met, 'IsExpense': 1, 'AppliedRate': cr_final, 'Note': '', 'Receipt_URL': ",".join([u for u in url_list if u])}])
                if append_new_data(new_row): 
                    st.session_state.clear_exp_desc = True
                    st.rerun()

        elif mode == "🛫 항공권(특수)":
            st.subheader("✈️ 항공권 통합 기록")
            f_trip_type = st.radio("여정 구분", ["왕복", "편도"], horizontal=True)
            c1, c2, c3 = st.columns(3)
            with c1: f_gw = st.text_input("1. 결제 플랫폼 (필수)")
            with c2: f_carrier = st.text_input("2. 항공사")
            with c3: f_route = st.text_input("3. 노선")

            c4, c5 = st.columns(2)
            with c4:
                st.info(f"🛫 {'출국' if f_trip_type == '왕복' else '탑승'} 스케줄")
                f_dep_info = st.text_input("4. 스케줄 정보")
                f_dep_date = st.date_input("5. 탑승 날짜", value=sel_date)
            with c5:
                if f_trip_type == "왕복":
                    st.success("🛬 귀국 스케줄")
                    f_ret_info = st.text_input("6. 귀국편 정보")
                    f_ret_date = st.date_input("7. 귀국 날짜", value=sel_date + timedelta(days=7))
                else: f_ret_info, f_ret_date = "", None

            c6, c7, c8 = st.columns([1, 1, 1])
            with c6: f_baggage = st.selectbox("8. 위탁수화물", ["포함", "미포함", "일부포함"])
            with c7: f_bag_memo = st.text_input("9. 수화물 상세")
            with c8: f_asset = st.selectbox("10. 결제 수단", ["네이버페이(원화고정)", "원화계좌(한국)", "해외송금(한국계좌)", "트래블카드(외화)", "신용카드(원화결제)", "기타"])
            f_memo = st.text_input("📝 비고/메모")

            st.divider()
            c9, c10, c11, c12 = st.columns([1, 2, 1, 1])
            with c9: 
                curr_opts_flight = ["KRW", "USD", "EUR"] + [c for c in available_currs if c not in ["KRW", "USD", "EUR"]]
                f_curr = st.selectbox("11. 통화", curr_opts_flight)
            with c10: f_amt = st.number_input(f"12. 결제 금액({f_curr})", min_value=0.0, step=1.0)
            with c11: f_rate = st.number_input("13. 환율", value=1.0 if f_curr=="KRW" or "네이버" in f_asset else get_default_rate(f_curr), format="%.4f")
            with c12: f_fee = st.number_input("14. 수수료(원)", min_value=0)

            if st.button("🚀 기록", use_container_width=True, type="primary"):
                if not f_gw or not f_route: st.stop()
                clean_asset = f"트래블카드({f_curr})" if "트래블카드" in f_asset else f_asset.split('(')[0].strip()
                full_desc = f"[{f_gw}+{clean_asset}] {f_route}({f_carrier}) | 출국:{f_dep_info}" + (f" | 귀국:{f_ret_info}" if f_trip_type == "왕복" and f_ret_info else "") + f" | 수화물:{f_baggage}({f_bag_memo})" + (f" | 메모:{f_memo}" if f_memo else "")
                
                new_rows = [pd.DataFrame([{'Date': format_date_korean(sel_date), 'Country': sel_node, 'Category': '항공권', 'Description': full_desc, 'Currency': f_curr, 'Amount': f_amt, 'PaymentMethod': clean_asset, 'IsExpense': 1, 'AppliedRate': f_rate, 'Note': f"수수료:{f_fee}원" if f_fee > 0 else ""}])]
                if f_dep_info: new_rows.append(pd.DataFrame([{'Date': format_date_korean(f_dep_date), 'Country': sel_node, 'Category': '출국' if f_trip_type == '왕복' else '항공스케줄', 'Description': f"🛫 {f_route} ({f_dep_info})", 'Currency': 'KRW', 'Amount': 0, 'PaymentMethod': '정보', 'IsExpense': 0, 'AppliedRate': 1.0, 'Note': 'Auto'}]))
                if f_trip_type == "왕복" and f_ret_info: new_rows.append(pd.DataFrame([{'Date': format_date_korean(f_ret_date), 'Country': sel_node, 'Category': '입국', 'Description': f"🛬 {f_route} ({f_ret_info})", 'Currency': 'KRW', 'Amount': 0, 'PaymentMethod': '정보', 'IsExpense': 0, 'AppliedRate': 1.0, 'Note': 'Auto'}]))
                if append_new_data(pd.concat(new_rows, ignore_index=True)): st.rerun()
                    
        elif mode == "🏨 호텔(특수)":
            st.subheader("🏨 호텔 예약 상세 기록")
            c1, c2 = st.columns(2)
            with c1:
                h_gw = st.text_input("1. 결제 플랫폼 (필수)")
                h_name = st.text_input("2. 호텔명")
                h_checkin = st.date_input("3. 체크인", value=sel_date)
                h_asset = st.selectbox("4. 결제 수단", ["네이버페이(원화고정)", "원화계좌(한국)", "해외송금(한국계좌)", "트래블카드(외화)", "신용카드(원화결제)", "기타"])
            with c2:
                h_nights = st.number_input("5. 숙박 일수", min_value=1, step=1)
                h_checkout = h_checkin + timedelta(days=h_nights)
                st.caption(f"📅 체크아웃: {h_checkout.strftime('%Y-%m-%d')}")
                h_detail = st.text_area("6. 내용 (룸타입/특징)", height=68)
                h_curr = st.selectbox("7. 결제 통화", ["KRW", "VND", "USD", "PHP", "EUR", "CNY", "TRY"], key="h_curr")

            c3, c4, c5 = st.columns(3)
            with c3: h_amt = st.number_input(f"8. 결제 금액({h_curr})", min_value=0.0, step=1.0)
            with c4: h_rate = st.number_input("9. 적용 환율", value=1.0 if h_curr=="KRW" or "네이버" in h_asset else get_default_rate(h_curr), format="%.4f")
            with c5: h_fee = st.number_input("10. 환율 수수료(원)", min_value=0)

            if st.button("🚀 저장", use_container_width=True):
                if not h_gw: st.stop()
                clean_asset = f"트래블카드({h_curr})" if "트래블카드" in h_asset else h_asset.split('(')[0].strip()
                full_desc = f"[{h_gw}] {h_name} | {h_nights}박({h_checkin.strftime('%m/%d')}~{h_checkout.strftime('%m/%d')}) | {h_detail.replace('\\n', ' ')}"
                if append_new_data(pd.DataFrame([{'Date': format_date_korean(sel_date), 'Country': sel_node, 'Category': '호텔', 'Description': full_desc, 'Currency': h_curr, 'Amount': h_amt, 'PaymentMethod': clean_asset, 'IsExpense': 1, 'AppliedRate': h_rate, 'Note': f"수수료:{h_fee}원" if h_fee > 0 else ""}])): st.rerun()
                    
        elif mode == "자산 이동":
            ty = st.selectbox("유형",["직접환전 (원 -> 현금)", "이종환전 (외화 -> 현금)", "충전 (원 -> 카드)", "ATM출금 (카드 -> 현금)", "재환전 (외화 -> 원)"], key="tr_type")
            c1, c2 = st.columns(2)
            if "이종환전" in ty:
                with c1:
                    curr_tr = st.selectbox("얻게 되는 통화 (Target)", [c for c in available_currs if c != "KRW"])
                    mult_tr = get_mult(curr_tr)
                    t_amt = st.number_input(f"얻은 금액 ({curr_tr})", min_value=0, step=1000, format="%d") if mult_tr == 100 else st.number_input(f"얻은 금액 ({curr_tr})", min_value=0.0, step=10.0, format="%.2f")
                with c2:
                    curr_src = st.selectbox("지불하는 외화 (Source)", [c for c in available_currs if c not in ["KRW", curr_tr]])
                    src_met = st.selectbox("지불 재원", [f"현금({curr_src})", f"트래블카드({curr_src})"])
                    s_amt = st.number_input(f"지불한 금액 ({curr_src})", min_value=0.0, step=10.0, format="%.2f")
                    if s_amt > 0 and t_amt > 0:
                        fifo_rate = auto_calc_fifo_rate(s_amt, src_met, curr_src)
                        est_krw_cost = s_amt * (fifo_rate / get_mult(curr_src))
                        target_rate = (est_krw_cost / t_amt) * mult_tr
                        st.success(f"🎯 산출 환율: **{target_rate:.4f}**")
                if st.button("🔄 실행", use_container_width=True, type="primary"):
                    fifo_rate = auto_calc_fifo_rate(s_amt, src_met, curr_src)
                    target_rate = ((s_amt * (fifo_rate/get_mult(curr_src))) / t_amt) * mult_tr if t_amt > 0 else 0
                    if append_new_data(pd.DataFrame([
                        {'Date': format_date_korean(sel_date), 'Country': sel_node, 'Category': '이종환전', 'Description': f"지불 (-> {curr_tr} {t_amt})", 'Currency': curr_src, 'Amount': s_amt, 'PaymentMethod': src_met, 'IsExpense': 0, 'AppliedRate': fifo_rate, 'Note': ''},
                        {'Date': format_date_korean(sel_date), 'Country': sel_node, 'Category': '직접환전', 'Description': f"획득 (<- {curr_src} {s_amt})", 'Currency': curr_tr, 'Amount': t_amt, 'PaymentMethod': src_met, 'IsExpense': 0, 'AppliedRate': target_rate, 'Note': ''}
                    ])): st.rerun()

            elif "재환전" in ty:
                with c1:
                    curr_tr = st.selectbox("팔(Sell) 통화", [c for c in available_currs if c != "KRW"])
                    s_amt = st.number_input(f"팔 외화 금액 ({curr_tr})", min_value=0.0, step=10.0, format="%.2f")
                    source_met = st.selectbox("외화 출처",[f"트래블카드({curr_tr})", f"현금({curr_tr})"])
                with c2:
                    rcv_krw = st.number_input("입금받은 원화 총액 (KRW)", min_value=0, step=1000, format="%d")
                    if s_amt > 0:
                        fifo_cost = s_amt * (auto_calc_fifo_rate(s_amt, source_met, curr_tr) / get_mult(curr_tr))
                        fx_diff = rcv_krw - fifo_cost
                        if rcv_krw > 0:
                            if fx_diff < -1: st.error(f"📉 환차손: {abs(fx_diff):,.0f} 원")
                            elif fx_diff > 1: st.success(f"📈 환차익: {fx_diff:,.0f} 원")
                            
                if st.button("🔄 재환전 실행", use_container_width=True):
                    applied_sell_rate = (rcv_krw / s_amt) * get_mult(curr_tr) if s_amt > 0 else 0
                    new_rows = [pd.DataFrame([{'Date': format_date_korean(sel_date), 'Country': sel_node, 'Category': '재환전', 'Description': f"재환전 (외화매도)", 'Currency': curr_tr, 'Amount': s_amt, 'PaymentMethod': source_met, 'IsExpense': 0, 'AppliedRate': applied_sell_rate, 'Note': f"원화 {rcv_krw}원 입금"}])]
                    fx_diff = rcv_krw - (s_amt * (auto_calc_fifo_rate(s_amt, source_met, curr_tr) / get_mult(curr_tr))) if s_amt > 0 else 0
                    if abs(fx_diff) >= 1: new_rows.append(pd.DataFrame([{'Date': format_date_korean(sel_date), 'Country': sel_node, 'Category': '수수료', 'Description': f"[{curr_tr}] 환차" + ("익" if fx_diff > 0 else "손"), 'Currency': 'KRW', 'Amount': abs(fx_diff) * (-1 if fx_diff < 0 else 1), 'PaymentMethod': '원화계좌(한국)', 'IsExpense': 1, 'AppliedRate': 1.0, 'Note': 'FX Diff'}]))
                    if append_new_data(pd.concat(new_rows, ignore_index=True)): st.rerun()
            else:
                with c1:
                    curr_tr = st.selectbox("대상 통화", [IN_CURR, "USD"] +[c for c in available_currs if c not in[IN_CURR, "USD", "KRW"]])
                    mult_tr = get_mult(curr_tr)
                    t_amt = st.number_input(f"받은 금액 ({curr_tr})", min_value=0, step=1000, format="%d") if mult_tr == 100 else st.number_input(f"받은 금액 ({curr_tr})", min_value=0.0, step=10.0, format="%.2f")
                    if "ATM" in ty:
                        inherited_r = auto_calc_fifo_rate(t_amt, f"트래블카드({curr_tr})", curr_tr)
                        st.info(f"💳 카드 재고 계승 환율: **{inherited_r:.4f}**")
                        applied_tr_rate = inherited_r
                    else:
                        s_cost = st.number_input("소요 원금 (KRW)", min_value=0, step=1, format="%d")
                        applied_tr_rate = (s_cost / t_amt) * mult_tr if t_amt > 0 else 0
                with c2: fee_amt = st.number_input(f"수수료 ({curr_tr})", min_value=0, step=1000, format="%d") if mult_tr == 100 else st.number_input(f"수수료 ({curr_tr})", min_value=0.0, step=1.0, format="%.2f")
                        
                if st.button("🔄 이동 실행", use_container_width=True):
                    dest = f"트래블카드({curr_tr})" if "충전" in ty else f"현금({curr_tr})"
                    source = "원화계좌(한국)" if "원화계좌" in ty else f"트래블카드({curr_tr})"
                    new_rows = [pd.DataFrame([{'Date': format_date_korean(sel_date), 'Country': sel_node, 'Category': ty.split(" ")[0], 'Description': f"{ty.split(' ')[0]} (-> {dest})", 'Currency': curr_tr, 'Amount': t_amt, 'PaymentMethod': source, 'IsExpense': 0, 'AppliedRate': applied_tr_rate, 'Note': ''}])]
                    if fee_amt > 0: new_rows.append(pd.DataFrame([{'Date': format_date_korean(sel_date), 'Country': sel_node, 'Category': "수수료", 'Description': "수수료", 'Currency': curr_tr, 'Amount': fee_amt, 'PaymentMethod': f"트래블카드({curr_tr})", 'IsExpense': 1, 'AppliedRate': auto_calc_fifo_rate(fee_amt, f"트래블카드({curr_tr})", curr_tr), 'Note': ''}]))
                    if append_new_data(pd.concat(new_rows, ignore_index=True)): st.rerun()
                        
        elif mode == "환불(취소)":
            st.subheader("🔙 결제 취소 (Rollback)")
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                r_curr = st.selectbox("취소된 통화", [IN_CURR, "KRW", "USD"] +[c for c in available_currs if c not in[IN_CURR, "KRW", "USD"]])
                r_met = st.selectbox("돌려받을 지갑",[f"현금({r_curr})", f"트래블카드({r_curr})", "원화계좌(한국)", "원화계좌(현지)"] if r_curr != "KRW" else["원화계좌(한국)", "원화계좌(현지)"])
                mult_r = get_mult(r_curr)
                r_amt = st.number_input("금액", min_value=0, step=1000, format="%d") if r_curr == "KRW" or mult_r == 100 else st.number_input("금액", min_value=0.0, step=1.0, format="%.2f")
            with col_r2:
                r_rate = st.number_input("과거 적용 환율", value=(1.0 if r_curr=="KRW" else get_default_rate(r_curr)), format="%.5f")
                r_desc = st.text_input("메모", placeholder="예: 호텔 보증금 반환")
                
            if st.button("🔙 롤백 실행", use_container_width=True):
                if append_new_data(pd.DataFrame([{'Date': format_date_korean(sel_date), 'Country': sel_node, 'Category': '환불', 'Description': f"취소: {r_desc}", 'Currency': r_curr, 'Amount': r_amt, 'PaymentMethod': r_met, 'IsExpense': 0, 'AppliedRate': r_rate, 'Note': 'Rollback', 'Receipt_URL': ''}])): st.rerun()

    with tab_his:
        st.info("💡 **표의 행(Row)을 클릭하시면 바로 아래에 영수증 뷰어가 열립니다!**")
        viewer_placeholder = st.empty()
        c_filter, c_search, c_tog = st.columns([2, 3, 1])
        with c_filter:
            filter_options =["모든 여행가계부", "이번 여행가계부"] + list(TRIP_CONFIGS[st.session_state.current_trip]["nodes"].keys())
            country_filter = st.selectbox("🌍 국가 필터", filter_options, index=1, key="his_country", label_visibility="collapsed")
        with c_search: 
            search_query = st.text_input("🔎 검색어 입력", placeholder="상호명, 메모, 카테고리 등", key="his_search", label_visibility="collapsed")
        with c_tog: 
            edit_mode = st.toggle("✏️ 직접 수정 모드", value=False, key="his_edit_toggle")

        if country_filter == "모든 여행가계부": edit_mode = False; display_df = load_all_trips_data()
        else:
            display_df = ledger_df.copy()
            if country_filter != "이번 여행가계부": display_df = display_df[display_df['Country'] == country_filter]

        if not display_df.empty: 
            display_df = display_df.sort_values(by='Date', kind='mergesort').reset_index(drop=True)
            display_df = display_df.reindex(columns=FINAL_COLUMNS)
            link_cfg = st.column_config.LinkColumn("영수증 📸", display_text="🔗 보기", disabled=True)
            
            # [Refactored] 완벽한 숫자 포매팅 및 IsExpense 제외 행 렌더링 뷰
            if edit_mode:
                edited_df = st.data_editor(display_df, use_container_width=True, num_rows="dynamic", key="editor_gtl_final", column_config={"Receipt_URL": link_cfg})
                if not display_df.equals(edited_df) and st.button("💾 변경사항 저장"):
                    if save_data(edited_df): st.rerun()
            else:
                if search_query.strip():
                    mask = (display_df['Category'].str.contains(search_query, case=False, na=False) | display_df['Description'].str.contains(search_query, case=False, na=False) | display_df['Note'].str.contains(search_query, case=False, na=False) | display_df['Country'].str.contains(search_query, case=False, na=False))
                    render_df = display_df[mask]
                else: render_df = display_df
                    
                df_str = render_df.copy()
                for i, row in df_str.iterrows():
                    c, m = row['Currency'], get_mult(row['Currency'])
                    if row['IsExpense'] == 0: df_str.at[i, 'Category'] = f"🚫 {row['Category']}"
                    
                    try: df_str.at[i, 'Amount'] = f"{float(row['Amount']):,.0f}" if c == 'KRW' or m == 100 else f"{float(row['Amount']):,.2f}"
                    except: pass
                    try: df_str.at[i, 'AppliedRate'] = "-" if c == 'KRW' or row['AppliedRate'] == 0 else f"{float(row['AppliedRate']):,.2f}"
                    except: pass
                    try: df_str.at[i, 'Cum_Budget_KRW'] = f"{float(row['Cum_Budget_KRW']):,.0f}"
                    except: pass
                    try: df_str.at[i, 'Cum_Card_Local'] = f"{float(row['Cum_Card_Local']):,.0f}" if c == 'KRW' or m == 100 else f"{float(row['Cum_Card_Local']):,.2f}"
                    except: pass
                    try: df_str.at[i, 'Cum_Cash_Local'] = f"{float(row['Cum_Cash_Local']):,.0f}" if c == 'KRW' or m == 100 else f"{float(row['Cum_Cash_Local']):,.2f}"
                    except: pass

                df_event = st.dataframe(df_str, use_container_width=True, column_config={"Receipt_URL": link_cfg}, selection_mode="single-row", on_select="rerun")
                
                if df_event.selection.rows:
                    real_idx = render_df.index[df_event.selection.rows[0]] 
                    row_data = display_df.loc[real_idx]
                    
                    with viewer_placeholder.container():
                        st.markdown("---")
                        c_info, c_edit = st.columns([1, 1])
                        
                        with c_info:
                            st.subheader("🧾 영수증 뷰어")
                            krw_equivalent = row_data['Amount'] if row_data['Currency'] == 'KRW' else row_data['Amount'] * (row_data['AppliedRate'] / get_mult(row_data['Currency']))
                            krw_display = f" ➔ <span style='color:#FFD700'>약 {krw_equivalent:,.0f} 원</span>" if row_data['Currency'] != 'KRW' else ""
                            
                            amt_fmt2 = "{:,.0f}" if get_mult(row_data['Currency']) == 100 or row_data['Currency'] == 'KRW' else "{:,.2f}"
                            st.markdown(f"### 🛒 {row_data['Category']} ({amt_fmt2.format(row_data['Amount'])} {row_data['Currency']}{krw_display})", unsafe_allow_html=True)
                            st.markdown(f"**📝 내역:** {row_data['Description'].replace(chr(10), '<br>')}", unsafe_allow_html=True)
                                
                            urls = str(row_data['Receipt_URL']).split(",") if str(row_data['Receipt_URL']).strip() else []
                            for idx, url in enumerate(urls):
                                if url.strip().startswith("http"): st.image(url.strip(), use_container_width=True, caption=f"영수증 #{idx+1}")
                                
                        with c_edit:
                            st.subheader("✏️ 영수증 보강")
                            desc_key = f"edit_desc_{real_idx}"
                            if st.session_state.get('current_edit_idx') != real_idx:
                                st.session_state[desc_key] = str(row_data['Description'])
                                st.session_state['current_edit_idx'] = real_idx
                                
                            new_receipt = st.file_uploader("📸 사진 업로드", type=['png', 'jpg', 'jpeg'], key="inline_receipt")
                            if new_receipt and st.button("🤖 AI 영수증 번역", use_container_width=True):
                                with st.spinner("번역 중..."):
                                    smart_text = summarize_receipt_with_gemini(extract_text_from_vision_api(new_receipt.getvalue()))
                                    if smart_text:
                                        st.session_state[desc_key] = st.session_state.get(desc_key, '') + "\n" + smart_text
                                        st.rerun()

                            new_desc = st.text_area("📝 세부 내역 수정", height=150, key=desc_key)
                            if st.button("💾 행 저장", use_container_width=True):
                                display_df.at[real_idx, 'Description'] = new_desc
                                if new_receipt:
                                    url = upload_image_to_imgbb(new_receipt)
                                    if url: display_df.at[real_idx, 'Receipt_URL'] = url
                                if save_data(display_df): st.success("업데이트 완료!"); time.sleep(1); st.rerun()
                        st.markdown("---")

    with tab_stats:
        if not ledger_df.empty:
            exp_df = ledger_df.sort_values(by='Date', kind='mergesort', ignore_index=True)
            exp_df = exp_df[exp_df['IsExpense'] == 1].copy()
            
            if not exp_df.empty:
                exp_df['Macro_Category'] = exp_df['Category'].map(MACRO_MAP).fillna("기타")
                exp_df['KRW_val'] = exp_df.apply(lambda r: r['Amount'] if str(r['Currency']).strip() == 'KRW' else r['Amount'] * (r['AppliedRate'] / get_mult(r['Currency'])), axis=1)
                
                def get_local_val(r):
                    c_curr = str(r['Currency']).strip()
                    if c_curr == TRAVEL_CURRENCY: return r['Amount']
                    krw_v = r['Amount'] if c_curr == 'KRW' else r['Amount'] * (r['AppliedRate'] / get_mult(c_curr))
                    war_t = get_WAR(TRAVEL_CURRENCY)
                    return krw_v / (war_t / get_mult(TRAVEL_CURRENCY)) if war_t > 0 else 0
                exp_df['Local_val'] = exp_df.apply(get_local_val, axis=1)
                exp_df['IsSurvival'] = exp_df['Category'].apply(lambda x: 1 if x in SURVIVAL_CATS else 0)

                color_map = {"식사": "#2E7D32", "간식": "#4CAF50", "마트": "#E91E63", "Grab": "#00897B", "교통": "#009688", "렌트카": "#009688", "마사지": "#0288D1", "투어": "#673AB7", "입장료": "#3F51B5", "선물": "#9C27B0", "통신": "#FF9800", "수수료": "#795548", "항공권": "#D32F2F", "호텔": "#1976D2", "보험": "#FBC02D"}
                macro_color_map = {"🍔 식음료": "#4CAF50", "🚗 교통": "#00ACC1", "🏄 액티비티": "#0288D1", "🎁 쇼핑": "#9C27B0", "📱 통신/기타": "#FF9800", "✈️ 항공권": "#D32F2F", "🏨 숙박": "#1976D2", "기타": "#9E9E9E"}

                c_mode = st.radio("📊 통화 선택",["원화(KRW)", f"현지화({TRAVEL_CURRENCY})"], horizontal=True, key="st_curr_top")
                y_col = 'KRW_val' if "원화" in c_mode else 'Local_val'

                is_fixed_cost = (exp_df['PaymentMethod'].str.strip() == '원화계좌(한국)') | (exp_df['Category'].isin(FIXED_COST_CATS))
                ovr_df = exp_df[(~is_fixed_cost) & (~exp_df['Category'].isin(['입국','출국']))]
                
                if not ovr_df.empty:
                    ovr_df = ovr_df.copy()
                    ovr_df['Date_Clean'] = ovr_df['Date'].str.split('(').str[0]
                    ovr_df = ovr_df.sort_values(by='Date_Clean')
                    ovr_df['Date_Country'] = ovr_df['Date_Clean'] + "<br><span style='font-size:11px;color:#AAAAAA'>" + ovr_df['Country'] + "</span>"
                    
                    fig2 = px.bar(ovr_df, x='Date_Country', y=y_col, color='Category', title=None, color_discrete_map=color_map)
                    fig2.update_layout(barmode='stack', margin=dict(l=10, r=10, t=30, b=150), legend=dict(orientation="h", yanchor="top", y=-0.3, xanchor="center", x=0.5))
                    st.markdown(f"<h4 style='text-align: center;'>🗺️ 여행지 일별지출</h4>", unsafe_allow_html=True)
                    st.plotly_chart(fig2, use_container_width=True, config={'displaylogo': False})

                st.divider()
                daily_set = ovr_df.groupby('Date').agg({'Country': lambda x: ' / '.join(x.unique()), 'KRW_val': 'sum', 'Local_val': 'sum'}).reset_index() if not ovr_df.empty else pd.DataFrame(columns=['Date', 'Country', 'KRW_val', 'Local_val'])
                surv_only = ovr_df[ovr_df['IsSurvival'] == 1].groupby('Date').agg({'KRW_val': 'sum', 'Local_val': 'sum'}).reset_index().rename(columns={'KRW_val': 'S_KRW', 'Local_val': 'S_Loc'}) if not ovr_df.empty else pd.DataFrame(columns=['Date', 'S_KRW', 'S_Loc'])
                daily_table = pd.merge(daily_set, surv_only, on='Date', how='left').fillna(0) if not daily_set.empty else pd.DataFrame()
                
                if not daily_table.empty:
                    display_table = daily_table[['Country', 'Date', 'KRW_val', 'Local_val', 'S_KRW', 'S_Loc']].rename(columns={'Country':'국가', 'Date':'날짜', 'KRW_val':'총(원)', 'Local_val':f'총({LOCAL_SYM})', 'S_KRW':'일상(원)', 'S_Loc':f'일상({LOCAL_SYM})'})
                    st.dataframe(display_table.style.format({'총(원)': '{:,.0f}', f'총({LOCAL_SYM})': "{:,.0f}" if MULTIPLIER==100 else "{:,.2f}", '일상(원)': '{:,.0f}', f'일상({LOCAL_SYM})': "{:,.0f}" if MULTIPLIER==100 else "{:,.2f}"}), use_container_width=True, hide_index=True)

                dom_df = exp_df[is_fixed_cost & (~exp_df['Category'].isin(['입국','출국']))]
                if not dom_df.empty:
                    st.divider()
                    st.markdown("<h4 style='text-align: center;'>🛫 사전결제</h4>", unsafe_allow_html=True)
                    dom_chart_df = dom_df.copy()
                    dom_chart_df['Short_Desc'] = dom_chart_df['Description'].apply(lambda x: str(x)[:15] + ".." if len(str(x)) > 15 else x)
                    fig1 = px.treemap(dom_chart_df, path=['Macro_Category', 'Category', 'Short_Desc'], values=y_col, color='Macro_Category', color_discrete_map=macro_color_map)
                    fig1.update_traces(texttemplate="<b>%{label}</b><br>%{value:,.0f}원", hovertemplate="<b>%{label}</b><br>금액: %{value:,.0f}원")
                    fig1.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=550)
                    st.plotly_chart(fig1, use_container_width=True, config={'displaylogo': False})

    with tab_final:
        if not ledger_df.empty and 'exp_df' in locals() and not exp_df.empty:
            total_trip_krw = exp_df['KRW_val'].sum()
            total_trip_loc = exp_df['Local_val'].sum()
            
            trip_cfg = TRIP_CONFIGS.get(st.session_state.current_trip, {})
            travelers = trip_cfg.get("travelers", 2)
            nights_match = re.findall(r'(\d+(?:\.\d+)?)', trip_cfg.get("stay_mapping", ""))
            total_nights = sum(float(n) for n in nights_match) if nights_match else 7
            
            is_fixed_cost_final = (exp_df['PaymentMethod'].str.strip() == '원화계좌(한국)') | (exp_df['Category'].isin(FIXED_COST_CATS))
            dom_total_krw = exp_df[is_fixed_cost_final]['KRW_val'].sum()
            ovr_total_krw = total_trip_krw - dom_total_krw
            ovr_total_loc = exp_df[~is_fixed_cost_final]['Local_val'].sum()
            
            local_v = exp_df[(exp_df['IsSurvival'] == 1) & (exp_df['Currency'].str.strip() != 'KRW')]
            denom = (travelers * max(1, total_nights))
            avg_local_krw = local_v['KRW_val'].sum() / denom
            
            fmt_local = "{:,.0f}" if MULTIPLIER == 100 else "{:,.2f}"
            def kpi_box(title, krw, loc=None):
                loc_str = f"<div class='kpi-value-vnd'>({fmt_local.format(loc)} {LOCAL_SYM})</div>" if loc is not None else ""
                return f"<div class='kpi-box'><div class='kpi-title'>{title}</div><div class='kpi-value-krw'>{krw:,.0f} 원</div>{loc_str}</div>"
                
            st.header("🏁 여행요약")
            k1, k2, k3, k4 = st.columns(4)
            with k1: st.markdown(kpi_box("최종 지출", total_trip_krw, total_trip_loc), unsafe_allow_html=True)
            with k2: st.markdown(kpi_box("사전결제 지출", dom_total_krw), unsafe_allow_html=True)
            with k3: st.markdown(kpi_box("현지 체류 지출", ovr_total_krw, ovr_total_loc), unsafe_allow_html=True)
            with k4: st.markdown(kpi_box("현지 체감(1인/1박)", avg_local_krw), unsafe_allow_html=True)

st.caption(f"GTL Platform {VERSION} | Sync: {datetime.now(st.session_state.current_tz).strftime('%Y-%m-%d %H:%M:%S')} | Strategic Partner Gem")
