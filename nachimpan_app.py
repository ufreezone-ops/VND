# ==============================================================================
# 나침반 | 인터뷰이를 위한 삶과 재무의 산책로
# 화면 개편 1차본: 다섯 페이지(시작 포함), 실제 입력값 중심
# ==============================================================================
import os
import random
import json
import urllib.request
import urllib.error
import requests
from datetime import date
import base64
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_option_menu import option_menu

st.set_page_config(
    page_title="나침반 — 나의 삶을 바라보는 산책로",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
:root { color-scheme: light dark; }
.stApp { background: var(--background-color, #0b1120) !important; color: var(--text-color, #f8fafc) !important; }
[data-testid="stSidebar"] { background: var(--secondary-background-color, #0f172a) !important; border-right: 1px solid var(--border-color, #263449) !important; }
.block-container { padding-top: 2.5rem; padding-bottom: 1rem; max-width: 1180px; }
.hero { border: 1px solid var(--border-color, #334155); border-radius: 20px; padding: 38px 30px; text-align: center;
        background: var(--secondary-background-color, #0f172a); margin: 14px 0 22px; }
.hero-mark { font-size: 52px; line-height: 1.3; }
.hero-title { font-size: clamp(32px, 5vw, 52px); font-weight: 850; letter-spacing: -1px; color: var(--text-color, #f8fafc); }
.hero-sub { color: var(--text-color, #cbd5e1); font-size: 17px; line-height: 1.8; max-width: 720px; margin: 12px auto 0; }
.soft-card { background: var(--secondary-background-color, #151e2f); border: 1px solid var(--border-color, #334155); border-radius: 13px; padding: 17px 19px; margin: 10px 0; }
.eyebrow { color: #fbbf24; font-size: 13px; font-weight: 750; letter-spacing: .04em; }
.small-muted { color: var(--text-color, #94a3b8); font-size: 12px; }
.quad { border-radius: 10px; padding: 8px 10px; border: 1px solid #475569; background: #172033; text-align: center; }
.quad-active { border: 2px solid #f59e0b; background: #34291a; color: #fde68a; }
.question { font-size: clamp(20px, 2.5vw, 27px); line-height: 1.55; font-weight: 750; color: var(--text-color, #f8fafc); }
/* 시작 팝업은 화면 중앙, 제목·입력·버튼 글자도 중앙 정렬 */
div[data-testid="stDialog"] > div { margin: auto !important; }
div[data-testid="stDialog"] [data-testid="stVerticalBlock"] { align-items: stretch; }
/* 시작 팝업 제목: 닫기 버튼과 분리하고 중앙 정렬 */
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
div[data-testid="stDialog"] label { display:block !important; width:100% !important; text-align:center !important; }
div[data-testid="stDialog"] [data-testid="stWidgetLabel"] { justify-content:center !important; width:100% !important; }
div[data-testid="stDialog"] input, div[data-testid="stDialog"] button { text-align:center !important; }
div[data-testid="stDialog"] input { text-align:center !important; }
/* 시작 팝업 나이 입력의 +/- 조절 버튼 제거 */
div[data-testid="stDialog"] input[type="number"]::-webkit-inner-spin-button,
div[data-testid="stDialog"] input[type="number"]::-webkit-outer-spin-button { -webkit-appearance:none; margin:0; }
div[data-testid="stDialog"] input[type="number"] { appearance:textfield; -moz-appearance:textfield; }
.quad, .quad-active { min-height:145px; height:100%; box-sizing:border-box; display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; padding:12px 10px; }
.income-card { min-height:180px; height:100%; box-sizing:border-box; display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; padding:18px 14px; }
/* 첫 화면은 표지 이미지가 배경 */
.cover-bg { position: relative; min-height: 68vh; border-radius: 18px; overflow: hidden; background-size: cover; background-position: center; display:flex; align-items:center; justify-content:center; }
.cover-shade { position:absolute; inset:0; background:linear-gradient(180deg,rgba(8,17,32,.05),rgba(8,17,32,.25)); }
.cover-caption { position:relative; z-index:1; text-align:center; color:#fff; text-shadow:0 2px 16px rgba(0,0,0,.7); padding:8px; }
.cover-caption h1 { margin:0; font-size:clamp(20px,3vw,30px); color:#fff; }
/* 전체 글자 크기를 키워 읽기 편하게 */
.stApp, .stApp p, .stApp label, .stApp [data-testid="stWidgetLabel"],
.stApp [data-testid="stMarkdownContainer"] { font-size: 17px; }
.stApp [data-testid="stCaptionContainer"] { font-size: 14px; }
/* 입력 라벨은 Streamlit이 선택한 테마의 글자색을 사용 */
.stApp [data-testid="stWidgetLabel"],
.stApp [data-testid="stWidgetLabel"] label,
.stApp [data-testid="stWidgetLabel"] p {
    color: var(--text-color, inherit) !important;
    font-weight: 600 !important;
    opacity: 1 !important;
}
/* Light/Dark 전환 시 앱 바탕·기본 글자색도 Streamlit 테마를 따름 */
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"] {
    background-color: var(--background-color, #0b1120) !important;
    color: var(--text-color, #f8fafc) !important;
}
.stApp input, .stApp textarea, .stApp [data-baseweb="select"] { font-size: 17px !important; }
.stApp [data-testid="stNumberInput"] button { min-width: 34px; }
.stApp h1 { font-size: clamp(30px, 3.5vw, 38px); }
.stApp h2 { font-size: clamp(26px, 3vw, 32px); }
.stApp h3 { font-size: clamp(22px, 2.5vw, 27px); }
.stApp h4 { font-size: 21px; }
/* 재무 카테고리별 배경색 */
.st-key-income-panel { background: #163b35 !important; border-color: #2f806d !important; }
.st-key-expense-panel { background: #442a2d !important; border-color: #a34c56 !important; }
.st-key-asset-panel { background: #183653 !important; border-color: #3b82b5 !important; }
.st-key-debt-panel { background: #44351d !important; border-color: #a8792d !important; }
.st-key-retirement-panel { background: #34264a !important; border-color: #8761b3 !important; }
.st-key-income-panel [data-testid="stMarkdownContainer"], .st-key-income-panel [data-testid="stWidgetLabel"],
.st-key-expense-panel [data-testid="stMarkdownContainer"], .st-key-expense-panel [data-testid="stWidgetLabel"],
.st-key-asset-panel [data-testid="stMarkdownContainer"], .st-key-asset-panel [data-testid="stWidgetLabel"],
.st-key-debt-panel [data-testid="stMarkdownContainer"], .st-key-debt-panel [data-testid="stWidgetLabel"],
.st-key-retirement-panel [data-testid="stMarkdownContainer"], .st-key-retirement-panel [data-testid="stWidgetLabel"] { color: #f8fafc; }
html[data-theme="light"] .st-key-income-panel { background: #e0f2ec !important; border-color: #70b9a6 !important; }
html[data-theme="light"] .st-key-expense-panel { background: #fce7e7 !important; border-color: #e5a0a5 !important; }
html[data-theme="light"] .st-key-asset-panel { background: #e2effb !important; border-color: #8db9df !important; }
html[data-theme="light"] .st-key-debt-panel { background: #fff1d6 !important; border-color: #dfbd78 !important; }
html[data-theme="light"] .st-key-retirement-panel { background: #f0e7fb !important; border-color: #b9a0dc !important; }
html[data-theme="light"] .st-key-income-panel [data-testid="stMarkdownContainer"], html[data-theme="light"] .st-key-income-panel [data-testid="stWidgetLabel"],
html[data-theme="light"] .st-key-expense-panel [data-testid="stMarkdownContainer"], html[data-theme="light"] .st-key-expense-panel [data-testid="stWidgetLabel"],
html[data-theme="light"] .st-key-asset-panel [data-testid="stMarkdownContainer"], html[data-theme="light"] .st-key-asset-panel [data-testid="stWidgetLabel"],
html[data-theme="light"] .st-key-debt-panel [data-testid="stMarkdownContainer"], html[data-theme="light"] .st-key-debt-panel [data-testid="stWidgetLabel"],
html[data-theme="light"] .st-key-retirement-panel [data-testid="stMarkdownContainer"], html[data-theme="light"] .st-key-retirement-panel [data-testid="stWidgetLabel"] { color: #172033 !important; }
/* 원래처럼 큼직한 4개 가로 탭 */
.nav-link-container { padding: 8px !important; background:var(--secondary-background-color, #0f172a) !important; border:1px solid var(--border-color, #263449) !important; border-radius:12px !important; margin:8px 0 24px !important; }
.nav-link { min-height:52px !important; padding:14px 8px !important; font-size:16px !important; font-weight:700 !important; border-radius:9px !important; }
.nav-link i { font-size:18px !important; }
@media (max-width: 700px) { .nav-link { min-height:48px !important; font-size:12px !important; padding:9px 2px !important; } }
hr { border-color: var(--border-color, #334155); }
/* Light/System 모드에서도 입력 글자와 카드의 대비를 확보 */
html[data-theme="light"] {
    color-scheme: light;
    --app-bg: #f8fafc;
    --app-fg: #172033;
}
html[data-theme="light"] .stApp { background: #f8fafc !important; color: #172033 !important; }
html[data-theme="light"] [data-testid="stSidebar"] { background: #eef2f7 !important; border-right-color: #cbd5e1 !important; }
html[data-theme="light"] .soft-card,
html[data-theme="light"] .nav-link-container { background: #ffffff !important; border-color: #cbd5e1 !important; }
html[data-theme="light"] .hero { background: radial-gradient(circle at top, #ffffff 0%, #eaf0f8 78%) !important; border-color: #cbd5e1 !important; }
html[data-theme="light"] .hero-title,
html[data-theme="light"] .question { color: #172033 !important; }
html[data-theme="light"] .hero-sub { color: #475569 !important; }
html[data-theme="light"] .small-muted { color: #475569 !important; }
html[data-theme="light"] .quad { background: #f1f5f9 !important; color: #172033 !important; border-color: #cbd5e1 !important; }
html[data-theme="light"] .quad-active { background: #fef3c7 !important; color: #78350f !important; border-color: #d97706 !important; }
html[data-theme="light"] [data-testid="stForm"],
html[data-theme="light"] [data-testid="stVerticalBlockBorderWrapper"] > div { border-color: #cbd5e1 !important; }
html[data-theme="light"] [data-testid="stWidgetLabel"],
html[data-theme="light"] [data-testid="stMarkdownContainer"],
html[data-theme="light"] label,
html[data-theme="light"] p,
html[data-theme="light"] h1,
html[data-theme="light"] h2,
html[data-theme="light"] h3,
html[data-theme="light"] h4 { color: #172033; }
/* 입력창은 Streamlit 테마의 기본·보조 배경과 글자색을 사용 */
.stApp input,
.stApp textarea,
.stApp [data-baseweb="select"] > div {
    background-color: var(--secondary-background-color, #151e2f) !important;
    color: var(--text-color, #f8fafc) !important;
    border-color: var(--border-color, #475569) !important;
}

/* 사이드바: 모든 글자와 보조 문구를 현재 테마의 글자색에 맞춤 */
[data-testid="stSidebar"],
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] [data-testid="stWidgetLabel"],
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] h4 {
    color: var(--text-color, #f8fafc) !important;
    opacity: 1 !important;
}
[data-testid="stSidebar"] [data-testid="stWidgetLabel"],
[data-testid="stSidebar"] label {
    font-size: 17px !important;
    font-weight: 600 !important;
}

/* 입력값과 placeholder(금액·월 금액·모르면 0 등): 라벨과 같은 테마 대비 적용 */
.stApp input,
.stApp textarea,
.stApp input::placeholder,
.stApp textarea::placeholder,
.stApp [data-baseweb="select"] [role="combobox"] {
    color: var(--text-color, #f8fafc) !important;
    opacity: 1 !important;
    font-size: 17px !important;
}
.stApp input::placeholder,
.stApp textarea::placeholder {
    -webkit-text-fill-color: var(--text-color, #f8fafc) !important;
}
html[data-theme="light"] [data-testid="stCaptionContainer"] { color: #475569 !important; }
html[data-theme="light"] .nav-link { color: #334155 !important; }
html[data-theme="light"] .nav-link-selected { background-color: #c2410c !important; color: #ffffff !important; }
@media (max-width: 700px) { .hero { padding: 26px 16px; } .hero-sub { font-size: 15px; } }
</style>
""", unsafe_allow_html=True)

# National Transfer Accounts benchmark values from the existing app.
LIFECYCLE_BENCHMARK = pd.DataFrame([
    {"age": 20, "labor_income": 45,  "consumption": 130}, 
    {"age": 25, "labor_income": 180, "consumption": 150},
    {"age": 28, "labor_income": 260, "consumption": 170}, # 흑자 진입 (골든크로스 약 27~28세)
    {"age": 35, "labor_income": 360, "consumption": 220},
    {"age": 43, "labor_income": 435, "consumption": 265}, # 소득 피크 정점 (42~44세)
    {"age": 50, "labor_income": 410, "consumption": 280},
    {"age": 55, "labor_income": 330, "consumption": 280},
    {"age": 60, "labor_income": 220, "consumption": 250}, # 적자 전환 (데드크로스 약 59세)
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

if "anonymous_id" not in st.session_state:
    st.session_state.anonymous_id = f"#{random.choice('ABCDE')}-{random.randint(101,999)}"
if "started" not in st.session_state:
    st.session_state.started = False
if "page" not in st.session_state:
    st.session_state.page = "가계부"
if "answers" not in st.session_state:
    st.session_state.answers = {}

# No invented example data: unanswered financial values remain blank and are treated as zero only for calculations.
def getv(key, default=0):
    value = st.session_state.get(key, default)
    return default if value is None else value

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
    # 은퇴 이후 예상 연금은 현재 소득·월 잔액에 포함하지 않습니다.
    # 은퇴 이후 자산 궤적 계산에서만 별도로 사용합니다.
    income = sum(float(getv(k, 0)) for k in ["income_self", "income_spouse", "income_other"])
    expenses = sum(float(getv(k, 0)) for k in ["expense_living", "expense_loan", "expense_other"])
    assets = sum(float(getv(k, 0)) for k in ["asset_cash", "asset_financial", "asset_home", "asset_deposit", "asset_other"])
    debts = sum(float(getv(k, 0)) for k in ["debt_home", "debt_other"])
    return {"income": income, "expenses": expenses, "surplus": income-expenses,
            "assets": assets, "debts": debts, "net_worth": assets-debts}

# Cover + centered start dialog. Embed the cover so deployment needs no extra image file.
cover_path = os.path.join(os.path.dirname(__file__), "나침반_표지_배경.png")
if os.path.exists(cover_path):
    with open(cover_path, "rb") as f:
        cover_b64 = base64.b64encode(f.read()).decode("ascii")
    cover_style = f"background-image:url(data:image/png;base64,{cover_b64});"
else:
    cover_style = "background:radial-gradient(circle at top,#38506c,#0f172a 70%);"
if not st.session_state.started:
    st.markdown(f"""
    <div class="cover-bg" style="{cover_style}">
      <div class="cover-shade"></div>
      <div class="cover-caption">
        <h1>나침반</h1>
        <div style="font-size:clamp(11px,1.2vw,14px);font-weight:600;">나를 돌아보고, 내일을 그리는 여정</div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    @st.dialog("나침반 산책을 시작합니다", width="small")
    def start_dialog():
        st.markdown("", unsafe_allow_html=True)
        with st.form("start_form", clear_on_submit=False):
            name = st.text_input("이름 또는 별칭", placeholder="이름이나 편한 별칭", key="start_person_name")
            age_text = st.text_input("나이", placeholder="나이 입력", key="start_person_age_text", max_chars=3)
            try:
                age = int(age_text) if age_text.strip() else None
                if age is not None and not 1 <= age <= 120:
                    age = None
            except ValueError:
                age = None
            submitted = st.form_submit_button("시작", use_container_width=True, type="primary")
        if submitted:
            if not name.strip() or age is None:
                st.warning("이름(또는 별칭)과 나이를 입력해 주세요.")
            else:
                st.session_state.person_name = name.strip()
                st.session_state.person_age = int(age)
                st.session_state.started = True
                st.rerun()
    start_dialog()
    st.stop()

# Sidebar: interviewee-facing compact profile, not an admin console.
with st.sidebar:
    st.markdown("### 🧭 나침반 기록")
    st.markdown(f"**이름/별칭:** {st.session_state.get('person_name','')}")
    st.markdown(f"**나이:** {st.session_state.get('person_age','')}세")
    code = active_quadrant(st.session_state.get("job_form", ""))
    st.markdown(f"**익숙한 소득 형태:** {code or '아직 미정'}")
    st.caption(f"익명 고유번호 {st.session_state.anonymous_id}")
    st.caption("입력 내용은 이 화면의 세션에서 사용됩니다.")

# 페이지 이동은 위젯 key에 직접 값을 쓰지 않고, 다음 rerun의 기본 선택으로 전달합니다.
_pending_nav = st.session_state.pop("_pending_nav", None)
nav_options = ["우리집\n가계부", "삶과\n생계수단", "인생의\n사계절", "AI\n시선"]
_nav_targets = {"우리집 가계부":nav_options[0], "삶과 생계수단":nav_options[1], "인생의 사계절":nav_options[2], "AI 시선":nav_options[3]}
if "active_navigation_key" not in st.session_state:
    st.session_state.active_navigation_key = "main_navigation"
if _pending_nav in _nav_targets:
    # Give the target page a fresh widget key so Streamlit never tries to mutate an instantiated widget.
    st.session_state.active_navigation_key = "main_navigation_" + str(list(_nav_targets.keys()).index(_pending_nav))
    st.session_state.active_navigation_default = _nav_targets[_pending_nav]
_nav_widget_key = st.session_state.active_navigation_key
_nav_default = st.session_state.get("active_navigation_default", nav_options[0])
_nav_index = nav_options.index(_nav_default) if _nav_default in nav_options else 0
selected = option_menu(
    menu_title=None,
    options=nav_options,
    icons=["", "", "", ""],
    menu_icon=None, default_index=_nav_index, orientation="horizontal", key=_nav_widget_key,
    styles={"container":{"padding":"8px 8px","background-color":"#0F172A","border":"1px solid #263449","border-radius":"12px","margin-top":"8px","margin-bottom":"24px","width":"100%"},
            "icon":{"display":"none"},
            "nav-link":{"font-size":"16px","white-space":"pre-line","line-height":"1.25","text-align":"center","margin":"3px 4px","padding":"10px 8px","color":"#CBD5E1","--hover-color":"#334155","border-radius":"9px","min-height":"64px"},
            "nav-link-selected":{"background-color":"#EA580C","color":"#FFFFFF","font-weight":"800","box-shadow":"0 3px 10px rgba(234,88,12,0.25)"}}
)

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
        return "", "Streamlit Secrets에서 GEMINI_API_KEY 또는 Gemini_API_KEY를 찾지 못했습니다. 여행 가계부 앱과 나침반 앱의 Secrets는 별도로 관리됩니다."
    last_error = ""
    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}],
        "generationConfig": {"maxOutputTokens": 8192, "temperature": 0.45},
    }
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
                text_parts = [part.get("text", "") for part in parts if part.get("text")]
                if text_parts:
                    return "".join(text_parts).strip(), ""
            else:
                last_error = f"[{model_name}] {response.status_code}: {response.text[:160]}"
        except Exception as exc:
            last_error = f"[{model_name}] 요청 오류: {exc}"
    return "", last_error or "Gemini 서버에서 응답을 받지 못했습니다."


# Page 1 — Household finances
selected_page = {"우리집\n가계부":"우리집 가계부", "삶과\n생계수단":"삶과 생계수단", "인생의\n사계절":"인생의 사계절", "AI\n시선":"AI 시선"}.get(selected, selected)
if selected_page == "우리집 가계부":
    st.markdown("## 우리집 가계부")
    with st.form("finance_form"):
        # 직업은 소득의 성격을 이해하기 위한 보조 정보로 먼저 배치합니다.
        st.markdown("#### 현재 상황")
        job_options = ["선택하세요", "직장인", "자영업", "전문직", "사업가", "투자자", "임대소득자", "그외"]
        previous_job = st.session_state.get("job_form", "선택하세요")
        job_index = job_options.index(previous_job) if previous_job in job_options else 0
        job = st.selectbox("나의 직업은?", job_options, index=job_index, key="job_form_input")

        # 현재의 현금흐름: 들어오는 돈과 나가는 돈을 나란히 배치합니다.
        income_col, expense_col = st.columns(2)
        with income_col:
            with st.container(border=True, key="income-panel"):
                st.markdown("#### ① 들어오는 돈")
                st.caption("현재 한 달 기준 · 만원")
                income_self = st.number_input("본인 월 실수령액", min_value=0, value=st.session_state.get("income_self"), step=10, placeholder="금액")
                income_spouse = st.number_input("배우자 월 실수령액", min_value=0, value=st.session_state.get("income_spouse"), step=10, placeholder="금액")
                income_other = st.number_input("기타·자산 소득", min_value=0, value=st.session_state.get("income_other"), step=10, placeholder="금액", help="임대료, 이자, 배당 등 현재 들어오는 기타 소득입니다.")
        with expense_col:
            with st.container(border=True, key="expense-panel"):
                st.markdown("#### ② 나가는 돈")
                st.caption("현재 한 달 기준 · 만원")
                expense_living = st.number_input("기본 생활비", min_value=0, value=st.session_state.get("expense_living"), step=10, placeholder="월 금액", help="식비, 공과금, 통신비처럼 매달 기본적으로 드는 비용입니다.")
                expense_loan = st.number_input("대출 원리금 상환액", min_value=0, value=st.session_state.get("expense_loan"), step=10, placeholder="금액", help="대출 원금과 이자를 합쳐 매달 갚는 금액입니다.")
                expense_other = st.number_input("그 밖의 월평균 지출", min_value=0, value=st.session_state.get("expense_other"), step=10, placeholder="금액", help="보험료, 교육비, 의료비, 자동차 유지비, 경조사비 등 기본 생활비 외 지출을 포함합니다.")

        # 현재 보유 상태: 자산과 부채를 한 쌍으로 배치합니다.
        asset_col, debt_col = st.columns(2)
        with asset_col:
            with st.container(border=True, key="asset-panel"):
                st.markdown("#### ③ 가지고 있는 것")
                st.caption("현재 보유 금액·시세 기준 · 만원")
                asset_cash = st.number_input("현금·예적금", min_value=0, value=st.session_state.get("asset_cash"), step=100, placeholder="금액")
                asset_financial = st.number_input("주식·채권 등 금융자산", min_value=0, value=st.session_state.get("asset_financial"), step=100, placeholder="금액")
                asset_home = st.number_input("부동산 시세", min_value=0, value=st.session_state.get("asset_home"), step=100, placeholder="금액", help="현재 집이나 보유 부동산의 대략적인 시세입니다.")
                asset_deposit = st.number_input("전세보증금", min_value=0, value=st.session_state.get("asset_deposit"), step=100, placeholder="금액", help="현재 돌려받을 수 있는 전세보증금입니다. 전세대출은 부채에 따로 입력하세요.")
                asset_other = st.number_input("기타 자산·사업 가치", min_value=0, value=st.session_state.get("asset_other"), step=100, placeholder="금액", help="위 항목에 포함되지 않는 자산입니다. 현금화하기 어려운 자산은 참고용으로 입력하세요.")
        with debt_col:
            with st.container(border=True, key="debt-panel"):
                st.markdown("#### ④ 갚아야 할 돈")
                st.caption("현재 남은 대출 원금 기준 · 만원")
                debt_home = st.number_input("주택담보·전세대출 잔액", min_value=0, value=st.session_state.get("debt_home"), step=100, placeholder="금액", help="주택담보대출과 전세대출의 현재 남은 원금입니다.")
                debt_other = st.number_input("그 밖의 부채 잔액", min_value=0, value=st.session_state.get("debt_other"), step=100, placeholder="금액", help="신용대출, 자동차 할부, 학자금대출, 카드론 등 남은 금액입니다.")

        # 미래 가정은 현재의 수입·지출과 섞이지 않도록 별도 영역으로 분리합니다.
        with st.container(border=True, key="retirement-panel"):
            st.markdown("#### 은퇴 후에는?")
            pension_col, retirement_expense_col = st.columns(2)
            with pension_col:
                income_pension = st.number_input(
                    "은퇴 후 받을 월 연금", min_value=0,
                    value=st.session_state.get("income_pension"), step=10,
                    placeholder="모르면 0",
                    help="국민연금·퇴직연금·개인연금 등 은퇴 후 받을 것으로 예상하는 월 금액입니다. 현재 월수입에는 포함되지 않습니다.",
                )
            with retirement_expense_col:
                retirement_monthly_expenses = st.number_input(
                    "은퇴 후 한 달 생활비", min_value=0,
                    value=int(st.session_state.get("retirement_monthly_expenses", 200) or 0),
                    step=10,
                    help="은퇴 후 식비·주거비·공과금·의료비 등 한 달에 쓸 돈입니다. 현재 지출과 별도로 입력하세요.",
                )
            st.caption("적정 노후생활비(월): 1인 197.6만 원, 부부 298.1만 원 (국민연금연구원 2024년 조사). 가구원 수와 주거·의료비에 맞게 조정하세요.")

        save_finance = st.form_submit_button("입력 내용 반영", use_container_width=True, type="primary")
    st.caption("참고 통계: 국민연금공단의 2025년 12월 기준 안내에서 가입기간 20년 이상 노령연금 수급자의 평균은 월 약 113만 원입니다. 부부 합산 평균은 약 120만 원으로 보도된 바 있습니다. 개인별 가입기간·소득에 따라 차이가 크므로, 실제 예상액은 공단의 ‘내 연금 알아보기’에서 확인하세요.")
    link1, link2 = st.columns(2)
    link1.link_button("국민연금공단 급여지급 통계", "https://www.nps.or.kr/pnsinfo/statistics/getOHAF0119M0.do", use_container_width=True)
    link2.link_button("내 연금 알아보기 안내", "https://www.nps.or.kr/pnsinfo/ntpsklg/getOHAF0095M0.do", use_container_width=True)
    if save_finance:
        # Never index locals() by a different session key: this was the KeyError source.
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
        for key, value in submitted_values.items():
            st.session_state[key] = value
        # 입력 반영 사실을 알리고 선택된 ESBI 영역으로 화면을 이동합니다.
        st.session_state["finance_saved_notice"] = True

    q = active_quadrant(st.session_state.get("job_form", ""))
    st.markdown("#### ESBI")
    st.markdown("<div id='selected-esbi'></div>", unsafe_allow_html=True)
    if st.session_state.pop("finance_saved_notice", False):
        st.success("입력 내용이 반영되었습니다.")
        st.components.v1.html("<script>try { window.parent.document.getElementById('selected-esbi').scrollIntoView({behavior:'smooth',block:'center'}); } catch(e) {}</script>", height=0)
    cols = st.columns(4)
    for col, code in zip(cols, ["E","S","B","I"]):
        title, desc = ESBI[code]
        css = "quad-active" if q == code else "quad"
        col.markdown(f"<div class='{css}'><b style='font-size:21px'>{code}</b><br><b>{title}</b><br><span class='small-muted'>{desc}</span></div>", unsafe_allow_html=True)
    st.caption("이 표시는 직업이나 소득 형태를 단순히 바라보는 참고 지도이며, 사람의 성격이나 삶의 가치를 분류하지 않습니다.")

    s = current_financial_summary()
    st.markdown("#### 현재 입력값 요약")
    cols = st.columns(4)
    cols[0].metric("월수입 합계", money(s["income"]))
    cols[1].metric("월지출 합계", money(s["expenses"]))
    cols[2].metric("월 잔액", money(s["surplus"]))
    cols[3].metric("순자산", fmt_eok(s["net_worth"]))
    st.markdown("#### 미래 자산·연금 궤적")
    cur_age = int(st.session_state.person_age)
    retirement_value = st.session_state.get("retirement_age")
    # 은퇴 나이를 아직 입력하지 않은 경우에는 65세를 임시 가정하고, 실제 입력값이 있으면 우선 적용합니다.
    retire_age = int(retirement_value) if retirement_value is not None else 65
    retire_age = max(cur_age, min(retire_age, 100))
    annual_savings = s["surplus"] * 12
    years = sorted(set([cur_age, 80, retire_age] + list(range(((cur_age // 5) + 1) * 5, 81, 5))))
    vals = []
    # 은퇴 후 지출은 현재 지출을 자동 대입하지 않고, 별도 입력한 가정을 사용합니다.
    # 기존 사용자 데이터에 해당 항목이 없으면 개인 기준 참고값 200만원을 적용합니다.
    retirement_monthly_expenses = float(getv("retirement_monthly_expenses", 200) or 0)
    retirement_monthly_pension = float(getv("income_pension", 0) or 0)
    # 은퇴 전에는 현재 월 잔액을 누적하고, 은퇴 후에는 연금에서 은퇴 후 월지출을 뺀 만큼 자산이 변합니다.
    for age in years:
        working_years = max(0, min(age, retire_age) - cur_age)
        projected = s["net_worth"] + annual_savings * working_years
        if age > retire_age:
            retirement_annual_cashflow = (retirement_monthly_pension - retirement_monthly_expenses) * 12
            projected += retirement_annual_cashflow * (age - retire_age)
        vals.append(projected)
    fig = go.Figure(go.Scatter(x=years,y=vals,mode="lines+markers",line=dict(color="#f59e0b",width=3),name="단순 가정에 따른 순자산"))
    fig.add_vline(x=retire_age, line_dash="dash", line_color="#38bdf8",
                  annotation_text=f"은퇴 가정 {retire_age}세",
                  annotation_position="top")
    fig.update_layout(height=360,margin=dict(l=18,r=18,t=28,b=42),paper_bgcolor="#0b1120",plot_bgcolor="#0b1120",font_color="#e2e8f0",xaxis_title="나이",yaxis_title="순자산 (만원)",autosize=True)
    st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False,"scrollZoom":False,"doubleClick":False,"staticPlot":True})
    st.caption(
        ("은퇴 나이를 아직 입력하지 않아 65세를 임시 가정했습니다. 삶과 생계수단 탭에서 입력한 은퇴 나이가 있으면 그 값이 적용됩니다. " if retirement_value is None else "입력한 은퇴 나이를 적용했습니다. ")
        + f"은퇴 전에는 현재 월 잔액을 누적하고, 은퇴 후에는 예상 월 연금 {retirement_monthly_pension:,.0f}만 원에서 별도 입력한 은퇴 후 월 생활비 {retirement_monthly_expenses:,.0f}만 원을 뺀 금액만큼 자산이 변하는 단순 개념도입니다. "
        + "은퇴 후 생활비 기본값 200만 원은 국민연금연구원의 개인 기준 적정 노후생활비 조사 결과를 참고한 가정이며, 가구 상황에 맞게 조정해야 합니다. 물가·수익률·세금·은퇴 후 지출 변화는 반영하지 않으며, 예측이나 보장이 아닙니다."
    )

    _, next_col = st.columns([5,1])
    with next_col:
        if st.button("다음 →", key="finance_next", use_container_width=True, type="primary"):
            st.session_state["_pending_nav"] = "삶과 생계수단"
            st.rerun()

# Page 2 — livelihood choice and small/large bucket/pipeline illustration
elif selected_page == "삶과\n생계수단" or selected_page == "삶과 생계수단":
    st.markdown("## 삶과 생계수단")
    st.markdown("<div class='soft-card'><div class='eyebrow'>잠시 생각해 볼 질문</div><div class='question'>내가 생계를 유지해 온 방식은 나의 선택이었나? 주어진 상황에서 받아들인 것인가?</div></div>", unsafe_allow_html=True)
    st.text_area("떠오르는 생각이 있다면 적어두세요 (선택)", key="life_choice_note", height=90, placeholder="답을 정할 필요는 없습니다.")
    st.markdown("### 소득이 만들어지는 세 가지 모습")

    cols = st.columns(3)
    cols[0].markdown("<div class='soft-card income-card'><div style='font-size:38px'>🪣</div><b>작은 물통</b><p class='small-muted'>직접 일한 시간과 소득이 가까이 연결되는 모습</p></div>",unsafe_allow_html=True)
    cols[1].markdown("<div class='soft-card income-card'><div style='font-size:38px'>🛢️</div><b>큰 물통</b><p class='small-muted'>전문성·규모가 커져 한 번에 담는 양이 늘어나는 모습</p></div>",unsafe_allow_html=True)
    cols[2].markdown("<div class='soft-card income-card'><div style='font-size:38px'>🚰</div><b>파이프라인</b><p class='small-muted'>시스템·자산에서 소득 흐름이 생기는 모습</p></div>",unsafe_allow_html=True)
    st.markdown("### 은퇴 예상 나이 (지금 하는 일을 그만두는 나이)")
    with st.form("retirement_form"):
        retirement_input = st.number_input(
            "은퇴 예상 나이 (지금 하는 일을 그만두는 나이)",
            min_value=int(st.session_state.person_age), max_value=100,
            value=int(st.session_state["retirement_age"]) if st.session_state.get("retirement_age") is not None else int(st.session_state.person_age),
            step=1, key="retirement_age_input",
        )
        retirement_saved = st.form_submit_button("확인", use_container_width=True)
    if retirement_saved:
        st.session_state["retirement_age"] = int(retirement_input)
        st.success("은퇴 예상 나이가 반영되었습니다.")

    _, next_col = st.columns([5,1])
    with next_col:
        if st.button("다음 →", key="livelihood_next", use_container_width=True, type="primary"):
            # Submit the value already held by the widget before navigating.
            st.session_state["retirement_age"] = int(st.session_state.get("retirement_age_input", retirement_input))
            st.session_state["_pending_nav"] = "인생의 사계절"
            st.session_state["_scroll_to_top_once"] = True
            st.rerun()

# Page 3 — seasons, family ages, illustrative lifecycle curve, official statistics
elif selected_page == "인생의\n사계절" or selected_page == "인생의 사계절":
    if st.session_state.pop("_scroll_to_top_once", False):
        st.components.v1.html(
            "<script>try { window.parent.scrollTo({top: 0, behavior: 'instant'}); } catch(e) { try { window.parent.document.documentElement.scrollTop = 0; } catch(e2) {} }</script>",
            height=0,
        )
    st.markdown("## 인생의 사계절")
    st.markdown("자연에 사계절이 있듯, 삶에도 준비·성장·비축·음미의 시간이 있습니다. 계절마다 의미는 다르고, 누구에게나 같은 모습으로 오지는 않습니다.")
    age = int(st.session_state.person_age)
    retirement_value = st.session_state.get("retirement_age")
    retirement = int(retirement_value) if retirement_value is not None else age
    years_left = max(0, retirement-age)
    st.markdown("### 1. 가족 구성원과 나이")
    child_options = ["입력 안 함","없음","1명","2명","3명 이상"]
    child_count = st.selectbox(
        "자녀 수", child_options,
        index=child_options.index(st.session_state.get("child_count","입력 안 함"))
        if st.session_state.get("child_count","입력 안 함") in child_options else 0,
        key="child_count_live",
    )
    with st.form("family_form"):
        spouse_age = st.number_input("배우자 나이 (없거나 입력하지 않으려면 0)", min_value=0,max_value=120,value=int(st.session_state.get("spouse_age",0)),step=1)
        child_age = int(st.session_state.get("child_age",0)) if child_count in ["1명", "2명", "3명 이상"] else 0
        child_age2 = int(st.session_state.get("child_age2",0)) if child_count in ["2명", "3명 이상"] else 0
        child_age3 = int(st.session_state.get("child_age3",0)) if child_count == "3명 이상" else 0
        if child_count in ["1명", "2명", "3명 이상"]:
            child_age = st.number_input("첫째 자녀 나이 (선택)",min_value=0,max_value=100,value=child_age,step=1)
        if child_count in ["2명", "3명 이상"]:
            child_age2 = st.number_input("둘째 자녀 나이 (선택)",min_value=0,max_value=100,value=child_age2,step=1)
        if child_count == "3명 이상":
            child_age3 = st.number_input("셋째 자녀 나이 (선택)",min_value=0,max_value=100,value=child_age3,step=1)
        col_father, col_mother = st.columns(2)
        with col_father:
            father_age = st.number_input("아버지 나이 (선택, 모르면 0)", min_value=0, max_value=120, value=int(st.session_state.get("father_age", 0)), step=1)
        with col_mother:
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
            "형제자매 (해당 항목 모두 선택, 없거나 입력하지 않으려면 비워 두세요)",
            sibling_options,
            default=[x for x in st.session_state.get("siblings", []) if x in sibling_options],
            help="본인을 기준으로 선택하세요. 예: 남성은 형·남동생·누나·여동생, 여성은 오빠·남동생·언니·여동생 등. 관계 명칭이 맞지 않으면 관계 미지정 항목을 선택할 수 있습니다.",
        )
        save_family = st.form_submit_button("가족 정보 반영",use_container_width=True)
    if save_family:
        st.session_state.spouse_age=spouse_age; st.session_state.child_count=child_count
        st.session_state.child_age=child_age; st.session_state.child_age2=child_age2; st.session_state.child_age3=child_age3
        st.session_state.father_age=father_age; st.session_state.mother_age=mother_age
        st.session_state.siblings=siblings
        st.session_state.marriage_plan=marriage_plan
        st.session_state.child_plan=child_plan
        st.session_state.housing_plan=housing_plan
        st.rerun()

    people = [(st.session_state.get("person_name","나"),age)]
    if getv("spouse_age",0)>0: people.append(("배우자",int(getv("spouse_age"))))
    if getv("child_age",0)>0: people.append(("첫째 자녀",int(getv("child_age"))))
    if getv("child_age2",0)>0: people.append(("둘째 자녀",int(getv("child_age2"))))
    if getv("child_age3",0)>0: people.append(("셋째 자녀",int(getv("child_age3"))))
    if getv("father_age",0)>0: people.append(("아버지",int(getv("father_age"))))
    if getv("mother_age",0)>0: people.append(("어머니",int(getv("mother_age"))))
    for name, current in people:
        future = current + years_left
        st.markdown(f"<div class='soft-card' style='display:flex;align-items:center;gap:14px;flex-wrap:wrap'><b style='min-width:75px'>{name}</b><span style='font-size:22px;font-weight:800'>{current}세</span><span style='font-size:23px;color:#f59e0b;padding:0 12px'>⟶</span><span style='font-size:22px;font-weight:800;color:#fde68a'>{future}세</span><span class='small-muted'>은퇴 예정 시점</span></div>",unsafe_allow_html=True)
    st.markdown("### 2. 인생의 수입·지출 곡선 (일반적인 예시)")
    st.caption("국민이전계정의 연령별 흐름을 이해하기 위한 개념적 예시입니다. 개인의 실제 소득·지출 곡선과는 다릅니다.")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=LIFECYCLE_BENCHMARK["age"],y=LIFECYCLE_BENCHMARK["labor_income"],mode="lines+markers",name="노동소득",line=dict(color="#38bdf8",width=3),hovertemplate="나이 %{x}세<br>노동소득 지수 %{y}<extra></extra>"))
    fig.add_trace(go.Scatter(x=LIFECYCLE_BENCHMARK["age"],y=LIFECYCLE_BENCHMARK["consumption"],mode="lines+markers",name="소비",line=dict(color="#f59e0b",width=3),hovertemplate="나이 %{x}세<br>소비 지수 %{y}<extra></extra>"))
    fig.add_vline(x=age,line_dash="dash",line_color="#f472b6",line_width=3,annotation_text=f"현재 {age}세",annotation_position="top")
    fig.update_layout(height=370,margin=dict(l=10,r=10,t=35,b=10),paper_bgcolor="#0b1120",plot_bgcolor="#0b1120",font_color="#e2e8f0",xaxis_title="나이",yaxis_title="상대적 크기 (개념도)",legend=dict(orientation="h",y=1.12,x=1,xanchor="right",yanchor="bottom"))
    st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False,"scrollZoom":False,"doubleClick":False,"staticPlot":True})
    st.markdown("### 2024년 국가데이터처 통계")
    st.markdown("2024년 국민이전계정은 연령별 소비와 노동소득의 차이를 보여줍니다. 개인의 실제 가계부나 은퇴 시점과 구분해 읽어야 합니다.")
    cols=st.columns(3)
    cols[0].metric("흑자 전환", "28세")
    cols[1].metric("최대 흑자", "45세")
    cols[1].caption("1인당 연간 1,932만 원")
    cols[2].metric("적자 재전환", "61세")
    st.caption("공식 통계의 요약 수치이며, 평균적 흐름이지 개인의 운명이나 목표가 아닙니다.")
    st.link_button("📄 2024년 국가데이터처 통계",OFFICIAL_PDF_URL,use_container_width=True)
    st.link_button("🌐 국가데이터처 공식 발표 페이지",OFFICIAL_RELEASE_URL,use_container_width=True)
    st.caption(f"은퇴 예정 나이 {retirement}세 이후의 겨울: {max(0,88-retirement)}년 (기대수명 88세를 가정한 단순 계산)")
    _, next_col = st.columns([5,1])
    with next_col:
        if st.button("다음 →", key="seasons_next", use_container_width=True, type="primary"):
            st.session_state["_pending_nav"] = "AI 시선"
            st.rerun()

# Page 4 — AI perspective. Sends all currently entered answers, but only after explicit click.
else:
    st.markdown("## AI 시선")
    st.markdown("AI는 판정자가 아니라, 입력한 내용을 다른 각도에서 바라보는 참고 관점입니다.")
    model = st.radio(
        "분석할 AI 선택",
        ["Gemini", "ChatGPT (준비 중)", "Claude (준비 중)"],
        index=0,
        key="ai_provider",
        horizontal=True,
    )
    if model == "Gemini":
        st.caption("현재 사용 가능: Gemini")
    else:
        st.info(f"{model}은 연결 준비 중입니다. 현재는 Gemini만 사용할 수 있습니다.")
    if st.button("분석", type="primary", use_container_width=True, disabled=(model != "Gemini")):
        summary = current_financial_summary()
        details = {
            "나이": st.session_state.get("person_age"),
            "소득 형태": st.session_state.get("job_form", ""),
            "월수입 항목": {k:getv(k,0) for k in ["income_self","income_spouse","income_other","income_pension"]},
            "월지출 항목": {k:getv(k,0) for k in ["expense_living","expense_loan","expense_other"]},
            "자산 항목": {k:getv(k,0) for k in ["asset_cash","asset_financial","asset_home","asset_deposit","asset_other"]},
            "부채 항목": {k:getv(k,0) for k in ["debt_home","debt_other"]},
            "삶과 시간 메모": st.session_state.get("life_choice_note", ""),
            "은퇴 예정 나이": st.session_state.get("retirement_age"),
            "가족 나이": {k:getv(k,0) for k in ["spouse_age","child_age","child_age2","child_age3","father_age","mother_age"]},
            "형제자매": st.session_state.get("siblings", []),
            "결혼 계획": st.session_state.get("marriage_plan", "미정"),
            "출산·자녀 계획": st.session_state.get("child_plan", "미정"),
            "주거 계획": st.session_state.get("housing_plan", "미정"),
        }
        st.session_state.ai_summary = summary
        st.session_state.ai_details = details
        st.session_state.ai_comment = None
        try:
            prompt = (
                "역할: 한국의 가계 재무와 은퇴 준비를 함께 검토하는 현실적이고 친근한 성찰 파트너입니다. 투자상품을 권유하지 말고, 근거 없이 낙관하거나 비관하지 마세요.\n\n"
                "참고할 공식 통계: 국가데이터처의 2024년 국민이전계정에 따르면, 한국의 1인당 평균 생애주기에서 노동소득이 소비를 넘어서는 흑자 전환 연령은 28세, 생애주기흑자가 가장 큰 연령은 45세(연간 1,932만 원), 소비가 노동소득을 다시 넘어서는 적자 재전환 연령은 61세입니다. 이는 연령별 평균 노동소득과 소비의 차이를 나타내는 통계이며, 개인의 순자산·저축액·은퇴 준비 수준을 직접 측정하거나 예측하는 지표가 아닙니다.\n"
                "이 통계는 한국 사회의 일반적인 생애주기 맥락을 설명할 때만 사용하세요. 개인을 평균보다 낫거나 못하다고 판정하거나, 이 연령을 개인의 은퇴 기준으로 사용하지 마세요. 개인 평가는 입력된 재무정보를 별도로 살펴보고, 통계와 개인 정보를 혼동하지 마세요.\n\n"
                "아래 두 코멘트만 한국어로 작성하세요. 전체 250~350자 정도, 쉬운 대화체로 쓰고 재무제표 숫자를 길게 되풀이하지 마세요.\n"
                "출력 형식은 반드시 아래와 같이 정확히 지키세요. 제목은 각각 [은퇴 안정성], [소득 개선 방향]을 그대로 사용하고, 각 제목은 한 번씩만 출력하세요. 두 항목 사이에는 빈 줄을 한 줄 넣으세요. 제목을 중복하거나 Markdown 제목(####), 굵게 표시(**)를 추가하지 마세요.\n\n"
                "[은퇴 안정성]\n"
                "첫 문장은 '은퇴 안정성: 유리한 편 / 판단 보류 / 불리한 편' 중 가장 적합한 하나를 골라 시작하세요. 현재 저축 여력뿐 아니라 순자산, 실제로 쓸 수 있는 자산, 부채, 은퇴까지 남은 기간을 함께 보세요. 결혼·출산·주거 계획이 입력되어 있다면 예상되는 비용 변화와 현재 자산의 여유를 함께 고려하세요. 계획이 '미정'이거나 정보가 부족하면 미래 비용을 사실처럼 가정하지 말고, 현재 숫자만으로 지나치게 낙관하지 마세요. 공식 비교 통계가 입력되지 않았다면 평균보다 낫다거나 못하다고 주장하지 마세요.\n\n"
                "[소득 개선 방향]\n"
                "투잡 추가와 본업 유지 후 사업·투자 준비 중 현재 상황에 더 맞는 방향을 짧게 제시하세요. 결혼·출산·주거 계획이 있거나 불확실하다면, 무리한 확장이나 위험투자보다 현금 여력과 본업 안정성을 우선 고려할 수 있습니다. 단, 사용자의 계획·선호를 임의로 단정하지 말고 근거가 부족하면 결론을 유보하세요.\n\n"
                "가족 구성원 정보는 실제 부양·지원 여부가 입력되지 않았다면 지출이나 책임으로 가정하지 마세요. '현재 재무 모습 요약', '다음 단계', '성찰 질문'은 쓰지 마세요. 금액 단위는 만원으로 유지하세요.\n\n입력 데이터:\n"
                + json.dumps(details, ensure_ascii=False)
            )
            comment, error = call_gemini_text(prompt)
            st.session_state.ai_comment = comment if comment else error
        except Exception as exc:
            st.session_state.ai_comment = f"Gemini 분석 요청을 완료하지 못했습니다. API 키, 모델 사용 권한 및 사용 한도를 확인해 주세요. ({exc})"
    if st.session_state.get("ai_summary"):
        s=st.session_state.ai_summary
        st.markdown("### 재무제표 요약")
        cols=st.columns(4)
        cols[0].metric("월수입 합계",money(s["income"]))
        cols[1].metric("월지출 합계",money(s["expenses"]))
        cols[2].metric("월 잔액",money(s["surplus"]))
        cols[3].metric("순자산",fmt_eok(s["net_worth"]))
        st.markdown("### AI 코멘트")
        comment_text = str(st.session_state.get("ai_comment", ""))
        # Be tolerant of Gemini formatting variations: [heading], Markdown heading,
        # bold heading, or plain-text heading. Split at the first income heading.
        import re
        normalized = comment_text.replace("\r\n", "\n").replace("\r", "\n")
        income_heading = re.compile(
            r"(?im)^\s*(?:#{1,6}\s*)?(?:\*\*|__)?\s*(?:\[\s*)?소득\s*개선\s*방향\s*(?:\])?\s*(?:\*\*|__)?\s*:?\s*$"
        )
        match = income_heading.search(normalized)
        if match:
            retirement_comment = normalized[:match.start()]
            income_comment = normalized[match.end():]
        else:
            # Also handle inline heading forms such as "**소득 개선 방향** 내용".
            inline_match = re.search(
                r"(?i)(?:\[\s*소득\s*개선\s*방향\s*\]|(?:\*\*|__)\s*소득\s*개선\s*방향\s*(?:\*\*|__)|소득\s*개선\s*방향\s*:)",
                normalized,
            )
            if inline_match:
                retirement_comment = normalized[:inline_match.start()]
                income_comment = normalized[inline_match.end():]
            else:
                retirement_comment, income_comment = normalized, ""
        retirement_comment = re.sub(r"(?im)^\s*(?:#{1,6}\s*)?(?:\[\s*)?은퇴\s*안정성\s*(?:\])?\s*:?\s*$", "", retirement_comment)
        # Remove accidental duplicate inline heading from the retirement section.
        retirement_comment = re.sub(r"(?i)(?:\*\*|__)\s*소득\s*개선\s*방향\s*(?:\*\*|__)\s*", "", retirement_comment)
        retirement_comment = re.sub(r"(?i)\[\s*은퇴\s*안정성\s*\]", "", retirement_comment).strip()
        # The card already displays this heading, so remove a repeated label at the start of the AI text.
        retirement_comment = re.sub(r"(?i)^\s*(?:\*\*|__)?\s*은퇴\s*안정성\s*(?:\*\*|__)?\s*[:：]\s*", "", retirement_comment).strip()
        income_comment = re.sub(r"(?i)\[\s*소득\s*개선\s*방향\s*\]", "", income_comment).strip()
        income_comment = re.sub(r"(?i)^\s*(?:\*\*|__)?\s*소득\s*개선\s*방향\s*(?:\*\*|__)?\s*[:：]\s*", "", income_comment).strip()
        # Keep the two cards readable even if Gemini emits extra blank lines.
        retirement_comment = re.sub(r"\n{3,}", "\n\n", retirement_comment)
        income_comment = re.sub(r"\n{3,}", "\n\n", income_comment)
        st.markdown("#### 은퇴 안정성")
        st.markdown(f"<div class='soft-card'>{retirement_comment}</div>", unsafe_allow_html=True)
        st.markdown("#### 소득 개선 방향")
        st.markdown(f"<div class='soft-card'>{income_comment or '두 번째 코멘트를 찾지 못했습니다. 다시 분석해 주세요.'}</div>", unsafe_allow_html=True)
        st.caption("입력한 값과 AI 코멘트는 참고 자료입니다. 삶의 해석과 결정은 인터뷰이의 몫입니다.")
    else:
        st.info("‘분석’을 누르면 입력 내용의 재무제표 요약을 먼저 보여주고, 설정이 되어 있는 경우 AI 코멘트를 덧붙입니다.")
