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
    "항공권": "✈️ 항공권", "호텔": "🏨 숙박", "보험": "🛡️ 보험", "보증금": "🏦 자산이동", "재환전": "🏦 자산이동", "상환": "🏦 자산이동" # [Added] 상환 추가
}

CORE_COLUMNS =['Date', 'Country', 'Category', 'Description', 'Currency', 'Amount', 'PaymentMethod', 'Receipt_URL']
SYSTEM_LOGIC_COLUMNS =['IsExpense', 'AppliedRate', 'Cum_Budget_KRW', 'Cum_Card_Local', 'Cum_Cash_Local', 'Note']
FINAL_COLUMNS = CORE_COLUMNS + SYSTEM_LOGIC_COLUMNS

IMGBB_API_KEY = "81181bf834001b6191aaa90fa772c6f9"
BILLS =[500000, 200000, 100000, 50000, 20000, 10000, 5000, 2000, 1000]

# [Added] 마스터 설정 시트 상수 (기존 BILLS 아래에 삽입)
CONFIG_SHEET = "_GTL_CONFIG_"

# [Modified] 10분 동안 여행 설정 정보를 메모리에 보관 (API 호출 절감)
@st.cache_data(ttl=600)
def get_trip_configs():
    """구글 시트에서 모든 여행 설정 로드 (레거시 코드 제거 버전)"""
    try:
        cfg_df = conn.read(worksheet=CONFIG_SHEET, ttl="0s")
        if cfg_df is None or cfg_df.empty: 
            raise ValueError("Config sheet is empty")
    except Exception as e:
        # [Refactored] 이제 긴 데이터 리스트 대신 안내 메시지만 출력합니다.
        st.error(f"🚨 **관제탑 설정('{CONFIG_SHEET}')을 로드할 수 없습니다.**")
        st.info(f"💡 **해결 방법:** 구글 시트에 **'{CONFIG_SHEET}'** 탭이 있는지, 그리고 여행 설정 데이터가 들어있는지 확인해 주세요.")
        st.stop()
    
    dynamic_configs = {}
    for _, row in cfg_df.iterrows():
        # [Modified] 카테고리 로딩 시 공백 제거 및 유효성 검사 강화
        raw_cats = str(row['Categories']).replace("，", ",").split(",") # 전각 쉼표 대응
        cats = [c.strip() for c in raw_cats if c.strip()]
        
        dynamic_configs[str(row['TripName'])] = {
            "sheet": str(row['SheetName']),
            "nodes": {str(row['MainCountry']).strip(): {
                "currency": str(row['Currency']).strip(), 
                "symbol": str(row['Symbol']).strip(), 
                "timezone": int(row['Timezone']), 
                "multiplier": int(row['Multiplier'])
            }},
            "cats": cats
        }
    return dynamic_configs


# [Modified] 버전 및 업데이트 로그 v26.05.10.005
VERSION = "v26.05.10.005"

UPDATE_LOG_TEXT = """* `[Fixed]` 영수증 상세 뷰어의 Deep-Reader(자동 환산 엔진) 고도화. 용량/수량(ml, g, cm, 개 등)을 뜻하는 숫자는 무시하고, 실제 결제 금액(VND, USD 등)만 정확하게 선별하여 원화로 환산하도록 정규식(Regex) 논리 개선."""

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

# [Added] 하드코딩된 TRIP_CONFIGS를 동적 로더 결과로 덮어쓰기
TRIP_CONFIGS = get_trip_configs()

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

    # [Modified] 현존하는 모든 브라우저/버전에서 숫자 버튼을 강제로 지우는 CSS
    div[data-testid="stNumberInput"] button {
        display: none !important;
    }
    div[data-testid="stNumberInput"] input {
        padding-right: 10px !important;
    }
    div[data-testid="stNumberInput"] [data-baseweb="input"] {
        border-right-width: 1px !important;
    }
    
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

# [Module A] Data Engine (Modified)

def get_asset_class(text):    
    """결제 수단 명칭을 분석하여 자산 성격(CASH/PREPAID/CREDIT/DOMESTIC) 분류"""
    txt = str(text).replace(" ", "").upper()
    
    # [Modified] '충전', 'PAY', 'CARD' 등 카드 자산 키워드 강화
    if any(k in txt for k in ["트래블", "로그", "월렛", "카드", "CARD", "PAY", "WALLET", "충전"]): 
        return "PREPAID"
    
    if any(k in txt for k in ["현금", "지폐", "CASH", "환전"]): 
        return "CASH"
    
    if any(k in txt for k in ["외상", "부채", "CREDIT"]):
        return "CREDIT" 
        
    return "DOMESTIC"

### ⚙️[Logic: Rate Fallback] 평균 환율 동적 추론
def get_default_rate(curr):
    if curr == "KRW": return 1.0
    try:
        if 'ledger_df' in globals() and not ledger_df.empty:
            df_curr = ledger_df[(ledger_df['Currency'].str.strip() == curr) & (ledger_df['AppliedRate'] > 0)]
            if not df_curr.empty: return df_curr['AppliedRate'].mean()
    except: pass
    fallback_rates = {"VND": 0.056, "CNY": 190.0, "USD": 1350.0, "EUR": 1480.0, "TRY": 45.0, "RSD": 12.6, "HUF": 3.8}
    return fallback_rates.get(curr, 1.0)

### ⚙️ [Logic: API] ImgBB 영수증 업로드
def upload_image_to_imgbb(image_file):
    try:
        payload = {"key": IMGBB_API_KEY, "image": base64.b64encode(image_file.read()).decode("utf-8")}
        res = requests.post("https://api.imgbb.com/1/upload", data=payload)
        if res.status_code == 200: return res.json()['data']['url']
    except: pass
    return ""

### ⚙️[Logic: AI OCR - Vision] 구글 클라우드 비전 API 텍스트 추출 엔진 (눈)
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
                
        if "\\n" in secret_dict["private_key"]:
            secret_dict["private_key"] = secret_dict["private_key"].replace('\\n', '\n')
            
        credentials = service_account.Credentials.from_service_account_info(secret_dict)
        client = vision.ImageAnnotatorClient(credentials=credentials)
        image = vision.Image(content=image_bytes)
        response = client.text_detection(image=image)
        
        if response.error.message: return f"⚠️ [API 에러]: {response.error.message}"
        texts = response.text_annotations
        if texts: return texts[0].description
        return ""
    except ImportError: return "⚠️ [설정 오류] 'google-cloud-vision' 라이브러리가 없습니다."
    except Exception as e: return f"⚠️ [에러 발생]: {e}"

### ⚙️[Logic: AI LLM - Gemini] [Modified] 영수증 스마트 번역/요약 엔진 (뇌)
def summarize_receipt_with_gemini(raw_text):
    if not raw_text or "⚠️" in raw_text: return raw_text
    try:
        import google.generativeai as genai
        if "GEMINI_API_KEY" not in st.secrets:
            return raw_text + "\n\n(⚠️ Gemini API 키가 설정되지 않아 원본을 출력합니다.)"
        
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        
        prompt = """너는 다국어 영수증 전문 분석가야. 아래 주어진 영수증 텍스트에서 상호명, 주소, 전화번호, 세금(Tax), 날짜, 카드번호, 총액(Total) 등 불필요한 정보는 모두 버리고 오직 '소비한 품목'과 '가격'만 추출해.
지침:
1. 품목 이름은 무조건 '한국어'로 가장 자연스럽게 번역해 (예: CA PHE SUA DA -> 아이스 연유 커피).
2. 한국어 품목 이름 다음에 영문 품목이름을 넣어줘 (예: 후시코르트(Fucicort) 연고)
3. 품목의 주요특징을 요약해서 넣어줘 (예: (피부염/항생제, 15g))
4. 수량이 2개 이상일 때만 품목 이름 뒤에 '(X개)'라고 표시해 (예: 소고기 쌀국수 (2개) 120,000). 수량이 1개면 적지 마.
5. 가격 숫자는 베트남, 원화 등은 소수점 없이, 미국, 중국, 유로국가 등은 소수점 2자리까지 표기하고 화폐단위는 영문 3자리로 표기해 (예: 10,000 vnd, 10.00 usd, 10.00 eur)
6. 각 항목은 '품목명(영문) (특징, 용량) 가격' 형태로 한 줄씩 출력해. (예: 후시코르트(Fucicort) 연고 (피부염/항생제, 15g), 148,000)
7. 각 항목의 품목 이름에 주요 특징이 포함되어 있으면, 품목은 간단하게 표시하고, 특징을 중복해서 기록하지는 마. (예: 타이거밤(Tiger Balm) 통증 완화 파스 (통증 완화, 7x10cm) (3개) 156,000 vnd 라고 하지 말고, 타이거밤(Tiger Balm) 파스 (통증 완화, 7x10cm) (3개) 156,000 vnd 라고 해.)
8. 인사말이나 부연 설명은 절대 하지 말고 위 규칙에 맞춘 결과만 딱 출력해.

[영수증 텍스트]
""" + raw_text

        # [Modified] 모델명 버전 호환성 404 에러를 해결하는 다중 Fallback 로직 탑재 (최신 모델 반영)
        models_to_try =['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-flash-latest', 'gemini-pro-latest']
        last_error = ""
        
        for m_name in models_to_try:
            try:
                model = genai.GenerativeModel(m_name)
                response = model.generate_content(prompt)
                if response.text: return response.text.strip()
            except Exception as e:
                last_error = str(e)
                # 404(Not Found) 에러면 다음 모델 이름으로 재시도
                if "404" in str(e) or "not found" in str(e).lower(): continue
                break # 404가 아닌 다른 에러(키 오류 등)면 중단
                
        return raw_text + f"\n\n(⚠️ Gemini 요약 에러: {last_error})"
    except ImportError: return raw_text + "\n\n(⚠️ google-generativeai 라이브러리가 없어 원본 출력)"
    except Exception as e: return raw_text + f"\n\n(⚠️ Gemini 요약 에러: {e})"

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

