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

# 1.02.01 | Macro Mapping Matrix
# ➔ 🚀 [Modified] 아래와 같이 수정 ("개인지출" 매핑 추가 및 버전 업데이트)
MACRO_MAP = {
    "Grab": "🚗 교통", "VinBus": "🚗 교통", "DiDi": "🚗 교통", "지하철": "🚗 교통", "택시": "🚗 교통", "렌트카": "🚗 교통",
    "식사": "🍔 식음료", "간식": "🍔 식음료", "마트": "🍔 식음료",
    "마사지": "🏄 액티비티", "투어": "🏄 액티비티", "입장료": "🏄 액티비티",
    "선물": "🎁 쇼핑", "통신": "📱 통신/기타", "수수료": "📱 통신/기타", "팁": "📱 통신/기타",
    "항공권": "✈️ 항공권", "호텔": "🏨 숙박", "보험": "🛡️ 보험", "보증금": "🏦 자산이동", "재환전": "🏦 자산이동", "상환": "🏦 자산이동", "개인지출": "🏦 자산이동" # [Modified] 개인지출 추가
}
VERSION = "v26.05.27.002" # [Modified]

# 1.02.02 | Schema Column Definitions
CORE_COLUMNS =['Date', 'Country', 'Category', 'Description', 'Currency', 'Amount', 'PaymentMethod', 'Receipt_URL']
SYSTEM_LOGIC_COLUMNS =['IsExpense', 'AppliedRate', 'Cum_Budget_KRW', 'Cum_Card_Local', 'Cum_Cash_Local', 'Note']
FINAL_COLUMNS = CORE_COLUMNS + SYSTEM_LOGIC_COLUMNS

# 1.02.03 | Third-party Keys & Nominal Bills Configuration
IMGBB_API_KEY = "81181bf834001b6191aaa90fa772c6f9"
BILLS =[500000, 200000, 100000, 50000, 20000, 10000, 5000, 2000, 1000]

CONFIG_SHEET = "_GTL_CONFIG_"

UPDATE_LOG_TEXT = """* `[Added]` 🌍 **GTL 다중 국가 노드 동적 활성화**: 하나의 여행 시트 내에서 여러 국가의 통화와 인벤토리를 개별적으로 추적하는 'Multi-Node' 기능 탑재 (시트 분할 불필요).
* `[Refactored]` 관제탑(`_GTL_CONFIG_`)의 `Stay_Mapping` 정보를 파싱하여, 입력창의 국가 목록과 로컬 통화(TRY, TND, EUR 등)를 동적으로 스위칭하도록 업그레이드."""

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
# 1.05.00 | GUI Design System (커스텀 다크 테마 및 컴포넌트 CSS 주입)
# ------------------------------------------------------------------------------
# 1.05.01 | Custom Dark Theme & Component CSS Injector
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

# ------------------------------------------------------------------------------
# 1.06.00 | Session State Orchestrator (동적 세션 상태 및 컨텍스트 초기화)
# ------------------------------------------------------------------------------
# 1.06.01 | Dynamic Session Context & Initializer
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
# 2.02.00 | Media & Vision AI Subsystem (이미지 업로드, OCR, Gemini 번역)
# ------------------------------------------------------------------------------
# 2.02.01 | ImgBB Cloud Media Uploader
### ⚙️ [Logic: API] ImgBB 영수증 업로드
def upload_image_to_imgbb(image_file):
    try:
        payload = {"key": IMGBB_API_KEY, "image": base64.b64encode(image_file.read()).decode("utf-8")}
        res = requests.post("https://api.imgbb.com/1/upload", data=payload)
        if res.status_code == 200: return res.json()['data']['url']
    except: pass
    return ""

# 2.02.02 | Google Cloud Vision OCR Engine
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

# 2.02.03 | Gemini LLM Multi-Lingual Receipt Parser
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
        
ledger_df = load_data(ACTIVE_SHEET)
