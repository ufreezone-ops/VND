# ==============================================================================
# 나침반 (Compass) | 인터뷰이를 위한 삶과 재무의 산책로
# 통합 리팩토링 버전: [x.yy.zz] 계층 아키텍처 & 전역 테마 통합 엔진 적용
# ==============================================================================

# ==============================================================================
# 1.00.00 | 시스템 환경 및 전역 테마 엔진 (System & Theming Engine)
# ==============================================================================

# ------------------------------------------------------------------------------
# 1.01.00 | 라이브러리 로드 및 기본 페이지 설정
# ------------------------------------------------------------------------------
import os
import random
import json
import base64
import requests
import re
from datetime import date
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from streamlit_option_menu import option_menu

st.set_page_config(
    page_title="나침반 — 나의 삶을 바라보는 산책로",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ==============================================================================
# 1.02.00 | 전역 통합 테마 디자인 시스템 CSS (다이얼로그 삭제 & 인라인 툴바 스타일)
# ==============================================================================
st.markdown("""
<style>
/* ==========================================================================
   0. Streamlit 실제 스크롤 컨테이너에 스크롤바 상시 고정 (1,2,3,4탭 흔들림 박멸)
   ========================================================================== */
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
.stMain {
    overflow-y: scroll !important;
    scrollbar-gutter: stable;
}

/* ==========================================================================
   CSS Design Tokens (전역 색상 규칙)
   ========================================================================== */
:root {
    color-scheme: light dark;
    --nc-bg: #0b1120;
    --nc-sidebar-bg: #0f172a;
    --nc-text: #f8fafc;
    --nc-subtext: #94a3b8;
    --nc-border: #334155;
    --nc-card-bg: #151e2f;
    --nc-hero-bg: radial-gradient(circle at top, #1e293b 0%, #0f172a 75%);
    --nc-primary: #ea580c;
    --nc-primary-hover: #c2410c;
    --nc-accent-gold: #f59e0b;
    --nc-quad-bg: #172033;
    
    --nc-panel-income: #163b35;
    --nc-panel-income-border: #2f806d;
    --nc-panel-expense: #442a2d;
    --nc-panel-expense-border: #a34c56;
    --nc-panel-asset: #183653;
    --nc-panel-asset-border: #3b82b5;
    --nc-panel-debt: #44351d;
    --nc-panel-debt-border: #a8792d;
    --nc-panel-retire: #34264a;
    --nc-panel-retire-border: #8761b3;
}

/* 기본 폰트 17px로 대형화하여 전 연령 가독성 확보 */
.stApp {
    background-color: var(--nc-bg) !important;
    color: var(--nc-text) !important;
}
.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
    max-width: 1180px;
}
.stApp, .stApp p, .stApp label, .stApp [data-testid="stMarkdownContainer"] {
    font-size: 17px !important;
    color: var(--nc-text);
}

/* 카드 및 박스 */
.soft-card {
    background: var(--nc-card-bg);
    border: 1px solid var(--nc-border);
    border-radius: 14px;
    padding: 18px 20px;
    margin: 10px 0;
    color: var(--nc-text);
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

/* 재무 컬러 패널 */
.st-key-job-panel { 
    background: rgba(30, 41, 59, 0.45) !important; 
    border: 1.5px solid #475569 !important; 
    border-radius: 12px; 
    padding: 20px 22px !important;
}
.st-key-job-panel * { color: var(--nc-text) !important; }

.st-key-income-panel { background: var(--nc-panel-income) !important; border: 1px solid var(--nc-panel-income-border) !important; border-radius: 12px; }
.st-key-expense-panel { background: var(--nc-panel-expense) !important; border: 1px solid var(--nc-panel-expense-border) !important; border-radius: 12px; }
.st-key-asset-panel { background: var(--nc-panel-asset) !important; border: 1px solid var(--nc-panel-asset-border) !important; border-radius: 12px; }
.st-key-debt-panel { background: var(--nc-panel-debt) !important; border: 1px solid var(--nc-panel-debt-border) !important; border-radius: 12px; }
.st-key-retirement-panel { background: var(--nc-panel-retire) !important; border: 1px solid var(--nc-panel-retire-border) !important; border-radius: 12px; }

.st-key-income-panel *, .st-key-expense-panel *, .st-key-asset-panel *,
.st-key-debt-panel *, .st-key-retirement-panel * {
    color: var(--nc-text) !important;
}

/* Metric, Button, Sidebar */
[data-testid="stMetricLabel"] *, [data-testid="stMetricLabel"] { color: var(--nc-subtext) !important; font-size: 15px !important; font-weight: 600 !important; }
[data-testid="stMetricValue"] *, [data-testid="stMetricValue"] { color: var(--nc-text) !important; font-weight: 800 !important; font-size: 26px !important; }

button[kind="primary"], .stApp [data-testid="stFormSubmitButton"] button[kind="primary"] {
    background-color: var(--nc-primary) !important;
    border-color: var(--nc-primary) !important;
    color: #ffffff !important;
    font-weight: 700 !important;
    font-size: 17px !important;
    border-radius: 8px !important;
    padding: 10px !important;
}

[data-testid="stSidebar"] { background-color: var(--nc-sidebar-bg) !important; border-right: 1px solid var(--nc-border) !important; }
[data-testid="stSidebar"] * { color: var(--nc-text) !important; }

/* 일반 입력 필드 */
.stApp input, .stApp textarea {
    background-color: var(--nc-card-bg) !important;
    color: var(--nc-text) !important;
    border-color: var(--nc-border) !important;
    font-size: 17px !important;
    padding: 10px 12px !important;
}

/* Placeholder 고대비 강제 고정 */
input::placeholder, textarea::placeholder,
.stApp input::placeholder, .stApp textarea::placeholder {
    color: #94a3b8 !important;
    -webkit-text-fill-color: #94a3b8 !important;
    opacity: 1 !important;
    font-size: 15px !important;
}

/* st.pills 버튼 스타일 */
div[data-testid="stButtonGroup"],
div[data-testid="stPills"],
div[data-testid="stSegmentedControl"] {
    display: flex !important;
    flex-wrap: wrap !important;
    gap: 8px !important;
    overflow-x: visible !important;
}

div[data-testid="stButtonGroup"] button,
div[data-testid="stPills"] button,
div[data-testid="stSegmentedControl"] button {
    background-color: #1E293B !important;
    background: #1E293B !important;
    color: #CBD5E1 !important;
    border: 1px solid #334155 !important;
    font-size: 15.5px !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
    padding: 9px 15px !important;
    margin: 0 !important;
    box-shadow: none !important;
}

div[data-testid="stButtonGroup"] button:hover,
div[data-testid="stPills"] button:hover {
    background-color: #334155 !important;
    color: #F8FAFC !important;
}

div[data-testid="stButtonGroup"] button[aria-checked="true"],
div[data-testid="stButtonGroup"] button[aria-selected="true"],
div[data-testid="stPills"] button[aria-checked="true"],
div[data-testid="stPills"] button[aria-selected="true"] {
    background-color: #EA580C !important;
    background: linear-gradient(135deg, #EA580C 0%, #C2410C 100%) !important;
    color: #FFFFFF !important;
    border-color: #EA580C !important;
    font-weight: 800 !important;
    box-shadow: 0 2px 8px rgba(234, 88, 12, 0.35) !important;
}

/* 숫자 입력창 +/- 버튼 숨김 */
div[data-testid="stNumberInput"] button { display: none !important; }
div[data-testid="stNumberInput"] input { padding-right: 12px !important; }

/* ==========================================================================
   표지 아래 인라인 3칸 시작 툴바 전용 스타일 (수평 높이 일치)
   ========================================================================== */
/* 시작 폼 테두리 제거 */
div[data-testid="stForm"]:has(input[id*="start_person"]) {
    border: none !important;
    padding: 0 !important;
    background: transparent !important;
}

/* 시작 입력창 2개: 중앙 정렬 & 화이트 깔끔한 배경 */
input[id*="start_person"] {
    background-color: #FFFFFF !important;
    color: #0F172A !important;
    border: 1.5px solid #94A3B8 !important;
    border-radius: 8px !important;
    text-align: center !important;
    font-size: 16px !important;
    height: 44px !important;
}

/* 시작 버튼: 입력창과 높이(44px) 수평 일치 */
div[data-testid="stForm"]:has(input[id*="start_person"]) button {
    height: 44px !important;
    font-size: 17px !important;
    font-weight: 800 !important;
    border-radius: 8px !important;
    padding: 0 10px !important;
}
</style>
""", unsafe_allow_html=True)
# ------------------------------------------------------------------------------
# 1.03.00 | 공식 통계 벤치마크 및 전역 상수 (국민이전계정 NTA 데이터)
# ------------------------------------------------------------------------------
LIFECYCLE_BENCHMARK = pd.DataFrame([
    {"age": 20, "labor_income": 45,  "consumption": 130}, 
    {"age": 25, "labor_income": 180, "consumption": 150},
    {"age": 28, "labor_income": 260, "consumption": 170}, # 흑자 진입 (약 27~28세)
    {"age": 35, "labor_income": 360, "consumption": 220},
    {"age": 43, "labor_income": 435, "consumption": 265}, # 소득 피크 정점 (43~45세)
    {"age": 50, "labor_income": 410, "consumption": 280},
    {"age": 55, "labor_income": 330, "consumption": 280},
    {"age": 60, "labor_income": 220, "consumption": 250},
    {"age": 61, "labor_income": 190, "consumption": 240}, # 적자 재전환 (약 60~61세)
    {"age": 65, "labor_income": 120, "consumption": 230}, 
    {"age": 70, "labor_income": 60,  "consumption": 210},
    {"age": 75, "labor_income": 25,  "consumption": 195},
    {"age": 80, "labor_income": 10,  "consumption": 185},
])

OFFICIAL_PDF_URL = "https://mods.go.kr/boardDownload.es?bid=11898&list_no=447028&seq=3#page=7"
OFFICIAL_RELEASE_URL = "https://mods.go.kr/board.es?act=view&bid=11898&list_no=447028&mid=a10301130100"

ESBI = {
    "E": ("직장인", "고용된 일과 시간을 바꾸어 소득을 얻는 형태"),
    "S": ("자영업·전문직", "자신의 전문성·노동·브랜드에 크게 기대는 형태"),
    "B": ("사업가", "사람과 시스템이 함께 가치를 만드는 형태"),
    "I": ("투자자·임대소득자", "자본·자산에서 소득이 발생하는 형태"),
}


# ==============================================================================
# 2.00.00 | 상태 관리 및 재무 유틸리티 엔진 (State & Finance Engine)
# ==============================================================================

# ------------------------------------------------------------------------------
# 2.01.00 | 세션 상태 초기화 및 헬퍼 함수
# ------------------------------------------------------------------------------
if "anonymous_id" not in st.session_state:
    st.session_state.anonymous_id = f"#{random.choice('ABCDE')}-{random.randint(101,999)}"
if "started" not in st.session_state:
    st.session_state.started = False
if "answers" not in st.session_state:
    st.session_state.answers = {}

def getv(key, default=0):
    val = st.session_state.get(key, default)
    return default if val is None else val

# ==============================================================================
# 2.02.00 | 재무 포맷팅 및 집계 로직
# ==============================================================================
def money(value):
    return f"{value:,.0f}만 원"

def fmt_eok(value):
    if abs(value) >= 10000:
        return f"{value / 10000:,.2f}억 원"
    return money(value)

def active_quadrant(job):
    mapping = {
        "직장인": "E", "공무원": "E", "근로소득자": "E",
        "자영업": "S", "전문직": "S", "프리랜서": "S",
        "사업가": "B", "사업자": "B", "시스템 사업": "B",
        "투자자": "I", "임대소득자": "I", "연금·배당 중심": "I",
    }
    for word, code in mapping.items():
        if word in str(job):
            return code
    return ""

def current_financial_summary():
    # 1. 정기 소득 vs 비정기(연간 성과급/상여금)
    regular_income = sum(float(getv(k, 0)) for k in ["income_self", "income_spouse", "income_other"])
    annual_bonus = float(getv("income_bonus", 0))  # 연간 비정기 소득 (연, 만원)
    
    annual_total_income = (regular_income * 12.0) + annual_bonus
    monthly_effective_income = annual_total_income / 12.0
    
    # 2. 월 지출 합계 (생활비 + 원리금 + 기타지출)
    expenses = sum(float(getv(k, 0)) for k in ["expense_living", "expense_loan", "expense_other"])
    annual_total_expenses = expenses * 12.0
    
    # 3. 잉여금 듀얼 집계
    monthly_regular_surplus = regular_income - expenses          # 매달 일상 유동성 흐름
    annual_net_surplus = annual_total_income - annual_total_expenses  # 1년 종합 진짜 순저축 여력
    monthly_effective_surplus = annual_net_surplus / 12.0       # 연간 순저축의 월 환산액
    
    # 4. 자산 및 부채
    assets = sum(float(getv(k, 0)) for k in ["asset_cash", "asset_financial", "asset_home", "asset_deposit", "asset_other"])
    debts = sum(float(getv(k, 0)) for k in ["debt_home", "debt_other"])
    net_worth = assets - debts
    
    return {
        "regular_income": regular_income,
        "annual_bonus": annual_bonus,
        "annual_total_income": annual_total_income,
        "monthly_effective_income": monthly_effective_income,
        "income": regular_income,  # 기존 호환용
        "expenses": expenses,
        "annual_total_expenses": annual_total_expenses,
        "surplus": monthly_regular_surplus,  # 기존 호환용
        "monthly_regular_surplus": monthly_regular_surplus,
        "annual_net_surplus": annual_net_surplus,
        "monthly_effective_surplus": monthly_effective_surplus,
        "assets": assets,
        "debts": debts,
        "net_worth": net_worth
    }


# ==============================================================================
# 3.00.00 | 외부 AI 연동 서비스 (Gemini API Pipeline)
# ==============================================================================

# ------------------------------------------------------------------------------
# 3.01.00 | Gemini 엔드포인트 캐싱 및 텍스트 요청 파이프라인
# ------------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def get_cached_gemini_models(api_key):
    active_endpoints = []
    for ver in ["v1beta", "v1"]:
        try:
            response = requests.get(
                f"https://generativelanguage.googleapis.com/{ver}/models?key={api_key}",
                timeout=3,
            )
            if response.status_code == 200:
                for model_info in response.json().get("models", []):
                    if "generateContent" in model_info.get("supportedGenerationMethods", []):
                        clean_name = model_info.get("name", "").replace("models/", "")
                        if "flash" in clean_name and "exp" not in clean_name and "preview" not in clean_name:
                            active_endpoints.append((ver, clean_name))
        except Exception:
            pass
    active_endpoints.sort(key=lambda item: (
        0 if item == ("v1beta", "gemini-1.5-flash") else
        1 if item == ("v1", "gemini-1.5-flash") else 2
    ))
    return active_endpoints or [("v1beta", "gemini-2.0-flash")]

def call_gemini_text(prompt_text):
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("Gemini_API_KEY")
    if not api_key:
        try:
            api_key = st.secrets.get("GEMINI_API_KEY", "") or st.secrets.get("Gemini_API_KEY", "")
        except Exception:
            api_key = ""
    if not api_key:
        return "", "Streamlit Secrets에서 GEMINI_API_KEY를 찾지 못했습니다. 앱 대시보드의 Secrets 설정을 확인해 주세요."
    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}],
        "generationConfig": {"maxOutputTokens": 8192, "temperature": 0.45},
    }
    last_error = ""
    for api_version, model_name in get_cached_gemini_models(api_key):
        try:
            response = requests.post(
                f"https://generativelanguage.googleapis.com/{api_version}/models/{model_name}:generateContent?key={api_key}",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=25,
            )
            if response.status_code == 200:
                result = response.json()
                parts = result.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                text_parts = [p.get("text", "") for p in parts if p.get("text")]
                if text_parts:
                    return "".join(text_parts).strip(), ""
            else:
                last_error = f"[{model_name}] {response.status_code}: {response.text[:160]}"
        except Exception as exc:
            last_error = f"[{model_name}] 요청 오류: {exc}"
    return "", last_error or "Gemini 서버에서 응답을 받지 못했습니다."