### ⚙️ [Logic: DB Load] GSheet 데이터 로드 및 클리닝
# [Modified] 2분 동안 현재 장부 데이터를 메모리에 보관
@st.cache_data(ttl=120)
def load_data(sheet_name):
    try:
        # 인자로 받은 sheet_name을 사용하여 읽기
        df = conn.read(worksheet=sheet_name, ttl="0s")
        
        if df is None or df.empty: 
            df_init = pd.DataFrame(columns=FINAL_COLUMNS)
            try:
                # 텅 빈 시트에 14개 헤더를 강제로 주입합니다.
                conn.update(worksheet=ACTIVE_SHEET, data=df_init)
                st.info(f"✨ '{ACTIVE_SHEET}' 탭을 GTL 표준 양식으로 초기화했습니다.")
            except:
                pass # 권한 이슈 등으로 업데이트 실패 시 그냥 빈 DF 반환
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
        df['PaymentMethod'] = df['PaymentMethod'].astype(str).str.strip()
        df['Currency'] = df['Currency'].astype(str).str.strip()
        
        def fix_legacy_date(d):
            d = str(d).strip()
            if d and not re.match(r'^\d{4}', d): return f"{trip_year}-{d.replace('/', '-')}"
            return d

        df['Date'] = df['Date'].apply(fix_legacy_date)
        df['Date'] = df['Date'].apply(normalize_date)
        
        df = df.reindex(columns=FINAL_COLUMNS)
        
        # [Modified] 시스템 수치 컬럼 방어 로직 (글자가 들어있어도 숫자로 강제 변환)
        numeric_cols = ['Amount', 'AppliedRate', 'Cum_Budget_KRW', 'Cum_Card_Local', 'Cum_Cash_Local']
        for col in numeric_cols:
            if col in df.columns:
                # errors='coerce'를 통해 글자는 NaN으로 바꾸고, 다시 fillna(0)으로 숫자화함
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
        
        df['IsExpense'] = pd.to_numeric(df['IsExpense'], errors='coerce').fillna(0).astype(int)
        df['Note'] = df['Note'].fillna("").astype(str)
        
        df['Receipt_URL'] = df['Receipt_URL'].fillna("").astype(str)
        return df
    except Exception: return pd.DataFrame(columns=FINAL_COLUMNS)

### ⚙️[Logic: DB Load All] 모든 여행 가계부 로드 (조회 전용)
def load_all_trips_data():
    all_dfs =[]
    with st.spinner("🌍 모든 여행 기록을 불러오는 중..."):
        for trip_name, config in TRIP_CONFIGS.items():
            try:
                df_t = conn.read(worksheet=config['sheet'], ttl="0s")
                if df_t is None or df_t.empty: continue
                
                # [Modified] 여행 이름 정보 추가
                df_t['TripName'] = trip_name 
                
                first_node_name = list(config["nodes"].keys())[0]
                if 'Country' not in df_t.columns: df_t.insert(1, 'Country', first_node_name)
                else:
                    df_t['Country'] = df_t['Country'].astype(str).str.strip().fillna(first_node_name)
                
                all_dfs.append(df_t)
            except: continue
    if not all_dfs: return pd.DataFrame(columns=FINAL_COLUMNS + ['TripName'])
    return pd.concat(all_dfs, ignore_index=True)

### ⚙️[Logic: Core Calculation] 전체 원장 재계산 (DB 저장 전)
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
        
        # [Modified] 매칭 정확도를 높이기 위해 EXPENSE_CATS의 모든 항목에서도 공백을 제거하고 비교
        clean_expense_cats = [c.strip() for c in EXPENSE_CATS]
        is_exp = 1 if cat in clean_expense_cats and cat not in['환불', '보증금', '재환전', '상환'] else 0
        temp_df.at[i, 'IsExpense'] = is_exp
        
        # [Modified] '상환'도 인벤토리 차감(Deductible) 대상에 포함 (실제 돈이 나가므로)
        is_deductible = 1 if (is_exp == 1 or cat in ['보증금', '상환']) else 0
        
        rate = temp_df.at[i, 'AppliedRate'] 
        asset_cls = get_asset_class(method)
        
        if cat in['충전', '환전', '입금', '직접환전']:
            if curr != 'KRW' and (pd.isna(rate) or rate <= 0.0 or rate == 1.0): rate = get_default_rate(curr)
            
            # [Modified] 자산 분류 로직
            if cat == '충전':
                final_dest_cls = "PREPAID"
            elif cat in ['환전', '직접환전']:
                final_dest_cls = "CASH"
            else:
                final_dest_cls = get_asset_class(desc + method)

            target = f"트래블로그({curr})" if final_dest_cls == "PREPAID" else f"현금({curr})"
            
            if curr != 'KRW': inv_batches[target].append({'rate': rate, 'qty': qty})
            
            # [Modified] 예산(c_budget) 합산 조건 강화
            # 카테고리가 '충전'이거나 결제수단이 '국내자산'이면 예산으로 합산
            if asset_cls == "DOMESTIC" or cat == '충전': 
                c_budget += qty if curr == 'KRW' else qty * rate
        
             
        elif cat == '환불':
            # [Modified] 보증금 환율 자동 계승 엔진 (Dan's Constitution Rule)
            if curr != 'KRW' and (pd.isna(rate) or rate <= 1.0):
                inherited_rate = None
                # 현재 행(i)부터 역방향으로 가장 최근의 '보증금' 데이터 탐색
                for j in range(i - 1, -1, -1):
                    prev_cat = str(temp_df.at[j, 'Category']).strip()
                    prev_curr = str(temp_df.at[j, 'Currency']).strip()
                    # 같은 통화의 보증금 항목을 찾으면 환율을 계승
                    if prev_cat == '보증금' and prev_curr == curr:
                        inherited_rate = temp_df.at[j, 'AppliedRate']
                        break
                
                if inherited_rate and inherited_rate > 0:
                    rate = inherited_rate
                    temp_df.at[i, 'Note'] = f"Inherited Deposit Rate: {rate:.9f}"
                else:
                    rate = get_default_rate(curr)
            
            if asset_cls == "DOMESTIC": c_budget -= qty if curr == 'KRW' else qty * rate 
            else:
                target = f"트래블로그({curr})" if asset_cls == "PREPAID" else f"현금({curr})"
                if curr != 'KRW': inv_batches[target].append({'rate': rate, 'qty': qty})
                
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
                if pd.notna(rate) and rate > 0: c_budget -= qty * rate
        
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
                # [Added/Modified] 외상(CREDIT) 자산일 경우 물리적 주머니를 건드리지 않음
                if asset_cls == "CREDIT":
                    # [Modified] 외상은 인벤토리를 타지 않으므로 가중평균환율(WAR)을 적용해 평단을 맞춤
                    rate = get_WAR(curr)
                    temp_df.at[i, 'Note'] = "Credit (Debt Generated)"
                else:
                    target = f"트래블로그({curr})" if asset_cls == "PREPAID" else f"현금({curr})"
                    temp_qty = qty; total_cost_krw = 0.0; decomposed =[]


                    
                    if target in inv_batches:
                        for batch in inv_batches[target]:
                            if temp_qty <= 0: break
                            if batch['qty'] <= 0: continue
                            take = min(temp_qty, batch['qty']); batch['qty'] -= take; temp_qty -= take
                            total_cost_krw += take * batch['rate']
                            
                            # [Modified] VND/PHP/HUF는 환율 4자리, 금액은 정수(콤마) 표시
                            r_prec = ".4f" if curr in ["VND", "HUF", "PHP"] else ".2f"
                            q_fmt = ",.0f" if curr in ["VND", "HUF"] else ",.2f"
                            decomposed.append(f"{take:{q_fmt}}@{batch['rate']:{r_prec}}")

                    # [Modified] 부족분(자동충전) 발생 시에도 동일 포맷 적용
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
        rnd_dec = 0 if row_curr in["VND", "HUF", "KRW"] else 2
        
        temp_df.at[i, 'AppliedRate'] = rate
        temp_df.at[i, 'Cum_Budget_KRW'] = round(c_budget, 2)
        temp_df.at[i, 'Cum_Card_Local'] = round(sum([b['qty'] for b in inv_batches[f"트래블로그({row_curr})"]]), rnd_dec)
        temp_df.at[i, 'Cum_Cash_Local'] = round(sum([b['qty'] for b in inv_batches[f"현금({row_curr})"]]), rnd_dec)
        
    return temp_df

### ⚙️[Logic: DB Save] 구글 시트 동기화
# [Modified] 저장할 때는 최신 데이터를 반영해야 하므로 캐시를 즉시 삭제
def save_data(df, metrics=None):
    if df is None or len(df) == 0: return False
    # 저장 직전 캐시 삭제
    st.cache_data.clear() 
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

ledger_df = load_data(ACTIVE_SHEET)

# ==============================================================================
# --- SECTION 3:[Module B] URDI Engine ---
# ==============================================================================
### ⚙️[Logic: URDI Engine] 인벤토리 잔고 추적
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
        elif (row['IsExpense'] == 1 or cat in['보증금', '재환전']) and curr != 'KRW':
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

### ⚙️[Logic: URDI Engine] 가중 평균 환율(WAR) 및 FIFO 환율 계산
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
    available_batches =[b for b in temp_inv[target] if b['qty'] > 0]
    if not available_batches: return get_WAR(curr)
    total_cost_krw, remaining = 0.0, amount
    for batch in available_batches:
        if remaining <= 0: break
        take = min(remaining, batch['qty']); total_cost_krw += take * batch['rate']; remaining -= take
    if remaining > 0: total_cost_krw += remaining * available_batches[-1]['rate']
    return total_cost_krw / amount if amount > 0 else 0

