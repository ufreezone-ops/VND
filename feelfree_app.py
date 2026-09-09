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
# 1.05.00 | GUI Design System (커스텀 다크/화이트 듀얼 테마 엔진)
# ------------------------------------------------------------------------------
# 1.05.01 | Custom Dark Theme & Component CSS Injector (헤더 가림 방지 및 황금비율 여백)
### 🎨 [GUI: Layout] Custom CSS (화면 전반의 디자인 및 컴포넌트 스타일링)
if 'app_theme' not in st.session_state:
    st.session_state.app_theme = "🌙 다크"

current_theme = st.session_state.app_theme

if current_theme == "🌙 다크":
    # ------------------ [🌙 프리미엄 다크 테마] ------------------
    st.markdown("""
        <script>var link=document.createElement('link'); link.rel='apple-touch-icon'; link.href='https://img.icons8.com/color/512/globe--v1.png'; document.getElementsByTagName('head')[0].appendChild(link);</script>
        <style>
        /* 📱 [상단 헤더 가림 완벽 방어 + 최적 여백] */
        .block-container {
            padding-top: 3.5rem !important;  /* 상단 헤더 높이만큼 안전하게 확보 */
            padding-bottom: 2rem !important;
            padding-left: 0.8rem !important;
            padding-right: 0.8rem !important;
        }

        /* 여행 선택 드롭다운 여백 정규화 */
        div[data-testid="stSelectbox"] {
            margin-top: 0px !important;
            margin-bottom: 0px !important;
        }

        /* 구분선(st.divider) 간격 슬림화 */
        hr {
            margin: 0.4rem 0 0.6rem 0 !important;
        }

        /* 메인 타이틀(후에 2026 등) 상단 여백 제거 */
        h1 {
            padding-top: 0rem !important;
            margin-top: 0rem !important;
            padding-bottom: 0.2rem !important;
            margin-bottom: 0.4rem !important;
        }

        .main { background-color: #0e1117; color: #ffffff; }
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
        div[data-testid="stSidebar"] .stSelectbox label p { color: #FFD700 !important; }
        [data-testid="stSidebar"] hr { margin: 0.5rem 0 !important; }

        /* 다크모드 검색창 & 입력창 고대비 흰색 글씨 고정 */
        div[data-baseweb="input"] { background-color: #1e2130 !important; border: 1px solid #4B5563 !important; border-radius: 8px !important; }
        div[data-baseweb="input"] input { color: #FFFFFF !important; font-size: 14px !important; }

        div[data-testid="stNumberInput"] button { display: none !important; }
        div[data-testid="stNumberInput"] input { padding-right: 10px !important; }
        div[data-testid="stNumberInput"] [data-baseweb="input"] { border-right-width: 1px !important; }

        /* 사이드바 상단 여백 회수 */
        section[data-testid="stSidebar"] > div:first-child { padding-top: 1rem !important; }
        div[data-testid="stSidebarHeader"] { height: 35px !important; min-height: 35px !important; padding-top: 0px !important; padding-bottom: 0px !important; margin-bottom: 0px !important; }
        div[data-testid="stSidebarContent"] { padding-top: 0px !important; }
        div[data-testid="stSidebarUserContent"] { padding-top: 0px !important; }
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] { padding-top: 0px !important; gap: 0px !important; }
        [data-testid="stSidebar"] div[data-testid="stExpanderDetails"] { padding-top: 6px !important; padding-bottom: 8px !important; }

        /* 실물현금 카운터 튜닝 스타일 */
        [data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stHorizontalBlock"] {
            display: flex !important; flex-direction: row !important; flex-wrap: nowrap !important; align-items: center !important; justify-content: center !important; width: 100% !important; gap: 10px !important; margin-bottom: 3px !important; margin-top: 0px !important; padding: 0px !important;
        }
        [data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child {
            flex: 0 0 55px !important; width: 55px !important; max-width: 55px !important; min-width: 55px !important; display: flex !important; align-items: center !important; justify-content: flex-end !important; height: 30px !important;
        }
        [data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child p,
        [data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child div {
            margin: 0px !important; padding: 0px !important; line-height: 30px !important;
        }
        [data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stHorizontalBlock"] > [data-testid="column"]:last-child {
            flex: 0 0 85px !important; width: 85px !important; max-width: 85px !important; min-width: 85px !important; display: flex !important; align-items: center !important; height: 30px !important;
        }
        [data-testid="stSidebar"] [data-testid="stExpander"] div.stNumberInput { width: 85px !important; margin: 0px !important; padding: 0px !important; height: 30px !important; }
        [data-testid="stSidebar"] [data-testid="stExpander"] div.stNumberInput div[data-baseweb="input"] { width: 85px !important; min-height: 30px !important; height: 30px !important; border-radius: 6px !important; padding: 0px !important; display: flex !important; align-items: center !important; }
        [data-testid="stSidebar"] [data-testid="stExpander"] div.stNumberInput input { height: 30px !important; font-size: 14px !important; text-align: center !important; padding: 0px !important; line-height: 30px !important; }
        </style>
    """, unsafe_allow_html=True)