# ==============================================================================
# 4.00.00 | 진입 커버 및 사이드바 프로필 (Cover & Sidebar Profile)
# ==============================================================================

# ==============================================================================
# 4.01.00 | 첫 진입 표지 및 인라인 시작 바 (라벨 폰트 18px 볼드 확대)
# ==============================================================================
cover_file_path = None
possible_covers = [
    "cover.png", "cover.jpg", "cover.jpeg",
    "나침반_표지_배경.png", "나침판_표지_배경.png"
]

for c_name in possible_covers:
    c_path = os.path.join(os.path.dirname(__file__), c_name)
    if os.path.exists(c_path):
        cover_file_path = c_path
        break

if not st.session_state.started:
    col_left, col_center, col_right = st.columns([1, 1.8, 1])
    
    with col_center:
        if cover_file_path:
            st.image(cover_file_path, use_container_width=True)
        else:
            st.markdown("""
            <div style="background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%); border-radius: 18px; padding: 60px 20px; text-align: center; border: 1px solid #334155;">
                <div style="font-size: 40px; margin-bottom: 10px;">🧭</div>
                <h1 style="color: #FFFFFF; font-size: 32px; font-weight: 850; margin: 0 0 10px 0;">나 침 반</h1>
                <div style="color: #94A3B8; font-size: 15px;">당신의 삶을 위한 질문과 시간의 산책로</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
        
        # 표지 바로 아래 2줄 3칸 인라인 시작 바 (라벨 폰트 18px 시원하게 확대)
        with st.form("start_inline_form", clear_on_submit=False):
            in_col1, in_col2, in_col3 = st.columns([2.0, 1.1, 1.1])
            
            with in_col1:
                st.markdown("<div style='font-size: 18px; font-weight: 800; color: #F8FAFC; margin-bottom: 6px; text-align: center;'>이름(별칭)</div>", unsafe_allow_html=True)
                name = st.text_input("이름(별칭)", placeholder="이름 또는 별칭", key="start_person_name", label_visibility="collapsed")
                
            with in_col2:
                st.markdown("<div style='font-size: 18px; font-weight: 800; color: #F8FAFC; margin-bottom: 6px; text-align: center;'>나이</div>", unsafe_allow_html=True)
                age_text = st.text_input("나이", placeholder="예: 38", key="start_person_age_text", max_chars=3, label_visibility="collapsed")
                
            with in_col3:
                st.markdown("<div style='font-size: 18px; font-weight: 800; margin-bottom: 6px; text-align: center;'>&nbsp;</div>", unsafe_allow_html=True)
                submitted = st.form_submit_button("시작", use_container_width=True, type="primary")

            try:
                age = int(age_text) if age_text.strip() else None
                if age is not None and not (1 <= age <= 120):
                    age = None
            except ValueError:
                age = None

            if submitted:
                if not name.strip() or age is None:
                    st.warning("이름(별칭)과 나이를 올바르게 입력해 주세요.")
                else:
                    st.session_state.person_name = name.strip()
                    st.session_state.person_age = int(age)
                    st.session_state.started = True
                    st.rerun()
            
    st.stop()
    
# ==============================================================================
# 4.02.00 | 사이드바 프로필 요약 카드 (은은한 그레이톤 익명 배지)
# ==============================================================================
with st.sidebar:
    # 1. 익명 고유번호: 튀지 않는 차분한 회색톤으로 은은하게 톤다운
    st.markdown(f"""
    <div style="background: rgba(30, 41, 59, 0.4); border: 1px solid #334155; border-radius: 10px; padding: 12px 14px; text-align: center; margin-bottom: 20px;">
        <div style="font-size: 11.5px; color: #94a3b8; font-weight: 600; letter-spacing: 0.04em;">익명 진단 고유번호</div>
        <div style="font-size: 20px; font-weight: 750; color: #cbd5e1; letter-spacing: 1px; margin-top: 3px;">{st.session_state.anonymous_id}</div>
    </div>
    """, unsafe_allow_html=True)

    # 2. 나의 프로필 정보 (셀프 거울 호칭 적용)
    st.markdown("#### 나의 기본 정보")
    st.markdown(f"**나의 이름/별칭:** {st.session_state.get('person_name','')}")
    st.markdown(f"**나의 나이:** {st.session_state.get('person_age','')}세")

    # 3. 우리집 듀얼 소득 형태 연동
    q_self = active_quadrant(st.session_state.get("job_form", ""))
    q_spouse = active_quadrant(st.session_state.get("job_spouse_form", ""))

    types_desc = []
    if q_self:
        types_desc.append(f"나({q_self})")
    if q_spouse:
        types_desc.append(f"배우자({q_spouse})")

    dual_income_str = " + ".join(types_desc) if types_desc else "아직 미선택"
    st.markdown(f"**우리집 소득 형태:** {dual_income_str}")
    st.caption("※ 나침반은 외부 서버에 저장되지 않는 일회성 안전 세션입니다.")


# ==============================================================================
# 5.00.00 | 메인 네비게이션 헤더 (Main Navigation Segment)
# ==============================================================================

# ==============================================================================
# 5.01.00 | 가로 4대 메뉴 네비게이터 (바깥 라운딩 완전 제거)
# ==============================================================================
_pending_nav = st.session_state.pop("_pending_nav", None)
nav_options = ["우리집\n가계부", "삶과\n생계수단", "인생의\n사계절", "AI\n시선"]
_nav_targets = {
    "우리집 가계부": nav_options[0],
    "삶과 생계수단": nav_options[1],
    "인생의 사계절": nav_options[2],
    "AI 시선": nav_options[3]
}

if "active_navigation_key" not in st.session_state:
    st.session_state.active_navigation_key = "main_navigation"
if _pending_nav in _nav_targets:
    st.session_state.active_navigation_key = "main_navigation_" + str(list(_nav_targets.keys()).index(_pending_nav))
    st.session_state.active_navigation_default = _nav_targets[_pending_nav]

_nav_widget_key = st.session_state.active_navigation_key
_nav_default = st.session_state.get("active_navigation_default", nav_options[0])
_nav_index = nav_options.index(_nav_default) if _nav_default in nav_options else 0

selected = option_menu(
    menu_title=None,
    options=nav_options,
    icons=["", "", "", ""],
    default_index=_nav_index,
    orientation="horizontal",
    key=_nav_widget_key,
    styles={
        "container": {
            # 👇 [핵심 조절 레버] padding: (위 오른쪽 아래 왼쪽)
            # 윗쪽을 14px로 늘려 버튼 머리 위로 확실한 여백을 줍니다!
            "padding": "16px 6px 8px 6px",
            
            "background-color": "#0F172A",
            "border": "none",
            "border-radius": "0px",
            "margin": "0px",
            "width": "100%"
        },
        "icon": {"display": "none"},
        "nav-link": {
            "font-size": "15px",
            "white-space": "pre-line",
            "line-height": "1.25",
            "text-align": "center",
            "margin": "0px 3px",
            "padding": "8px 4px",
            "color": "#CBD5E1",
            "--hover-color": "#1E293B",
            "border-radius": "8px",
            "min-height": "48px",
            
            # 👇 [추가] 4개 탭이 항상 25%씩 자리를 꽉 잡아서 글자가 굵어져도 옆 탭을 밀지 않음
            "flex": "1"
        },
        "nav-link-selected": {
            "background-color": "#EA580C",
            "color": "#FFFFFF",
            "font-weight": "800",
            "box-shadow": "none"
        }
    }
)

selected_page = {
    "우리집\n가계부": "우리집 가계부",
    "삶과\n생계수단": "삶과 생계수단",
    "인생의\n사계절": "인생의 사계절",
    "AI\n시선": "AI 시선"
}.get(selected, selected)

# ==============================================================================
# 6.00.00 | 메인 뷰 페이지 (Main View Tabs)
# ==============================================================================

# ==============================================================================
# 6.01.00 | Tab 1 — 우리집 가계부 (차트 터치 잠금 & 세로축 동적 정수 단위)
# ==============================================================================
if selected_page == "우리집 가계부":
    st.markdown("## 우리집 가계부")
    
    with st.form("finance_form"):
        # ----------------------------------------------------------------------
        # ⓪ 우리집 소득 성격
        # ----------------------------------------------------------------------
        with st.container(border=True, key="job-panel"):
            st.markdown("### ⓪ 우리집 소득 성격")
            
            job_options = ["직장인", "자영업", "전문직", "사업가", "투자자", "임대소득자", "전업주부", "그외"]
            job_spouse_options = ["해당 없음", "직장인", "자영업", "전문직", "사업가", "투자자", "임대소득자", "전업주부", "그외"]
            
            prev_job = st.session_state.get("job_form", "직장인")
            if prev_job not in job_options:
                prev_job = "직장인"
                
            prev_spouse_job = st.session_state.get("job_spouse_form", "해당 없음")
            if prev_spouse_job not in job_spouse_options:
                prev_spouse_job = "해당 없음"
            
            st.markdown("<div style='font-size: 17px; font-weight: 700; color: #F8FAFC; margin-bottom: 6px;'>나의 직업은?</div>", unsafe_allow_html=True)
            job_selected = st.pills(
                "나의 직업은?",
                job_options,
                default=prev_job,
                key="pills_job_self",
                label_visibility="collapsed"
            )
            
            st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
            
            st.markdown("<div style='font-size: 17px; font-weight: 700; color: #F8FAFC; margin-bottom: 6px;'>배우자의 직업은? (선택)</div>", unsafe_allow_html=True)
            job_spouse_selected = st.pills(
                "배우자의 직업은?",
                job_spouse_options,
                default=prev_spouse_job,
                key="pills_job_spouse",
                label_visibility="collapsed"
            )

        st.write("")

        # ----------------------------------------------------------------------
        # ① 들어오는 돈 vs ② 나가는 돈
        # ----------------------------------------------------------------------
        income_col, expense_col = st.columns(2)
        with income_col:
            with st.container(border=True, key="income-panel"):
                st.markdown("### ① 들어오는 돈 (만원)")
                income_self = st.number_input("나의 월 실수령액 (월급·기본소득)", min_value=0, value=st.session_state.get("income_self"), step=10, placeholder="월 금액")
                income_spouse = st.number_input("배우자 월 실수령액", min_value=0, value=st.session_state.get("income_spouse"), step=10, placeholder="월 금액")
                income_other = st.number_input("그 밖의 월 정기소득 (임대·부업 등)", min_value=0, value=st.session_state.get("income_other"), step=10, placeholder="월 금액")
                income_bonus = st.number_input("연간 비정기 소득 (상여금·성과급·연말수입)", min_value=0, value=st.session_state.get("income_bonus"), step=100, placeholder="1년 합계 금액 (없으면 빈칸)")
        with expense_col:
            with st.container(border=True, key="expense-panel"):
                st.markdown("### ② 나가는 돈 (월, 만원)")
                expense_living = st.number_input("기본 생활비 (식비·관리비·통신비·가족생활)", min_value=0, value=st.session_state.get("expense_living"), step=10, placeholder="월 생활 유지비")
                expense_loan = st.number_input("대출 원리금 상환액 (원금+이자 합계)", min_value=0, value=st.session_state.get("expense_loan"), step=10, placeholder="은행 납입 합계")
                expense_other = st.number_input("그 밖의 월평균 지출 (연간 여행·경조사·세금÷12)", min_value=0, value=st.session_state.get("expense_other"), step=10, placeholder="비정기 지출 월평균")

        # ----------------------------------------------------------------------
        # ③ 가지고 있는 것 vs ④ 갚아야 할 돈
        # ----------------------------------------------------------------------
        asset_col, debt_col = st.columns(2)
        with asset_col:
            with st.container(border=True, key="asset-panel"):
                st.markdown("### ③ 가지고 있는 것 (시세, 만원)")
                asset_cash = st.number_input("현금·예적금", min_value=0, value=st.session_state.get("asset_cash"), step=100, placeholder="금액")
                asset_financial = st.number_input("주식·채권 등 금융자산", min_value=0, value=st.session_state.get("asset_financial"), step=100, placeholder="금액")
                asset_home = st.number_input("부동산 시세", min_value=0, value=st.session_state.get("asset_home"), step=100, placeholder="금액")
                asset_deposit = st.number_input("전세보증금", min_value=0, value=st.session_state.get("asset_deposit"), step=100, placeholder="금액")
                asset_other = st.number_input("그 밖의 자산 (현금화 가능한 사업체·지분 등)", min_value=0, value=st.session_state.get("asset_other"), step=100, placeholder="금액")
        with debt_col:
            with st.container(border=True, key="debt-panel"):
                st.markdown("### ④ 갚아야 할 돈 (원금, 만원)")
                debt_home = st.number_input("주택담보·전세대출 잔액", min_value=0, value=st.session_state.get("debt_home"), step=100, placeholder="금액")
                debt_other = st.number_input("그 밖의 부채 잔액 (신용·마이너스통장)", min_value=0, value=st.session_state.get("debt_other"), step=100, placeholder="금액")

        # ----------------------------------------------------------------------
        # 은퇴 후 가정
        # ----------------------------------------------------------------------
        with st.container(border=True, key="retirement-panel"):
            st.markdown("### 은퇴 후에는? (월, 만원)")
            pension_col, retirement_expense_col = st.columns(2)
            with pension_col:
                income_pension = st.number_input(
                    "은퇴 후 받을 월 연금", min_value=0,
                    value=st.session_state.get("income_pension"), step=10,
                    placeholder="모르면 빈칸으로 두세요"
                )
            with retirement_expense_col:
                retirement_monthly_expenses = st.number_input(
                    "은퇴 후 한 달 생활비", min_value=0,
                    value=int(st.session_state.get("retirement_monthly_expenses", 200) or 0),
                    step=10
                )

        save_finance = st.form_submit_button("입력 내용 반영하기", use_container_width=True, type="primary")

    if save_finance:
        final_job = job_selected if job_selected else "직장인"
        final_spouse_job = "" if (not job_spouse_selected or job_spouse_selected == "해당 없음") else job_spouse_selected
        
        submitted_values = {
            "job_form": final_job,
            "job_spouse_form": final_spouse_job,
            "income_self": income_self, "income_spouse": income_spouse,
            "income_other": income_other, "income_bonus": income_bonus,
            "income_pension": income_pension,
            "expense_living": expense_living, "expense_loan": expense_loan,
            "expense_other": expense_other, "retirement_monthly_expenses": retirement_monthly_expenses,
            "asset_cash": asset_cash, "asset_financial": asset_financial, "asset_home": asset_home,
            "asset_deposit": asset_deposit, "asset_other": asset_other,
            "debt_home": debt_home, "debt_other": debt_other,
        }
        for k, v in submitted_values.items():
            st.session_state[k] = v
        st.session_state["finance_saved_notice"] = True

    # --------------------------------------------------------------------------
    # 우리집 재무 현황 (2x2 동일 규격 카드 & 세로 굵은 점선 분할)
    # --------------------------------------------------------------------------
    q_self = active_quadrant(st.session_state.get("job_form", "직장인"))
    q_spouse = active_quadrant(st.session_state.get("job_spouse_form", ""))

    st.markdown("### 우리집 재무 현황")
    st.markdown("<div id='selected-esbi'></div>", unsafe_allow_html=True)
    if st.session_state.pop("finance_saved_notice", False):
        st.success("입력하신 재무 정보가 반영되었습니다.")
        st.components.v1.html("<script>try { window.parent.document.getElementById('selected-esbi').scrollIntoView({behavior:'smooth',block:'center'}); } catch(e) {}</script>", height=0)

    def get_quad_ui(code, title, desc):
        is_self = (q_self == code)
        is_spouse = (q_spouse == code)
        
        if is_self and is_spouse:
            border_style = "border: 2.5px solid #EA580C; outline: 2.5px dashed #38BDF8; outline-offset: -5px; background: rgba(234, 88, 12, 0.16);"
        elif is_self:
            border_style = "border: 2.5px solid #EA580C; background: rgba(234, 88, 12, 0.14);"
        elif is_spouse:
            border_style = "border: 2.5px dashed #38BDF8; background: rgba(56, 189, 248, 0.14);"
        else:
            border_style = "border: 1px solid #334155; background: rgba(15, 23, 42, 0.7);"
            
        badges = []
        if is_self:
            badges.append("<span style='background:#EA580C; color:#FFFFFF; font-size:12px; font-weight:800; padding:2px 8px; border-radius:4px;'>나</span>")
        if is_spouse:
            badges.append("<span style='background:#0284C7; color:#FFFFFF; font-size:12px; font-weight:800; padding:2px 8px; border-radius:4px;'>배우자</span>")
        
        badge_row = f"<div style='min-height:24px; margin-bottom:4px; display:flex; justify-content:center; gap:6px;'>{' '.join(badges)}</div>" if badges else "<div style='min-height:24px; margin-bottom:4px;'></div>"
        
        return f'<div style="{border_style} border-radius: 12px; padding: 18px 12px; text-align: center; display: flex; flex-direction: column; justify-content: center; align-items: center; height: 165px; box-sizing: border-box; width: 100%;">{badge_row}<div style="font-size: 28px; font-weight: 850; color: #F8FAFC; line-height: 1.1;">{code}</div><div style="font-size: 17.5px; font-weight: 700; color: #F1F5F9; margin: 4px 0 6px 0;">{title}</div><div style="font-size: 14px; color: #CBD5E1; line-height: 1.4; word-break: keep-all; text-align: center;">{desc}</div></div>'

    card_e = get_quad_ui("E", "직장인", "나의 시간과 돈을 바꿈.<br><span style='color:#F59E0B; font-weight:600;'>(작은 물통)</span>")
    card_s = get_quad_ui("S", "자영업·전문직", "나의 시간과 돈을 바꿈.<br><span style='color:#F59E0B; font-weight:600;'>(큰 물통)</span>")
    card_b = get_quad_ui("B", "사업가", "나의 회사가 돈을 만듦.<br><span style='color:#38BDF8; font-weight:600;'>(파이프라인)</span>")
    card_i = get_quad_ui("I", "투자자·임대소득자", "나의 자산이 돈을 만듦.<br><span style='color:#38BDF8; font-weight:600;'>(파이프라인)</span>")

    esbi_html = f"""<div style="margin: 16px 0 24px 0;">
<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0px; align-items: stretch;">
<div style="display: flex; flex-direction: column; gap: 14px; padding-right: 14px; border-right: 3.5px dashed #475569;">
<div>{card_e}</div>
<div>{card_s}</div>
</div>
<div style="display: flex; flex-direction: column; gap: 14px; padding-left: 14px;">
<div>{card_b}</div>
<div>{card_i}</div>
</div>
</div>
<div style="text-align: center; margin-top: 14px;">
<span style="font-size: 14px; color: #94A3B8;">
🧱 좌측(E·S)에서 우측(B·I)으로 넘어가는 것은 소득의 성격을 바꾸는 과정입니다.
</span>
</div>
</div>"""

    st.markdown(esbi_html, unsafe_allow_html=True)

    # --------------------------------------------------------------------------
    # 현재 재무 요약
    # --------------------------------------------------------------------------
    s = current_financial_summary()
    st.markdown("### 현재 재무 요약")
    cols = st.columns(4)
    cols[0].metric("월 정기수입", money(s["regular_income"]), help="나 + 배우자 + 기타 월 정기소득")
    cols[1].metric("월 현금지출", money(s["expenses"]), help="기본생활비 + 대출원리금 + 기타지출")
    
    bonus_help = f"연간 상여금 {money(s['annual_bonus'])} 반영" if s['annual_bonus'] > 0 else "월 정기수지 기준"
    cols[2].metric(
        "연간 순저축 여력",
        money(s["annual_net_surplus"]),
        delta=f"월평균 {money(s['monthly_effective_surplus'])}",
        help=f"1년 총수입({money(s['annual_total_income'])}) - 1년 총지출({money(s['annual_total_expenses'])}) | {bonus_help}"
    )
    cols[3].metric("순자산", fmt_eok(s["net_worth"]))

    # --------------------------------------------------------------------------
    # 미래 순자산·연금 궤적 (터치 락 & 정수 단위 표시)
    # --------------------------------------------------------------------------
    st.markdown("### 미래 순자산·연금 궤적")
    
    cur_age = int(st.session_state.person_age)
    retire_val = st.session_state.get("retirement_age")
    retire_age = int(retire_val) if retire_val is not None else 65
    retire_age = max(cur_age, min(retire_age, 90))
    
    # 1. 초기 순자산 (억 원 단위)
    start_asset_eok = s["net_worth"] / 10000.0
    base_annual_surplus_eok = s["annual_net_surplus"] / 10000.0
    
    # [구간 1] 은퇴 전: 자산 축적기
    ages_accum = list(range(cur_age, retire_age + 1))
    vals_accum_eok = []
    current_asset = start_asset_eok
    
    for a in ages_accum:
        vals_accum_eok.append(current_asset)
        if a < 45:
            lifecycle_weight = 1.0 + (0.02 * (a - cur_age))
        elif 45 <= a <= 53:
            lifecycle_weight = 1.0 + (0.02 * (45 - cur_age)) - 0.15
        else:
            lifecycle_weight = max(0.65, 1.0 + (0.02 * (45 - cur_age)) - 0.25)
            
        annual_save = base_annual_surplus_eok * max(0.1, lifecycle_weight)
        current_asset += annual_save

    peak_asset_eok = vals_accum_eok[-1]

    # [구간 2] 은퇴 후: 자산 인출·연금기
    ret_pension = float(getv("income_pension", 0) or 0)
    ret_expenses = float(getv("retirement_monthly_expenses", 200) or 0)
    annual_ret_cashflow_eok = ((ret_pension - ret_expenses) * 12) / 10000.0

    ages_retire = list(range(retire_age, 91))
    vals_retire_eok = []
    ret_asset = peak_asset_eok
    depletion_age = None

    for idx, a in enumerate(ages_retire):
        vals_retire_eok.append(ret_asset)
        if idx > 0 and ret_asset <= 0 and depletion_age is None:
            depletion_age = a
        ret_asset += annual_ret_cashflow_eok

    # 최대치에 따른 동적 단위 판단 (1억 이상이면 '억', 1억 미만이면 '천만')
    max_val_eok = max(max(vals_accum_eok), max(vals_retire_eok) if vals_retire_eok else 0)
    use_cheonman = (max_val_eok < 1.0 and max_val_eok > 0)
    
    if use_cheonman:
        mult = 10.0
        unit_str = "천만"
        y_accum = [v * mult for v in vals_accum_eok]
        y_retire = [v * mult for v in vals_retire_eok]
        peak_disp = f"{peak_asset_eok * mult:.0f}천만 원"
        hover_tmpl = "나이: %{x}세<br>추정 순자산: <b>%{y:.0f}천만 원</b><extra></extra>"
    else:
        mult = 1.0
        unit_str = "억"
        y_accum = vals_accum_eok
        y_retire = vals_retire_eok
        peak_disp = f"{peak_asset_eok:.0f}억 원" if abs(peak_asset_eok) >= 10 else f"{peak_asset_eok:.1f}억 원"
        hover_tmpl = "나이: %{x}세<br>추정 순자산: <b>%{y:.1f}억 원</b><extra></extra>"

    # Plotly 차트 구성
    fig_asset = go.Figure()

    # 기준선 (0)
    fig_asset.add_hline(y=0, line_dash="solid", line_color="#334155", line_width=1.5)

    # 1. 은퇴 전 축적기
    fig_asset.add_trace(go.Scatter(
        x=ages_accum, y=y_accum,
        mode="lines+markers",
        line=dict(color="#F59E0B", width=3.5),
        marker=dict(size=6),
        fill='tozeroy',
        fillcolor='rgba(245, 158, 11, 0.12)',
        name="🌱 자산 축적기 (연간 총저축 + NTA 생애주기)",
        hovertemplate=hover_tmpl
    ))

    # 2. 은퇴 후 인출기
    fig_asset.add_trace(go.Scatter(
        x=ages_retire, y=y_retire,
        mode="lines+markers",
        line=dict(color="#38BDF8", width=3.5),
        marker=dict(size=6),
        fill='tozeroy',
        fillcolor='rgba(56, 189, 248, 0.08)',
        name="🍂 자산 인출기 (연금 - 노후생활비)",
        hovertemplate=hover_tmpl
    ))

    # 피크 깃발
    fig_asset.add_vline(x=retire_age, line_dash="dash", line_color="#F8FAFC", line_width=2)
    fig_asset.add_annotation(
        x=retire_age, y=peak_asset_eok * mult,
        text=f"은퇴 정점 {retire_age}세 ({peak_disp})",
        showarrow=True, arrowhead=2, arrowcolor="#F59E0B",
        font=dict(size=13, color="#FDE68A", family="sans-serif"),
        ay=-38, bgcolor="rgba(15, 23, 42, 0.85)", bordercolor="#F59E0B", borderpad=4
    )

    # 소진 깃발
    if depletion_age and depletion_age <= 90:
        fig_asset.add_annotation(
            x=depletion_age, y=0,
            text=f"자산 소진 ({depletion_age}세)",
            showarrow=True, arrowhead=2, arrowcolor="#EF4444",
            font=dict(size=12.5, color="#FCA5A5"),
            ay=35, bgcolor="rgba(15, 23, 42, 0.85)", bordercolor="#EF4444", borderpad=3
        )

    fig_asset.update_layout(
        height=380,
        margin=dict(l=20, r=20, t=30, b=35),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E2E8F0", size=13),
        xaxis=dict(
            title=dict(text="나이 (세)", font=dict(size=14, color="#94A3B8")),
            tickfont=dict(size=13, color="#94A3B8"),
            gridcolor="rgba(100, 116, 139, 0.2)",
            tickmode="linear", tick0=20, dtick=5,
            fixedrange=True  # 터치/드래그 확대·이동 잠금
        ),
        yaxis=dict(
            title=dict(text="추정 순자산", font=dict(size=14, color="#94A3B8")),
            tickfont=dict(size=13, color="#94A3B8"),
            ticksuffix=unit_str,
            tickformat=",.0f",  # 소수점 완전 제거
            gridcolor="rgba(100, 116, 139, 0.2)",
            fixedrange=True  # 터치/드래그 확대·이동 잠금
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            font=dict(size=12.5, color="#F1F5F9")
        ),
        hovermode="x unified"
    )

    # 터치 확대 및 모드바 완전 차단 고정
    st.plotly_chart(
        fig_asset,
        use_container_width=True,
        config={"displayModeBar": False, "scrollZoom": False, "doubleClick": False, "showAxisDragHandles": False}
    )

    # 그래프 팩트 안내 카드
    bonus_note = f" (연간 상여금 {money(s['annual_bonus'])} 포함)" if s['annual_bonus'] > 0 else ""
    st.markdown(f"""
<div style="background: rgba(30, 41, 59, 0.5); border: 1px solid #334155; border-radius: 10px; padding: 14px 16px; margin-top: 10px;">
<div style="font-size: 13.5px; color: #CBD5E1; line-height: 1.6;">
• <b>🌱 은퇴 전 (만 {cur_age}세 ~ {retire_age}세)</b>: 1년 총 저축여력({money(s['annual_net_surplus'])}{bonus_note})을 바탕으로, 국가데이터처 국민이전계정(NTA)의 생애주기 소득 피크(45세) 및 40~50대 가족 지출 집중기를 반영한 실질 자산 궤적입니다.<br>
• <b>🍂 은퇴 후 ({retire_age}세 ~ 90세)</b>: 예상 월 연금({ret_pension:,.0f}만 원)에서 노후 월 생활비({ret_expenses:,.0f}만 원)를 뺀 순현금흐름({annual_ret_cashflow_eok*10000:,.0f}만 원/년)에 따른 순자산 변화입니다.
</div>
</div>
""", unsafe_allow_html=True)

    _, next_col = st.columns([5, 1])
    with next_col:
        if st.button("다음 →", key="finance_next", use_container_width=True, type="primary"):
            st.session_state["_pending_nav"] = "삶과 생계수단"
            st.rerun()

# ==============================================================================
# 6.02.00 | Tab 2 — 삶과 생계수단 (물통/파이프라인 매핑 & 돌쇠와 똘똘이 우화)
# ==============================================================================
elif selected_page == "삶과 생계수단":
    st.markdown("## 삶과 생계수단")
    
    # --------------------------------------------------------------------------
    # 1. 소득이 만들어지는 세 가지 모습 (아이콘 시각화 & 부부 매핑 뱃지)
    # --------------------------------------------------------------------------
    st.markdown("### 소득이 만들어지는 세 가지 모습")
    
    # 부부 직업 사분면 판별 (E, S, B, I)
    q_self = active_quadrant(st.session_state.get("job_form", "직장인"))
    q_spouse = active_quadrant(st.session_state.get("job_spouse_form", ""))
    
    def get_livelihood_badge(target_quads):
        badges = []
        if q_self in target_quads:
            badges.append("<span style='background:#EA580C; color:#FFFFFF; font-size:12px; font-weight:800; padding:3px 9px; border-radius:4px;'>나</span>")
        if q_spouse in target_quads:
            badges.append("<span style='background:#0284C7; color:#FFFFFF; font-size:12px; font-weight:800; padding:3px 9px; border-radius:4px;'>배우자</span>")
        return f"<div style='min-height:26px; margin-bottom:8px; display:flex; justify-content:center; gap:6px;'>{' '.join(badges)}</div>" if badges else "<div style='min-height:26px; margin-bottom:8px;'></div>"

    badge_small = get_livelihood_badge(["E"])
    badge_big = get_livelihood_badge(["S"])
    badge_pipe = get_livelihood_badge(["B", "I"])

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
<div class='soft-card' style='text-align:center; min-height:230px;'>
{badge_small}
<div style='font-size:32px; letter-spacing:4px; margin-bottom:6px;'>🪣🪣🪣</div>
<div style='font-size:19px; font-weight:800; color:#F8FAFC; margin-bottom:6px;'>작은 물통</div>
<div style='font-size:14px; color:#CBD5E1; line-height:1.5; word-break:keep-all;'>
직접 일한 시간과 돈을 1:1로 맞바꾸는 모습<br><span style='color:#F59E0B; font-weight:600;'>(시간이 멈추면 물통도 멈춤)</span>
</div>
</div>
""", unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
<div class='soft-card' style='text-align:center; min-height:230px;'>
{badge_big}
<div style='font-size:40px; margin-bottom:6px;'>🛢️</div>
<div style='font-size:19px; font-weight:800; color:#F8FAFC; margin-bottom:6px;'>큰 물통</div>
<div style='font-size:14px; color:#CBD5E1; line-height:1.5; word-break:keep-all;'>
전문성과 몸값을 높여 한 번에 담는 양을 키운 모습<br><span style='color:#F59E0B; font-weight:600;'>(큰 물통이지만 여전히 지고 다님)</span>
</div>
</div>
""", unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
<div class='soft-card' style='text-align:center; min-height:230px;'>
{badge_pipe}
<div style='font-size:32px; letter-spacing:2px; margin-bottom:6px;'>🚰➰⚙️</div>
<div style='font-size:19px; font-weight:800; color:#F8FAFC; margin-bottom:6px;'>파이프라인</div>
<div style='font-size:14px; color:#CBD5E1; line-height:1.5; word-break:keep-all;'>
내가 잠시 멈추어도 시스템과 자산에서 흐르는 모습<br><span style='color:#38BDF8; font-weight:600;'>(시간으로부터 자유로운 소득)</span>
</div>
</div>
""", unsafe_allow_html=True)

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # --------------------------------------------------------------------------
    # 2. 산책로의 우화: '돌쇠와 똘똘이' (플랜 B의 지혜)
    # --------------------------------------------------------------------------
    st.markdown("### 🌾 지혜로운 산책: 돌쇠와 똘똘이 이야기")
    
    st.markdown("""
<div style="background: rgba(30, 41, 59, 0.55); border: 1.5px solid #334155; border-radius: 14px; padding: 22px 24px; margin-bottom: 24px;">
<div style="font-size: 15px; color: #94A3B8; font-weight: 700; margin-bottom: 12px;">옛날 어느 마을, 머슴을 구하는 대감댁에 두 젊은이가 찾아왔습니다.</div>

<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;">
<div style="background: rgba(15, 23, 42, 0.7); border: 1px solid #475569; border-radius: 10px; padding: 14px 16px;">
<div style="font-size: 17px; font-weight: 800; color: #F59E0B; margin-bottom: 6px;">💪 돌쇠의 선택 (물통의 삶)</div>
<div style="font-size: 14px; color: #CBD5E1; line-height: 1.6; word-break: keep-all;">
"대감마님, 저는 첫 달부터 매달 <b>쌀 한 가마(80kg)</b>씩을 주십시오."<br>
돌쇠는 첫 달부터 쌀 한 가마를 받아 가족을 부양했습니다. 하지만 늙어 힘이 빠질 때까지 지게를 내려놓지 못했습니다.
</div>
</div>

<div style="background: rgba(15, 23, 42, 0.7); border: 1px solid #475569; border-radius: 10px; padding: 14px 16px;">
<div style="font-size: 17px; font-weight: 800; color: #38BDF8; margin-bottom: 6px;">🧠 똘똘이의 선택 (파이프라인의 삶)</div>
<div style="font-size: 14px; color: #CBD5E1; line-height: 1.6; word-break: keep-all;">
"저는 첫 달에 <b>쌀 한 되(1kg)</b>만 주시고, 매달 곱절(2되, 4되, 8되...)로 주십시오."<br>
똘똘이는 훗날 창고가 넘치는 거부가 되었습니다. <b>하지만 당장 첫 달에 쌀 한 되만 받았다면 굶어 죽었을 것입니다.</b>
</div>
</div>
</div>

<div style="background: rgba(234, 88, 12, 0.12); border-left: 4px solid #EA580C; border-radius: 4px; padding: 12px 16px;">
<div style="font-size: 15.5px; font-weight: 750; color: #F8FAFC; line-height: 1.6; word-break: keep-all;">
💡 <b>나침반의 성찰</b>: 돌쇠의 삶(현업)을 버리라는 것이 아닙니다.<br>
낮에는 돌쇠처럼 성실하게 가족의 생계(쌀 한 가마)를 책임지면서, 저녁과 주말의 시간에 똘똘이의 지혜(파이프라인)를 한 되, 두 되 차근차근 놓아가는 <b>'현명한 플랜 B'</b>가 필요한 이유입니다.
</div>
</div>
</div>
""", unsafe_allow_html=True)

    # --------------------------------------------------------------------------
    # 3. 내가 생각하는 은퇴 예상 나이
    # --------------------------------------------------------------------------
    st.markdown("### 내가 생각하는 은퇴 예상 나이")
    with st.form("retirement_form"):
        retirement_input = st.number_input(
            "지금 하는 현업을 졸업(은퇴)하고 싶은 나이",
            min_value=int(st.session_state.person_age), max_value=100,
            value=int(st.session_state["retirement_age"]) if st.session_state.get("retirement_age") is not None else 60,
            step=1, key="retirement_age_input",
        )
        retirement_saved = st.form_submit_button("은퇴 나이 확인", use_container_width=True, type="primary")
    
    if retirement_saved:
        st.session_state["retirement_age"] = int(retirement_input)
        st.success(f"은퇴 예상 나이({retirement_input}세)가 반영되었습니다.")

    _, next_col = st.columns([5, 1])
    with next_col:
        if st.button("다음 →", key="livelihood_next", use_container_width=True, type="primary"):
            st.session_state["retirement_age"] = int(st.session_state.get("retirement_age_input", retirement_input))
            st.session_state["_pending_nav"] = "인생의 사계절"
            st.session_state["_scroll_to_top_once"] = True
            st.rerun()