### ⚙️[Logic: Metrics] 대시보드 지표 추출
def calculate_summary_metrics(df):
    if df.empty: return 0.0, 0.0
    temp_df = df.sort_values(by='Date', kind='mergesort', ignore_index=True)
    b_total = temp_df['Cum_Budget_KRW'].iloc[-1] if 'Cum_Budget_KRW' in temp_df.columns else 0
    gross_spent = temp_df[temp_df['IsExpense'] == 1].apply(lambda r: r['Amount'] if str(r['Currency']).strip() == 'KRW' else r['Amount'] * r['AppliedRate'], axis=1).sum()
    expense_refunds = temp_df[(temp_df['Category'] == '환불') & (temp_df['PaymentMethod'].apply(get_asset_class) == 'DOMESTIC')]
    refund_total = expense_refunds.apply(lambda r: r['Amount'] if str(r['Currency']).strip() == 'KRW' else r['Amount'] * r['AppliedRate'], axis=1).sum()
    return b_total, gross_spent - refund_total

# ==============================================================================
# --- SECTION 4: [Sidebar] UI & Dashboard ---
# ==============================================================================
### 🎨 [GUI: Layout] 사이드바 영역
with st.sidebar:
    st.subheader("💰 지갑 잔고")
    b_val, spent_val = calculate_summary_metrics(ledger_df)
    
    active_currs = set([k.split('(')[1].replace(')','') for k in current_inventory_batches.keys() if len(current_inventory_batches[k]) > 0 and sum(b['qty'] for b in current_inventory_batches[k]) > 0])
    trip_currs = set(node['currency'] for node in TRIP_CONFIGS[st.session_state.current_trip]["nodes"].values())
    display_currs = sorted(list(active_currs | trip_currs))
    
    ### 📊 [GUI: Chart/Table] 통화별 잔고 표시
    for c in display_currs:
        if c == "KRW": continue

        # [Modified] NameError 방지: fmt 정의를 루프 최상단으로 이동
        fmt = "{:,.2f}" if c not in["VND", "HUF", "PHP"] else "{:,.0f}"

        # [Added] 외상(Debt) 잔액 계산 및 표시
        debt_amt = ledger_df[(ledger_df['Currency']==c) & (ledger_df['PaymentMethod'].str.contains("외상|부채|CREDIT", na=False))]['Amount'].sum()
        repay_amt = ledger_df[(ledger_df['Currency']==c) & (ledger_df['Category']=="상환")]['Amount'].sum()
        current_debt = debt_amt - repay_amt
        
        if current_debt > 0:
            st.markdown(f"<div style='color:#FF4B4B; font-size:14px;'>📌 <b>미결제 외상: {fmt.format(current_debt)}</b></div>", unsafe_allow_html=True)
        
        c_card = sum([b['qty'] for b in current_inventory_batches.get(f"트래블로그({c})",[])])
        c_cash = sum([b['qty'] for b in current_inventory_batches.get(f"현금({c})",[])])
        
        if c_card > 0 or c_cash > 0 or c in trip_currs:
            st.markdown(f"<div style='color:#FFA500; font-weight:bold; margin-top:14px; margin-bottom:12px;'>● {c}</div>", unsafe_allow_html=True)
            st.markdown(f"💳 카드: **{fmt.format(c_card)}**")
            st.markdown(f"<div style='margin-bottom:18px;'>💵 현금: **{fmt.format(c_cash)}**</div>", unsafe_allow_html=True) 
            
            card_batches = current_inventory_batches.get(f"트래블로그({c})", [])
            cash_batches = current_inventory_batches.get(f"현금({c})", [])
            
            if any(b['qty'] > 0 for b in (card_batches + cash_batches)):
                with st.expander("🔍 상세 배치", expanded=False):
                    # [Added] 통화별 환율 표시 정밀도 결정
                    r_fmt = ".4f" if c in ["VND", "HUF"] else ".2f"
                    
                    if any(b['qty'] > 0 for b in card_batches):
                        st.caption("[카드]")
                        for b in card_batches:
                            # [Modified] 하드코딩된 :.1f를 동적 r_fmt로 변경
                            if b['qty'] > 0: 
                                st.caption(f"• {fmt.format(b['qty'])} @{b['rate']:{r_fmt}}")
                                
                    if any(b['qty'] > 0 for b in cash_batches):
                        st.caption("[현금]")
                        for b in cash_batches:
                            # [Modified] 하드코딩된 :.1f를 동적 r_fmt로 변경
                            if b['qty'] > 0: 
                                st.caption(f"• {fmt.format(b['qty'])} @{b['rate']:{r_fmt}}")
            st.divider()

    ### 📊 [GUI: Chart/Table] 예산 및 지출 총액 요약
    st.markdown("<div style='margin-top:35px;'></div>", unsafe_allow_html=True)
    st.metric("🏦 총 예산", f"{b_val:,.0f} 원")
    st.metric("💸 지출총액", f"{spent_val:,.0f} 원")

    st.divider()
    ### 🎛️[GUI: Component] 타임존 및 새로고침
    st.markdown("<div style='margin-top:35px;'></div>", unsafe_allow_html=True)
    tz_sel = st.radio("📍 기준 시간 (Timezone)",["🇰🇷 한국 시간", "🌍 여행지 현지 시간"], horizontal=True, index=0 if "한국" in str(st.session_state.current_tz) else 1)
    st.session_state.current_tz = TZ_KST if "한국" in tz_sel else TRIP_TZ

    st.markdown("<div style='margin-top:35px;'></div>", unsafe_allow_html=True)
    if st.button("🔄 Cloud Refresh", use_container_width=True): st.cache_data.clear(); st.rerun()

# ==============================================================================
# --- SECTION 5: [Module C] Intelligent Input (📝 입력) ---
# ==============================================================================
st.title(f"{st.session_state.current_trip}")

# [Modified] 여행 목록을 연도별 최신순으로 정렬하여 드롭다운 생성
# 1. 정렬된 여행 이름 리스트 생성
def sort_trips(trip_names):
    # 이름에서 (2025) 같은 연도를 찾아 숫자로 변환, 없으면 0으로 처리
    return sorted(trip_names, 
                  key=lambda x: (re.search(r'\((\d{4})\)', x).group(1) if re.search(r'\((\d{4})\)', x) else '0000', x), 
                  reverse=True)

sorted_trips = sort_trips(list(TRIP_CONFIGS.keys()))

### 🎨[GUI: Layout] 메인 화면 상단 여행 선택 영역
c_trip_top, c_empty = st.columns([2, 2])
with c_trip_top:
    ### 🎛️ [GUI: Component] 여행 선택 드롭다운 (정렬된 리스트 적용)
    sel_trip = st.selectbox("✈️ 내 여행함 (Trip Selector)", sorted_trips, 
                             index=sorted_trips.index(st.session_state.current_trip) if st.session_state.current_trip in sorted_trips else 0,
                             label_visibility="collapsed")
    if sel_trip != st.session_state.current_trip:
        st.session_state.current_trip = sel_trip; st.rerun()

st.divider() 

### 🎨 [GUI: Layout] 5대 핵심 탭 컨테이너[Modified]
tab_in, tab_his, tab_stats, tab_final, tab_nav = st.tabs(["📝 입력", "🔍 조회", "📊 일일", "🏁 요약", "🧭 비교"])