else:
    # ------------------ [☀️ 고대비 화이트 모드] ------------------
    st.markdown("""
        <script>var link=document.createElement('link'); link.rel='apple-touch-icon'; link.href='https://img.icons8.com/color/512/globe--v1.png'; document.getElementsByTagName('head')[0].appendChild(link);</script>
        <style>
        /* 📱 [상단 헤더 가림 완벽 방어 + 최적 여백] */
        .block-container {
            padding-top: 3.5rem !important;  /* 상단 헤더 높이만큼 안전하게 확보 */
            padding-bottom: 2rem !important;
            padding-left: 0.8rem !important;
            padding-right: 0.8rem !important;
        }

        /* 여행 선택 드롭다운 여백 정규화 */
        div[data-testid="stSelectbox"] {
            margin-top: 0px !important;
            margin-bottom: 0px !important;
        }

        /* 구분선(st.divider) 간격 슬림화 */
        hr {
            margin: 0.4rem 0 0.6rem 0 !important;
        }

        /* 메인 타이틀(후에 2026 등) 상단 여백 제거 */
        h1 {
            padding-top: 0rem !important;
            margin-top: 0rem !important;
            padding-bottom: 0.2rem !important;
            margin-bottom: 0.4rem !important;
        }

        .main { background-color: #F8FAFC; color: #0F172A; }
        .kpi-box { background-color: #FFFFFF; padding: 20px; border-radius: 15px; border-left: 8px solid #F59E0B; margin-bottom: 20px; min-height: 130px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.08); border-top: 1px solid #E2E8F0; border-right: 1px solid #E2E8F0; border-bottom: 1px solid #E2E8F0; }
        .kpi-title { font-size: 15px; color: #64748B; margin-bottom: 10px; font-weight: 600; }
        .kpi-value-krw { font-size: 26px; font-weight: bold; color: #0F172A; line-height: 1.1; }
        .kpi-value-vnd { font-size: 18px; color: #D97706; margin-top: 8px; font-family: 'Courier New', monospace; font-weight: 600; }
        div[data-testid="stTable"] { border: 1px solid #CBD5E1; border-radius: 10px; overflow: hidden; background-color: #FFFFFF; }

        .stTabs[data-baseweb="tab-list"] { gap: 5px; padding: 5px 5px; background-color: #F1F5F9; border-radius: 12px; border: 2px solid #F59E0B; box-shadow: 0px 2px 8px rgba(245, 158, 11, 0.15); }
        .stTabs[data-baseweb="tab"] { height: 40px; background-color: #FFFFFF; border-radius: 8px !important; padding: 0px 10px !important; color: #475569 !important; border: 1px solid #CBD5E1; font-size: 14px !important; transition: all 0.3s ease; }
        .stTabs[data-baseweb="tab"]:hover { background-color: #E2E8F0; color: #0F172A !important; }
        .stTabs [aria-selected="true"] { background-color: #F59E0B !important; color: #FFFFFF !important; font-weight: 800 !important; box-shadow: 0px 4px 10px rgba(245, 158, 11, 0.3) !important; border: 1px solid #F59E0B !important; }

        div[data-testid="stSidebar"] { background-color: #F1F5F9 !important; border-right: 1px solid #E2E8F0; }
        div[data-testid="stSidebar"] div[data-baseweb="select"] > div { border: 2px solid #F59E0B !important; background-color: #FFFFFF !important; border-radius: 10px !important; color: #0F172A !important; }
        div[data-testid="stSidebar"] .stSelectbox label { color: #D97706 !important; font-weight: bold !important; }
        div[data-testid="stSidebar"] .stSelectbox label p { color: #B45309 !important; font-weight: bold !important; }
        [data-testid="stSidebar"] hr { margin: 0.5rem 0 !important; border-color: #CBD5E1 !important; }

        /* [핵심] 화이트모드 검색창 & 입력창 고대비 흑요석 블랙 글씨 강제 고정 */
        div[data-baseweb="input"] { background-color: #FFFFFF !important; border: 1.5px solid #94A3B8 !important; border-radius: 8px !important; }
        div[data-baseweb="input"] input { color: #0F172A !important; font-size: 14px !important; font-weight: 500 !important; }
        div[data-baseweb="input"] input::placeholder { color: #94A3B8 !important; }

        div[data-testid="stNumberInput"] button { display: none !important; }
        div[data-testid="stNumberInput"] input { padding-right: 10px !important; }
        div[data-testid="stNumberInput"] [data-baseweb="input"] { border-right-width: 1px !important; }

        section[data-testid="stSidebar"] > div:first-child { padding-top: 1rem !important; }
        div[data-testid="stSidebarHeader"] { height: 35px !important; min-height: 35px !important; padding: 0px !important; margin-bottom: 0px !important; }
        div[data-testid="stSidebarContent"] { padding-top: 0px !important; }
        div[data-testid="stSidebarUserContent"] { padding-top: 0px !important; }
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] { padding-top: 0px !important; gap: 0px !important; }
        [data-testid="stSidebar"] div[data-testid="stExpanderDetails"] { padding-top: 6px !important; padding-bottom: 8px !important; background-color: #FFFFFF !important; border-radius: 8px; border: 1px solid #E2E8F0; }

        /* 실물현금 카운터 화이트모드 스타일 */
        [data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stHorizontalBlock"] {
            display: flex !important; flex-direction: row !important; flex-wrap: nowrap !important; align-items: center !important; justify-content: center !important; width: 100% !important; gap: 10px !important; margin-bottom: 3px !important; margin-top: 0px !important; padding: 0px !important;
        }
        [data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child {
            flex: 0 0 55px !important; width: 55px !important; max-width: 55px !important; min-width: 55px !important; display: flex !important; align-items: center !important; justify-content: flex-end !important; height: 30px !important;
        }
        [data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child p,
        [data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child div {
            margin: 0px !important; padding: 0px !important; line-height: 30px !important; color: #1E293B !important;
        }
        [data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stHorizontalBlock"] > [data-testid="column"]:last-child {
            flex: 0 0 85px !important; width: 85px !important; max-width: 85px !important; min-width: 85px !important; display: flex !important; align-items: center !important; height: 30px !important;
        }
        [data-testid="stSidebar"] [data-testid="stExpander"] div.stNumberInput { width: 85px !important; margin: 0px !important; padding: 0px !important; height: 30px !important; }
        [data-testid="stSidebar"] [data-testid="stExpander"] div.stNumberInput div[data-baseweb="input"] { width: 85px !important; min-height: 30px !important; height: 30px !important; border-radius: 6px !important; padding: 0px !important; display: flex !important; align-items: center !important; background-color: #FFFFFF !important; border: 1.5px solid #CBD5E1 !important; }
        [data-testid="stSidebar"] [data-testid="stExpander"] div.stNumberInput input { height: 30px !important; font-size: 14px !important; text-align: center !important; padding: 0px !important; line-height: 30px !important; color: #0F172A !important; }
        </style>
    """, unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# 1.06.00 | Session State Orchestrator (동적 세션 상태 및 컨텍스트 초기화)
# ------------------------------------------------------------------------------
# 1.06.01 | Dynamic Session Context & Initializer (가장 최신 여행 자동 시작)
def sort_trips(trip_names):
    return sorted(trip_names, key=lambda x: (re.search(r'\((\d{4})\)', x).group(1) if re.search(r'\((\d{4})\)', x) else '0000', x), reverse=True)

sorted_trips_initial = sort_trips(list(TRIP_CONFIGS.keys()))
if 'current_trip' not in st.session_state: 
    st.session_state.current_trip = sorted_trips_initial[0]  # 무조건 가장 최신 여행으로 시작

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
        # [Fixed] 다중 업로드 및 재사용 시 파일 포인터를 항상 처음으로 되감기
        if hasattr(image_file, "seek"):
            image_file.seek(0)
            
        # [Fixed] getvalue() 우선 사용으로 스트림 소모 방지
        img_bytes = image_file.getvalue() if hasattr(image_file, "getvalue") else image_file.read()
        if not img_bytes:
            return ""
            
        payload = {"key": IMGBB_API_KEY, "image": base64.b64encode(img_bytes).decode("utf-8")}
        res = requests.post("https://api.imgbb.com/1/upload", data=payload, timeout=15)
        if res.status_code == 200: 
            time.sleep(0.2)  # 연속 업로드 시 API 레이트 리밋 보호
            return res.json()['data']['url']
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

# ------------------------------------------------------------------------------
# 2.05.03 | Cash Inventory Cloud Loader & Saver (지폐 실사 잔고 클라우드 동기화)
# ------------------------------------------------------------------------------
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
# 4.01.00 | Sidebar Dashboard (지갑 잔고, 외상 관리, KPI 모니터링)
# ------------------------------------------------------------------------------
### 🎨 [GUI: Layout] 사이드바 영역
with st.sidebar:
    # 4.01.01 | SPI Mode Context-Aware Panel
    # [Added] SPI 비교 모드일 때의 사이드바 UI 분리
    if st.session_state.get('show_spi', False):
        st.subheader("🧭 GTL 관제탑 모드")
        st.info("💡 **글로벌 물가 지표(SPI) 비교 분석 중**\n\n특정 여행의 지출 내역이나 잔고를 보시려면 상단의 '내 여행함'에서 여행지를 선택해 주세요.")
        st.divider()
        tz_sel = st.radio("📍 기준 시간 (Timezone)",["🇰🇷 한국 시간", "🌍 현지 시간"], horizontal=True, index=0)
        st.session_state.current_tz = TZ_KST if "한국" in tz_sel else TRIP_TZ
        st.markdown("<div style='margin-top:35px;'></div>", unsafe_allow_html=True)
        if st.button("🔄 Cloud Refresh", use_container_width=True): st.cache_data.clear(); st.rerun()
    else:
        # ----------------------------------------------------------------------
        # 4.01.02 | Multi-Currency Dynamic Wallet Monitor & Physical Cash Counter
        # ----------------------------------------------------------------------
        st.subheader("💰 지갑 잔고")
        b_val, spent_val = calculate_summary_metrics(ledger_df)
        
        # 1. 여행 진행 중 여부 판별
        korea_arr = ledger_df[ledger_df['Category'].str.contains('입국_한국|입국.*한국', na=False)]
        arr_rows = ledger_df[ledger_df['Category'].str.contains('입국', na=False)]
        target_arr_row = korea_arr if not korea_arr.empty else arr_rows

        is_trip_active = True
        if not target_arr_row.empty:
            m_arr = re.search(r'(\d{4}-\d{2}-\d{2})', str(target_arr_row.iloc[-1]['Date']))
            if m_arr:
                arr_dt = datetime.strptime(m_arr.group(1), "%Y-%m-%d").date()
                today_dt = datetime.now(st.session_state.current_tz).date()
                is_trip_active = (today_dt <= arr_dt)

        active_currs = set([k.split('(')[1].replace(')','') for k in current_inventory_batches.keys() if len(current_inventory_batches[k]) > 0 and sum(b['qty'] for b in current_inventory_batches[k]) > 0])
        trip_currs = set(node['currency'] for node in TRIP_CONFIGS[st.session_state.current_trip]["nodes"].values())
        display_currs = sorted(list(active_currs | trip_currs))

        # [글로벌 실물현금: 지폐 + 동전 통합 권종 매핑]
        CURR_BILLS = {
            "VND": BILLS,  # 베트남은 동전 없음 (50만동 ~ 1천동 지폐)
            "EUR": [100, 50, 20, 10, 5, 2, 1, 0.5, 0.2, 0.1],  # 100~5€ 지폐 + 2€, 1€, 50c, 20c, 10c 동전
            "USD": [100, 50, 20, 10, 5, 2, 1, 0.25, 0.1],      # 지폐 + 25¢(쿼터), 10¢(다임) 동전
            "TRY": [200, 100, 50, 20, 10, 5, 1, 0.5],          # 지폐 + 1₺, 50kr 동전
            "JPY": [10000, 5000, 2000, 1000, 500, 100, 50, 10], # 지폐 + 동전
            "PHP": [1000, 500, 200, 100, 50, 20, 10, 5, 1],    # 지폐 + 동전
            "CNY": [100, 50, 20, 10, 5, 1, 0.5, 0.1]
        }

        LOW_CASH_THRESHOLD = {
            "VND": 1000000, "USD": 50, "EUR": 50, "TRY": 1000, "JPY": 5000, "CNY": 300, "PHP": 2000
        }
        
        ### 📊 [GUI: Chart/Table] 통화별 잔고 표시
        for c in display_currs:
            if c == "KRW": continue

            fmt = "{:,.2f}" if c not in["VND", "HUF", "PHP"] else "{:,.0f}"

            debt_amt = ledger_df[(ledger_df['Currency']==c) & (ledger_df['PaymentMethod'].str.contains("외상|부채|CREDIT", na=False))]['Amount'].sum()
            repay_amt = ledger_df[(ledger_df['Currency']==c) & (ledger_df['Category']=="상환")]['Amount'].sum()
            current_debt = debt_amt - repay_amt
            
            if current_debt > 0:
                st.markdown(f"<div style='color:#FF4B4B; font-size:14px;'>📌 <b>미결제 외상: {fmt.format(current_debt)}</b></div>", unsafe_allow_html=True)
            
            c_card = sum([b['qty'] for b in current_inventory_batches.get(f"트래블카드({c})",[])])
            c_cash = sum([b['qty'] for b in current_inventory_batches.get(f"현금({c})",[])])
            
            if c_card > 0 or c_cash > 0 or c in trip_currs:
                st.markdown(f"<div style='color:#FFA500; font-weight:bold; margin-top:14px; margin-bottom:12px;'>● {c}</div>", unsafe_allow_html=True)
                st.markdown(f"💳 카드: **{fmt.format(c_card)}**")
                st.markdown(f"<div style='margin-bottom:14px;'>💵 현금: **{fmt.format(c_cash)}**</div>", unsafe_allow_html=True) 

                threshold = LOW_CASH_THRESHOLD.get(c, 1000000 if c == "VND" else 50)
                if is_trip_active and c_cash <= threshold:
                    st.markdown("""
                        <div style='color:#FFA500; font-size:13px; font-weight:bold; margin-top:2px; margin-bottom:16px; padding: 6px 12px; background-color: rgba(255, 165, 0, 0.12); border-radius: 8px; border-left: 3px solid #FFA500;'>
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

                # [개편] 🪙 실물현금 카운터 (지폐 + 동전 완벽 지원)
                bills_to_count = CURR_BILLS.get(c, [])
                if bills_to_count and (c_cash > 0 or is_trip_active):
                    with st.expander("🪙 실물현금 카운터", expanded=False):
                        cash_df = load_cash_inventory()
                        cloud_total = 0.0
                        cloud_time = ""
                        cloud_counts = {}
                        
                        if not cash_df.empty:
                            m_sync = (cash_df['TripName'] == st.session_state.current_trip) & (cash_df['Currency'] == c)
                            if m_sync.any():
                                row_sync = cash_df[m_sync].iloc[0]
                                cloud_total = float(row_sync.get('Total_Amount', 0))
                                
                                raw_t = str(row_sync.get('Updated_At', '')).strip()
                                m_t = re.search(r'\d{4}-(\d{2}-\d{2})\s+(\d{1,2}):(\d{2})', raw_t)
                                if m_t:
                                    cloud_time = f"{m_t.group(1)} {int(m_t.group(2)):02d}:{m_t.group(3)}"
                                else:
                                    cloud_time = raw_t[5:16].rstrip(':')
                                    
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

                        total_counted = 0.0
                        cur_counts = {}
                        for bill in bills_to_count:
                            b_flt = float(bill)
                            b_key_id = str(bill).replace('.', '_')
                            
                            # [통화별 지폐 및 동전 라벨 정규화]
                            if c == "VND":
                                b_label = f"{int(bill // 10000)}만동" if bill >= 10000 else f"{int(bill // 1000)}천동"
                            elif c == "EUR":
                                b_label = f"{int(bill)} €" if bill >= 1 else f"{int(round(bill * 100))} c"
                            elif c == "USD":
                                b_label = f"{int(bill)} $" if bill >= 1 else f"{int(round(bill * 100))} ¢"
                            elif c == "TRY":
                                b_label = f"{int(bill)} ₺" if bill >= 1 else f"{int(round(bill * 100))} kr"
                            elif c == "JPY":
                                b_label = f"{int(bill)} ¥"
                            elif c == "PHP":
                                b_label = f"{int(bill)} ₱"
                            else:
                                b_label = f"{bill} {c}"
                                
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
                            
                        # 센트 단위 부동소수점 오차 방지
                        total_counted = round(total_counted, 2) if c not in ["VND", "HUF", "JPY"] else round(total_counted)
                        
                        st.markdown(f"""
                            <div style='margin-top: 14px; margin-bottom: 8px; padding: 6px 10px; background-color: rgba(255, 255, 255, 0.05); border-radius: 8px; text-align: center; border: 1px solid rgba(255, 255, 255, 0.1);'>
                                <span style='font-size:11.5px; color:#A0AEC0;'>🧮 실물현금 합계 (지폐+동전)</span><br>
                                <span style='font-size:15px; font-weight:bold; color:#4EFEB3;'>{fmt.format(total_counted)} {c}</span>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        diff_val = round(total_counted - c_cash, 2) if c not in ["VND", "HUF", "JPY"] else round(total_counted - c_cash)
                        if total_counted > 0:
                            if abs(diff_val) < 0.001:
                                st.success("✅ 장부/실물 일치!")
                            elif diff_val < 0:
                                st.error(f"🚨 실물 **{fmt.format(abs(diff_val))} {c}** 부족!")
                            else:
                                st.warning(f"⚠️ 실물 **+{fmt.format(diff_val)} {c}** 초과!")

                        has_cloud_record = bool(cloud_counts)
                        has_conflict = has_cloud_record and (cur_counts != cloud_counts)

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
                                if st.button("📥 클라우드 가져오기", key=f"btn_pull_{c}", use_container_width=True):
                                    for b in bills_to_count:
                                        val_b = cloud_counts.get(float(b), 0)
                                        b_key_id = str(b).replace('.', '_')
                                        st.session_state[f"cnt_{c}_{b_key_id}"] = int(val_b) if val_b > 0 else None
                                    st.success("가져오기 완료!")
                                    time.sleep(0.6)
                                    st.rerun()
                                    
                            with col_sel2:
                                if st.button("⚠️ 현재값 덮어쓰기", key=f"btn_force_push_{c}", use_container_width=True):
                                    with st.spinner("클라우드 저장 중..."):
                                        if save_cash_inventory(st.session_state.current_trip, c, cur_counts, total_counted):
                                            st.success("덮어쓰기 완료!")
                                            time.sleep(0.6)
                                            st.rerun()
                        else:
                            if cloud_total > 0:
                                st.caption(f"클라우드 동기완료 ({cloud_time})")
                                
                            if st.button(f"💾 {c} 실물현금 저장", key=f"btn_save_normal_{c}", use_container_width=True):
                                with st.spinner("구글 시트 저장 중..."):
                                    if save_cash_inventory(st.session_state.current_trip, c, cur_counts, total_counted):
                                        st.success("🎉 저장 완료!")
                                        time.sleep(0.6)
                                        st.rerun()
                
                st.divider()

        # 4.01.03 | Net Financial Summary KPI Display (총 예산 및 실지출 총액)
        st.markdown("<div style='margin-top:35px;'></div>", unsafe_allow_html=True)
        st.metric("🏦 총 예산", f"{float(b_val):,.0f} 원")
        st.metric("💸 지출총액", f"{float(spent_val):,.0f} 원")

        # 4.01.04 | Dual Timezone Controller & Cache Refresh Trigger
        st.divider()
        ### 🎛️[GUI: Component] 타임존 및 새로고침
        st.markdown("<div style='margin-top:35px;'></div>", unsafe_allow_html=True)
        tz_sel = st.radio("📍 기준 시간 (Timezone)",["🇰🇷 한국 시간", "🌍 여행지 현지 시간"], horizontal=True, index=0 if "한국" in str(st.session_state.current_tz) else 1)
        st.session_state.current_tz = TZ_KST if "한국" in tz_sel else TRIP_TZ

        st.markdown("<div style='margin-top:35px;'></div>", unsafe_allow_html=True)
        if st.button("🔄 Cloud Refresh", use_container_width=True): st.cache_data.clear(); st.rerun()

# ------------------------------------------------------------------------------
# 4.02.00 | Top Navigation Router (여행지 선택 및 관제탑 모드 스위처)
# ------------------------------------------------------------------------------
# 4.02.01 | Chronological Trip Sorter
def sort_trips(trip_names):
    return sorted(trip_names, key=lambda x: (re.search(r'\((\d{4})\)', x).group(1) if re.search(r'\((\d{4})\)', x) else '0000', x), reverse=True)

sorted_trips = sort_trips(list(TRIP_CONFIGS.keys()))

# 4.02.02 | Global Flight/SPI View Mode Switcher
# [Modified] 비교(SPI) 모드를 풀다운 메뉴의 가장 마지막 독립 메뉴로 승격
SPECIAL_MODE = "📊 모든 여행지 물가비교"
dropdown_options = sorted_trips + [SPECIAL_MODE]

if 'show_spi' not in st.session_state: 
    st.session_state.show_spi = False

curr_idx = len(sorted_trips) if st.session_state.show_spi else (sorted_trips.index(st.session_state.current_trip) if st.session_state.current_trip in sorted_trips else 0)

# [수정] 2분할 컬럼 및 우측 라디오 테마 버튼 삭제 -> 단독 풀다운 배치
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

# ==============================================================================
# [Module 5.00.00] Global Comparison Mode (Module F: 다국적 물가 및 단가 비교)
# ==============================================================================
if st.session_state.show_spi:
    st.title("여행지 물가비교")
    df_all = load_all_trips_data()
    
    if not df_all.empty:

        # [Added] 1일비용, 호텔, 항공 3개 서브탭 생성
        sub_tab_spi, sub_tab_hotel, sub_tab_flight = st.tabs(["📊 1일비용", "🏨 호텔", "✈️ 항공"])
      
        # ----------------------------------------------------------------------
        # 5.01.00 | Channel 1: Daily Living Cost (SPI) (1일 체감비용 분석)
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
                    stay_nights[(trip, country)] = max(1, extracted_nights if extracted_nights > 0 else 1)

            df_spi = df_all[(df_all['Category'].isin(SPI_CATS)) & (~df_all['Country'].str.contains('글로벌|경유|크로아티아|불가리아', na=False))].copy()
            
            if not df_spi.empty:
                df_spi['KRW_val'] = df_spi.apply(lambda r: r['Amount'] if r['Currency'] == 'KRW' else r['Amount'] * float(r['AppliedRate']), axis=1)
                refund_df = df_all[(df_all['Category'] == '환불') & (~df_all['Country'].str.contains('글로벌|경유|크로아티아|불가리아', na=False))].copy()
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

                # 5.01.02 | Spending Factor Diagnosis (Theme Generator)
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
                
                # 5.01.03 | Daily Survival Cost Bar Chart & Table
                if not final_total_df.empty:
                    st.markdown("### 여행지 1박비용(원)")
                    def make_chart_label(r):
                        country, trip = str(r['Country']), str(r['TripName'])
                        if "발칸" in trip: return country 
                        match = re.search(r'([가-힣]+)', trip)
                        city = match.group(1) if match else ""
                        return f"{country}({city})" if city and city not in country else country

                    final_total_df['Chart_Label'] = final_total_df.apply(make_chart_label, axis=1)
                    display_df = final_total_df.copy()
                    display_df['Daily_SPI_Fmt'] = display_df['Daily_SPI'].apply(lambda x: f"{x:,.0f} 원")
                    display_df = display_df.rename(columns={'TripName': '여행명', 'Country': '국가', 'Travelers': '인원수', 'Nights': '숙박일(박)', 'Daily_SPI_Fmt': '1박 체감물가', 'Theme': '💡 특이사항 및 요인'})
                    st.dataframe(display_df[['여행명', '국가', '인원수', '숙박일(박)', '1박 체감물가', '💡 특이사항 및 요인']], use_container_width=True, hide_index=True)
                    
                    label_map = dict(zip(zip(final_total_df['TripName'], final_total_df['Country']), final_total_df['Chart_Label']))
                    agg_group['Chart_Label'] = agg_group.apply(lambda r: label_map.get((r['TripName'], r['Country']), r['Country']), axis=1)
                    category_order_x = final_total_df['Chart_Label'].tolist()
                    stack_order = ['📱 기타', '🚕 로컬교통', '🍔 식음료', '🏄 투어/액티비티', '🏨 숙박', '🚗 렌트카']
                    color_map = {'🚗 렌트카': '#D32F2F', '🏨 숙박': '#1976D2', '🏄 투어/액티비티': '#9C27B0', '🍔 식음료': '#4CAF50', '🚕 로컬교통': '#00ACC1', '📱 기타': '#795548'}
                    fig_stacked = px.bar(agg_group, x='Chart_Label', y='Daily_SPI', color='SPI_Group', color_discrete_map=color_map, category_orders={"Chart_Label": category_order_x, "SPI_Group": stack_order})
                    fig_stacked.update_layout(barmode='stack', margin=dict(l=10, r=10, t=10, b=30), legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5, title=None), xaxis_title=None, yaxis_title=None)
                    st.plotly_chart(fig_stacked, use_container_width=True)

        # ----------------------------------------------------------------------
        # 5.02.00 | Channel 2: Hotel Unit Cost Analytics (호텔 요금 및 투숙 비교)
        # ----------------------------------------------------------------------
        with sub_tab_hotel:
            st.subheader("🏨 호텔 1박 요금 비교")
            st.caption("💡 실제 지출이 발생한 호텔 결제 정보(Category='호텔', Amount > 0)만 수집하며, 단순 일정인 체크인은 제외합니다. 동일 호텔명으로 기록된 여러 결제 건 중 '가장 금액이 큰 건'을 기본숙박비로 지정하여 투숙일수를 추출하고, '그 외 금액이 작은 결제 건'은 일수 증가 없이 기타추가비용(업그레이드/세금 등)으로 자동 분류하여 정합성을 보장합니다.")
            
            # 5.02.01 | Hotel Data Cleaning & Magnitude Priority Sorter
            def clean_hotel_name(desc):
                s = str(desc)
                s = re.sub(r'^\[.*?\]\s*', '', s)
                parts = re.split(r'[,|]', s)
                name = parts[0].strip()
                name = re.sub(r'\s*\d+\s*박.*$', '', name)
                return name.strip()
            
            raw_hotel_rows = []
            refund_rows = []
            
            # 1. 1차 수집 (지출액이 존재하는 호텔/수수료 내역만 텍스트 차단 없이 우선 긁어모음)
            for _, row in df_all.iterrows():
                cat = str(row['Category']).strip()
                desc = str(row['Description']).strip()
                amt = float(row['Amount'])
                is_exp = int(row['IsExpense']) if 'IsExpense' in row else 1
                
                # 1-1. 환불 내역 수집
                if cat == '환불':
                    desc_lower = desc.lower()
                    if any(k in desc_lower for k in ["호텔", "숙박", "인페라", "라이온", "스플랜디도", "벨몬트", "센터호텔", "agoda", "아고다", "booking", "소피아", "코럴베이", "파노라마"]):
                        refund_rows.append(row)
                        continue
                
                # 1-2. 실제 지출이 발생한 호텔 카테고리 수집 (IsExpense == 1, Amount > 0)
                if cat in ['호텔', '숙박'] and is_exp == 1 and amt > 0:
                    h_name = clean_hotel_name(desc)
                    # 텍스트 내 박수 정보 사전 추출
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
                    
                # 1-3. 카테고리는 호텔이 아니지만, 별도의 도시세 수수료로 기록된 행 수집
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
            
            # 5.02.02 | Multi-Payment Merging & Surcharge Aggregator
            from collections import defaultdict
            grouped_hotels = defaultdict(list)
            for r in raw_hotel_rows:
                key = (r['TripName'], r['Country'], r['Clean_Name'])
                grouped_hotels[key].append(r)
                
            consolidated_hotels = []
            for key, rows in grouped_hotels.items():
                trip_name, country, clean_name = key
                
                # [Magnitude Priority Sorting] 원화 요금 기준 크기순 내림차순 정렬!
                rows_sorted = sorted(rows, key=lambda x: x['Cost_KRW'], reverse=True)
                
                # 가장 금액이 큰 행을 '기본 숙박비' 핵심 지표로 채택하고 투숙일수 상속
                primary_stay = rows_sorted[0]
                base_cost = primary_stay['Cost_KRW']
                nights = primary_stay['Nights']
                
                # 만약 가장 금액이 큰 행에 "X박" 정보가 없고 서브 행에 있다면 서브 행에서 일수를 백업 상속
                if nights == 0:
                    for r in rows_sorted[1:]:
                        if r['Nights'] > 0:
                            nights = r['Nights']
                            break
                
                # 박수가 명시되지 않은 호텔은 비교 차트 및 정규 산정에서 엄격하게 자동 배제
                if nights == 0:
                    continue
                
                # 그 외 크기가 작은 결제 건들은 일수 증가 없는 '기타 추가비용'으로 자동 분류 및 누적합산
                extra_fees = sum(r['Cost_KRW'] for r in rows_sorted[1:])
                
                # 환불 내역 매칭 연산
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
                    'Upgrade_Cost_KRW': extra_fees, # 이종 결제나 도시세, 업그레이드 등 모든 추가 결제는 여기에 병합!
                    'Refund_KRW': total_refund,
                    'Cancellation_Rate': cancellation_rate,
                    'FX_GainLoss': total_fx_loss
                })

            # 5.02.03 | Net Nightly Rate & Cancellation Matrix Table
            if consolidated_hotels:
                display_hotel_rows = []
                chart_data = []
                
                for h in consolidated_hotels:
                    # 기본 숙박비 + 업그레이드 비용 + 도시세 - 환불액 = 실지불 순액
                    net_cost = h['Cost_KRW'] + h['Upgrade_Cost_KRW'] - h['Refund_KRW']
                    nights = h['Nights']
                    avg_rate = net_cost / nights if nights > 0 and h['Cancellation_Rate'] < 100.0 else 0.0
                    
                    status_str = "정상 투숙"
                    if h['Cancellation_Rate'] >= 100.0: status_str = "🔴 100% 취소"
                    elif h['Cancellation_Rate'] > 0.0: status_str = f"🟡 부분취소 ({h['Cancellation_Rate']:.1f}%)"
                    
                    fx_diff = h['FX_GainLoss']
                    fx_loss_str = f"{fx_diff:+,.0f}원" if fx_diff != 0 else "-"
                    
                    # 업그레이드 금액이 있을 경우 기본 숙박비에 합산 표시
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
                            'Hotel_Label': f"{h['Clean_Name']} ({h['TripName']})",
                            '1박당 요금(원)': avg_rate
                        })
                
                st.dataframe(pd.DataFrame(display_hotel_rows), use_container_width=True, hide_index=True)
                
                # 5.02.04 | Hotel Cost Comparison Bar Chart
                if chart_data:
                    chart_df = pd.DataFrame(chart_data).sort_values(by='1박당 요금(원)', ascending=True)
                    fig_hotel = px.bar(chart_df, x='Hotel_Label', y='1박당 요금(원)', color='1박당 요금(원)', color_continuous_scale='Blues', title="🏨 숙소별 1박 실질 투숙 비용 비교 (도시세/업그레이드 포함/취소 제외)")
                    fig_hotel.update_layout(xaxis_title=None, yaxis_title="1박 평균 요금 (원)", margin=dict(l=10, r=10, t=30, b=100))
                    st.plotly_chart(fig_hotel, use_container_width=True, config={'displaylogo': False})
            else:
                st.info("비교할 호텔 숙박 내역이 없습니다. (카테고리가 '호텔', '숙박'이며 내용에 'X박'이 명시되어야 합니다.)")
                
        # ----------------------------------------------------------------------
        # 5.03.00 | Channel 3: Flight Pricing Matrix (항공권 왕복 환산 및 노선 비교)
        # ----------------------------------------------------------------------
        with sub_tab_flight:
            st.subheader("✈️ 항공권 요금 비교")
            st.caption("💡 각 항공권의 왕복/편도 여정을 구분하여 '1인당 왕복 환산 요금'으로 공평하게 비교합니다. 노선(Route)이 기재되지 않은 수화물/수수료 행은 해당 여행지의 메인 항공권에 자동으로 합산되며, 여행지별 설정된 인원수(Travelers)로 나누어 실질적인 '1인당 비용'을 산출합니다.")
            
            # 5.03.01 | Flight Route Extraction & Journey Classifier (노선 추출용 헬퍼)
            def extract_airport_route(text):
                match = re.search(r'([가-힣a-zA-Z\s]+)-([가-힣a-zA-Z\s]+)', str(text))
                if match:
                    dep = match.group(1).replace('[', '').replace(']', '').strip()
                    arr = match.group(2).replace('[', '').replace(']', '').strip()
                    dep_clean = dep.split()[-1] if dep.split() else dep
                    arr_clean = arr.split()[0] if arr.split() else arr
                    return f"{dep_clean}-{arr_clean}"
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
                    
                    # [Modified] 여정 유형 자동 감별 규칙 고도화
                    # Description에 '귀국' 혹은 '왕복'이 들어가야 왕복으로 인정하며, 그 외는 '편도'로 기본 설정하여 기항지 간 편도 항공권 완벽 수용
                    # ➔ 🚀 [Modified] Dan의 명시적 키워드('다구간', '왕복', '편도') 우선 감별 룰 수립
                    if "다구간" in desc_lower:
                        f_type = "다구간"
                    elif "왕복" in desc_lower:
                        f_type = "왕복"
                    elif "편도" in desc_lower:
                        f_type = "편도"
                    else:
                        # 폴백 조건: 키워드가 모두 없는 과거 데이터 구제
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
                        # 노선이 적혀있지 않은 자잘한 수화물/수수료 행은 surcharge로 분류
                        flight_surcharges.append(flight_data)
                        
                elif cat == '환불':
                    desc_lower = desc.lower()
                    if any(k in desc_lower for k in ["항공", "비행기", "페가수스", "세르비아", "항공사", "flight", "airline"]):
                        flight_refund_rows.append(row)

            # 5.03.02 | Surcharge/Baggage Allocation & Penalty Calculator
            for f in primary_flights:
                f_route = f['Route']
                
                # 동일 여행지 내에서 노선이 없는 수화물/추가비용 행들을 메인 항공비용에 누적 합산
                for s in flight_surcharges:
                    if s['TripName'] == f['TripName']:
                        f['Surcharge_Sum_KRW'] += s['Ticket_KRW']
                
                # 동일 여행지 내 노선별 환불 매칭 및 위약금 연산
                for r in flight_refund_rows:
                    if r['TripName'] == f['TripName']:
                        r_route = extract_airport_route(r['Description'])
                        if f_route and r_route and f_route == r_route:
                            r_cost_krw = r['Amount'] if r['Currency'] == 'KRW' else r['Amount'] * r['AppliedRate']
                            f['Refund_KRW'] += r_cost_krw
                            f['Refund_Foreign'] += r['Amount']
                
                # 1인당 계산 및 왕복 환산 요금 연산
                num_travelers = travelers_map.get(f['TripName'], 2)
                
                # 총 비용 = 기본 티켓값 + 수수료 + 수화물 추가금
                total_initial = f['Ticket_KRW'] + f['Extra_Fee_KRW'] + f['Surcharge_Sum_KRW']
                f['Net_Cost_KRW'] = total_initial - f['Refund_KRW']
                f['Refund_Rate'] = min(100.0, (f['Refund_Foreign'] / f['Amount']) * 100.0) if f['Amount'] > 0 else 0.0
                f['Loss_KRW'] = f['Ticket_KRW'] - f['Refund_KRW'] if f['Refund_KRW'] > 0 else 0.0
                
                # 1인당 비용으로 전환
                f['Per_Person_Initial_KRW'] = total_initial / num_travelers
                f['Per_Person_Net_KRW'] = f['Net_Cost_KRW'] / num_travelers
                f['Per_Person_Loss_KRW'] = f['Loss_KRW'] / num_travelers
                f['Per_Person_Refund_KRW'] = f['Refund_KRW'] / num_travelers
                
                # 5.03.03 | Per-Person Roundtrip Equivalent Normalizer
                # [Modified] 왕복 요금으로 환산 공식 적용
                # 편도 항공권일 경우 1인당 Net 요금에 2를 곱하여 왕복 환산 요금 산출
                if f['Type'] == "편도":
                    f['RT_Equivalent_Per_Person_KRW'] = f['Per_Person_Net_KRW'] * 2
                else:
                    f['RT_Equivalent_Per_Person_KRW'] = f['Per_Person_Net_KRW']

            # 5.03.04 | Flight Price Benchmark Bar Chart & Display Table
            if primary_flights:
                display_flight_rows = []
                chart_flight_data = []
                
                for f in primary_flights:
                    status_str = "정상"
                    if f['Refund_Rate'] >= 100.0: status_str = "🔴 100% 취소"
                    elif f['Refund_Rate'] > 0.0: status_str = f"🟡 부분환불 ({f['Refund_Rate']:.1f}%)"
                    
                    num_travelers = int(travelers_map.get(f['TripName'], 2))
                    
                    # 왕복 환산 요금 칼럼 포맷 지정 (편도일 경우 '왕복요금으로 환산' 명시)
                    if f['Type'] == "편도":
                        rt_eq_str = f"{f['RT_Equivalent_Per_Person_KRW']:,.0f}원 (왕복요금으로 환산)"
                    else:
                        rt_eq_str = f"{f['RT_Equivalent_Per_Person_KRW']:,.0f}원"
                        
                    display_flight_rows.append({
                        '여행명': f['TripName'],
                        '노선(공항)': f['Route'],
                        '인원수': f"{num_travelers}인",
                        '구분': f['Type'], # [Modified] 편도/왕복 정확히 표기
                        '1인당 구매요금': f"{f['Per_Person_Initial_KRW']:,.0f}원",
                        '1인당 환불액': f"{f['Per_Person_Refund_KRW']:,.0f}원" if f['Per_Person_Refund_KRW'] > 0 else "-",
                        '환불율': f"{f['Refund_Rate']:.1f}%" if f['Refund_Rate'] > 0 else "-",
                        '1인당 취소손실': f"{f['Per_Person_Loss_KRW']:,.0f}원" if f['Per_Person_Loss_KRW'] > 0 else "-",
                        '1인당 실지불(Net)': f"{max(0, f['Per_Person_Net_KRW']):,.0f}원",
                        '1인당 왕복 환산 요금': rt_eq_str, # [Modified] 편도 시 '왕복요금으로 환산' 안내 문구 포함
                        '상태': status_str
                    })
                    
                    if f['Refund_Rate'] < 100.0 and f['RT_Equivalent_Per_Person_KRW'] > 0:
                        chart_flight_data.append({
                            'Flight_Label': f"{f['Route']} ({f['TripName']})",
                            '1인당 왕복 환산 요금(원)': f['RT_Equivalent_Per_Person_KRW']
                        })
                
                st.dataframe(pd.DataFrame(display_flight_rows), use_container_width=True, hide_index=True)
                
                if chart_flight_data:
                    chart_flight_df = pd.DataFrame(chart_flight_data).sort_values(by='1인당 왕복 환산 요금(원)', ascending=True)
                    fig_flight = px.bar(chart_flight_df, x='Flight_Label', y='1인당 왕복 환산 요금(원)', color='1인당 왕복 환산 요금(원)', color_continuous_scale='Reds', title="✈️ 1인당 왕복 기준 항공요금 공평 비교 (편도 노선 2배 환산 적용/취소 제외)")
                    fig_flight.update_layout(xaxis_title=None, yaxis_title="1인당 왕복 환산 요금 (원)", margin=dict(l=10, r=10, t=30, b=100))
                    st.plotly_chart(fig_flight, use_container_width=True, config={'displaylogo': False})
            else:
                st.info("비교할 항공권 내역이 없습니다.")