# ==============================================================================
# 6.03.00 | Tab 3 — 인생의 사계절 (Life Seasons & Official Benchmark)
# ==============================================================================
elif selected_page == "인생의 사계절":
    if st.session_state.pop("_scroll_to_top_once", False):
        st.components.v1.html(
            "<script>try { window.parent.scrollTo({top: 0, behavior: 'instant'}); } catch(e) {}</script>",
            height=0,
        )
    
    st.markdown("## 인생의 사계절")
    st.markdown("자연에 사계절이 있듯 사람의 삶에도 준비(봄) · 성장(여름) · 결실(가을) · 음미(겨울)의 시간이 있습니다.")
    
    age = int(st.session_state.person_age)
    retirement_value = st.session_state.get("retirement_age")
    retirement = int(retirement_value) if retirement_value is not None else 60
    years_left = max(0, retirement - age)

    # 가족 구성원 및 은퇴 시점 나이 연동
    st.markdown("### 1. 가족 구성원과 은퇴 시점의 나이")
    child_options = ["입력 안 함", "없음", "1명", "2명", "3명 이상"]
    child_count = st.selectbox(
        "자녀 수", child_options,
        index=child_options.index(st.session_state.get("child_count", "입력 안 함"))
        if st.session_state.get("child_count", "입력 안 함") in child_options else 0,
        key="child_count_live",
    )

    with st.form("family_form"):
        spouse_age = st.number_input("배우자 나이 (없거나 입력하지 않으려면 0)", min_value=0, max_value=120, value=int(st.session_state.get("spouse_age", 0)), step=1)
        child_age = int(st.session_state.get("child_age", 0)) if child_count in ["1명", "2명", "3명 이상"] else 0
        child_age2 = int(st.session_state.get("child_age2", 0)) if child_count in ["2명", "3명 이상"] else 0
        child_age3 = int(st.session_state.get("child_age3", 0)) if child_count == "3명 이상" else 0
        
        if child_count in ["1명", "2명", "3명 이상"]:
            child_age = st.number_input("첫째 자녀 나이", min_value=0, max_value=100, value=child_age, step=1)
        if child_count in ["2명", "3명 이상"]:
            child_age2 = st.number_input("둘째 자녀 나이", min_value=0, max_value=100, value=child_age2, step=1)
        if child_count == "3명 이상":
            child_age3 = st.number_input("셋째 자녀 나이", min_value=0, max_value=100, value=child_age3, step=1)
            
        col_f, col_m = st.columns(2)
        with col_f:
            father_age = st.number_input("아버지 나이 (선택, 모르면 0)", min_value=0, max_value=120, value=int(st.session_state.get("father_age", 0)), step=1)
        with col_m:
            mother_age = st.number_input("어머니 나이 (선택, 모르면 0)", min_value=0, max_value=120, value=int(st.session_state.get("mother_age", 0)), step=1)
            
        st.markdown("#### 앞으로의 가족 계획 (선택)")
        marriage_options = ["미정", "계획 없음", "1~3년 내 결혼 생각 있음", "3년 이후 결혼 생각 있음", "결혼 예정/준비 중"]
        marriage_plan = st.selectbox("결혼 계획", marriage_options, index=marriage_options.index(st.session_state.get("marriage_plan", "미정")) if st.session_state.get("marriage_plan", "미정") in marriage_options else 0)
        
        child_plan_options = ["미정", "계획 없음", "자녀 계획 있음", "출산 예정/준비 중", "추가 자녀 계획 있음"]
        child_plan = st.selectbox("출산·자녀 계획", child_plan_options, index=child_plan_options.index(st.session_state.get("child_plan", "미정")) if st.session_state.get("child_plan", "미정") in child_plan_options else 0)
        
        housing_options = ["미정", "현재 주거 유지", "전세·월세 이동 고려", "주택 구입 고려", "주거 계획 확정"]
        housing_plan = st.selectbox("주거 계획", housing_options, index=housing_options.index(st.session_state.get("housing_plan", "미정")) if st.session_state.get("housing_plan", "미정") in housing_options else 0)
        
        sibling_options = ["형", "남동생", "누나", "여동생", "오빠", "언니", "남자 형제(관계 미지정)", "여자 형제(관계 미지정)"]
        siblings = st.multiselect(
            "형제자매 (해당 항목 모두 선택)",
            sibling_options,
            default=[x for x in st.session_state.get("siblings", []) if x in sibling_options],
        )
        save_family = st.form_submit_button("가족 정보 반영하기", use_container_width=True, type="primary")

    if save_family:
        st.session_state.spouse_age = spouse_age
        st.session_state.child_count = child_count
        st.session_state.child_age = child_age
        st.session_state.child_age2 = child_age2
        st.session_state.child_age3 = child_age3
        st.session_state.father_age = father_age
        st.session_state.mother_age = mother_age
        st.session_state.siblings = siblings
        st.session_state.marriage_plan = marriage_plan
        st.session_state.child_plan = child_plan
        st.session_state.housing_plan = housing_plan
        st.rerun()

    # 가족 미래 나이 카드 렌더링
    people = [(st.session_state.get("person_name", "나"), age)]
    if getv("spouse_age", 0) > 0: people.append(("배우자", int(getv("spouse_age"))))
    if getv("child_age", 0) > 0: people.append(("첫째 자녀", int(getv("child_age"))))
    if getv("child_age2", 0) > 0: people.append(("둘째 자녀", int(getv("child_age2"))))
    if getv("child_age3", 0) > 0: people.append(("셋째 자녀", int(getv("child_age3"))))
    if getv("father_age", 0) > 0: people.append(("아버지", int(getv("father_age"))))
    if getv("mother_age", 0) > 0: people.append(("어머니", int(getv("mother_age"))))

    for name, current in people:
        future = current + years_left
        st.markdown(f"""
        <div class='soft-card' style='display:flex;align-items:center;gap:14px;flex-wrap:wrap;'>
            <b style='min-width:75px;font-size:16px;'>{name}</b>
            <span style='font-size:20px;font-weight:800;'>{current}세</span>
            <span style='font-size:22px;color:var(--nc-primary);padding:0 8px;'>➔</span>
            <span style='font-size:20px;font-weight:800;color:var(--nc-accent-gold);'>{future}세</span>
            <span class='small-muted'>(내가 {retirement}세 은퇴하는 시점)</span>
        </div>
        """, unsafe_allow_html=True)

    # 2. 공식 국민이전계정 곡선
    st.markdown("### 2. 대한민국 통계청 국민이전계정 생애주기 곡선")
    fig_nta = go.Figure()
    fig_nta.add_trace(go.Scatter(
        x=LIFECYCLE_BENCHMARK["age"], y=LIFECYCLE_BENCHMARK["labor_income"],
        mode="lines+markers", name="노동소득", line=dict(color="#10b981", width=3)
    ))
    fig_nta.add_trace(go.Scatter(
        x=LIFECYCLE_BENCHMARK["age"], y=LIFECYCLE_BENCHMARK["consumption"],
        mode="lines+markers", name="소비", line=dict(color="#f97316", width=3, dash="dash")
    ))
    fig_nta.add_vline(x=age, line_dash="solid", line_color="#38bdf8", line_width=2.5,
                      annotation_text=f"현재 나 ({age}세)", annotation_position="top")
    fig_nta.update_layout(
        height=370, margin=dict(l=20, r=20, t=35, b=20),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="var(--nc-text)"),
        xaxis=dict(title="연령 (세)", gridcolor="rgba(100,116,139,0.2)"),
        yaxis=dict(title="상대 규모 (지수)", gridcolor="rgba(100,116,139,0.2)"),
        legend=dict(orientation="h", y=1.12, x=1, xanchor="right")
    )
    st.plotly_chart(fig_nta, use_container_width=True, config={"displayModeBar": False})

    # 국가데이터처 팩트 통계 지표
    st.markdown("### 국가데이터처 공식 생애 통계 지표")
    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("흑자 진입", "28세", help="노동소득이 소비를 추월하는 연령")
    col_m2.metric("최대 흑자 정점", "45세", "연 1,932만 원")
    col_m3.metric("적자 재전환", "61세", help="은퇴 후 소비가 노동소득을 다시 초과")

    col_btn1, col_btn2 = st.columns(2)
    col_btn1.link_button("📄 2024년 국가데이터처 통계 보도자료", OFFICIAL_PDF_URL, use_container_width=True)
    col_btn2.link_button("🌐 국가데이터처 공식 발표 페이지", OFFICIAL_RELEASE_URL, use_container_width=True)

    winter_len = max(0, 88 - retirement)
    st.caption(f"은퇴 예정 나이 {retirement}세 이후 맞이할 겨울: 약 {winter_len}년 ({winter_len * 12}개월, 건강 기대수명 88세 가정)")

    _, next_col = st.columns([5, 1])
    with next_col:
        if st.button("다음 →", key="seasons_next", use_container_width=True, type="primary"):
            st.session_state["_pending_nav"] = "AI 시선"
            st.rerun()