with tab_in:
    ### 🎨 [GUI: Layout] 입력 탭 최상단 옵션 (국가/모드)
    c_node, c_mode = st.columns([1, 2])
    with c_node:
        ### 🎛️ [GUI: Component] 국가 선택
        sel_node = st.selectbox("🌍 국가 선택", list(TRIP_CONFIGS[st.session_state.current_trip]["nodes"].keys()), key="in_country")
        IN_CFG = TRIP_CONFIGS[st.session_state.current_trip]["nodes"][sel_node]
        IN_CURR = IN_CFG["currency"]
        IN_MULTI = IN_CFG["multiplier"]
    with c_mode:
        ### 🎛️ [GUI: Component] 기록 모드 선택기 (출입국 삭제됨)
        mode = st.radio("기록 모드 선택",["일반 지출", "🛫 항공권(특수)", "🏨 호텔(특수)", "자산 이동", "환불(취소)"], horizontal=True, key="mode_radio", label_visibility="collapsed")
    
    ### 🎛️ [GUI: Component] 날짜 입력
    dynamic_tz = timezone(timedelta(hours=IN_CFG["timezone"])) if "한국" not in str(st.session_state.current_tz) else TZ_KST
    sel_date = st.date_input("날짜 선택", value=datetime.now(dynamic_tz).date(), key="shared_date_input")
    available_currs = sorted(list(set(node["currency"] for node in TRIP_CONFIGS[st.session_state.current_trip]["nodes"].values())))

    # ------------------------------------------------------------------
    #[Mode 1: 일반 지출]
    # ------------------------------------------------------------------
    if mode == "일반 지출":        
        ### 🎛️[GUI: Component] 지출 카테고리
        def_index = EXPENSE_CATS.index(st.session_state.last_cat_name) if st.session_state.last_cat_name in EXPENSE_CATS else 0
        cat = st.radio("항목 선택", EXPENSE_CATS, index=def_index, horizontal=True, key="exp_cat")
        st.session_state.last_cat_name = cat
        
        # [Fixed] 안전한 메모칸 초기화 로직
        if st.session_state.get('clear_exp_desc', False):
            st.session_state.exp_desc = ""
            st.session_state.clear_exp_desc = False
            
        ### 🎨[GUI: Layout] 세부내역 및 영수증 업로드 (OCR 지원)
        col_desc, col_receipt = st.columns([3, 1])
        
        with col_receipt: 
            # [Modified] 다중 파일 업로드 허용 (accept_multiple_files=True)
            uploaded_files = st.file_uploader("📸 영수증 첨부 (다중 가능)", type=['png', 'jpg', 'jpeg'], key="exp_receipt", accept_multiple_files=True)
            
            if uploaded_files:
                if st.button("🤖 영수증 AI 스캔 (통합 번역)", use_container_width=True):
                    with st.spinner(f"AI가 {len(uploaded_files)}장의 사진을 분석 중..."):
                        all_raw_texts = []
                        for file in uploaded_files:
                            # 각 사진에서 텍스트 추출 (눈)
                            raw_text = extract_text_from_vision_api(file.getvalue())
                            all_raw_texts.append(raw_text)
                        
                        # 모든 텍스트를 하나로 합쳐서 AI 요약 (뇌)
                        combined_text = "\n---\n".join(all_raw_texts)
                        smart_text = summarize_receipt_with_gemini(combined_text)
                        
                        if smart_text:
                            st.session_state.exp_desc = st.session_state.get('exp_desc', '') + "\n" + smart_text
                            st.rerun()
                            
        with col_desc: 
            desc = st.text_area("📝 내용 (상호명 및 다중 내역)", placeholder="예: 안바카페 - 소고기버거\n반미정식\n(사진을 스캔하면 AI가 한국어로 번역하여 적어줍니다)", height=120, key="exp_desc")
            
        ### 🎨 [GUI: Layout] 통화/수단/게이트웨이
        col_m1, col_m2, col_m3 = st.columns([1, 1, 1])
        with col_m1: 
            ### 🎛️[GUI: Component] 통화 선택
            curr_opts =[IN_CURR, "KRW", "USD"] +[c for c in available_currs if c not in[IN_CURR, "KRW", "USD"]]
            curr = st.selectbox("통화", curr_opts, key="exp_curr")
        with col_m2:
            ### 🎛️ [GUI: Component] 결제 자산 수단
            if curr != "KRW":
                # [Modified] 현금, 카드 외에 '호텔외상' 옵션을 동적으로 추가
                met_options = [f"현금({curr})", f"트래블로그({curr})", f"호텔외상({curr})", "원화계좌(한국)", "원화계좌(현지)"]
            else:
                met_options = ["원화계좌(한국)", "원화계좌(현지)"]
            
            met = st.selectbox("결제 자산(Asset)", met_options, index=0, key="exp_met")
            
        with col_m3:
            ### 🎛️ [GUI: Component] 게이트웨이(결제플랫폼) 선택
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

        ### 🎨[GUI: Layout] 금액 및 환율 설정 영역
        col_a1, col_a2 = st.columns(2)
        with col_a1:
            ### 🎛️ [GUI: Component] 금액 입력
            if curr == "KRW" or (curr == IN_CURR and IN_MULTI == 100):
                amt = st.number_input(f"금액 ({curr})", min_value=0, step=1000 if curr != "KRW" else 1, format="%d", key="exp_amt_int")
            else:
                amt = st.number_input(f"금액 ({curr})", min_value=0.0, step=1.0, format="%.2f", key="exp_amt_float")
        with col_a2:
            ### 🎛️ [GUI: Component] 환율 조율 (FIFO 자동 표시)
            if curr != "KRW" and amt > 0:
                calc_rate = auto_calc_fifo_rate(amt, met, curr)
                st.caption(f"💡 {curr} 인벤토리 계산 환율: **{calc_rate:.5f}**")
                cr_final = st.number_input("확정 환율", value=float(calc_rate), format="%.5f", key=f"exp_cr_auto_{met}_{amt}")
            else: cr_final = st.number_input("확정 환율", value=(1.0 if curr=="KRW" else get_default_rate(curr)), format="%.5f", key=f"exp_cr_man_{curr}")
            
        ### 🎛️ [GUI: Component] 최종 기록 버튼 및 ⚙️[Logic: DB Save]
        if st.button("🚀 지출 기록하기", use_container_width=True):
            # [Added] 다중 URL 처리 로직
            final_receipt_urls = ""
            if uploaded_files:
                with st.spinner("📸 모든 영수증을 클라우드에 보관 중..."):
                    url_list = []
                    for file in uploaded_files:
                        u = upload_image_to_imgbb(file)
                        if u: url_list.append(u)
                    final_receipt_urls = ",".join(url_list) # 쉼표로 구분하여 저장
            
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
                'Receipt_URL': final_receipt_urls # [Modified] 통합된 URL 저장
            }])
            if save_data(pd.concat([ledger_df, new_row], ignore_index=True)): 
                st.session_state.clear_exp_desc = True
                st.rerun()

    # ------------------------------------------------------------------
    # [Mode: 🛫 항공권(특수)]
    # ------------------------------------------------------------------
    elif mode == "🛫 항공권(특수)":
        st.subheader("✈️ 항공권 및 스케줄 통합 기록")
        
        # 1층: 기본 정보 (왼쪽에서 오른쪽으로 1, 2, 3 순서)
        c1, c2, c3 = st.columns(3)
        with c1: f_gw = st.text_input("1. 결제 플랫폼 (필수)", placeholder="예: 트립닷컴")
        with c2: f_carrier = st.text_input("2. 항공사", placeholder="예: 비엣젯")
        with c3: f_route = st.text_input("3. 노선", placeholder="예: 부산-푸꾸옥")

        # 2층: 출국 및 입국 스케줄
        c4, c5 = st.columns(2)
        with c4:
            st.info("🛫 출국 스케줄")
            f_dep_info = st.text_input("4. 출국편 정보", placeholder="예: VJ969, 07:45 - 11:10")
            f_dep_date = st.date_input("5. 출국 날짜", value=sel_date)
        with c5:
            st.success("🛬 입국 스케줄")
            f_ret_info = st.text_input("6. 귀국편 정보", placeholder="예: VJ968, 23:10 - 06:40 (+1)")
            f_ret_date = st.date_input("7. 입국 날짜", value=sel_date + timedelta(days=7))

        # 3층: 수화물 및 결제수단
        c6, c7, c8 = st.columns([1, 2, 1])
        with c6: f_baggage = st.selectbox("8. 위탁수화물", ["포함", "미포함", "일부포함"])
        with c7: f_bag_memo = st.text_input("9. 수화물 상세 메모", placeholder="예: 귀국편 20kg 추가")
        with c8: f_asset = st.selectbox("10. 결제 수단", ["네이버페이(원화고정)", "원화계좌(한국)", "트래블로그(VND)", "현대카드"])

        # 4층: 금액 및 환율 (한 줄로 배치)
        st.divider()
        c9, c10, c11, c12 = st.columns([1, 2, 1, 1])
        with c9: f_curr = st.selectbox("11. 통화", ["KRW", "VND", "USD", "PHP"])
        with c10: f_amt = st.number_input(f"12. 결제 금액({f_curr})", min_value=0.0, step=1.0)
        with c11: f_rate = st.number_input("13. 환율", value=1.0 if f_curr=="KRW" or "네이버" in f_asset else get_default_rate(f_curr), format="%.4f")
        with c12: f_fee = st.number_input("14. 수수료(원)", min_value=0)

        if st.button("🚀 항공권 및 출입국 일정 동시 기록", use_container_width=True, type="primary"):
            if not f_gw or not f_route:
                st.warning("결제 플랫폼과 노선 정보는 필수입니다."); st.stop()
            
            # [Refined] 결제수단 이름 정제 (예: 네이버페이(원화고정) -> 네이버페이)
            clean_asset = f_asset.split('(')[0].strip()
            
            # 1. 항공권 메인 기록 (데이터 누락 방지)
            full_desc = f"[{f_gw}+{clean_asset}] {f_route}({f_carrier}) | 출국:{f_dep_info} | 귀국:{f_ret_info} | 수화물:{f_baggage}({f_bag_memo})"
            flight_row = pd.DataFrame([{'Date': sel_date.strftime("%Y-%m-%d(%a)"), 'Country': sel_node, 'Category': '항공권', 'Description': full_desc, 'Currency': f_curr, 'Amount': f_amt, 'PaymentMethod': f_asset, 'IsExpense': 1, 'AppliedRate': f_rate, 'Note': f"수수료:{f_fee}원" if f_fee > 0 else ""}])
            
            # 2. 출입국 일정 자동 기록 (정보 보존)
            dep_desc = f"🛫 {f_route} 출국 ({f_dep_info})"
            arr_desc = f"🛬 {f_route} 입국 ({f_ret_info})"
            
            dep_row = pd.DataFrame([{'Date': f_dep_date.strftime("%Y-%m-%d(%a)"), 'Country': sel_node, 'Category': '출국', 'Description': dep_desc, 'Currency': 'KRW', 'Amount': 0, 'PaymentMethod': '정보', 'IsExpense': 0, 'AppliedRate': 1.0, 'Note': 'Auto-created'}])
            arr_row = pd.DataFrame([{'Date': f_ret_date.strftime("%Y-%m-%d(%a)"), 'Country': sel_node, 'Category': '입국', 'Description': arr_desc, 'Currency': 'KRW', 'Amount': 0, 'PaymentMethod': '정보', 'IsExpense': 0, 'AppliedRate': 1.0, 'Note': 'Auto-created'}])
            
            if save_data(pd.concat([ledger_df, flight_row, dep_row, arr_row], ignore_index=True)):
                st.success("항공권과 출입국 일정이 모두 기록되었습니다!"); time.sleep(1); st.rerun()
                
    # ------------------------------------------------------------------
    # [Mode: 🏨 호텔(특수)]
    # ------------------------------------------------------------------
    elif mode == "🏨 호텔(특수)":
        st.subheader("🏨 호텔/숙소 예약 상세 기록")
        c1, c2 = st.columns(2)
        with c1:
            h_gw = st.text_input("1. 결제 플랫폼 (필수)", placeholder="예: Agoda, Booking.com")
            h_name = st.text_input("2. 호텔명", placeholder="예: 인터콘티넨털 호치민")
            h_checkin = st.date_input("3. 체크인", value=sel_date)
            h_asset = st.selectbox("4. 결제 수단", ["네이버페이(원화고정)", "원화계좌(한국)", "트래블로그(VND)", "현대카드"])
        with c2:
            h_nights = st.number_input("5. 숙박 일수", min_value=1, step=1)
            h_checkout = h_checkin + timedelta(days=h_nights)
            st.caption(f"📅 체크아웃 예정: {h_checkout.strftime('%Y-%m-%d')}")
            h_detail = st.text_area("6. 내용 (룸타입/특징)", placeholder="예: 디럭스 더블, 수영장뷰, 30m2", height=68)
            h_curr = st.selectbox("7. 결제 통화", ["KRW", "VND", "USD", "PHP"], key="h_curr")

        c3, c4, c5 = st.columns(3)
        with c3: h_amt = st.number_input(f"8. 결제 금액({h_curr})", min_value=0.0, step=1.0)
        with c4: h_rate = st.number_input("9. 적용 환율", value=1.0 if h_curr=="KRW" or "네이버" in h_asset else get_default_rate(h_curr), format="%.4f")
        with c5: h_fee = st.number_input("10. 환율 수수료(원)", min_value=0)

        if st.button("🚀 호텔 예약 저장", use_container_width=True):
            if not h_gw: st.warning("결제 플랫폼을 입력하세요."); st.stop()
            full_desc = f"[{h_gw}] {h_name} | {h_nights}박({h_checkin.strftime('%m/%d')}~{h_checkout.strftime('%m/%d')}) | {h_detail.replace('\\n', ' ')}"
            new_row = pd.DataFrame([{'Date': sel_date.strftime("%Y-%m-%d(%a)"), 'Country': sel_node, 'Category': '호텔', 'Description': full_desc, 'Currency': h_curr, 'Amount': h_amt, 'PaymentMethod': h_asset, 'IsExpense': 1, 'AppliedRate': h_rate, 'Note': f"수수료:{h_fee}원" if h_fee > 0 else ""}])
            if save_data(pd.concat([ledger_df, new_row], ignore_index=True)): st.rerun()
                
    # ------------------------------------------------------------------
    #[Mode 2: 자산 이동 및 환전]
    # ------------------------------------------------------------------
    elif mode == "자산 이동":
        st.subheader("🔁 자산 이동 및 환전")
        ### 🎛️[GUI: Component] 자산 이동 유형
        ty = st.selectbox("유형",["직접환전 (원화계좌 -> 지폐)", "충전 (원화계좌 -> 카드)", "ATM출금 (카드 -> 지폐)", "재환전 (외화 -> 원화계좌)"], key="tr_type")
        c1, c2 = st.columns(2)
        
        #[재환전 (외화 매도) 프로세스]
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
                        
            ### 🎛️ [GUI: Component] 재환전 기록 버튼
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
                
        #[일반 자산 이동 (충전, 환전, ATM)]
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
                    # 원금 입력칸을 삭제하고, 계산된 결과를 정보 메시지로 보여줍니다.
                    st.success(f"💰 인출로 소모되는 원화 가치: **{(t_amt * inherited_r):,.0f} 원**")
                    applied_tr_rate = inherited_r
                else:
                    s_cost = st.number_input("소요 원금 (KRW)", min_value=0, step=1, format="%d", key="tr_source_swap")
                    applied_tr_rate = s_cost / t_amt if t_amt > 0 else 0
            with c2:
                if curr_tr == IN_CURR and IN_MULTI == 100:
                    fee_amt = st.number_input(f"ATM 수수료 ({curr_tr})", min_value=0, step=1000, format="%d", key="tr_fee_int")
                else:
                    fee_amt = st.number_input(f"ATM 수수료 ({curr_tr})", min_value=0.0, step=1.0, format="%.2f", key="tr_fee_flt")
                    
            ### 🎛️ [GUI: Component] 이동 기록 버튼
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

    # ------------------------------------------------------------------
    #[Mode 3: 환불 및 취소 롤백]
    # ------------------------------------------------------------------
    elif mode == "환불(취소)":
        st.subheader("🔙 결제 취소 및 환불 (Rollback)")
        ### 🎨 [GUI: Layout] 환불 정보 입력부
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
            
        ### 🎛️[GUI: Component] 환불 롤백 실행 버튼
        if st.button("🔙 환불 인벤토리 롤백 실행", use_container_width=True):
            new_row = pd.DataFrame([{'Date': sel_date.strftime("%Y-%m-%d(%a)"), 'Country': sel_node, 'Category': '환불', 'Description': f"취소: {r_desc}", 'Currency': r_curr, 'Amount': r_amt, 'PaymentMethod': r_met, 'IsExpense': 0, 'AppliedRate': r_rate, 'Note': 'Rollback', 'Receipt_URL': ''}])
            if save_data(pd.concat([ledger_df, new_row], ignore_index=True)): st.rerun()

    # ------------------------------------------------------------------
    #[Mode 4: 출입국 일정 기록]
    # ------------------------------------------------------------------
    else:
        st.subheader("✈️ 출입국 일정 기록")
        io_type = st.radio("구분",["출국", "입국"], horizontal=True, key="io_radio")
        io_desc = st.text_input("내용 (메모)", placeholder="편명, 시간 등", key="io_desc_input")
        if st.button("🚀 일정 기록 완료", use_container_width=True):
            new_row = pd.DataFrame([{'Date': sel_date.strftime("%Y-%m-%d(%a)"), 'Country': sel_node, 'Category': io_type, 'Description': io_desc, 'Currency': 'KRW', 'Amount': 0, 'PaymentMethod': '원화계좌(한국)', 'IsExpense': 1, 'AppliedRate': 1.0, 'Note': '', 'Receipt_URL': ''}])
            if save_data(pd.concat([ledger_df, new_row], ignore_index=True)): st.rerun()

    # [Added] 새 여행지 개설 UI (중복 제거된 단일 블록)
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.divider()
    with st.expander("➕ 새로운 여행지 개설 (GTL Provisioning)", expanded=False):
        st.subheader("🌍 새로운 여행지 설계")
        new_t_name = st.text_input("1. 여행 이름", placeholder="예: 🇨🇿 프라하 2027")
        new_s_name = st.text_input("2. 시트 이름 (영문/숫자만)", placeholder="예: PRG_2027")
        
        c_p1, c_p2, c_p3 = st.columns(3)
        with c_p1:
            new_curr = st.text_input("통화 코드", value="USD", key="prov_curr_final")
            new_sym = st.text_input("통화 기호", value="$", key="prov_sym_final")
        with c_p2:
            new_mult = st.selectbox("환율 배율", [1, 100], index=0, key="prov_mult_final")
            new_tz = st.number_input("현지 시차", value=9, key="prov_tz_final")
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
                    st.success(f"🎉 '{new_t_name}' 여행지가 개설되었습니다!")
                    st.cache_data.clear(); time.sleep(1); st.rerun()
                except:
                    st.warning(f"탭 '{new_s_name}'을 수동으로 생성해 주세요.")
                    st.cache_data.clear(); time.sleep(2); st.rerun()