# ==============================================================================
# [Module 6.00.00] Individual Trip Manager Views (개별 여행 전용 모듈)
# ==============================================================================
else:
    st.title(f"{st.session_state.current_trip}")
    
    # [Modified] 5개 탭에서 무거웠던 '비교' 탭을 완전히 제거
    tab_in, tab_his, tab_stats, tab_final = st.tabs(["📝 입력", "🔍 조회", "📊 일일", "🏁 요약"])

    # --------------------------------------------------------------------------
    # 6.01.00 | Console Tab 1: Input Engine (입력 콘솔)
    # --------------------------------------------------------------------------
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

        # 6.01.01 | Sub-Form: General Expense (일반 지출 및 영수증 다중 AI 스캔)
        if mode == "일반 지출":        
            def_index = EXPENSE_CATS.index(st.session_state.last_cat_name) if st.session_state.last_cat_name in EXPENSE_CATS else 0
            cat = st.radio("항목 선택", EXPENSE_CATS, index=def_index, horizontal=True, key="exp_cat")
            st.session_state.last_cat_name = cat
            
            if st.session_state.get('clear_exp_desc', False):
                st.session_state.exp_desc = ""
                st.session_state.clear_exp_desc = False
                
            col_desc, col_receipt = st.columns([3, 1])
            
            with col_receipt: 
                uploaded_files = st.file_uploader("📸 영수증 첨부 (다중 가능)", type=['png', 'jpg', 'jpeg'], key="exp_receipt", accept_multiple_files=True)
                if uploaded_files:
                    if st.button("🤖 영수증 AI 스캔 (통합 번역)", use_container_width=True):
                        with st.spinner(f"AI가 {len(uploaded_files)}장의 사진을 분석 중..."):
                            all_raw_texts = []
                            for file in uploaded_files:
                                raw_text = extract_text_from_vision_api(file.getvalue())
                                all_raw_texts.append(raw_text)
                            combined_text = "\n---\n".join(all_raw_texts)
                            smart_text = summarize_receipt_with_gemini(combined_text)
                            if smart_text:
                                st.session_state.exp_desc = st.session_state.get('exp_desc', '') + "\n" + smart_text
                                st.rerun()
                                
            with col_desc: 
                desc = st.text_area("📝 내용 (상호명 및 다중 내역)", placeholder="예: 안바카페 - 소고기버거\n반미정식", height=120, key="exp_desc")
                
            col_m1, col_m2, col_m3 = st.columns([1, 1, 1])
            with col_m1: 
                curr_opts =[IN_CURR, "KRW", "USD"] +[c for c in available_currs if c not in[IN_CURR, "KRW", "USD"]]
                curr = st.selectbox("통화", curr_opts, key="exp_curr")
            with col_m2:
                # [Added] '해외송금(한국계좌)' 옵션 추가
                if curr != "KRW": met_options = [f"현금({curr})", f"트래블카드({curr})", f"호텔외상({curr})", "원화계좌(한국)", "해외송금(한국계좌)", "원화계좌(현지)"]
                else: met_options = ["원화계좌(한국)", "원화계좌(현지)"]
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
                if curr == "KRW" or (curr == IN_CURR and IN_MULTI == 100): amt = st.number_input(f"금액 ({curr})", min_value=0, step=1000 if curr != "KRW" else 1, format="%d", key="exp_amt_int")
                else: amt = st.number_input(f"금액 ({curr})", min_value=0.0, step=1.0, format="%.2f", key="exp_amt_float")
            with col_a2:
                if curr != "KRW" and amt > 0:
                    calc_rate = auto_calc_fifo_rate(amt, met, curr)
                    st.caption(f"💡 {curr} 인벤토리 계산 환율: **{calc_rate:.5f}**")
                    cr_final = st.number_input("확정 환율", value=float(calc_rate), format="%.5f", key=f"exp_cr_auto_{met}_{amt}")
                else: cr_final = st.number_input("확정 환율", value=(1.0 if curr=="KRW" else get_default_rate(curr)), format="%.5f", key=f"exp_cr_man_{curr}")
                
            if st.button("🚀 지출 기록하기", use_container_width=True):
                final_receipt_urls = ""
                if uploaded_files:
                    with st.spinner("📸 모든 영수증을 클라우드에 보관 중..."):
                        url_list = []
                        for file in uploaded_files:
                            u = upload_image_to_imgbb(file)
                            if u: url_list.append(u)
                        final_receipt_urls = ",".join(url_list)
                
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
                    'Receipt_URL': final_receipt_urls
                }])
                if append_new_data(new_row): 
                    st.session_state.clear_exp_desc = True
                    st.rerun()

        # 6.01.02 | Sub-Form: Flight Integrated Scheduler (항공권 특수)
        # [Modified] 항공권 모드 고도화 (편도/왕복 및 메모 추가)
        elif mode == "🛫 항공권(특수)":
            st.subheader("✈️ 항공권 및 스케줄 통합 기록")
            
            f_trip_type = st.radio("여정 구분", ["왕복", "편도"], horizontal=True)
            
            c1, c2, c3 = st.columns(3)
            with c1: f_gw = st.text_input("1. 결제 플랫폼 (필수)", placeholder="예: 트립닷컴")
            with c2: f_carrier = st.text_input("2. 항공사", placeholder="예: 비엣젯")
            with c3: f_route = st.text_input("3. 노선", placeholder="예: 부산-푸꾸옥")

            c4, c5 = st.columns(2)
            with c4:
                st.info(f"🛫 {'출국' if f_trip_type == '왕복' else '탑승'} 스케줄")
                f_dep_info = st.text_input("4. 스케줄 정보", placeholder="예: VJ969, 07:45 - 11:10")
                f_dep_date = st.date_input("5. 탑승 날짜", value=sel_date)
            with c5:
                if f_trip_type == "왕복":
                    st.success("🛬 귀국 스케줄")
                    f_ret_info = st.text_input("6. 귀국편 정보", placeholder="예: VJ968, 23:10 - 06:40 (+1)")
                    f_ret_date = st.date_input("7. 귀국 날짜", value=sel_date + timedelta(days=7))
                else:
                    st.empty() # 자리 맞춤
                    f_ret_info, f_ret_date = "", None

            c6, c7, c8 = st.columns([1, 1, 1])
            with c6: f_baggage = st.selectbox("8. 위탁수화물", ["포함", "미포함", "일부포함"])
            with c7: f_bag_memo = st.text_input("9. 수화물 상세", placeholder="예: 귀국편 20kg 추가")
            # [Added] '해외송금(한국계좌)' 옵션 추가
            with c8: f_asset = st.selectbox("10. 결제 수단", ["네이버페이(원화고정)", "원화계좌(한국)", "해외송금(한국계좌)", "트래블카드(외화)", "신용카드(원화결제)", "기타"])
                
            f_memo = st.text_input("📝 비고/메모 (결제 후 변경 이력 등 기록)", placeholder="예: 3/10 결제 후, 3/12에 항공사 스케줄 1회 변경됨")

            st.divider()
            c9, c10, c11, c12 = st.columns([1, 2, 1, 1])
            with c9: 
                curr_opts_flight = ["KRW", "USD", "EUR"] + [c for c in available_currs if c not in ["KRW", "USD", "EUR"]]
                f_curr = st.selectbox("11. 통화", curr_opts_flight)
            with c10: f_amt = st.number_input(f"12. 결제 금액({f_curr})", min_value=0.0, step=1.0)
            with c11: f_rate = st.number_input("13. 환율", value=1.0 if f_curr=="KRW" or "네이버" in f_asset else get_default_rate(f_curr), format="%.4f")
            with c12: f_fee = st.number_input("14. 수수료(원)", min_value=0)

            btn_label = "🚀 항공권 및 출입국 일정(왕복) 동시 기록" if f_trip_type == "왕복" else "🚀 항공권 및 편도 일정 동시 기록"
            if st.button(btn_label, use_container_width=True, type="primary"):
                if not f_gw or not f_route:
                    st.warning("결제 플랫폼과 노선 정보는 필수입니다."); st.stop()
                
                clean_asset = f_asset.split('(')[0].strip()
                if "트래블카드" in f_asset:
                    clean_asset = f"트래블카드({f_curr})" # 통화에 맞춰 트래블카드 동적 셋팅

                route_str = f" | 출국:{f_dep_info}" if f_dep_info else ""
                ret_str = f" | 귀국:{f_ret_info}" if f_trip_type == "왕복" and f_ret_info else ""
                memo_str = f" | 메모:{f_memo}" if f_memo else ""
                
                full_desc = f"[{f_gw}+{clean_asset}] {f_route}({f_carrier}){route_str}{ret_str} | 수화물:{f_baggage}({f_bag_memo}){memo_str}"
                flight_row = pd.DataFrame([{'Date': sel_date.strftime("%Y-%m-%d(%a)"), 'Country': sel_node, 'Category': '항공권', 'Description': full_desc, 'Currency': f_curr, 'Amount': f_amt, 'PaymentMethod': clean_asset, 'IsExpense': 1, 'AppliedRate': f_rate, 'Note': f"수수료:{f_fee}원" if f_fee > 0 else ""}])
                
                new_rows = [flight_row]
                
                if f_dep_info:
                    dep_desc = f"🛫 {f_route} {'출국' if f_trip_type == '왕복' else '탑승'} ({f_dep_info})"
                    dep_row = pd.DataFrame([{'Date': f_dep_date.strftime("%Y-%m-%d(%a)"), 'Country': sel_node, 'Category': '출국' if f_trip_type == '왕복' else '항공스케줄', 'Description': dep_desc, 'Currency': 'KRW', 'Amount': 0, 'PaymentMethod': '정보', 'IsExpense': 0, 'AppliedRate': 1.0, 'Note': 'Auto-created'}])
                    new_rows.append(dep_row)
                    
                if f_trip_type == "왕복" and f_ret_info:
                    arr_desc = f"🛬 {f_route} 입국 ({f_ret_info})"
                    arr_row = pd.DataFrame([{'Date': f_ret_date.strftime("%Y-%m-%d(%a)"), 'Country': sel_node, 'Category': '입국', 'Description': arr_desc, 'Currency': 'KRW', 'Amount': 0, 'PaymentMethod': '정보', 'IsExpense': 0, 'AppliedRate': 1.0, 'Note': 'Auto-created'}])
                    new_rows.append(arr_row)
                
                if append_new_data(pd.concat(new_rows, ignore_index=True)):
                    st.success("항공권과 일정이 모두 기록되었습니다!"); time.sleep(1); st.rerun()
                    
        # 6.01.03 | Sub-Form: Hotel Integrated Booking (호텔 특수)
        # [Modified] 호텔 모드 (결제수단 동적 매핑)
        elif mode == "🏨 호텔(특수)":
            st.subheader("🏨 호텔/숙소 예약 상세 기록")
            c1, c2 = st.columns(2)
            with c1:
                h_gw = st.text_input("1. 결제 플랫폼 (필수)", placeholder="예: Agoda, Booking.com")
                h_name = st.text_input("2. 호텔명", placeholder="예: 인터콘티넨털 호치민")
                h_checkin = st.date_input("3. 체크인", value=sel_date)
                # [Added] '해외송금(한국계좌)' 옵션 추가
                h_asset = st.selectbox("4. 결제 수단", ["네이버페이(원화고정)", "원화계좌(한국)", "해외송금(한국계좌)", "트래블카드(외화)", "신용카드(원화결제)", "기타"])
            with c2:
                h_nights = st.number_input("5. 숙박 일수", min_value=1, step=1)
                h_checkout = h_checkin + timedelta(days=h_nights)
                st.caption(f"📅 체크아웃 예정: {h_checkout.strftime('%Y-%m-%d')}")
                h_detail = st.text_area("6. 내용 (룸타입/특징)", placeholder="예: 디럭스 더블, 수영장뷰, 30m2", height=68)
                h_curr = st.selectbox("7. 결제 통화", ["KRW", "VND", "USD", "PHP", "EUR", "CNY", "TRY"], key="h_curr")

            c3, c4, c5 = st.columns(3)
            with c3: h_amt = st.number_input(f"8. 결제 금액({h_curr})", min_value=0.0, step=1.0)
            with c4: h_rate = st.number_input("9. 적용 환율", value=1.0 if h_curr=="KRW" or "네이버" in h_asset else get_default_rate(h_curr), format="%.4f")
            with c5: h_fee = st.number_input("10. 환율 수수료(원)", min_value=0)

            if st.button("🚀 호텔 예약 저장", use_container_width=True):
                if not h_gw: st.warning("결제 플랫폼을 입력하세요."); st.stop()
                
                clean_asset = h_asset.split('(')[0].strip()
                if "트래블카드" in h_asset:
                    clean_asset = f"트래블카드({h_curr})"
                    
                full_desc = f"[{h_gw}] {h_name} | {h_nights}박({h_checkin.strftime('%m/%d')}~{h_checkout.strftime('%m/%d')}) | {h_detail.replace('\\n', ' ')}"
                new_row = pd.DataFrame([{'Date': sel_date.strftime("%Y-%m-%d(%a)"), 'Country': sel_node, 'Category': '호텔', 'Description': full_desc, 'Currency': h_curr, 'Amount': h_amt, 'PaymentMethod': clean_asset, 'IsExpense': 1, 'AppliedRate': h_rate, 'Note': f"수수료:{h_fee}원" if h_fee > 0 else ""}])
                if append_new_data(new_row): st.rerun()
                    
        # 6.01.04 | Sub-Form: Asset Transfer & Dual FX Swap (자산 이동/재환전/개인지출)
        # [Modified] 자산 이동 (결제수단 트래블카드로 통일)
        # ➔ 🚀 [Modified] 및 [Added] 아래와 같이 수정/추가
        elif mode == "자산 이동":
            st.subheader("🔁 자산 이동 및 환전")
            ty = st.selectbox("유형",[
                "이월잔액 (지난여행 -> 현금잔액)", # [Added] 이월잔액 항목 추가
                "직접환전 (원화계좌 -> 로컬현금)", 
                "이종환전 (외화 -> 타국 외화)",
                "충전 (원화계좌 -> 트래블카드)", 
                "ATM출금 (카드 -> 로컬현금)", 
                "재환전 (외화 -> 원화계좌)",
                "개인지출 (외화잔액 -> 여행외 소비)" # [Added] 개인지출 유형 추가
            ], key="tr_type")
            c1, c2 = st.columns(2)
            
            # [Added] 이종환전 전용 처리 로직 (듀얼 트랜잭션 고도화: 카드-카드, 카드-현금 완벽 지원)
            if "이종환전" in ty:
                with c1:
                    curr_opts_tr = [c for c in available_currs if c not in ["KRW"]]
                    curr_tr = st.selectbox("얻게 되는 통화 (Target)", curr_opts_tr, key="tr_target_curr")
                    # [Added] 얻은 통화를 보관할 지갑 형태 지정 (카테고리 자동 유추에 사용)
                    tr_target_met = st.selectbox("얻은 통화 보관 자산", [f"트래블카드({curr_tr})", f"현금({curr_tr})"], key="tr_target_met")
                    
                    if curr_tr == IN_CURR and IN_MULTI == 100: 
                        t_amt = st.number_input(f"얻은 금액 ({curr_tr})", min_value=0, step=1000, format="%d", key="tr_target_int")
                    else: 
                        t_amt = st.number_input(f"얻은 금액 ({curr_tr})", min_value=0.0, step=10.0, format="%.2f", key="tr_target_flt")
                with c2:
                    curr_opts_src = [c for c in available_currs if c not in ["KRW", curr_tr]]
                    curr_src = st.selectbox("지불하는 외화 (Source)", curr_opts_src, key="tr_source_curr")
                    src_met = st.selectbox("지불 재원 출처", [f"트래블카드({curr_src})", f"현금({curr_src})"], key="tr_source_met")
                    s_amt = st.number_input(f"지불한 금액 ({curr_src})", min_value=0.0, step=10.0, format="%.2f", key="tr_source_flt")
                    
                    if s_amt > 0 and t_amt > 0:
                        fifo_rate = auto_calc_fifo_rate(s_amt, src_met, curr_src)
                        est_krw_cost = s_amt * fifo_rate
                        target_rate = est_krw_cost / t_amt
                        st.info(f"💡 시스템 내 지불 원가: **{est_krw_cost:,.0f} 원**")
                        st.success(f"🎯 획득한 {curr_tr}의 산출 환율: **{target_rate:.5f}**")
                        
                if st.button("🔄 이종환전 실행 (차감 및 충전 동시기록)", use_container_width=True, type="primary"):
                    if s_amt <= 0 or t_amt <= 0:
                        st.warning("금액을 정확히 입력해 주세요.")
                        st.stop()
                    
                    fifo_rate = auto_calc_fifo_rate(s_amt, src_met, curr_src)
                    target_rate = (s_amt * fifo_rate) / t_amt if t_amt > 0 else 0
                    
                    # 1. 지불 외화 차감 기록 (이종환전 카테고리)
                    desc_src = f"이종환전 지불 (-> {curr_tr} {t_amt})"
                    row_src = pd.DataFrame([{'Date': sel_date.strftime("%Y-%m-%d(%a)"), 'Country': sel_node, 'Category': '이종환전', 'Description': desc_src, 'Currency': curr_src, 'Amount': s_amt, 'PaymentMethod': src_met, 'IsExpense': 0, 'AppliedRate': fifo_rate, 'Note': '', 'Receipt_URL': ''}])
                    
                    # 2. 획득 외화 충전 기록 (보관자산 형태에 따라 '충전' 또는 '직접환전'으로 동적 매핑하여 카드/현금 인벤토리 완벽 분류)
                    tgt_cat = "충전" if "트래블카드" in tr_target_met else "직접환전"
                    desc_tgt = f"이종환전 획득 (<- {curr_src} {s_amt})"
                    row_tgt = pd.DataFrame([{'Date': sel_date.strftime("%Y-%m-%d(%a)"), 'Country': sel_node, 'Category': tgt_cat, 'Description': desc_tgt, 'Currency': curr_tr, 'Amount': t_amt, 'PaymentMethod': src_met, 'IsExpense': 0, 'AppliedRate': target_rate, 'Note': '', 'Receipt_URL': ''}])
                    
                    if append_new_data(pd.concat([row_src, row_tgt], ignore_index=True)): 
                        st.success("이종 자산 환전 기록이 성공적으로 완료되었습니다!")
                        time.sleep(1)
                        st.rerun()

            # [Added] 이월잔액 전용 입력기 설계 및 FIFO 계산 루틴 탑재
            elif "이월잔액" in ty:
                with c1:
                    curr_opts_tr = [IN_CURR, "USD"] + [c for c in available_currs if c not in [IN_CURR, "USD", "KRW"]]
                    curr_tr = st.selectbox("대상 통화", curr_opts_tr, key="tr_curr")
                    if curr_tr == IN_CURR and IN_MULTI == 100: t_amt = st.number_input(f"가져온 잔돈 금액 ({curr_tr})", min_value=0, step=1000, format="%d", key="tr_target_int")
                    else: t_amt = st.number_input(f"가져온 잔돈 금액 ({curr_tr})", min_value=0.0, step=10.0, format="%.2f", key="tr_target_flt")
                with c2:
                    applied_tr_rate = st.number_input("당시 취득 환율 (원가)", value=get_default_rate(curr_tr), format="%.5f")
                    st.caption(f"💡 시스템 투입 가치: **{(t_amt * applied_tr_rate):,.0f} 원**")
                if st.button("🚀 이월잔고 현금지갑에 투입", use_container_width=True, type="primary"):
                    new_row = pd.DataFrame([{'Date': sel_date.strftime("%Y-%m-%d(%a)"), 'Country': sel_node, 'Category': '이월잔액', 'Description': f"지난여행 잔돈 유입 (-> 현금({curr_tr}))", 'Currency': curr_tr, 'Amount': t_amt, 'PaymentMethod': '기타(지난여행)', 'IsExpense': 0, 'AppliedRate': applied_tr_rate, 'Note': 'Carry-over Asset', 'Receipt_URL': ''}])
                    if append_new_data(new_row): st.rerun()

            elif "재환전" in ty:
                with c1:
                    curr_opts_tr =[c for c in available_currs if c not in ["KRW"]]
                    curr_tr = st.selectbox("팔(Sell) 통화", curr_opts_tr, key="tr_curr")
                    s_amt = st.number_input(f"팔 외화 금액 ({curr_tr})", min_value=0.0, step=100.0, format="%.2f", key="tr_sell_flt")
                    source_met = st.selectbox("외화 출처",[f"트래블카드({curr_tr})", f"현금({curr_tr})"], key="tr_sell_met")
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
                    
                    new_rows = [main_row]
                    fx_diff = rcv_krw - (s_amt * auto_calc_fifo_rate(s_amt, source_met, curr_tr)) if s_amt > 0 else 0
                    if abs(fx_diff) >= 1:
                        fx_amt = -abs(fx_diff) if fx_diff > 0 else abs(fx_diff)
                        desc_fx = f"[{curr_tr} 재환전] 환차익" if fx_diff > 0 else f"[{curr_tr} 재환전] 환차손"
                        fx_row = pd.DataFrame([{'Date': sel_date.strftime("%Y-%m-%d(%a)"), 'Country': sel_node, 'Category': '수수료', 'Description': desc_fx, 'Currency': 'KRW', 'Amount': fx_amt, 'PaymentMethod': '원화계좌(한국)', 'IsExpense': 1, 'AppliedRate': 1.0, 'Note': 'Auto-FX Diff', 'Receipt_URL': ''}])
                        new_rows.append(fx_row)
                    if append_new_data(pd.concat(new_rows, ignore_index=True)): st.rerun()

            # [Added] 개인지출 전용 입력기 설계 및 FIFO 계산 루틴 탑재
            elif "개인지출" in ty:
                with c1:
                    curr_opts_tr = [c for c in available_currs if c not in ["KRW"]]
                    curr_tr = st.selectbox("사용 외화 통화", curr_opts_tr, key="tr_curr")
                    s_amt = st.number_input(f"사용 외화 금액 ({curr_tr})", min_value=0.0, step=1.0, format="%.2f", key="tr_sell_flt")
                    source_met = st.selectbox("외화 출처", [f"트래블카드({curr_tr})", f"현금({curr_tr})"], key="tr_sell_met")
                with c2:
                    s_desc = st.text_input("상세 용도 (예: 알리익스프레스 결제)", placeholder="여행 경비가 아닌 개인지출 용도 입력", key="tr_sell_desc")
                    if s_amt > 0:
                        fifo_rate = auto_calc_fifo_rate(s_amt, source_met, curr_tr)
                        fifo_cost = s_amt * fifo_rate
                        st.info(f"💡 시스템 내 회수 원가(FIFO): **{fifo_cost:,.0f} 원**")
                        st.caption(f"적용 환율: {fifo_rate:.4f}")
                        
                if st.button("🚀 개인지출 기록하기 (여행비용 제외 및 잔고 차감)", use_container_width=True):
                    if s_amt <= 0 or not s_desc:
                        st.warning("금액과 상세 용도를 정확히 입력해 주세요.")
                        st.stop()
                    
                    fifo_rate = auto_calc_fifo_rate(s_amt, source_met, curr_tr)
                    new_row = pd.DataFrame([{
                        'Date': sel_date.strftime("%Y-%m-%d(%a)"),
                        'Country': sel_node,
                        'Category': '개인지출',
                        'Description': f"[개인지출] {s_desc}",
                        'Currency': curr_tr,
                        'Amount': s_amt,
                        'PaymentMethod': source_met,
                        'IsExpense': 0, # IsExpense = 0 으로 지출 집계에서 무조건 제외
                        'AppliedRate': fifo_rate,
                        'Note': 'Exclude from Travel',
                        'Receipt_URL': ''
                    }])
                    if append_new_data(new_row):
                        st.success("개인지출 기록 완료 (여행 비용 및 지출 통계에서 완벽 배제되었습니다!)")
                        time.sleep(1)
                        st.rerun()
            
            else:
                with c1:
                    curr_opts_tr =[IN_CURR, "USD"] +[c for c in available_currs if c not in[IN_CURR, "USD", "KRW"]]
                    curr_tr = st.selectbox("대상 통화", curr_opts_tr, key="tr_curr")
                    if curr_tr == IN_CURR and IN_MULTI == 100: t_amt = st.number_input(f"받은 금액 ({curr_tr})", min_value=0, step=1000, format="%d", key="tr_target_int")
                    else: t_amt = st.number_input(f"받은 금액 ({curr_tr})", min_value=0.0, step=10.0, format="%.2f", key="tr_target_flt")
                        
                    if "ATM" in ty:
                        inherited_r = auto_calc_fifo_rate(t_amt, f"트래블카드({curr_tr})", curr_tr)
                        st.info(f"💳 카드 재고 계승 환율: **{inherited_r:.5f}**")
                        st.success(f"💰 인출로 소모되는 원화 가치: **{(t_amt * inherited_r):,.0f} 원**")
                        applied_tr_rate = inherited_r
                    else:
                        s_cost = st.number_input("소요 원금 (KRW)", min_value=0, step=1, format="%d", key="tr_source_swap")
                        applied_tr_rate = s_cost / t_amt if t_amt > 0 else 0
                with c2:
                    if curr_tr == IN_CURR and IN_MULTI == 100: fee_amt = st.number_input(f"ATM 수수료 ({curr_tr})", min_value=0, step=1000, format="%d", key="tr_fee_int")
                    else: fee_amt = st.number_input(f"ATM 수수료 ({curr_tr})", min_value=0.0, step=1.0, format="%.2f", key="tr_fee_flt")
                        
                if st.button("🔄 이동 실행", use_container_width=True):
                    # [Modified] 타겟과 소스 지갑을 안전하게 지정하도록 로직 강화
                    dest = f"트래블카드({curr_tr})" if "충전" in ty else f"현금({curr_tr})"
                    source = "원화계좌(한국)" if "원화계좌" in ty else f"트래블카드({curr_tr})"
                    
                    main_row = pd.DataFrame([{'Date': sel_date.strftime("%Y-%m-%d(%a)"), 'Country': sel_node, 'Category': ty.split(" ")[0], 'Description': f"{ty.split(' ')[0]} (-> {dest})", 'Currency': curr_tr, 'Amount': t_amt, 'PaymentMethod': source, 'IsExpense': 0, 'AppliedRate': applied_tr_rate, 'Note': '', 'Receipt_URL': ''}])
                    
                    new_rows = [main_row]
                    if fee_amt > 0:
                        fee_rate = auto_calc_fifo_rate(fee_amt, f"트래블카드({curr_tr})", curr_tr)
                        fee_row = pd.DataFrame([{'Date': sel_date.strftime("%Y-%m-%d(%a)"), 'Country': sel_node, 'Category': "수수료", 'Description': f"{ty.split(' ')[0]} 수수료", 'Currency': curr_tr, 'Amount': fee_amt, 'PaymentMethod': f"트래블카드({curr_tr})", 'IsExpense': 1, 'AppliedRate': fee_rate, 'Note': '', 'Receipt_URL': ''}])
                        new_rows.append(fee_row)
                    if append_new_data(pd.concat(new_rows, ignore_index=True)): st.rerun()
                        
        # 6.01.05 | Sub-Form: Refund Inventory Rollback (환불 취소)
        # [Modified] 환불 취소 (트래블카드로 통일)
        elif mode == "환불(취소)":
            st.subheader("🔙 결제 취소 및 환불 (Rollback)")
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                curr_opts_rf =[IN_CURR, "KRW", "USD"] +[c for c in available_currs if c not in[IN_CURR, "KRW", "USD"]]
                r_curr = st.selectbox("취소된 통화", curr_opts_rf, key="rf_curr")
                
                r_met = st.selectbox("돌려받을 지갑",[f"현금({r_curr})", f"트래블카드({r_curr})", "원화계좌(한국)", "원화계좌(현지)"] if r_curr != "KRW" else["원화계좌(한국)", "원화계좌(현지)"], key="rf_met")
                if r_curr == "KRW" or (r_curr == IN_CURR and IN_MULTI == 100): r_amt = st.number_input("환불 금액", min_value=0, step=1000 if r_curr != "KRW" else 1, format="%d", key="rf_amt_int")
                else: r_amt = st.number_input("환불 금액", min_value=0.0, step=1.0, format="%.2f", key="rf_amt_flt")
            with col_r2:
                r_rate = st.number_input("과거 결제 시 적용됐던 환율", value=(1.0 if r_curr=="KRW" else get_default_rate(r_curr)), format="%.5f", key="rf_rate")
                r_desc = st.text_input("취소 내역 메모", placeholder="예: 호텔 보증금 반환", key="rf_desc")
                
            if st.button("🔙 환불 인벤토리 롤백 실행", use_container_width=True):
                new_row = pd.DataFrame([{'Date': sel_date.strftime("%Y-%m-%d(%a)"), 'Country': sel_node, 'Category': '환불', 'Description': f"취소: {r_desc}", 'Currency': r_curr, 'Amount': r_amt, 'PaymentMethod': r_met, 'IsExpense': 0, 'AppliedRate': r_rate, 'Note': 'Rollback', 'Receipt_URL': ''}])
                if append_new_data(new_row): st.rerun()

        # 6.01.06 | Sub-Form: Immigration Schedule (출입국 일정 기록)
        else:
            st.subheader("✈️ 출입국 일정 기록")
            io_type = st.radio("구분",["출국", "입국"], horizontal=True, key="io_radio")
            io_desc = st.text_input("내용 (메모)", placeholder="편명, 시간 등", key="io_desc_input")
            if st.button("🚀 일정 기록 완료", use_container_width=True):
                new_row = pd.DataFrame([{'Date': sel_date.strftime("%Y-%m-%d(%a)"), 'Country': sel_node, 'Category': io_type, 'Description': io_desc, 'Currency': 'KRW', 'Amount': 0, 'PaymentMethod': '원화계좌(한국)', 'IsExpense': 1, 'AppliedRate': 1.0, 'Note': '', 'Receipt_URL': ''}])
                if append_new_data(new_row): st.rerun()

        # 6.01.07 | Sub-Form: GTL Provisioning Wizard (새 여행지 개설)
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

    # --------------------------------------------------------------------------
    # 6.02.00 | Console Tab 2: Audit History & Viewer (조회 및 내역 수정)
    # --------------------------------------------------------------------------
    with tab_his:
        st.info("💡 **표의 행(Row)을 클릭(터치)하시면 바로 아래에 상세 내역 수정과 영수증 첨부 화면이 펼쳐집니다!**")
        viewer_placeholder = st.empty()

        # 6.02.01 | Multi-Dimensional AND Filter Bar (다차원 필터 및 직접 수정 토글)
        # ➔ 🚀 [Modified] AND 연산 기반 다차원 필터링 레이아웃으로 변경
        # 세션 스테이트 초기화 및 로드 데이터 기준 동적 카테고리 생성 준비
        initial_country = st.session_state.get('his_country', "이번 여행가계부")
        if initial_country == "모든 여행가계부":
            temp_display_df = load_all_trips_data()
        else:
            temp_display_df = ledger_df.copy()
            if initial_country != "이번 여행가계부":
                temp_display_df = temp_display_df[temp_display_df['Country'] == initial_country]
        
        # 현재 데이터에 들어있는 유니크 카테고리만 동적으로 추출
        if not temp_display_df.empty:
            cat_list = sorted(list(temp_display_df['Category'].dropna().unique()))
            cat_options = ["모든 카테고리"] + cat_list
        else:
            cat_options = ["모든 카테고리"]

        # 4분할 레이아웃 배치
        c_filter, c_cat, c_search, c_tog = st.columns([2.5, 2.5, 3.5, 1.5])
        with c_filter:
            filter_options = ["모든 여행가계부", "이번 여행가계부"] + list(TRIP_CONFIGS[st.session_state.current_trip]["nodes"].keys())
            country_filter = st.selectbox("🌍 국가 필터", filter_options, index=filter_options.index(initial_country) if initial_country in filter_options else 1, key="his_country")
        with c_cat:
            cat_filter = st.selectbox("📂 카테고리 필터", cat_options, index=0, key="his_cat")
        with c_search: 
            search_query = st.text_input("🔎 검색어 입력", placeholder="상호명, 메모 등 검색", key="his_search")
        with c_tog: 
            st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
            edit_mode = st.toggle("✏️ 직접 수정", value=False, key="his_edit_toggle")
        
        # ➔ 🚀 [Modified] 필터 선택에 따른 원본 데이터셋 확보 및 정합성 재계산
        if country_filter == "모든 여행가계부":
            st.warning("⚠️ '모든 여행가계부' 모드에서는 내역 조회만 가능하며, 수정은 불가능합니다.")
            edit_mode = False 
            display_df = load_all_trips_data()
        else:
            display_df = ledger_df.copy()
            if country_filter != "이번 여행가계부":
                display_df = display_df[display_df['Country'] == country_filter]

        # 6.02.02 | Ledger Integrity Auto-Rebuilder Trigger
        if st.button(f"🔄 '{st.session_state.current_trip}' 가계부 정합성 재계산", use_container_width=True, type="primary"):
            if save_data(ledger_df):
                st.success("데이터 정합성 복구 완료!"); time.sleep(1); st.rerun()
                
        # 6.02.03 | Interactive Dataframe / Direct Grid Editor (보색 대비 웜앰버+블루 지브라)
        if not display_df.empty: 
            display_df = display_df.sort_values(by='Date', kind='mergesort').reset_index(drop=True)
            display_df = display_df.reindex(columns=FINAL_COLUMNS)
            link_cfg = st.column_config.LinkColumn("영수증 📸", display_text="🔗 보기", disabled=True)
            
            if edit_mode:
                edited_df = st.data_editor(display_df, use_container_width=True, num_rows="dynamic", key="editor_gtl_final", column_config={"Receipt_URL": link_cfg})
                if not display_df.equals(edited_df) and st.button("💾 데이터베이스 수정사항 저장", use_container_width=True):
                    if save_data(edited_df): st.rerun()
            else:
                render_df = display_df.copy()
                
                # 1차 필터: 카테고리 AND 조건
                if cat_filter != "모든 카테고리":
                    render_df = render_df[render_df['Category'] == cat_filter]
                
                # 2차 필터: 검색어 AND 조건
                if search_query.strip():
                    mask = (
                        render_df['Category'].str.contains(search_query, case=False, na=False) | 
                        render_df['Description'].str.contains(search_query, case=False, na=False) | 
                        render_df['Note'].str.contains(search_query, case=False, na=False) |
                        render_df['Country'].str.contains(search_query, case=False, na=False) 
                    )
                    render_df = render_df[mask]
                    
                st.write(f"🔎 검색 결과: {len(render_df)}건")

                # 1. 출국일(dep_dt) 및 입국일(arr_dt) 파싱
                dep_rows = ledger_df[ledger_df['Category'].str.contains('출국', na=False)]
                korea_dep = ledger_df[ledger_df['Category'].str.contains('출국_한국|출국.*한국', na=False)]
                target_dep_row = korea_dep if not korea_dep.empty else dep_rows
                
                dep_dt, arr_dt = None, None
                if not target_dep_row.empty:
                    m_dep = re.search(r'(\d{4}-\d{2}-\d{2})', str(target_dep_row.iloc[0]['Date']))
                    if m_dep: 
                        dep_dt = datetime.strptime(m_dep.group(1), "%Y-%m-%d").date()

                arr_rows = ledger_df[ledger_df['Category'].str.contains('입국', na=False)]
                korea_arr = ledger_df[ledger_df['Category'].str.contains('입국_한국|입국.*한국', na=False)]
                target_arr_row = korea_arr if not korea_arr.empty else arr_rows
                
                if not target_arr_row.empty:
                    m_arr = re.search(r'(\d{4}-\d{2}-\d{2})', str(target_arr_row.iloc[-1]['Date']))
                    if m_arr: 
                        arr_dt = datetime.strptime(m_arr.group(1), "%Y-%m-%d").date()

                unique_dates = sorted(list(set(re.search(r'(\d{4}-\d{2})-(\d{2})', str(d)).group(0) for d in render_df['Date'] if re.search(r'(\d{4}-\d{2})-(\d{2})', str(d)))))
                date_to_group = {d: i % 2 for i, d in enumerate(unique_dates)}

                def is_real_departure(cat, cur_d):
                    if not dep_dt: return False
                    if '출국_한국' in cat: return True
                    if '출국' in cat and cur_d == dep_dt and not any(k in cat for k in ['베트남', '일본', '중국', '태국', '미국', '유럽', '다낭', '나트랑', '푸꾸옥', '칭다오', '세부', '필리핀']):
                        return True
                    return False

                def is_real_arrival(cat, cur_d):
                    if not arr_dt: return False
                    if '입국_한국' in cat: return True
                    if '입국' in cat and cur_d == arr_dt and not any(k in cat for k in ['베트남', '일본', '중국', '태국', '미국', '유럽', '다낭', '나트랑', '푸꾸옥', '칭다오', '세부', '필리핀']):
                        return True
                    return False

                # 2. 날짜 포맷터
                day_kr_names = ['월', '화', '수', '목', '금', '토', '일']
                def format_display_date_se(row):
                    orig_d = str(row['Date']).strip()
                    cat = str(row['Category']).strip()
                    m_full = re.search(r'(\d{4})-(\d{2})-(\d{2})', orig_d)
                    if m_full:
                        pure_date = m_full.group(0)
                        mm, dd = m_full.group(2), m_full.group(3)
                    else:
                        m_short = re.search(r'(\d{2})-(\d{2})-(\d{2})', orig_d)
                        if m_short:
                            pure_date = f"20{m_short.group(1)}-{m_short.group(2)}-{m_short.group(3)}"
                            mm, dd = m_short.group(2), m_short.group(3)
                        else:
                            return orig_d
                    
                    try:
                        cur_d = datetime.strptime(pure_date, "%Y-%m-%d").date()
                        day_kr = day_kr_names[cur_d.weekday()]
                    except:
                        cur_d = None
                        day_kr = ""
                        
                    day_str = f"({day_kr})" if day_kr else ""
                    short_d = f"{mm}/{dd}{day_str}"

                    if cur_d and is_real_departure(cat, cur_d): return f"{short_d} 🛫출국"
                    if cur_d and is_real_arrival(cat, cur_d): return f"{short_d} 🛬귀국"
                    
                    if not dep_dt or not cur_d: return short_d
                    diff = (cur_d - dep_dt).days
                    
                    if diff < 0: return f"{short_d} 🏷️사전"
                    elif diff == 0: return f"{short_d} 🛫Day1"
                    else:
                        if arr_dt and cur_d == arr_dt: return f"{short_d} 🛬귀국"
                        elif arr_dt and cur_d > arr_dt: return f"{short_d} [귀국후]"
                        return f"{short_d} 📍D-{diff + 1}"

                styled_render_df = render_df.copy()
                styled_render_df['Date'] = styled_render_df.apply(format_display_date_se, axis=1)

                # 3. 단일 국가 여행 시 'Country' 열 자동 숨김
                trip_nodes = TRIP_CONFIGS.get(st.session_state.current_trip, {}).get("nodes", {})
                is_single_country = (len(trip_nodes) <= 1) or (styled_render_df['Country'].dropna().nunique() <= 1)
                if is_single_country and 'Country' in styled_render_df.columns:
                    styled_render_df = styled_render_df.drop(columns=['Country'])

                # 4. [보색 대비 완벽 튜닝] 웜 앰버 배경 + 비비드 블루 글씨 스타일러
                def style_journey_rows_se(row):
                    cat = str(row.get('Category', '')).strip()
                    orig_d = str(render_df.loc[row.name, 'Date'])
                    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', orig_d)
                    if not m: return [''] * len(row)
                    pure_date = m.group(0)
                    cur_d = datetime.strptime(pure_date, "%Y-%m-%d").date()
                    
                    # (1) [출국일]: 앰버 골드 음영 + 볼드
                    if is_real_departure(cat, cur_d):
                        return ['background-color: rgba(245, 158, 11, 0.28); font-weight: bold; color: #F59E0B;'] * len(row)
                            
                    # (2) [귀국일]: 에메랄드 그린 음영 + 볼드
                    if is_real_arrival(cat, cur_d):
                        return ['background-color: rgba(16, 185, 129, 0.28); font-weight: bold; color: #10B981;'] * len(row)

                    # (3) [사전결제]: 차분한 음영
                    if dep_dt:
                        diff = (cur_d - dep_dt).days
                        if diff < 0:
                            return ['opacity: 0.7; font-style: italic;'] * len(row)

                    # (4) [지브라 교대행]: 청색의 보색(은은한 웜 앰버 틴트) 배경 + 선명한 코발트/스카이블루 글씨
                    grp = date_to_group.get(pure_date, 0)
                    if grp == 1:
                        return ['background-color: rgba(249, 115, 22, 0.12); color: #0284C7; font-weight: normal;'] * len(row)
                    else:
                        return ['background-color: transparent;'] * len(row)

                styled_table = styled_render_df.style.apply(style_journey_rows_se, axis=1)
                
                # 숫자 포맷터
                def smart_num_fmt(v):
                    if pd.isna(v) or not isinstance(v, (int, float)): return v
                    if v == 0: return "0"
                    if abs(v) >= 1 and v == int(v): return f"{int(v):,}"
                    if abs(v) < 1: return f"{v:.4f}".rstrip('0').rstrip('.')
                    return f"{v:,.2f}"

                num_cols = ['Amount', 'AppliedRate', 'Cum_Budget_KRW', 'Cum_Card_Local', 'Cum_Cash_Local']
                styled_table = styled_table.format(smart_num_fmt, subset=[c for c in num_cols if c in styled_render_df.columns])
                
                # 5. 테이블 렌더링
                col_cfg = {
                    "Date": st.column_config.TextColumn("날짜", width=120),
                    "Category": st.column_config.TextColumn("항목", width="small"),
                    "Receipt_URL": link_cfg
                }
                df_event = st.dataframe(
                    styled_table, 
                    use_container_width=True, 
                    column_config=col_cfg, 
                    hide_index=True,
                    selection_mode="single-cell",
                    on_select="rerun"
                )

                # 6. 터치된 셀의 행 인덱스 감지
                selected_idx = None
                if getattr(df_event.selection, "cells", None) and len(df_event.selection.cells) > 0:
                    selected_idx = df_event.selection.cells[0][0]
                elif getattr(df_event.selection, "rows", None) and len(df_event.selection.rows) > 0:
                    selected_idx = df_event.selection.rows[0]

                # 6.02.04 | Detail Voucher Viewer & Smart KRW Currency Translator
                if selected_idx is not None:
                    real_idx = render_df.index[selected_idx] 
                    row_data = display_df.loc[real_idx]
                    
                    with viewer_placeholder.container():
                        st.markdown("---")
                        c_info, c_edit = st.columns([1, 1])
                        
                        # 6.02.04 | 상세 내역 및 영수증 뷰어 (개별 사진 삭제 버튼 탑재)
                        with c_info:
                            st.subheader("🧾 상세 내역 및 영수증 뷰어")
                            amt_fmt2 = "{:,.2f}" if MULTIPLIER == 1 and row_data['Currency'] != 'KRW' else "{:,.0f}"

                            krw_equivalent = row_data['Amount'] if row_data['Currency'] == 'KRW' else row_data['Amount'] * row_data['AppliedRate']
                            krw_display = f" ➔ <span style='color:#FFD700'>약 {krw_equivalent:,.0f} 원</span>" if row_data['Currency'] != 'KRW' else ""
                            
                            st.markdown(f"### 🛒 {row_data['Category']} ({amt_fmt2.format(row_data['Amount'])} {row_data['Currency']}{krw_display})", unsafe_allow_html=True)
                            st.markdown(f"**🏦 결제수단:** {row_data['PaymentMethod']}")
                            
                            def smart_krw_translator(text, rate, curr):
                                if rate <= 0 or curr == 'KRW': return text
                                def replacer(match):
                                    num_str = match.group(1).replace(',', '')
                                    suffix = match.group(2).lower() if match.group(2) else ""
                                    try:
                                        v = float(num_str)
                                        is_currency = any(c in suffix for c in['vnd', 'usd', 'eur', 'cny', 'try', 'rsd', 'huf', 'krw', '원', '동', '달러'])
                                        is_unit = any(u in suffix for u in['ml', 'g', 'kg', 'cm', 'mm', '개', 'x', '입', '장', '명', '박스'])
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
                                
                            # 영수증 사진 표시 및 삭제
                            receipt_data = str(row_data['Receipt_URL']).strip()
                            if receipt_data.startswith("http"):
                                urls = [u.strip() for u in receipt_data.split(",") if u.strip().startswith("http")]
                                for idx, url in enumerate(urls):
                                    st.image(url, use_container_width=True, caption=f"영수증 사진 #{idx+1}")
                                    if st.button(f"🗑️ 사진 #{idx+1} 삭제", key=f"btn_del_rcpt_{real_idx}_{idx}", use_container_width=True):
                                        remaining_urls = [u for i, u in enumerate(urls) if i != idx]
                                        display_df.at[real_idx, 'Receipt_URL'] = ",".join(remaining_urls)
                                        if save_data(display_df):
                                            st.success(f"사진 #{idx+1}이 성공적으로 삭제되었습니다!")
                                            time.sleep(0.6)
                                            st.rerun()
                            else:
                                st.info("첨부된 영수증 사진이 없습니다.")
                                
                        # 6.02.05 | 인라인 수정기
                        with c_edit:
                            st.subheader("✏️ 내역 보강 및 영수증 첨부")
                            st.caption("세부 내역을 엑셀에서 복사해 붙여넣거나 엔터(줄바꿈)로 여러 개 입력하시면, 왼쪽 뷰어에서 깔끔하게 분리되어 표시됩니다.")
                            
                            if row_data['Currency'] != 'KRW' and row_data['AppliedRate'] > 0:
                                with st.expander(f"🧮 타임머신 계산기 (적용 환율: {row_data['AppliedRate']:.4f})", expanded=False):
                                    mini_amt = st.number_input(f"영수증 속 현지 금액을 입력해 보세요 ({row_data['Currency']})", min_value=0.0, step=10.0, key="mini_calc")
                                    if mini_amt > 0:
                                        st.success(f"➔ 당시 원화 가치: **{mini_amt * row_data['AppliedRate']:,.0f} 원**")
                            
                            desc_key = f"edit_desc_{real_idx}"
                            if st.session_state.get('current_edit_idx') != real_idx:
                                st.session_state[desc_key] = str(row_data['Description'])
                                st.session_state['current_edit_idx'] = real_idx
                                
                            new_receipts = st.file_uploader("📸 새 영수증 사진 업로드 (다중 가능)", type=['png', 'jpg', 'jpeg'], key=f"inline_receipt_{real_idx}", accept_multiple_files=True)
                            if new_receipts:
                                if st.button("🤖 첨부된 사진 AI 스캔 (스마트 번역)", use_container_width=True):
                                    with st.spinner(f"AI가 {len(new_receipts)}장의 사진을 분석 중..."):
                                        all_raw_texts = []
                                        for f in new_receipts:
                                            ext_text = extract_text_from_vision_api(f.getvalue())
                                            all_raw_texts.append(ext_text)
                                        combined_text = "\n---\n".join(all_raw_texts)
                                        smart_text = summarize_receipt_with_gemini(combined_text)
                                        if smart_text:
                                            st.session_state[desc_key] = st.session_state.get(desc_key, '') + "\n" + smart_text
                                            st.rerun()

                            new_desc = st.text_area("📝 세부 내역 (수정/추가)", height=150, key=desc_key)
                            
                            if st.button("💾 이 내역 업데이트", use_container_width=True):
                                display_df.at[real_idx, 'Description'] = new_desc
                                if new_receipts:
                                    with st.spinner(f"📸 {len(new_receipts)}장의 영수증을 클라우드에 전송 중..."):
                                        new_urls = []
                                        for f in new_receipts:
                                            u = upload_image_to_imgbb(f)
                                            if u: new_urls.append(u)
                                        
                                        if new_urls:
                                            existing_raw = str(row_data['Receipt_URL']).strip()
                                            existing_urls = [x.strip() for x in existing_raw.split(',') if x.strip().startswith('http')]
                                            merged_urls = existing_urls + new_urls
                                            display_df.at[real_idx, 'Receipt_URL'] = ",".join(merged_urls)
                                            
                                if save_data(display_df): st.success("업데이트 완료!"); time.sleep(1); st.rerun()
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
                # 6.03.03 | Pre-Departure Domestic Cost Treemap (절대 금액 비례 폰트 엔진)
                # --------------------------------------------------------------
                dom_df = exp_df[is_fixed_cost & (~exp_df['Category'].isin(['입국','출국']))]
                if not dom_df.empty:
                    st.divider()
                    st.markdown("<h4 style='text-align: center;'>🛫 사전결제 분석 (스마트 트리맵)</h4>", unsafe_allow_html=True)
                    
                    dom_chart_df = dom_df.copy()
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
                    for _, r in dom_chart_df.iterrows():
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

                        # (2) [핵심] 비중에 따른 절대 폰트 크기 계산 (역전 방지 탑재)
                        if is_small or pct < 5.5:
                            # 5등급 (소액 원라이너): 가로 한 줄 표기
                            tile_html = f"<span style='font-size:11.5px; font-weight:bold;'>{name_lbl} ({amt:,.0f}원)</span>"
                        elif pct >= 35.0:
                            # 1등급 (특대형 / 항공권 42만): 제목 18.5px, 금액 15.5px
                            tile_html = f"<span style='font-size:18.5px; font-weight:bold;'>{name_lbl}</span><br><span style='font-size:15.5px; font-weight:600;'>{amt:,.0f}원</span><br><span style='font-size:12px; opacity:0.85;'>({pct:.1f}%)</span>"
                        elif pct >= 18.0:
                            # 2등급 (대형 / 사이공모린 22만): 제목 15.5px, 금액 13px
                            tile_html = f"<span style='font-size:15.5px; font-weight:bold;'>{name_lbl}</span><br><span style='font-size:13px; font-weight:600;'>{amt:,.0f}원</span><br><span style='font-size:11px; opacity:0.85;'>({pct:.1f}%)</span>"
                        elif pct >= 11.0:
                            # 3등급 (중형 / 사누바 다낭 11.8만): 제목 13.5px, 금액 11.5px (센츄리보다 무조건 큼!)
                            tile_html = f"<span style='font-size:13.5px; font-weight:bold;'>{name_lbl}</span><br><span style='font-size:11.5px; font-weight:600;'>{amt:,.0f}원</span><br><span style='font-size:10px; opacity:0.85;'>({pct:.1f}%)</span>"
                        else:
                            # 4등급 (소형 / 센츄리 리버 9만): 제목 12px, 금액 10.5px
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
            
            local_v = exp_df[(exp_df['IsSurvival'] == 1) & (exp_df['Currency'].str.strip() != 'KRW')].copy()
            denom = (travelers * total_nights)
            avg_local_krw = local_v['KRW_val'].sum() / denom if denom > 0 else 0
            avg_local_loc = 0 if len(local_v['Currency'].unique()) > 1 else (local_v['Local_val'].sum() / denom if denom > 0 else 0)
            
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
            
            # ------------------------------------------------------------------
            # 6.04.02 | Comprehensive Expense Treemap Matrix (우측 세로 컬러바 완전 삭제)
            # ------------------------------------------------------------------
            st.subheader("🌳 지출분석 (Treemap)")
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
                # [핵심] coloraxis_showscale=False 로 우측 세로 막대 완전 삭제 & 가로 100% 전폭 확장!
                fig_tree.update_layout(
                    margin=dict(l=0, r=0, t=20, b=10), 
                    height=650,
                    coloraxis_showscale=False
                )
                st.plotly_chart(fig_tree, use_container_width=True, config={'displaylogo': False})
            
            # ------------------------------------------------------------------
            # 6.04.03 | Donut Category Distribution Chart (중앙 미니멀 & 슬라이스 확대)
            # ------------------------------------------------------------------
            st.subheader("🍕 지출비중")
            cat_pie = exp_df.groupby('Macro_Category')['KRW_val'].sum().reset_index().sort_values(by='KRW_val', ascending=False)
            
            # [수정] 도넛 구멍 축소: 0.5 -> 0.35 (파이 조각 두께 40% 확장으로 글씨 확대 공간 확보)
            fig_donut = px.pie(
                cat_pie, 
                values='KRW_val', 
                names='Macro_Category', 
                hole=0.35, 
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            
            # 파이 조각 내부 글자 13.5px 볼드로 시원시원하게 확대
            fig_donut.update_traces(
                textposition='inside', 
                textinfo='label+value+percent', 
                texttemplate="<b>%{label}</b><br>%{value:,.0f}원<br>(%{percent:.1%})",
                insidetextfont=dict(size=13.5)
            )

            # 여행 상태 연동 중앙 텍스트 산출 (출발전/진행중/종료 연동)
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

            today_f = datetime.now(st.session_state.current_tz).date()

            # [사용자 정의 공식 연동]
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

            # [핵심] '순지출(Net)' 삭제, 금액 선명한 볼드 유지, 아래에 상태 표기 결합
            center_annotation_html = f"<b>{total_trip_krw:,.0f}원</b><br><span style='font-size:12px; color:#A0AEC0;'>{center_sub_text}</span>"
            
            fig_donut.add_annotation(
                text=center_annotation_html, 
                showarrow=False, 
                align="center",
                font=dict(size=16)
            )
            
            fig_donut.update_layout(
                height=600, 
                margin=dict(l=10, r=10, t=30, b=80), 
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
            )
            st.plotly_chart(fig_donut, use_container_width=True)

# 6.04.04 | Build Version & Sync Timestamp Footer
st.caption(f"GTL Platform {VERSION} | Volume Guard: ~ 70 KB | Sync: {datetime.now(st.session_state.current_tz).strftime('%Y-%m-%d %H:%M:%S')} | Strategic Partner Gem")