# ==============================================================================
# 6.04.00 | Tab 4 — AI 시선 (AI Perspective & Gemini Analysis)
# ==============================================================================
else:
    st.markdown("## AI 시선")
    st.markdown("AI는 평가자가 아닌, 내가 작성한 숫자를 객관적인 거울처럼 비춰주는 성찰 파트너입니다.")
    
    model = st.radio(
        "분석할 AI 모델 선택",
        ["Gemini", "ChatGPT (준비 중)", "Claude (준비 중)"],
        index=0, key="ai_provider", horizontal=True,
    )
    
    if model != "Gemini":
        st.info(f"{model}은 연결 준비 중입니다. 현재는 Gemini 분석 엔진을 바로 사용하실 수 있습니다.")

    if st.button("내 가계부 AI 분석 실행", type="primary", use_container_width=True, disabled=(model != "Gemini")):
        summary = current_financial_summary()
        details = {
            "나이": st.session_state.get("person_age"),
            "소득 형태": st.session_state.get("job_form", ""),
            "월수입 항목": {k: getv(k, 0) for k in ["income_self", "income_spouse", "income_other", "income_pension"]},
            "월지출 항목": {k: getv(k, 0) for k in ["expense_living", "expense_loan", "expense_other"]},
            "자산 항목": {k: getv(k, 0) for k in ["asset_cash", "asset_financial", "asset_home", "asset_deposit", "asset_other"]},
            "부채 항목": {k: getv(k, 0) for k in ["debt_home", "debt_other"]},
            "삶과 시간 메모": st.session_state.get("life_choice_note", ""),
            "은퇴 예정 나이": st.session_state.get("retirement_age"),
            "가족 나이": {k: getv(k, 0) for k in ["spouse_age", "child_age", "child_age2", "child_age3", "father_age", "mother_age"]},
            "형제자매": st.session_state.get("siblings", []),
            "결혼 계획": st.session_state.get("marriage_plan", "미정"),
            "출산·자녀 계획": st.session_state.get("child_plan", "미정"),
            "주거 계획": st.session_state.get("housing_plan", "미정"),
        }
        st.session_state.ai_summary = summary
        st.session_state.ai_details = details
        st.session_state.ai_comment = None

        prompt = (
            "역할: 한국의 가계 재무와 은퇴 준비를 함께 검토하는 현실적이고 친근한 성찰 파트너입니다. "
            "투자상품을 권유하지 말고, 위협이나 공포 마케팅을 절대 배제하세요.\n\n"
            "참고 공식통계: 국가데이터처 2024 국민이전계정 기준 한국인 평균 흑자진입 28세, 최대흑자 45세(연 1,932만 원), 적자전환 61세.\n"
            "아래 두 코멘트만 작성하세요 (250~350자 내외, 쉬운 대화체).\n"
            "[은퇴 안정성]\n"
            "첫 문장은 '은퇴 안정성: 유리한 편 / 판단 보류 / 불리한 편' 중 하나로 시작.\n"
            "[소득 개선 방향]\n"
            "투잡 추가와 본업 유지 후 파이프라인(자산/사업) 준비 중 적합한 방향 조언.\n\n"
            f"입력 데이터:\n{json.dumps(details, ensure_ascii=False)}"
        )
        with st.spinner("AI가 입력하신 삶과 재무의 지표를 성찰 중입니다..."):
            comment, error = call_gemini_text(prompt)
            st.session_state.ai_comment = comment if comment else error

    if st.session_state.get("ai_summary"):
        s = st.session_state.ai_summary
        st.markdown("### 재무제표 요약")
        cols = st.columns(4)
        cols[0].metric("월수입 합계", money(s["income"]))
        cols[1].metric("월지출 합계", money(s["expenses"]))
        cols[2].metric("월 저축여력", money(s["surplus"]))
        cols[3].metric("순자산", fmt_eok(s["net_worth"]))

        st.markdown("### AI 성찰 리포트")
        comment_text = str(st.session_state.get("ai_comment", ""))
        
        # 코멘트 파싱 (은퇴 안정성 vs 소득 개선 방향)
        normalized = comment_text.replace("\r\n", "\n").replace("\r", "\n")
        match = re.search(r"(?im)^\s*(?:#{1,6}\s*)?(?:\*\*|__)?\s*(?:\[\s*)?소득\s*개선\s*방향\s*(?:\])?\s*(?:\*\*|__)?\s*:?\s*$", normalized)
        if match:
            retirement_comment = normalized[:match.start()]
            income_comment = normalized[match.end():]
        else:
            retirement_comment, income_comment = normalized, ""

        retirement_comment = re.sub(r"(?i)\[\s*은퇴\s*안정성\s*\]", "", retirement_comment).strip()
        income_comment = re.sub(r"(?i)\[\s*소득\s*개선\s*방향\s*\]", "", income_comment).strip()

        st.markdown("#### 은퇴 안정성 관점")
        st.markdown(f"<div class='soft-card'>{retirement_comment}</div>", unsafe_allow_html=True)
        st.markdown("#### 소득 개선 관점 (파이프라인)")
        st.markdown(f"<div class='soft-card'>{income_comment or '분석 결과를 정리 중입니다. 다시 시도해 주세요.'}</div>", unsafe_allow_html=True)
        st.caption("※ AI의 코멘트는 참고용 거울이며, 삶의 가장 중요한 결정은 온전히 당신의 것입니다.")
    else:
        st.info("‘내 가계부 AI 분석 실행’ 버튼을 누르면 입력하신 데이터를 바탕으로 AI의 따뜻한 피드백이 생성됩니다.")