# ==============================================================================
# --- SECTION 6: [Module D] History & Edit (🔍 조회 탭) ---
# ==============================================================================
with tab_his:
    st.info("💡 **표의 행(Row)을 클릭(터치)하시면 바로 아래에 상세 내역 수정과 영수증 첨부 화면이 펼쳐집니다!**")
    
    ### 🎨 [GUI: Layout] 뷰어 플레이스홀더
    viewer_placeholder = st.empty()
    
    ### 🎨[GUI: Layout] 상단 검색 및 필터부
    c_filter, c_search, c_tog = st.columns([2, 3, 1])
    with c_filter:
        ### 🎛️ [GUI: Component] 여행/국가 필터
        filter_options =["모든 여행가계부", "이번 여행가계부"] + list(TRIP_CONFIGS[st.session_state.current_trip]["nodes"].keys())
        country_filter = st.selectbox("🌍 국가 필터", filter_options, index=1, key="his_country")
    with c_search: 
        ### 🎛️ [GUI: Component] 검색 바
        search_query = st.text_input("🔎 검색어 입력", placeholder="상호명, 메모, 카테고리 등", key="his_search", label_visibility="collapsed")
    with c_tog: 
        ### 🎛️ [GUI: Component] 전체 편집 모드 토글
        edit_mode = st.toggle("✏️ 직접 수정 모드", value=False, key="his_edit_toggle")

    ### ⚙️ [Logic: DB Filter] 필터 데이터 로드
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
        
        #[Mode 1: 직접 수정 모드 (Data Editor)]
        if edit_mode:
            edited_df = st.data_editor(display_df, use_container_width=True, num_rows="dynamic", key="editor_gtl_final", column_config={"Receipt_URL": link_cfg})
            if not display_df.equals(edited_df) and st.button("💾 데이터베이스 수정사항 저장", use_container_width=True):
                if save_data(edited_df): st.rerun()
                
        #[Mode 2 & 3 통합: 검색 결과 및 기본 조회 모드]
        else:
            if search_query.strip():
                mask = (
                    display_df['Category'].str.contains(search_query, case=False, na=False) | 
                    display_df['Description'].str.contains(search_query, case=False, na=False) | 
                    display_df['Note'].str.contains(search_query, case=False, na=False) |
                    display_df['Country'].str.contains(search_query, case=False, na=False) 
                )
                render_df = display_df[mask]
                st.write(f"🔎 검색 결과: {len(render_df)}건")
            else:
                render_df = display_df
                
            ### 📊[GUI: Chart/Table] 메인 데이터 그리드 표
            df_event = st.dataframe(render_df, use_container_width=True, column_config={"Receipt_URL": link_cfg}, selection_mode="single-row", on_select="rerun")
            
            #[행 클릭 시 상세 뷰어 표시 로직]
            if df_event.selection.rows:
                selected_idx = df_event.selection.rows[0]
                real_idx = render_df.index[selected_idx] 
                row_data = display_df.loc[real_idx]
                
                with viewer_placeholder.container():
                    st.markdown("---")
                    ### 🎨[GUI: Layout] 뷰어 좌우 2단 분할
                    c_info, c_edit = st.columns([1, 1])
                    
                    with c_info:
                        ### 🎨[GUI: Layout] 좌측: 뷰어 화면
                        st.subheader("🧾 상세 내역 및 영수증 뷰어")
                        amt_fmt2 = "{:,.2f}" if MULTIPLIER == 1 and row_data['Currency'] != 'KRW' else "{:,.0f}"

                        krw_equivalent = row_data['Amount'] if row_data['Currency'] == 'KRW' else row_data['Amount'] * row_data['AppliedRate']
                        krw_display = f" ➔ <span style='color:#FFD700'>약 {krw_equivalent:,.0f} 원</span>" if row_data['Currency'] != 'KRW' else ""
                        
                        st.markdown(f"### 🛒 {row_data['Category']} ({amt_fmt2.format(row_data['Amount'])} {row_data['Currency']}{krw_display})", unsafe_allow_html=True)
                        st.markdown(f"**🏦 결제수단:** {row_data['PaymentMethod']}")
                        
                        # [Modified] ⚙️ 딥-리더 (Deep-Reader) 자동 환산 엔진 고도화
                        def smart_krw_translator(text, rate, curr):
                            if rate <= 0 or curr == 'KRW': return text
                            def replacer(match):
                                num_str = match.group(1).replace(',', '')
                                suffix = match.group(2).lower() if match.group(2) else ""
                                try:
                                    v = float(num_str)
                                    is_currency = any(c in suffix for c in['vnd', 'usd', 'eur', 'cny', 'try', 'rsd', 'huf', 'krw', '원', '동', '달러'])
                                    is_unit = any(u in suffix for u in['ml', 'g', 'kg', 'cm', 'mm', '개', 'x', '입', '장', '명', '박스'])
                                    
                                    # 수량, 길이, 무게 등 단위가 직접 붙어있으면 환산 생략
                                    if is_unit and not is_currency: 
                                        return match.group(0)
                                        
                                    # 1. 화폐 단위가 명시됨
                                    # 2. 대단위 화폐(VND 등)에서 1000 이상의 큰 숫자
                                    # 3. 소수점이 있는 정확한 금액 표기 (예: 15.00)
                                    # 4. 금액이 100을 초과하는 일반 정수
                                    if is_currency or (curr in ['VND', 'HUF'] and v >= 1000) or ('.' in num_str) or (v > 100):
                                        krw_val = v * rate
                                        return f"{match.group(1)}<span style='font-size:13px;color:#FFD700;font-style:italic;'> (약 {krw_val:,.0f}원)</span>{match.group(2)}"
                                except: pass
                                return match.group(0)
                                
                            # 그룹1: 숫자 부분, 그룹2: 숫자 뒤에 따라오는 공백 및 문자 (단위 확인용)
                            pattern = re.compile(r'(?<![\d\.])(\d{1,3}(?:,\d{3})*(?:\.\d+)?)(?!\d)(\s*[a-zA-Z가-힣]*)')
                            return pattern.sub(replacer, text)

                        desc_full = str(row_data['Description'])
                        rate_for_calc = row_data['AppliedRate']
                        curr_for_calc = row_data['Currency']

                        if "-" in desc_full:
                            parts = desc_full.split("-", 1)
                            st.markdown(f"**🏪 상호명:** {parts[0].strip()}")
                            detail_str = parts[1].strip()
                            st.markdown("**📝 세부 구매 내역:**")
                            items = detail_str.split("\n") if "\n" in detail_str else detail_str.split(",")
                            for item in items: 
                                if item.strip(): 
                                    trans_item = smart_krw_translator(item.strip(), rate_for_calc, curr_for_calc)
                                    st.markdown(f"- {trans_item}", unsafe_allow_html=True)
                        else:
                            if "\n" in desc_full:
                                st.markdown("**📝 세부 내역:**")
                                for item in desc_full.split("\n"):
                                    if item.strip(): 
                                        trans_item = smart_krw_translator(item.strip(), rate_for_calc, curr_for_calc)
                                        st.markdown(f"- {trans_item}", unsafe_allow_html=True)
                            else:
                                trans_item = smart_krw_translator(desc_full, rate_for_calc, curr_for_calc)
                                st.markdown(f"**📝 내역:** {trans_item}", unsafe_allow_html=True)
                            
                        # [Modified] 쉼표로 구분된 다중 URL을 분리하여 모두 출력
                        receipt_data = str(row_data['Receipt_URL'])
                        if receipt_data.strip().startswith("http"):
                            urls = receipt_data.split(",")
                            for idx, url in enumerate(urls):
                                if url.strip():
                                    st.image(url.strip(), use_container_width=True, caption=f"영수증 사진 #{idx+1}")
                        else:
                            st.info("첨부된 영수증 사진이 없습니다.")
                            
                    with c_edit:
                        ### 🎨[GUI: Layout] 우측: 간편 인라인 수정 폼
                        st.subheader("✏️ 내역 보강 및 영수증 첨부")
                        st.caption("세부 내역을 엑셀에서 복사해 붙여넣거나 엔터(줄바꿈)로 여러 개 입력하시면, 왼쪽 뷰어에서 깔끔하게 분리되어 표시됩니다.")
                        
                        # [Added] 🎛️ 타임머신 미니 계산기
                        if row_data['Currency'] != 'KRW' and row_data['AppliedRate'] > 0:
                            with st.expander(f"🧮 타임머신 계산기 (적용 환율: {row_data['AppliedRate']:.4f})", expanded=False):
                                mini_amt = st.number_input(f"영수증 속 현지 금액을 입력해 보세요 ({row_data['Currency']})", min_value=0.0, step=10.0, key="mini_calc")
                                if mini_amt > 0:
                                    st.success(f"➔ 당시 원화 가치: **{mini_amt * row_data['AppliedRate']:,.0f} 원**")
                        
                        desc_key = f"edit_desc_{real_idx}"
                        if st.session_state.get('current_edit_idx') != real_idx:
                            st.session_state[desc_key] = str(row_data['Description'])
                            st.session_state['current_edit_idx'] = real_idx
                            
                        new_receipt = st.file_uploader("📸 새 영수증 사진 업로드", type=['png', 'jpg', 'jpeg'], key="inline_receipt")
                        # [Added] 🎛️ 수정 뷰어용 OCR 및 LLM 번역 파이프라인
                        if new_receipt:
                            if st.button("🤖 첨부된 사진 AI 스캔 (스마트 번역)", use_container_width=True):
                                with st.spinner("AI가 영수증을 분석하고 번역하는 중입니다..."):
                                    ext_text = extract_text_from_vision_api(new_receipt.getvalue())
                                    smart_text = summarize_receipt_with_gemini(ext_text)
                                    if smart_text:
                                        st.session_state[desc_key] = st.session_state.get(desc_key, '') + "\n" + smart_text
                                        st.rerun()

                        new_desc = st.text_area("📝 세부 내역 (수정/추가)", height=150, key=desc_key)
                        
                        if st.button("💾 이 내역 업데이트", use_container_width=True):
                            display_df.at[real_idx, 'Description'] = new_desc
                            if new_receipt:
                                with st.spinner("클라우드 전송 중..."):
                                    url = upload_image_to_imgbb(new_receipt)
                                    if url: display_df.at[real_idx, 'Receipt_URL'] = url
                            if save_data(display_df): st.success("업데이트 완료!"); time.sleep(1); st.rerun()
                    st.markdown("---")

