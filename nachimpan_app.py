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
# 1.02.00 | 전역 통합 테마 디자인 시스템 CSS (1단계: 팝업창 중앙정렬 원본 복원)
# ==============================================================================
st.markdown("""
<style>
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
    --nc-quad-active-bg: #34291a;
    --nc-quad-active-border: #f59e0b;
    --nc-quad-active-text: #fde68a;
    
    /* 재무 패널 전용 다크 테마 색상 */
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

/* 라이트 모드 (명시적 선택 또는 OS 기본이 라이트인 경우 자동 활성화) */
html[data-theme="light"],
@media (prefers-color-scheme: light) {
    :root {
        --nc-bg: #f8fafc;
        --nc-sidebar-bg: #eef2f7;
        --nc-text: #0f172a;
        --nc-subtext: #475569;
        --nc-border: #cbd5e1;
        --nc-card-bg: #ffffff;
        --nc-hero-bg: radial-gradient(circle at top, #ffffff 0%, #eaf0f8 78%);
        --nc-quad-bg: #f1f5f9;
        --nc-quad-active-bg: #fef3c7;
        --nc-quad-active-border: #d97706;
        --nc-quad-active-text: #78350f;
        
        /* 재무 패널 라이트 테마 가독성 색상 */
        --nc-panel-income: #e0f2ec;
        --nc-panel-income-border: #70b9a6;
        --nc-panel-expense: #fce7e7;
        --nc-panel-expense-border: #e5a0a5;
        --nc-panel-asset: #e2effb;
        --nc-panel-asset-border: #8db9df;
        --nc-panel-debt: #fff1d6;
        --nc-panel-debt-border: #dfbd78;
        --nc-panel-retire: #f0e7fb;
        --nc-panel-retire-border: #b9a0dc;
    }
}

/* ==========================================================================
   글로벌 레이아웃 & 폰트 크기
   ========================================================================== */
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
    font-size: 16.5px;
    color: var(--nc-text);
}

/* ==========================================================================
   통합 공통 카드 & 히어로 섹션
   ========================================================================== */
.hero {
    border: 1px solid var(--nc-border);
    border-radius: 18px;
    padding: 32px 24px;
    text-align: center;
    background: var(--nc-hero-bg);
    margin: 12px 0 20px;
}
.hero-title {
    font-size: clamp(28px, 4vw, 44px);
    font-weight: 800;
    color: var(--nc-text);
}
.hero-sub {
    color: var(--nc-subtext);
    font-size: 16px;
    line-height: 1.7;
    max-width: 680px;
    margin: 10px auto 0;
}
.soft-card {
    background: var(--nc-card-bg);
    border: 1px solid var(--nc-border);
    border-radius: 14px;
    padding: 18px 20px;
    margin: 10px 0;
    color: var(--nc-text);
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}
.eyebrow {
    color: var(--nc-accent-gold);
    font-size: 13px;
    font-weight: 700;
    letter-spacing: .04em;
    margin-bottom: 4px;
}
.question {
    font-size: clamp(18px, 2.2vw, 24px);
    line-height: 1.5;
    font-weight: 700;
    color: var(--nc-text);
}
.small-muted {
    color: var(--nc-subtext);
    font-size: 13px;
}

/* ==========================================================================
   ESBI 사분면 & 물통 카드
   ========================================================================== */
.quad {
    border-radius: 10px;
    padding: 14px 10px;
    border: 1px solid var(--nc-border);
    background: var(--nc-quad-bg);
    color: var(--nc-text);
    text-align: center;
    min-height: 145px;
    display: flex;
    flex-direction: column;
    justify-content: center;
}
.quad-active {
    border: 2px solid var(--nc-quad-active-border);
    background: var(--nc-quad-active-bg);
    color: var(--nc-quad-active-text);
}
.income-card {
    min-height: 180px;
    height: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 18px 14px;
}

/* ==========================================================================
   재무 카테고리별 컬러 패널 (라이트/다크 완전 분리)
   ========================================================================== */
.st-key-income-panel { background: var(--nc-panel-income) !important; border: 1px solid var(--nc-panel-income-border) !important; border-radius: 12px; }
.st-key-expense-panel { background: var(--nc-panel-expense) !important; border: 1px solid var(--nc-panel-expense-border) !important; border-radius: 12px; }
.st-key-asset-panel { background: var(--nc-panel-asset) !important; border: 1px solid var(--nc-panel-asset-border) !important; border-radius: 12px; }
.st-key-debt-panel { background: var(--nc-panel-debt) !important; border: 1px solid var(--nc-panel-debt-border) !important; border-radius: 12px; }
.st-key-retirement-panel { background: var(--nc-panel-retire) !important; border: 1px solid var(--nc-panel-retire-border) !important; border-radius: 12px; }

/* 패널 내부 텍스트 색상 */
.st-key-income-panel *, .st-key-expense-panel *, .st-key-asset-panel *,
.st-key-debt-panel *, .st-key-retirement-panel * {
    color: var(--nc-text) !important;
}

/* ==========================================================================
   Streamlit 위젯 가독성 강화 (Metric, Button, Input, Caption)
   ========================================================================== */
/* 지표(Metric) */
[data-testid="stMetricLabel"] *, [data-testid="stMetricLabel"] {
    color: var(--nc-subtext) !important;
    font-size: 14px !important;
    font-weight: 600 !important;
}
[data-testid="stMetricValue"] *, [data-testid="stMetricValue"] {
    color: var(--nc-text) !important;
    font-weight: 800 !important;
}
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * {
    color: var(--nc-subtext) !important;
    font-size: 13px !important;
}

/* 버튼 (Primary) */
button[kind="primary"], .stApp [data-testid="stFormSubmitButton"] button[kind="primary"] {
    background-color: var(--nc-primary) !important;
    border-color: var(--nc-primary) !important;
    color: #ffffff !important;
    font-weight: 700 !important;
    border-radius: 8px !important;
}
button[kind="primary"]:hover {
    background-color: var(--nc-primary-hover) !important;
    border-color: var(--nc-primary-hover) !important;
}
button[kind="primary"] * {
    color: #ffffff !important;
}

/* 사이드바 스타일 통일 */
[data-testid="stSidebar"] {
    background-color: var(--nc-sidebar-bg) !important;
    border-right: 1px solid var(--nc-border) !important;
}
[data-testid="stSidebar"] * {
    color: var(--nc-text) !important;
}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] * {
    color: var(--nc-subtext) !important;
}

/* 입력 필드 (Text, Number, Select) */
.stApp input, .stApp textarea, .stApp [data-baseweb="select"] > div {
    background-color: var(--nc-card-bg) !important;
    color: var(--nc-text) !important;
    border-color: var(--nc-border) !important;
    font-size: 16px !important;
}

/* ==========================================================================
   시작 팝업창 중앙 정렬 원본 복원 (닫기 버튼 분리, 제목/라벨/버튼 중앙 정렬)
   ========================================================================== */
div[data-testid="stDialog"] > div { margin: auto !important; }
div[data-testid="stDialog"] [data-testid="stVerticalBlock"] { align-items: stretch; }

div[data-testid="stDialog"] section[role="dialog"] {
    position: relative !important;
}

div[data-testid="stDialog"] section[role="dialog"] > button[aria-label="Close"] {
    position: absolute !important;
    top: 12px !important;
    right: 12px !important;
    z-index: 2 !important;
}

div[data-testid="stDialog"] section[role="dialog"] > h2[slot="title"] {
    display: block !important;
    width: 100% !important;
    box-sizing: border-box !important;
    text-align: center !important;
    padding: 20px 32px 0 !important;
    margin: 0 0 1rem 0 !important;
    line-height: 1.4 !important;
}

div[data-testid="stDialog"] section[role="dialog"] > h2[slot="title"] span,
div[data-testid="stDialog"] section[role="dialog"] > h2[slot="title"] [data-testid="stMarkdownContainer"],
div[data-testid="stDialog"] section[role="dialog"] > h2[slot="title"] p {
    display: block !important;
    width: 100% !important;
    box-sizing: border-box !important;
    text-align: center !important;
    margin: 0 auto !important;
}
div[data-testid="stDialog"] label { display: block !important; width: 100% !important; text-align: center !important; }
div[data-testid="stDialog"] [data-testid="stWidgetLabel"] { justify-content: center !important; width: 100% !important; }
div[data-testid="stDialog"] input, div[data-testid="stDialog"] button { text-align: center !important; }
div[data-testid="stDialog"] input { text-align: center !important; }

/* 시작 팝업 나이 입력의 +/- 조절 버튼 제거 */
div[data-testid="stDialog"] input[type="number"]::-webkit-inner-spin-button,
div[data-testid="stDialog"] input[type="number"]::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
div[data-testid="stDialog"] input[type="number"] { appearance: textfield; -moz-appearance: textfield; }

/* 커버 스타일 */
.cover-bg { position: relative; min-height: 68vh; border-radius: 18px; overflow: hidden; background-size: cover; background-position: center; display:flex; align-items:center; justify-content:center; }
.cover-shade { position:absolute; inset:0; background:linear-gradient(180deg,rgba(8,17,32,.08),rgba(8,17,32,.3)); }
.cover-caption { position:relative; z-index:1; text-align:center; color:#fff; text-shadow:0 2px 14px rgba(0,0,0,.7); padding:8px; }
.cover-caption h1 { margin:0; font-size:clamp(22px,3.5vw,34px); color:#fff; }
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

# ------------------------------------------------------------------------------
# 2.02.00 | 재무 포맷팅 및 집계 로직
# ------------------------------------------------------------------------------
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
    income = sum(float(getv(k, 0)) for k in ["income_self", "income_spouse", "income_other"])
    expenses = sum(float(getv(k, 0)) for k in ["expense_living", "expense_loan", "expense_other"])
    assets = sum(float(getv(k, 0)) for k in ["asset_cash", "asset_financial", "asset_home", "asset_deposit", "asset_other"])
    debts = sum(float(getv(k, 0)) for k in ["debt_home", "debt_other"])
    return {
        "income": income, "expenses": expenses, "surplus": income - expenses,
        "assets": assets, "debts": debts, "net_worth": assets - debts
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

# ------------------------------------------------------------------------------
# 4.01.00 | 첫 진입 표지 및 온보딩 다이얼로그
# ------------------------------------------------------------------------------
cover_path = os.path.join(os.path.dirname(__file__), "나침반_표지_배경.png")
if os.path.exists(cover_path):
    with open(cover_path, "rb") as f:
        cover_b64 = base64.b64encode(f.read()).decode("ascii")
    cover_style = f"background-image:url(data:image/png;base64,{cover_b64});"
else:
    cover_style = "background: radial-gradient(circle at top, #38506c, #0f172a 70%);"

if not st.session_state.started:
    st.markdown(f"""
    <div class="cover-bg" style="{cover_style}">
      <div class="cover-shade"></div>
      <div class="cover-caption">
        <h1>나침반</h1>
        <div style="font-size:clamp(12px,1.4vw,15px);font-weight:600;margin-top:6px;">나를 돌아보고, 내일을 그리는 여정</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    @st.dialog("나침반 산책을 시작합니다", width="small")
    def start_dialog():
        with st.form("start_form", clear_on_submit=False):
            name = st.text_input("이름 또는 별칭", placeholder="편하신 별칭을 적어주세요", key="start_person_name")
            age_text = st.text_input("나이", placeholder="예: 38", key="start_person_age_text", max_chars=3)
            try:
                age = int(age_text) if age_text.strip() else None
                if age is not None and not (1 <= age <= 120):
                    age = None
            except ValueError:
                age = None
            submitted = st.form_submit_button("시작하기", use_container_width=True, type="primary")
        if submitted:
            if not name.strip() or age is None:
                st.warning("이름(별칭)과 올바른 나이를 입력해 주세요.")
            else:
                st.session_state.person_name = name.strip()
                st.session_state.person_age = int(age)
                st.session_state.started = True
                st.rerun()

    start_dialog()
    st.stop()

# ------------------------------------------------------------------------------
# 4.02.00 | 사이드바 프로필 요약 카드 (불필요한 중복 문구 제거)
# ------------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🧭 나침반 기록")
    st.markdown(f"**이름/별칭:** {st.session_state.get('person_name','')}")
    st.markdown(f"**나이:** {st.session_state.get('person_age','')}세")
    code = active_quadrant(st.session_state.get("job_form", ""))
    st.markdown(f"**익숙한 소득 형태:** {code or '아직 미정'}")
    st.write("")
    st.caption(f"익명 고유번호 **{st.session_state.anonymous_id}**")


# ==============================================================================
# 5.00.00 | 메인 네비게이션 헤더 (Main Navigation Segment)
# ==============================================================================

# ==============================================================================
# 5.01.00 | 가로 4대 메뉴 네비게이터 (option_menu iframe 전용 색상 고정 복원)
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
            "padding": "8px",
            "background-color": "#0F172A",
            "border": "1px solid #263449",
            "border-radius": "12px",
            "margin-top": "6px",
            "margin-bottom": "22px",
            "width": "100%"
        },
        "icon": {"display": "none"},
        "nav-link": {
            "font-size": "15.5px",
            "white-space": "pre-line",
            "line-height": "1.25",
            "text-align": "center",
            "margin": "3px 4px",
            "padding": "10px 8px",
            "color": "#CBD5E1",
            "--hover-color": "#334155",
            "border-radius": "9px",
            "min-height": "60px"
        },
        "nav-link-selected": {
            "background-color": "#EA580C",
            "color": "#FFFFFF",
            "font-weight": "800",
            "box-shadow": "0 3px 10px rgba(234,88,12,0.3)"
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
# 6.01.00 | Tab 1 — 우리집 가계부 (Household Finances)
# ==============================================================================
if selected_page == "우리집 가계부":
    st.markdown("## 우리집 가계부")
    
    with st.form("finance_form"):
        # 직업 선택 (소득의 성격 파악)
        st.markdown("#### 현재 상황")
        job_options = ["선택하세요", "직장인", "자영업", "전문직", "사업가", "투자자", "임대소득자", "그외"]
        previous_job = st.session_state.get("job_form", "선택하세요")
        job_index = job_options.index(previous_job) if previous_job in job_options else 0
        job = st.selectbox("나의 직업은?", job_options, index=job_index, key="job_form_input")

        # 현금흐름 (수입 vs 지출)
        income_col, expense_col = st.columns(2)
        with income_col:
            with st.container(border=True, key="income-panel"):
                st.markdown("#### ① 들어오는 돈")
                st.caption("현재 한 달 기준 · 만원")
                income_self = st.number_input("본인 월 실수령액", min_value=0, value=st.session_state.get("income_self"), step=10, placeholder="금액")
                income_spouse = st.number_input("배우자 월 실수령액", min_value=0, value=st.session_state.get("income_spouse"), step=10, placeholder="금액")
                income_other = st.number_input("기타·자산 소득", min_value=0, value=st.session_state.get("income_other"), step=10, placeholder="금액", help="임대료, 배당 등")
        with expense_col:
            with st.container(border=True, key="expense-panel"):
                st.markdown("#### ② 나가는 돈")
                st.caption("현재 한 달 기준 · 만원")
                expense_living = st.number_input("기본 생활비", min_value=0, value=st.session_state.get("expense_living"), step=10, placeholder="월 금액", help="식비, 공과금, 통신비")
                expense_loan = st.number_input("대출 원리금 상환액", min_value=0, value=st.session_state.get("expense_loan"), step=10, placeholder="금액", help="대출 원금+이자")
                expense_other = st.number_input("그 밖의 월평균 지출", min_value=0, value=st.session_state.get("expense_other"), step=10, placeholder="금액", help="보험료, 교육비, 의료비 등")

        # 대차대조표 (자산 vs 부채)
        asset_col, debt_col = st.columns(2)
        with asset_col:
            with st.container(border=True, key="asset-panel"):
                st.markdown("#### ③ 가지고 있는 것")
                st.caption("현재 보유 금액·시세 기준 · 만원")
                asset_cash = st.number_input("현금·예적금", min_value=0, value=st.session_state.get("asset_cash"), step=100, placeholder="금액")
                asset_financial = st.number_input("주식·채권 등 금융자산", min_value=0, value=st.session_state.get("asset_financial"), step=100, placeholder="금액")
                asset_home = st.number_input("부동산 시세", min_value=0, value=st.session_state.get("asset_home"), step=100, placeholder="금액")
                asset_deposit = st.number_input("전세보증금", min_value=0, value=st.session_state.get("asset_deposit"), step=100, placeholder="금액")
                asset_other = st.number_input("기타 자산·사업 가치", min_value=0, value=st.session_state.get("asset_other"), step=100, placeholder="금액")
        with debt_col:
            with st.container(border=True, key="debt-panel"):
                st.markdown("#### ④ 갚아야 할 돈")
                st.caption("현재 남은 대출 원금 기준 · 만원")
                debt_home = st.number_input("주택담보·전세대출 잔액", min_value=0, value=st.session_state.get("debt_home"), step=100, placeholder="금액")
                debt_other = st.number_input("그 밖의 부채 잔액", min_value=0, value=st.session_state.get("debt_other"), step=100, placeholder="금액")

        # 미래 은퇴 후 가정 (현재 수입·지출과 엄격히 분리)
        with st.container(border=True, key="retirement-panel"):
            st.markdown("#### 은퇴 후에는?")
            pension_col, retirement_expense_col = st.columns(2)
            with pension_col:
                income_pension = st.number_input(
                    "은퇴 후 받을 월 연금", min_value=0,
                    value=st.session_state.get("income_pension"), step=10,
                    placeholder="모르면 0",
                    help="국민연금·퇴직연금 등 은퇴 후 예상 수령액입니다. 현재 월수입에는 합산되지 않습니다."
                )
            with retirement_expense_col:
                retirement_monthly_expenses = st.number_input(
                    "은퇴 후 한 달 생활비", min_value=0,
                    value=int(st.session_state.get("retirement_monthly_expenses", 200) or 0),
                    step=10,
                    help="은퇴 후 식비, 의료비, 주거비 등 한 달 예상 생활비입니다."
                )
            st.caption("📌 적정 노후생활비(월): 부부 298.1만 원, 1인 197.6만 원 (국민연금연구원 조사 기준)")

        save_finance = st.form_submit_button("입력 내용 반영하기", use_container_width=True, type="primary")

    if save_finance:
        submitted_values = {
            "job_form": "" if job == "선택하세요" else job,
            "income_self": income_self, "income_spouse": income_spouse,
            "income_other": income_other, "income_pension": income_pension,
            "expense_living": expense_living, "expense_loan": expense_loan,
            "expense_other": expense_other, "retirement_monthly_expenses": retirement_monthly_expenses,
            "asset_cash": asset_cash, "asset_financial": asset_financial, "asset_home": asset_home,
            "asset_deposit": asset_deposit, "asset_other": asset_other,
            "debt_home": debt_home, "debt_other": debt_other,
        }
        for k, v in submitted_values.items():
            st.session_state[k] = v
        st.session_state["finance_saved_notice"] = True

    # ESBI 사분면 매핑
    q = active_quadrant(st.session_state.get("job_form", ""))
    st.markdown("#### ESBI 사분면")
    st.markdown("<div id='selected-esbi'></div>", unsafe_allow_html=True)
    if st.session_state.pop("finance_saved_notice", False):
        st.success("입력하신 재무 정보가 반영되었습니다.")
        st.components.v1.html("<script>try { window.parent.document.getElementById('selected-esbi').scrollIntoView({behavior:'smooth',block:'center'}); } catch(e) {}</script>", height=0)

    cols = st.columns(4)
    for col, code in zip(cols, ["E", "S", "B", "I"]):
        title, desc = ESBI[code]
        css = "quad-active" if q == code else "quad"
        col.markdown(f"<div class='{css}'><b style='font-size:20px'>{code}</b><br><b>{title}</b><br><span class='small-muted'>{desc}</span></div>", unsafe_allow_html=True)

    # 현재 입력값 지표 요약
    s = current_financial_summary()
    st.markdown("#### 현재 재무 요약")
    cols = st.columns(4)
    cols[0].metric("월수입 합계", money(s["income"]))
    cols[1].metric("월지출 합계", money(s["expenses"]))
    cols[2].metric("월 저축여력", money(s["surplus"]))
    cols[3].metric("순자산", fmt_eok(s["net_worth"]))

    # 미래 순자산 궤적 차트
    st.markdown("#### 미래 순자산·연금 궤적")
    cur_age = int(st.session_state.person_age)
    retirement_value = st.session_state.get("retirement_age")
    retire_age = int(retirement_value) if retirement_value is not None else 65
    retire_age = max(cur_age, min(retire_age, 100))
    annual_savings = s["surplus"] * 12
    years = sorted(set([cur_age, 80, retire_age] + list(range(((cur_age // 5) + 1) * 5, 81, 5))))
    vals = []
    
    ret_expenses = float(getv("retirement_monthly_expenses", 200) or 0)
    ret_pension = float(getv("income_pension", 0) or 0)
    
    for a in years:
        working_yrs = max(0, min(a, retire_age) - cur_age)
        proj = s["net_worth"] + annual_savings * working_yrs
        if a > retire_age:
            ret_cashflow = (ret_pension - ret_expenses) * 12
            proj += ret_cashflow * (a - retire_age)
        vals.append(proj)

    fig_asset = go.Figure(go.Scatter(
        x=years, y=vals, mode="lines+markers",
        line=dict(color="#f59e0b", width=3), name="추정 순자산"
    ))
    fig_asset.add_vline(x=retire_age, line_dash="dash", line_color="#38bdf8",
                        annotation_text=f"은퇴 가정 {retire_age}세", annotation_position="top")
    fig_asset.update_layout(
        height=360, margin=dict(l=20, r=20, t=30, b=40),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="var(--nc-text)"),
        xaxis=dict(title="나이 (세)", gridcolor="rgba(100,116,139,0.2)"),
        yaxis=dict(title="순자산 (만 원)", gridcolor="rgba(100,116,139,0.2)")
    )
    st.plotly_chart(fig_asset, use_container_width=True, config={"displayModeBar": False})
    st.caption("※ 은퇴 전 월 저축액 누적 및 은퇴 후 [연금 - 노후생활비] 현금흐름을 단순 연산한 개념도입니다.")

    _, next_col = st.columns([5, 1])
    with next_col:
        if st.button("다음 →", key="finance_next", use_container_width=True, type="primary"):
            st.session_state["_pending_nav"] = "삶과 생계수단"
            st.rerun()


# ==============================================================================
# 6.02.00 | Tab 2 — 삶과 생계수단 (Livelihood & Buckets vs Pipeline)
# ==============================================================================
elif selected_page == "삶과 생계수단":
    st.markdown("## 삶과 생계수단")
    st.markdown("""
    <div class='soft-card'>
        <div class='eyebrow'>잠시 생각해보는 거울</div>
        <div class='question'>내가 지금까지 생계를 유지해 온 방식은 온전한 나의 선택이었을까요? 주어진 상황에서 최선을 다해 받아들인 결과였을까요?</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.text_area("떠오르는 생각이 있다면 편하게 적어두세요 (선택)", key="life_choice_note", height=90, placeholder="답을 정할 필요 없이 마음 가는 대로 적으셔도 좋습니다.")
    
    st.markdown("### 소득이 만들어지는 세 가지 모습")
    cols = st.columns(3)
    cols[0].markdown("<div class='soft-card income-card'><div style='font-size:38px'>🪣</div><b>작은 물통</b><p class='small-muted'>직접 일한 시간과 소득이 1:1로 맞바꿔지는 모습</p></div>", unsafe_allow_html=True)
    cols[1].markdown("<div class='soft-card income-card'><div style='font-size:38px'>🛢️</div><b>큰 물통</b><p class='small-muted'>전문성과 몸값을 높여 한 번에 담는 양을 키운 모습</p></div>", unsafe_allow_html=True)
    cols[2].markdown("<div class='soft-card income-card'><div style='font-size:38px'>🚰</div><b>파이프라인</b><p class='small-muted'>내가 멈추어도 시스템과 자산에서 흐름이 이어지는 모습</p></div>", unsafe_allow_html=True)

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