# ==============================================================================
# --- SECTION 7:[Module E] Stats & Settlement (📊 일일 & 🏁 요약 탭) ---
# ==============================================================================
with tab_stats:
    if not ledger_df.empty:
        ### ⚙️[Logic: Stats Pre-processing] 통계용 데이터 준비
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

            ### ⚙️[Logic: Net-ifier Engine] 환불 내역 역산 (지출에서 삭감)
            r_df = ledger_df[(ledger_df['Category'] == '환불') & 
                             (~ledger_df['Description'].str.contains("보증금|Deposit|deposit", na=False))].copy()
            
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

            ### 🎛️ [GUI: Component] 차트 기준 통화 선택기
            c_mode = st.radio("📊 통화 선택",["원화(KRW)", f"현지화({TRAVEL_CURRENCY})"], horizontal=True, key="st_curr_top")
            y_col = 'KRW_val' if "원화" in c_mode else 'Local_val'

            is_fixed_cost = (exp_df['PaymentMethod'].str.strip() == '원화계좌(한국)') | (exp_df['Category'].isin(FIXED_COST_CATS))
            ovr_df = exp_df[(~is_fixed_cost) & (~exp_df['Category'].isin(['입국','출국']))]
            
            if not ovr_df.empty:
                ovr_df = ovr_df.copy()
                ovr_df['Date_Clean'] = ovr_df['Date'].str.split('(').str[0]
                ovr_df = ovr_df.sort_values(by='Date_Clean')
                ovr_df['Date_Country'] = ovr_df['Date_Clean'] + "<br><span style='font-size:11px;color:#AAAAAA'>" + ovr_df['Country'] + "</span>"
                
                ### 📊 [GUI: Chart/Table] 일별 현지지출 막대 차트
                fig2 = px.bar(ovr_df, x='Date_Country', y=y_col, color='Category', title=None, color_discrete_map=color_map)
                fig2.update_layout(barmode='stack', margin=dict(l=10, r=10, t=30, b=150), legend=dict(orientation="h", yanchor="top", y=-0.3, xanchor="center", x=0.5))
                fig2.update_xaxes(categoryorder='array', categoryarray=ovr_df['Date_Country'].unique(), tickangle=-90, tickfont=dict(size=10))
                st.markdown(f"<h4 style='text-align: center;'>🗺️ 여행지 일별지출({len(ovr_df['Date_Clean'].unique())}일차)</h4>", unsafe_allow_html=True)
                st.plotly_chart(fig2, use_container_width=True, config={'displaylogo': False})

            st.divider()
            
            ### 📊[GUI: Chart/Table] 일별 지출 요약 표
            daily_set = ovr_df.groupby('Date').agg({'Country': lambda x: ' / '.join(x.unique()), 'KRW_val': 'sum', 'Local_val': 'sum'}).reset_index() if not ovr_df.empty else pd.DataFrame(columns=['Date', 'Country', 'KRW_val', 'Local_val'])
            surv_only = ovr_df[ovr_df['IsSurvival'] == 1].groupby('Date').agg({'KRW_val': 'sum', 'Local_val': 'sum'}).reset_index().rename(columns={'KRW_val': 'S_KRW', 'Local_val': 'S_Loc'}) if not ovr_df.empty else pd.DataFrame(columns=['Date', 'S_KRW', 'S_Loc'])
            daily_table = pd.merge(daily_set, surv_only, on='Date', how='left').fillna(0) if not daily_set.empty else pd.DataFrame()
            fmt_local = "{:,.2f}" if MULTIPLIER == 1 else "{:,.0f}"
            
            if not daily_table.empty:
                display_table = daily_table[['Country', 'Date', 'KRW_val', 'Local_val', 'S_KRW', 'S_Loc']].rename(
                    columns={'Country':'국가', 'Date':'날짜', 'KRW_val':'총(원)', 'Local_val':f'총({LOCAL_SYM})', 'S_KRW':'일상(원)', 'S_Loc':f'일상({LOCAL_SYM})'}
                )
                st.dataframe(display_table.style.format({'총(원)': '{:,.0f}', f'총({LOCAL_SYM})': fmt_local, '일상(원)': '{:,.0f}', f'일상({LOCAL_SYM})': fmt_local}), use_container_width=True, hide_index=True)
            else:
                st.info("현지 지출 데이터가 없습니다.")

            # [Modified] 일일 탭 사전결제 트리맵 가독성 향상 버전
            dom_df = exp_df[is_fixed_cost & (~exp_df['Category'].isin(['입국','출국']))]
            if not dom_df.empty:
                st.divider()
                st.markdown("<h4 style='text-align: center;'>🛫 사전결제(Treemap)</h4>", unsafe_allow_html=True)
                
                # [Added] 요약 탭과 동일한 15자 요약 데이터 생성
                dom_chart_df = dom_df.copy()
                dom_chart_df['Short_Desc'] = dom_chart_df['Description'].apply(lambda x: str(x)[:15] + ".." if len(str(x)) > 15 else x)
                
                # [Modified] 경로에 Short_Desc 적용 및 색상 맵 활성화
                fig1 = px.treemap(dom_chart_df, 
                                 path=['Macro_Category', 'Category', 'Short_Desc'], 
                                 values=y_col, 
                                 color='Macro_Category', 
                                 color_discrete_map=macro_color_map)
                
                # [Modified] 텍스트 가독성 설정 (요약 탭과 동일 사양)
                fig1.update_traces(
                    texttemplate="<b>%{label}</b><br>%{value:,.0f}원",
                    hovertemplate="<b>%{label}</b><br>금액: %{value:,.0f}원",
                    textposition='middle center',
                    insidetextfont=dict(size=16) # 기본 폰트 크기 상향
                )
                
                # [Added] 글자 겹침 방지 및 레이아웃 최적화
                fig1.update_layout(
                    margin=dict(l=10, r=10, t=10, b=10),
                    height=550, # 높이 적절히 조절
                    uniformtext=dict(minsize=11, mode='hide') # 11pt 이하로 작아지면 숨김
                )
                st.plotly_chart(fig1, use_container_width=True, config={'displaylogo': False})

            if len(TRIP_CONFIGS[st.session_state.current_trip]["nodes"]) > 1 and not ovr_df.empty:
                st.divider()
                ### 📊 [GUI: Chart/Table] 국가별 현지지출 트리맵 차트
                fig_country = px.treemap(ovr_df, path=['Country', 'Macro_Category', 'Category'], values=y_col, color='Country', color_discrete_sequence=px.colors.qualitative.Pastel)
                fig_country.update_traces(texttemplate="<b>%{label}</b><br>%{value:,.0f}", hovertemplate="<b>%{label}</b><br>금액: %{value:,.0f}")
                fig_country.update_layout(
                    margin=dict(l=10, r=10, t=30, b=30), 
                    height=500,
                    uniformtext=dict(minsize=10, mode='hide') 
                )
                st.markdown("<h4 style='text-align: center;'>🌍 국가별 현지지출(Treemap)</h4>", unsafe_allow_html=True)
                st.plotly_chart(fig_country, use_container_width=True, config={'displaylogo': False})

            st.divider()
            ### 🎨 [GUI: Layout] 하단 지출 요약표 2단
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
                st.subheader("🛡️ 손실과 보상 (환불 목록)")
                r_krw = refund_df.apply(lambda r: r['Amount'] if str(r['Currency']).strip() == 'KRW' else r['Amount'] * r['AppliedRate'], axis=1).sum()
                st.warning(f"**환불총액:** {r_krw:,.0f} 원")
                with st.expander("상세내역", expanded=False):
                    st.dataframe(refund_df[['Date', 'Country', 'Description', 'Amount', 'Currency', 'PaymentMethod']], use_container_width=True)

with tab_final:
    if not ledger_df.empty and 'exp_df' in locals() and not exp_df.empty:
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
            
        ### 🎨[GUI: Layout] 상단 4대 핵심 지표 KPI 카드
        st.header("🏁 여행요약")
        k1, k2, k3, k4 = st.columns(4)
        with k1: st.markdown(kpi_box("여행 최종 순지출", total_trip_krw, total_trip_loc), unsafe_allow_html=True)
        with k2: st.markdown(kpi_box("국내 지출 순액", dom_total_krw), unsafe_allow_html=True)
        with k3: st.markdown(kpi_box("현지 지출 총액", ovr_total_krw, ovr_total_loc), unsafe_allow_html=True)
        with k4: st.markdown(kpi_box(f"현지 일상/생존 1일 평균", avg_local_krw, avg_local_loc), unsafe_allow_html=True)
        
        ### 📊[GUI: Chart/Table] 결산 요약 트리맵 (전체비중)
        st.subheader("🌳 지출분석 (Treemap)")
        # [Added] 트리맵 가독성을 위한 데이터 전처리: 너무 긴 설명은 요약
        chart_df = exp_df.copy()
        chart_df['Short_Desc'] = chart_df['Description'].apply(lambda x: str(x)[:15] + ".." if len(str(x)) > 15 else x)
        
        # [Modified] 경로에 요약된 설명(Short_Desc) 사용
        fig_tree = px.treemap(chart_df, 
                             path=['Macro_Category', 'Category', 'Short_Desc'], 
                             values='KRW_val', 
                             color='KRW_val', 
                             color_continuous_scale='Greens')
        
        # [Modified] 텍스트 템플릿 개선 및 글자 크기 강제
        fig_tree.update_traces(
            texttemplate="<b>%{label}</b><br>%{value:,.0f}원",
            hovertemplate="<b>%{label}</b><br>금액: %{value:,.0f}원<br>비중: %{percentRoot:.1%}",
            textposition='middle center',
            insidetextfont=dict(size=16) # 기본 폰트 크기 상향
        )
        
        # [Added] 아무리 박스가 작아도 글자가 작아지지 않게 방어 (최소 12px)
        fig_tree.update_layout(
            margin=dict(l=0, r=0, t=30, b=0),
            height=650, 
            uniformtext=dict(minsize=11, mode='hide') # 글자가 박스보다 크면 숨겨서 겹침 방지
        )
        st.plotly_chart(fig_tree, use_container_width=True, config={'displaylogo': False})
        
        ### 📊[GUI: Chart/Table] 카테고리별 도넛 차트
        st.subheader("🍕 지출비중")
        cat_pie = exp_df.groupby('Macro_Category')['KRW_val'].sum().reset_index().sort_values(by='KRW_val', ascending=False)
        fig_donut = px.pie(cat_pie, values='KRW_val', names='Macro_Category', hole=0.5, color_discrete_sequence=px.colors.qualitative.Set3)
        fig_donut.update_traces(textposition='inside', textinfo='label+value+percent', texttemplate='%{label}<br>%{value:,.0f}원<br>%{percent:.1%}')
        until_day = exp_df['Date'].max().split('(')[0]
        fig_donut.add_annotation(text=f"<b>순지출(Net)</b><br>{total_trip_krw:,.0f} 원<br><span style='font-size:10px'>Until {until_day}</span>", showarrow=False, font=dict(size=16))
        fig_donut.update_layout(height=600, margin=dict(l=10, r=10, t=50, b=100), legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5), uniformtext_minsize=11, uniformtext_mode='hide')
        st.plotly_chart(fig_donut, use_container_width=True)

st.caption(f"GTL Platform {VERSION} | Volume Guard: ~ 70 KB | Sync: {datetime.now(st.session_state.current_tz).strftime('%Y-%m-%d %H:%M:%S')} | Strategic Partner Gem")

with tab_nav:
    st.subheader("🧭 GTL Survival Price Index (SPI v14 - 정밀 매핑)")
    df_all = load_all_trips_data()
    
    if not df_all.empty:
        # [수정] 탭 내부에서 conn.read를 직접 하지 않고 상단 전역변수 TRIP_CONFIGS와 
        # load_data(CONFIG_SHEET)로 로드된 데이터를 활용
        cfg_df = load_data(CONFIG_SHEET) 
        
        def parse_nights(mapping_str, country):
            if pd.isna(mapping_str): return 0
            for part in str(mapping_str).split(','):
                if country in part:
                    num = re.search(r'(\d+(?:\.\d+)?)', part)
                    return float(num.group(1)) if num else 0
            # default 값 확인
            default_num = re.search(r'default\s*:\s*(\d+(?:\.\d+)?)', str(mapping_str))
            return float(default_num.group(1)) if default_num else 0
            
        stay_nights = {}
        # 여행 기록 그룹별 루프
        for (trip, country), group in df_all.groupby(['TripName', 'Country']):
            # cfg_df에서 현재 trip에 해당하는 행 검색
            row_config = cfg_df[cfg_df['TripName'] == trip]
            mapping_str = row_config['Stay_Mapping'].values[0] if not row_config.empty else ""
            
            # 파싱 결과 적용 (국가명이 맵핑에 없으면 0 반환하여 에러 유발)
            stay_nights[(trip, country)] = parse_nights(mapping_str, country)
            
            # 파싱: 1. 국가명 매칭 -> 2. default 매칭 -> 3. 0(에러 유발용)
            parts = str(mapping_str).split(',')
            night_val = 0
            for part in parts:
                if country in part:
                    num = re.search(r'(\d+(?:\.\d+)?)', part)
                    night_val = float(num.group(1)) if num else 0
                    break
            
            if night_val == 0:
                default_num = re.search(r'default\s*:\s*(\d+(?:\.\d+)?)', str(mapping_str))
                night_val = float(default_num.group(1)) if default_num else 0
            
            stay_nights[(trip, country)] = night_val
            
        # 3. 데이터 필터링 및 SPI 세부 그룹핑
        df_spi = df_all[
            (df_all['Category'].isin(SPI_CATS)) & 
            (~df_all['Country'].str.contains('글로벌|경유|크로아티아', na=False))
        ].copy()
        
        if not df_spi.empty:
            df_spi['KRW_val'] = df_spi.apply(lambda r: r['Amount'] if r['Currency'] == 'KRW' else r['Amount'] * float(r['AppliedRate']), axis=1)
            
            def map_spi_group(cat):
                if cat in ['렌트카']: return '🚗 렌트카'
                if cat in ['호텔', '숙박']: return '🏨 숙박'
                if cat in ['투어', '입장료', '마사지']: return '🏄 투어/액티비티'
                if cat in ['식사', '간식', '마트']: return '🍔 식음료'
                if cat in ['Grab', 'VinBus', 'DiDi', '지하철', '택시', '교통']: return '🚕 로컬교통'
                return '📱 기타' 

            df_spi['SPI_Group'] = df_spi['Category'].apply(map_spi_group)
            
            # [Modified] 관제탑(_GTL_CONFIG_)의 J칼럼(Travelers)을 100% 신뢰하여 직접 맵핑
            travelers_map = {}
            try:
                cfg_df = conn.read(worksheet=CONFIG_SHEET, ttl="0s")
                if cfg_df is not None and 'Travelers' in cfg_df.columns:
                    travelers_map = dict(zip(cfg_df['TripName'], pd.to_numeric(cfg_df['Travelers'], errors='coerce')))
            except Exception:
                pass

            agg_group = df_spi.groupby(['TripName', 'Country', 'SPI_Group'])['KRW_val'].sum().reset_index()
            # 데이터 누락 시 최후의 보루로만 2명 할당
            agg_group['Travelers'] = agg_group['TripName'].map(travelers_map).fillna(2)
            
            # 분모를 명확한 'Nights(숙박일)'로 통일
            # Nights가 0이면 에러가 발생하도록 1 대신 0을 반환
            agg_group['Nights'] = agg_group.apply(lambda r: stay_nights.get((r['TripName'], r['Country']), 0), axis=1)
            agg_group['Daily_SPI'] = (agg_group['KRW_val'] / agg_group['Travelers']) / agg_group['Nights']

            agg_total = agg_group.groupby(['TripName', 'Country']).agg({'Daily_SPI': 'sum', 'Travelers': 'first', 'Nights': 'first'}).reset_index()

            # 4. 특이사항(Theme) 분석 엔진 (정확한 Nights 기반 산출)
            theme_notes =[]
            for idx, row in agg_total.iterrows():
                t, c, pp_nights = row['TripName'], row['Country'], row['Travelers'] * row['Nights']
                sub_df = df_spi[(df_spi['TripName'] == t) & (df_spi['Country'] == c)]
                
                hotel_v = sub_df[sub_df['SPI_Group'] == '🏨 숙박']['KRW_val'].sum()
                rent_v = sub_df[sub_df['SPI_Group'] == '🚗 렌트카']['KRW_val'].sum()
                tour_v = sub_df[sub_df['Category'].str.contains('투어|입장료', na=False)]['KRW_val'].sum()
                
                tags =[]
                if hotel_v > 0: tags.append(f"🏨 1박평균 {hotel_v/row['Nights']/10000:.1f}만")
                if rent_v > 0: tags.append(f"🚗 1일렌트 {rent_v/row['Nights']/10000:.1f}만")
                if tour_v > 0: tags.append(f"🏄 투어(1인) {tour_v/pp_nights/10000:.1f}만")
                
                if "칭다오" in t: tags.append("👑 5성급 럭셔리 테마")
                if "몬테네그로" in c: tags.append("🇭🇷 크로아 당일치기 루트")
                
                theme_notes.append(" | ".join(tags) if tags else "-")
                
            agg_total['Theme'] = theme_notes
            
            final_total_df = agg_total.sort_values(by='Daily_SPI', ascending=True)
            
            if not final_total_df.empty:
                st.markdown("### 📊 국가별 1인당 1박 체감 물가 (KRW)")
                st.caption("💡 모든 지표는 글로벌 여행 표준인 **'1박당(Per Night)'** 기준으로 계산되어 숫자의 왜곡이 없습니다. 누적 막대그래프의 렌트카(빨강)와 숙박(파랑)을 제외하면 순수 체류 물가를 비교할 수 있습니다.")
                
                def make_chart_label(r):
                    country, trip = str(r['Country']), str(r['TripName'])
                    if "발칸" in trip: return country 
                    match = re.search(r'([가-힣]+)', trip)
                    city = match.group(1) if match else ""
                    return f"{country}({city})" if city and city not in country else country

                final_total_df['Chart_Label'] = final_total_df.apply(make_chart_label, axis=1)
                
                display_df = final_total_df.copy()
                display_df['Daily_SPI_Fmt'] = display_df['Daily_SPI'].apply(lambda x: f"{x:,.0f} 원")
                
                # 정수면 소수점 제거해서 깔끔하게 표시
                display_df['Nights'] = display_df['Nights'].apply(lambda x: int(x) if x == int(x) else x)
                
                display_df = display_df.rename(columns={
                    'TripName': '여행명', 'Country': '국가', 'Travelers': '인원수', 
                    'Nights': '숙박일(박)', 'Daily_SPI_Fmt': '1박 체감물가', 'Theme': '💡 특이사항 및 요인'
                })
                
                st.dataframe(display_df[['여행명', '국가', '인원수', '숙박일(박)', '1박 체감물가', '💡 특이사항 및 요인']], use_container_width=True, hide_index=True)
                
                label_map = dict(zip(zip(final_total_df['TripName'], final_total_df['Country']), final_total_df['Chart_Label']))
                agg_group['Chart_Label'] = agg_group.apply(lambda r: label_map.get((r['TripName'], r['Country']), r['Country']), axis=1)
                
                category_order_x = final_total_df['Chart_Label'].tolist()
                stack_order = ['📱 기타', '🚕 로컬교통', '🍔 식음료', '🏄 투어/액티비티', '🏨 숙박', '🚗 렌트카']
                
                color_map = {
                    '🚗 렌트카': '#D32F2F', 
                    '🏨 숙박': '#1976D2',   
                    '🏄 투어/액티비티': '#9C27B0', 
                    '🍔 식음료': '#4CAF50', 
                    '🚕 로컬교통': '#00ACC1', 
                    '📱 기타': '#795548' 
                }

                fig_stacked = px.bar(
                    agg_group,
                    x='Chart_Label', y='Daily_SPI', color='SPI_Group',
                    color_discrete_map=color_map,
                    category_orders={"Chart_Label": category_order_x, "SPI_Group": stack_order}
                )
                
                fig_stacked.update_layout(
                    barmode='stack',
                    margin=dict(l=10, r=10, t=10, b=30),
                    legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5, title=None),
                    xaxis_title=None, yaxis_title=None
                )
                fig_stacked.update_traces(hovertemplate="%{x}<br><b>%{data.name}</b>: %{y:,.0f}원<extra></extra>")
                
                st.plotly_chart(fig_stacked, use_container_width=True, config={'displaylogo': False})
            else:
                st.info("비교할 SPI 데이터가 부족합니다.")
        else:
            st.info("SPI 기준에 부합하는 데이터가 없습니다.")
