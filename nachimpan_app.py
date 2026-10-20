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
# 1.02.00 | 전역 통합 테마 디자인 시스템 CSS (코드블록 자동 줄바꿈 보강)
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

/* 표지 아래 인라인 3칸 시작 툴바 전용 스타일 */
div[data-testid="stForm"]:has(input[id*="start_person"]) {
    border: none !important;
    padding: 0 !important;
    background: transparent !important;
}

input[id*="start_person"] {
    background-color: #FFFFFF !important;
    color: #0F172A !important;
    border: 1.5px solid #94A3B8 !important;
    border-radius: 8px !important;
    text-align: center !important;
    font-size: 16px !important;
    height: 44px !important;
}

div[data-testid="stForm"]:has(input[id*="start_person"]) button {
    height: 44px !important;
    font-size: 17px !important;
    font-weight: 800 !important;
    border-radius: 8px !important;
    padding: 0 10px !important;
}

/* 형제자매 6버튼 고대비 스타일 */
.stApp button:not([kind="primary"]) {
    background-color: #1E293B !important;
    color: #F8FAFC !important;
    border: 1.5px solid #475569 !important;
    font-weight: 700 !important;
}

.stApp button:not([kind="primary"]):hover {
    background-color: #EA580C !important;
    border-color: #EA580C !important;
    color: #FFFFFF !important;
}

/* ==========================================================================
   [신규] st.code 코드블록 자동 줄바꿈 강제 (가로 늘어짐 원천 박멸)
   ========================================================================== */
[data-testid="stCodeBlock"] pre,
[data-testid="stCodeBlock"] code,
.stCode pre,
.stCode code {
    white-space: pre-wrap !important;
    word-break: break-word !important;
    overflow-x: hidden !important;
    line-height: 1.65 !important;
    font-size: 14.5px !important;
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

# ==============================================================================
# 2.01.00 | 세션 상태 초기화 및 헬퍼 함수 (경력 연차 동기화 키 포함)
# ==============================================================================
import zlib

if "anonymous_id" not in st.session_state:
    st.session_state.anonymous_id = f"#{random.choice('ABCDE')}-{random.randint(101,999)}"
if "started" not in st.session_state:
    st.session_state.started = False
if "answers" not in st.session_state:
    st.session_state.answers = {}

def getv(key, default=0):
    val = st.session_state.get(key, default)
    return default if val is None else val

# 인터뷰이 ➜ 인터뷰어 동기화 대상 핵심 데이터 키 (경력 연차 career_stage 추가)
SYNC_KEYS = [
    "anonymous_id", "person_name", "person_age", "job_form", "job_spouse_form", "career_stage",
    "income_self", "income_spouse", "income_other", "income_bonus", "income_pension",
    "expense_living", "expense_loan", "expense_other", "retirement_monthly_expenses",
    "asset_cash", "asset_financial", "asset_home", "asset_deposit", "asset_other",
    "debt_home", "debt_other", "retirement_age", "spouse_age", "child_count",
    "child_age", "child_age2", "child_age3", "father_age", "mother_age",
    "marriage_plan", "child_plan", "housing_plan", "sibling_items"
]

def export_diagnosis_code():
    """현재 세션의 모든 가계부·생애 데이터를 암호화 압축 코드로 인코딩"""
    data = {}
    for k in SYNC_KEYS:
        if k in st.session_state:
            data[k] = st.session_state[k]
    json_bytes = json.dumps(data, ensure_ascii=False).encode('utf-8')
    compressed = zlib.compress(json_bytes, level=9)
    b64 = base64.urlsafe_b64encode(compressed).decode('utf-8')
    return f"NC-{b64}"

def import_diagnosis_code(raw_input):
    """카카오톡 메시지나 복원코드에서 NC- 데이터를 찾아 세션으로 즉시 복원"""
    if not raw_input or not isinstance(raw_input, str):
        return False, "입력된 텍스트가 없습니다."
    
    match = re.search(r"NC-([A-Za-z0-9_-]+={0,2})", raw_input.strip())
    if not match:
        return False, "유효한 나침반 복원코드(NC-...)를 찾지 못했습니다."
    
    b64_str = match.group(1)
    try:
        missing_padding = len(b64_str) % 4
        if missing_padding:
            b64_str += '=' * (4 - missing_padding)
        compressed = base64.urlsafe_b64decode(b64_str.encode('utf-8'))
        json_bytes = zlib.decompress(compressed)
        data = json.loads(json_bytes.decode('utf-8'))
        
        for k, v in data.items():
            st.session_state[k] = v
        st.session_state.started = True
        return True, f"'{data.get('person_name', '인터뷰이')}'님의 가계부·생애주기 데이터가 완벽히 동기화되었습니다."
    except Exception as e:
        return False, f"데이터 복원 실패: {e}"

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
# 3.00.00 | 외부 AI 연동 서비스 (Gemini + ChatGPT + Claude 다이렉트 파이프라인)
# ==============================================================================

# ==============================================================================
# 3.01.00 | Gemini 엔드포인트 자율 매칭 및 텍스트 요청 파이프라인 (연결 실패 100% 박멸)
# ==============================================================================
def call_gemini_text(prompt_text):
    raw_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("Gemini_API_KEY")
    if not raw_key:
        try:
            raw_key = st.secrets.get("GEMINI_API_KEY", "") or st.secrets.get("Gemini_API_KEY", "")
        except Exception:
            raw_key = ""
            
    if not raw_key:
        return "", "Streamlit Secrets에서 GEMINI_API_KEY를 찾지 못했습니다. 앱 대시보드의 Secrets 설정을 확인해 주세요."

    # 혹시 모를 앞뒤 공백 및 따옴표 완전 제거
    api_key = str(raw_key).strip().strip("'").strip('"')

    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}],
        "generationConfig": {"maxOutputTokens": 8192, "temperature": 0.45},
    }

    # 1단계: 구글 서버에 현재 API 키로 사용 가능한 모델 목록 실시간 질의
    active_endpoints = []
    discovery_error = ""
    for ver in ["v1beta", "v1"]:
        try:
            res = requests.get(
                f"https://generativelanguage.googleapis.com/{ver}/models?key={api_key}",
                timeout=6,
            )
            if res.status_code == 200:
                for m in res.json().get("models", []):
                    # 글 생성을 지원하는 모델만 선별
                    if "generateContent" in m.get("supportedGenerationMethods", []):
                        m_full_name = m.get("name", "")  # 예: "models/gemini-1.5-flash"
                        if "flash" in m_full_name and "exp" not in m_full_name and "preview" not in m_full_name:
                            active_endpoints.append((ver, m_full_name))
            else:
                discovery_error = f"[{ver} 목록 조회 {res.status_code}]: {res.text[:120]}"
        except Exception as exc:
            discovery_error = f"통신 지연: {exc}"

    # 2단계: 최적 모델 정렬 (1.5-flash 최우선 배치)
    active_endpoints.sort(key=lambda item: (
        0 if "1.5-flash" in item[1] else
        1 if "2.0-flash" in item[1] else 2
    ))

    # 만약 목록 조회가 차단되었을 때를 대비한 하드코딩 안전 폴백
    if not active_endpoints:
        active_endpoints = [
            ("v1beta", "models/gemini-1.5-flash"),
            ("v1beta", "models/gemini-2.0-flash"),
            ("v1", "models/gemini-1.5-flash")
        ]

    # 3단계: 구글이 승인한 활성 모델 경로로 다이렉트 호출 실행
    last_error = ""
    for api_version, model_full_path in active_endpoints:
        try:
            url = f"https://generativelanguage.googleapis.com/{api_version}/{model_full_path}:generateContent?key={api_key}"
            response = requests.post(
                url,
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
                last_error = f"[{model_full_path} {response.status_code}]: {response.text[:140]}"
        except Exception as exc:
            last_error = f"[{model_full_path} 요청 오류]: {exc}"

    # 실패 시 원인을 투명하게 노출하여 즉시 해결 가능하도록 안내
    final_err_msg = last_error or discovery_error or "구글 Gemini 서버 응답 없음"
    return "", f"Gemini 연결 실패: {final_err_msg}"


# ------------------------------------------------------------------------------
# 3.02.00 | ChatGPT (OpenAI GPT-4o-mini) 직타 파이프라인
# ------------------------------------------------------------------------------
def call_chatgpt_text(prompt_text):
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("OpenAI_API_KEY")
    if not api_key:
        try:
            api_key = st.secrets.get("OPENAI_API_KEY", "") or st.secrets.get("OpenAI_API_KEY", "")
        except Exception:
            api_key = ""
    if not api_key:
        return "", "NO_KEY"

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "당신은 가계 재무와 은퇴 준비를 진단하는 다정하고 객관적인 성찰 파트너입니다."},
            {"role": "user", "content": prompt_text}
        ],
        "temperature": 0.5,
        "max_tokens": 1500
    }
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            json=payload,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
            timeout=20
        )
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"].strip(), ""
        return "", f"[OpenAI] {response.status_code}: {response.text[:140]}"
    except Exception as exc:
        return "", f"OpenAI 요청 오류: {exc}"

# ------------------------------------------------------------------------------
# 3.03.00 | Claude (Anthropic Claude-3-5-Haiku) 직타 파이프라인
# ------------------------------------------------------------------------------
def call_claude_text(prompt_text):
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("Anthropic_API_KEY")
    if not api_key:
        try:
            api_key = st.secrets.get("ANTHROPIC_API_KEY", "") or st.secrets.get("Anthropic_API_KEY", "")
        except Exception:
            api_key = ""
    if not api_key:
        return "", "NO_KEY"

    payload = {
        "model": "claude-3-5-haiku-20241022",
        "max_tokens": 1500,
        "temperature": 0.5,
        "messages": [{"role": "user", "content": prompt_text}]
    }
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    try:
        response = requests.post("https://api.anthropic.com/v1/messages", json=payload, headers=headers, timeout=20)
        if response.status_code == 200:
            res_json = response.json()
            return res_json["content"][0]["text"].strip(), ""
        return "", f"[Claude] {response.status_code}: {response.text[:140]}"
    except Exception as exc:
        return "", f"Claude 요청 오류: {exc}"


# ==============================================================================
# 4.00.00 | 진입 커버 및 사이드바 프로필 (Cover & Sidebar Profile)
# ==============================================================================

# ==============================================================================
# 4.01.00 | 사이드바 프로필 요약 및 카톡 리포트 동기화
# ==============================================================================
with st.sidebar:
    # 1. 익명 고유번호 배지
    st.markdown(f"""
<div style="background: rgba(30, 41, 59, 0.4); border: 1px solid #334155; border-radius: 10px; padding: 12px 14px; text-align: center; margin-bottom: 20px;">
<div style="font-size: 11.5px; color: #94a3b8; font-weight: 600; letter-spacing: 0.04em;">익명 진단 고유번호</div>
<div style="font-size: 20px; font-weight: 750; color: #cbd5e1; letter-spacing: 1px; margin-top: 3px;">{st.session_state.anonymous_id}</div>
</div>
""", unsafe_allow_html=True)

    # 2. 나의 프로필 정보 (진단 시작 후 활성화)
    if st.session_state.started:
        st.markdown("#### 나의 기본 정보")
        st.markdown(f"**나의 이름/별칭:** {st.session_state.get('person_name','')}")
        st.markdown(f"**나의 나이:** {st.session_state.get('person_age','')}세")

        q_self = active_quadrant(st.session_state.get("job_form", ""))
        q_spouse = active_quadrant(st.session_state.get("job_spouse_form", ""))
        types_desc = []
        if q_self: types_desc.append(f"나({q_self})")
        if q_spouse: types_desc.append(f"배우자({q_spouse})")
        dual_income_str = " + ".join(types_desc) if types_desc else "아직 미선택"
        st.markdown(f"**우리집 소득 형태:** {dual_income_str}")

    # 3. 사이드바: 카톡 리포트 불러오기
    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    with st.expander("📥 카톡 리포트 불러오기"):
        st.markdown("<div style='font-size: 13px; color: #CBD5E1; margin-bottom: 6px;'>전달받은 <b>리포트 전문</b> 또는 <b>NC-코드</b>를 붙여넣으세요.</div>", unsafe_allow_html=True)
        pasted_code_sb = st.text_area("카톡 내용 붙여넣기", placeholder="NC-코드를 붙여넣으세요", height=90, key="sb_pasted_code", label_visibility="collapsed")
        if st.button("🔄 데이터 동기화", type="primary", use_container_width=True, key="sb_btn_sync"):
            ok, msg = import_diagnosis_code(pasted_code_sb)
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
    st.caption("※ 나침반은 외부 서버에 저장되지 않는 일회성 안전 세션입니다.")


# ==============================================================================
# 4.02.00 | 첫 진입 표지 및 인라인 시작 바 (클린 미니멀 툴바 복원)
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
        
        # 표지 바로 아래 2줄 3칸 슬림 툴바 (이름/나이/시작)
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
# 6.01.00 | Tab 1 — 우리집 가계부 (현업 연차 원터치 pills & 생애주기 궤적 연동)
# ==============================================================================
if selected_page == "우리집 가계부":
    st.markdown("## 우리집 가계부")
    
    with st.form("finance_form"):
        # ----------------------------------------------------------------------
        # ⓪ 우리집 소득 성격 (직업 및 현업 연차)
        # ----------------------------------------------------------------------
        with st.container(border=True, key="job-panel"):
            st.markdown("### ⓪ 우리집 소득 성격")
            
            job_options = ["직장인", "자영업", "전문직", "사업가", "투자자", "임대소득자", "전업주부", "그외"]
            job_spouse_options = ["해당 없음", "직장인", "자영업", "전문직", "사업가", "투자자", "임대소득자", "전업주부", "그외"]
            career_options = ["🌱 3년 이하 (초년생)", "🌿 4~9년 (성장기)", "🌳 10년 이상 (베테랑)"]
            
            prev_job = st.session_state.get("job_form", "직장인")
            if prev_job not in job_options:
                prev_job = "직장인"
                
            prev_spouse_job = st.session_state.get("job_spouse_form", "해당 없음")
            if prev_spouse_job not in job_spouse_options:
                prev_spouse_job = "해당 없음"

            prev_career = st.session_state.get("career_stage", "🌱 3년 이하 (초년생)")
            if prev_career not in career_options:
                prev_career = "🌱 3년 이하 (초년생)"
            
            st.markdown("<div style='font-size: 17px; font-weight: 700; color: #F8FAFC; margin-bottom: 6px;'>나의 직업은?</div>", unsafe_allow_html=True)
            job_selected = st.pills(
                "나의 직업은?",
                job_options,
                default=prev_job,
                key="pills_job_self",
                label_visibility="collapsed"
            )
            
            st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
            
            st.markdown("<div style='font-size: 17px; font-weight: 700; color: #F8FAFC; margin-bottom: 6px;'>나의 현업 경력(연차)은?</div>", unsafe_allow_html=True)
            career_selected = st.pills(
                "나의 현업 경력(연차)은?",
                career_options,
                default=prev_career,
                key="pills_career_stage",
                label_visibility="collapsed"
            )

            st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
            
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
        final_career = career_selected if career_selected else "🌱 3년 이하 (초년생)"
        final_spouse_job = "" if (not job_spouse_selected or job_spouse_selected == "해당 없음") else job_spouse_selected
        
        submitted_values = {
            "job_form": final_job,
            "career_stage": final_career,
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
    # 우리집 재무 현황 (2x2 동일 규격 카드)
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
    # 미래 순자산·연금 궤적 (경력 연차 및 생애주기 가족 이벤트 팩트 연동)
    # --------------------------------------------------------------------------
    st.markdown("### 미래 순자산·연금 궤적")
    
    cur_age = int(st.session_state.person_age)
    retire_val = st.session_state.get("retirement_age")
    retire_age = int(retire_val) if retire_val is not None else 65
    retire_age = max(cur_age, min(retire_age, 90))
    
    start_asset_eok = s["net_worth"] / 10000.0
    base_annual_surplus_eok = s["annual_net_surplus"] / 10000.0
    
    career_st = st.session_state.get("career_stage", "🌱 3년 이하 (초년생)")
    m_plan = st.session_state.get("marriage_plan", "미정")
    c_plan = st.session_state.get("child_plan", "미정")
    is_single_young = (int(getv("spouse_age", 0)) == 0 and cur_age < 40)

    ages_accum = list(range(cur_age, retire_age + 1))
    vals_accum_eok = []
    current_asset = start_asset_eok
    
    for a in ages_accum:
        vals_accum_eok.append(current_asset)
        
        # 기본 생애주기 소득 가중치
        if a < 45:
            growth_step = 0.025 if "초년생" in career_st else 0.018
            lifecycle_weight = 1.0 + (growth_step * (a - cur_age))
        elif 45 <= a <= 53:
            lifecycle_weight = 1.0 + (0.02 * (45 - cur_age)) - 0.15
        else:
            lifecycle_weight = max(0.65, 1.0 + (0.02 * (45 - cur_age)) - 0.25)
            
        # 미혼 청년의 결혼·출산 계획에 따른 객관적 생애 이벤트 팩트 반영
        if is_single_young:
            # 1~3년 내 결혼/주거 마련 계획 시 자산 지출 구간
            if m_plan in ["1~3년 내 결혼 생각 있음", "결혼 예정/준비 중"] and (cur_age + 1 <= a <= cur_age + 3):
                lifecycle_weight *= 0.75
            # 출산 계획 시 30대 초중반 육아기 소득·지출 변동 구간
            if c_plan in ["자녀 계획 있음", "출산 예정/준비 중"] and (33 <= a <= 36):
                lifecycle_weight *= 0.65

        annual_save = base_annual_surplus_eok * max(0.05, lifecycle_weight)
        current_asset += annual_save

    peak_asset_eok = vals_accum_eok[-1]

    # 은퇴 후: 자산 인출·연금기
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

    fig_asset = go.Figure()
    fig_asset.add_hline(y=0, line_dash="solid", line_color="#334155", line_width=1.5)

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

    fig_asset.add_vline(x=retire_age, line_dash="dash", line_color="#F8FAFC", line_width=2)
    fig_asset.add_annotation(
        x=retire_age, y=peak_asset_eok * mult,
        text=f"은퇴 정점 {retire_age}세 ({peak_disp})",
        showarrow=True, arrowhead=2, arrowcolor="#F59E0B",
        font=dict(size=13, color="#FDE68A", family="sans-serif"),
        ay=-38, bgcolor="rgba(15, 23, 42, 0.85)", bordercolor="#F59E0B", borderpad=4
    )

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
            fixedrange=True
        ),
        yaxis=dict(
            title=dict(text="추정 순자산", font=dict(size=14, color="#94A3B8")),
            tickfont=dict(size=13, color="#94A3B8"),
            ticksuffix=unit_str,
            tickformat=",.0f",
            gridcolor="rgba(100, 116, 139, 0.2)",
            fixedrange=True
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            font=dict(size=12.5, color="#F1F5F9")
        ),
        hovermode="x unified"
    )

    st.plotly_chart(
        fig_asset,
        use_container_width=True,
        config={"displayModeBar": False, "scrollZoom": False, "doubleClick": False, "showAxisDragHandles": False}
    )

    bonus_note = f" (연간 상여금 {money(s['annual_bonus'])} 포함)" if s['annual_bonus'] > 0 else ""
    st.markdown(f"""
<div style="background: rgba(30, 41, 59, 0.5); border: 1px solid #334155; border-radius: 10px; padding: 14px 16px; margin-top: 10px;">
<div style="font-size: 13.5px; color: #CBD5E1; line-height: 1.6;">
• <b>🌱 은퇴 전 (만 {cur_age}세 ~ {retire_age}세)</b>: 1년 총 저축여력({money(s['annual_net_surplus'])}{bonus_note})과 현업 경력({career_st}), 국가데이터처 국민이전계정(NTA)의 생애주기 소득 피크(45세) 및 가족 지출기를 결합한 실질 자산 궤적입니다.<br>
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
    
    st.markdown("""
<div style="background: rgba(30, 41, 59, 0.45); border: 1.5px solid #334155; border-radius: 14px; padding: 20px 22px; margin-bottom: 22px;">
<div style="font-size: 20px; font-weight: 850; color: #F8FAFC; margin-bottom: 14px;">소득이 만들어지는 세 가지 모습</div>
""", unsafe_allow_html=True)
    
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
<div class='soft-card' style='text-align:center; min-height:215px; margin:0;'>
{badge_small}
<div style='font-size:32px; letter-spacing:4px; margin-bottom:6px;'>🪣🪣🪣</div>
<div style='font-size:18.5px; font-weight:800; color:#F8FAFC; margin-bottom:6px;'>작은 물통</div>
<div style='font-size:14px; color:#CBD5E1; line-height:1.5; word-break:keep-all;'>
직접 일한 시간과 돈을 1:1로 맞바꾸는 모습<br><span style='color:#F59E0B; font-weight:600;'>(노동을 멈추면 수입도 멈춤)</span>
</div>
</div>
""", unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
<div class='soft-card' style='text-align:center; min-height:215px; margin:0;'>
{badge_big}
<div style='font-size:40px; margin-bottom:6px;'>🛢️</div>
<div style='font-size:18.5px; font-weight:800; color:#F8FAFC; margin-bottom:6px;'>큰 물통</div>
<div style='font-size:14px; color:#CBD5E1; line-height:1.5; word-break:keep-all;'>
전문성과 몸값을 높여 한 번에 담는 양을 키운 모습<br><span style='color:#F59E0B; font-weight:600;'>(큰 물통이지만 여전히 지고 다님)</span>
</div>
</div>
""", unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
<div class='soft-card' style='text-align:center; min-height:215px; margin:0;'>
{badge_pipe}
<div style='font-size:32px; letter-spacing:2px; margin-bottom:6px;'>🚰➰⚙️</div>
<div style='font-size:18.5px; font-weight:800; color:#F8FAFC; margin-bottom:6px;'>파이프라인</div>
<div style='font-size:14px; color:#CBD5E1; line-height:1.5; word-break:keep-all;'>
시스템과 자산이 나 대신 일하는 모습<br><span style='color:#38BDF8; font-weight:600;'>(시간으로부터 자유로운 소득)</span>
</div>
</div>
""", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("""
<div style="background: rgba(45, 35, 20, 0.55); border: 1.5px solid #6d4a1a; border-radius: 14px; padding: 22px 24px; margin-bottom: 22px;">
<div style="font-size: 20px; font-weight: 850; color: #FDE68A; margin-bottom: 12px;">🌾 지혜로운 산책: 돌쇠와 똘똘이</div>
<div style="font-size: 14.5px; color: #E2E8F0; margin-bottom: 16px;">옛날 어느 마을, 머슴을 구하는 대감댁에 두 젊은이가 찾아왔습니다.</div>

<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;">
<div style="background: rgba(15, 23, 42, 0.75); border: 1px solid #78350f; border-radius: 10px; padding: 14px 16px;">
<div style="font-size: 17px; font-weight: 800; color: #F59E0B; margin-bottom: 6px;">💪 돌쇠의 선택 (물통의 삶)</div>
<div style="font-size: 14px; color: #CBD5E1; line-height: 1.6; word-break: keep-all;">
"대감마님, 저는 첫 달부터 매달 <b>쌀 한 가마(80kg)</b>씩을 주십시오."<br>
돌쇠는 첫 달부터 쌀 한 가마를 받아 가족을 부양했습니다. 하지만 늙어 힘이 빠질 때까지 지게를 내려놓지 못했습니다.
</div>
</div>

<div style="background: rgba(15, 23, 42, 0.75); border: 1px solid #0369a1; border-radius: 10px; padding: 14px 16px;">
<div style="font-size: 17px; font-weight: 800; color: #38BDF8; margin-bottom: 6px;">🧠 똘똘이의 선택 (파이프라인의 삶)</div>
<div style="font-size: 14px; color: #CBD5E1; line-height: 1.6; word-break: keep-all;">
"저는 첫 달에 <b>쌀 한 되(1kg)</b>만 주시고, 매달 곱절(2되, 4되, 8되...)로 주십시오."<br>
똘똘이는 <b>'복리의 지혜'(파이프라인의 속성)</b>로 훗날 힘겨운 물통으로부터 자유로워졌습니다. <b>하지만 당장 첫 달에 쌀 한 되만 받았다면 굶어 죽었을 것입니다.</b>
</div>
</div>
</div>

<div style="background: rgba(234, 88, 12, 0.14); border-left: 4px solid #EA580C; border-radius: 4px; padding: 12px 16px;">
<div style="font-size: 15px; font-weight: 750; color: #F8FAFC; line-height: 1.6; word-break: keep-all;">
💡 <b>나침반의 성찰</b>: 돌쇠의 삶(현업)을 버리라는 것이 아닙니다.<br>
낮에는 돌쇠처럼 성실하게 가족의 생계(쌀 한 가마)를 책임지면서, 저녁과 주말의 시간에 똘똘이의 지혜(파이프라인)를 한 되, 두 되 차근차근 놓아가는 <b>'현명한 플랜 B'</b>가 필요한 이유입니다.
</div>
</div>
</div>
""", unsafe_allow_html=True)

    st.markdown("""
<div style="background: rgba(24, 32, 47, 0.65); border: 1.5px solid #3b4b66; border-radius: 14px; padding: 20px 22px; margin-bottom: 22px;">
<div style="font-size: 20px; font-weight: 850; color: #F8FAFC; margin-bottom: 12px;">내가 생각하는 은퇴 예상 나이</div>
""", unsafe_allow_html=True)

    cur_user_age = int(st.session_state.person_age)
    default_retire = int(st.session_state.get("retirement_age") or 60)
    if default_retire < cur_user_age:
        default_retire = cur_user_age

    with st.form("retirement_inline_form"):
        r_col1, r_col2 = st.columns([3.2, 1.0])
        with r_col1:
            retirement_input = st.number_input(
                "지금 하는 현업을 졸업(은퇴)하고 싶은 나이",
                min_value=cur_user_age, max_value=100,
                value=default_retire, step=1,
                label_visibility="collapsed"
            )
        with r_col2:
            retirement_saved = st.form_submit_button("은퇴 나이 확인", use_container_width=True, type="primary")

    if retirement_saved:
        st.session_state["retirement_age"] = int(retirement_input)
        st.success(f"은퇴 예상 나이({retirement_input}세)가 반영되었습니다.")

    st.markdown("</div>", unsafe_allow_html=True)

    _, next_col = st.columns([5, 1])
    with next_col:
        if st.button("다음 →", key="livelihood_next", use_container_width=True, type="primary"):
            st.session_state["retirement_age"] = int(st.session_state.get("retirement_age_input", retirement_input))
            st.session_state["_pending_nav"] = "인생의 사계절"
            st.session_state["_scroll_to_top_once"] = True
            st.rerun()


# ==============================================================================
# 6.03.00 | Tab 3 — 인생의 사계절 (생애주기 곡선에 가족계획 팩트 반영)
# ==============================================================================
elif selected_page == "인생의 사계절":
    if st.session_state.pop("_scroll_to_top_once", False):
        st.components.v1.html(
            "<script>try { window.parent.scrollTo({top: 0, behavior: 'instant'}); } catch(e) {}</script>",
            height=0,
        )
    
    st.markdown("## 인생의 사계절")
    st.markdown("자연에 사계절이 있듯 사람의 삶에도 준비(봄) · 성장(여름) · 결실(가을) · 음미(겨울)의 시간이 있습니다.")
    
    cur_age = int(st.session_state.person_age)
    retire_val = st.session_state.get("retirement_age")
    retire_age = int(retire_val) if retire_val is not None else 60
    retire_age = max(cur_age, min(retire_age, 90))
    years_left = max(0, retire_age - cur_age)

    # 1. 가족 구성원과 은퇴 시점의 나이
    st.markdown("### 1. 가족 구성원과 은퇴 시점의 나이")
    child_options = ["입력 안 함", "없음", "1명", "2명", "3명 이상"]
    child_count = st.selectbox(
        "자녀 수", child_options,
        index=child_options.index(st.session_state.get("child_count", "입력 안 함"))
        if st.session_state.get("child_count", "입력 안 함") in child_options else 0,
        key="child_count_live",
    )

    with st.form("family_form"):
        r1_c1, r1_c2 = st.columns(2)
        with r1_c1:
            spouse_age = st.number_input("배우자 나이 (없거나 미입력 시 0)", min_value=0, max_value=120, value=int(st.session_state.get("spouse_age", 0)), step=1)
        with r1_c2:
            child_age = int(st.session_state.get("child_age", 0)) if child_count in ["1명", "2명", "3명 이상"] else 0
            if child_count in ["1명", "2명", "3명 이상"]:
                child_age = st.number_input("첫째 자녀 나이", min_value=0, max_value=100, value=child_age, step=1)
            else:
                st.write("")

        child_age2 = int(st.session_state.get("child_age2", 0)) if child_count in ["2명", "3명 이상"] else 0
        child_age3 = int(st.session_state.get("child_age3", 0)) if child_count == "3명 이상" else 0
        if child_count in ["2명", "3명 이상"]:
            r2_c1, r2_c2 = st.columns(2)
            with r2_c1:
                child_age2 = st.number_input("둘째 자녀 나이", min_value=0, max_value=100, value=child_age2, step=1)
            with r2_c2:
                if child_count == "3명 이상":
                    child_age3 = st.number_input("셋째 자녀 나이", min_value=0, max_value=100, value=child_age3, step=1)

        col_f, col_m = st.columns(2)
        with col_f:
            father_age = st.number_input("아버지 나이 (선택, 모르면 0)", min_value=0, max_value=120, value=int(st.session_state.get("father_age", 0)), step=1)
        with col_m:
            mother_age = st.number_input("어머니 나이 (선택, 모르면 0)", min_value=0, max_value=120, value=int(st.session_state.get("mother_age", 0)), step=1)
            
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        st.markdown("#### 앞으로의 가족 계획 (선택)")
        p_c1, p_c2, p_c3 = st.columns(3)
        with p_c1:
            marriage_options = ["미정", "계획 없음", "1~3년 내 결혼 생각 있음", "3년 이후 결혼 생각 있음", "결혼 예정/준비 중"]
            marriage_plan = st.selectbox("결혼 계획", marriage_options, index=marriage_options.index(st.session_state.get("marriage_plan", "미정")) if st.session_state.get("marriage_plan", "미정") in marriage_options else 0)
        with p_c2:
            child_plan_options = ["미정", "계획 없음", "자녀 계획 있음", "출산 예정/준비 중", "추가 자녀 계획 있음"]
            child_plan = st.selectbox("출산·자녀 계획", child_plan_options, index=child_plan_options.index(st.session_state.get("child_plan", "미정")) if st.session_state.get("child_plan", "미정") in child_plan_options else 0)
        with p_c3:
            housing_options = ["미정", "현재 주거 유지", "전세·월세 이동 고려", "주택 구입 고려", "주거 계획 확정"]
            housing_plan = st.selectbox("주거 계획", housing_options, index=housing_options.index(st.session_state.get("housing_plan", "미정")) if st.session_state.get("housing_plan", "미정") in housing_options else 0)

        save_family = st.form_submit_button("가족 기본 정보 반영하기", use_container_width=True, type="primary")

    if save_family:
        st.session_state.spouse_age = spouse_age
        st.session_state.child_count = child_count
        st.session_state.child_age = child_age
        st.session_state.child_age2 = child_age2
        st.session_state.child_age3 = child_age3
        st.session_state.father_age = father_age
        st.session_state.mother_age = mother_age
        st.session_state.marriage_plan = marriage_plan
        st.session_state.child_plan = child_plan
        st.session_state.housing_plan = housing_plan
        st.rerun()

    if "sibling_items" not in st.session_state:
        st.session_state.sibling_items = []

    st.markdown("""
<div style="background: rgba(30, 41, 59, 0.45); border: 1.5px solid #334155; border-radius: 12px; padding: 18px 20px; margin-top: 14px;">
<div style="font-size: 16.5px; font-weight: 800; color: #F8FAFC; margin-bottom: 6px;">👥 형제자매 추가 (누를 때마다 1, 2, 3... 자동 추가)</div>
<div style="font-size: 13.5px; color: #94A3B8; margin-bottom: 12px;">버튼을 누르면 해당 형제자매가 순서대로 생성됩니다.</div>
""", unsafe_allow_html=True)

    b_cols = st.columns(6)
    role_types = ["형", "누나", "오빠", "언니", "남동생", "여동생"]
    for idx, role in enumerate(role_types):
        with b_cols[idx]:
            if st.button(f"+ {role}", key=f"btn_add_sib_{role}", use_container_width=True):
                count = sum(1 for item in st.session_state.sibling_items if item["role"] == role)
                st.session_state.sibling_items.append({
                    "id": f"{role}_{count+1}_{random.randint(100,999)}",
                    "role": role,
                    "label": f"{role} {count + 1}",
                    "age": 0
                })
                st.rerun()

    if st.session_state.sibling_items:
        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        items_to_remove = []
        sib_entry_cols = st.columns(2)
        for idx, s_item in enumerate(st.session_state.sibling_items):
            c = sib_entry_cols[idx % 2]
            with c:
                ic1, ic2 = st.columns([3, 1])
                with ic1:
                    new_age = st.number_input(
                        f"{s_item['label']} 나이",
                        min_value=0, max_value=120,
                        value=int(s_item.get("age", 0)),
                        step=1, key=f"inp_age_{s_item['id']}"
                    )
                    s_item["age"] = new_age
                with ic2:
                    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                    if st.button("삭제", key=f"btn_del_{s_item['id']}", use_container_width=True):
                        items_to_remove.append(s_item["id"])
        if items_to_remove:
            st.session_state.sibling_items = [
                it for it in st.session_state.sibling_items if it["id"] not in items_to_remove
            ]
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

    people = [(st.session_state.get("person_name", "나"), cur_age)]
    if getv("spouse_age", 0) > 0: people.append(("배우자", int(getv("spouse_age"))))
    if getv("child_age", 0) > 0: people.append(("첫째 자녀", int(getv("child_age"))))
    if getv("child_age2", 0) > 0: people.append(("둘째 자녀", int(getv("child_age2"))))
    if getv("child_age3", 0) > 0: people.append(("셋째 자녀", int(getv("child_age3"))))
    if getv("father_age", 0) > 0: people.append(("아버지", int(getv("father_age"))))
    if getv("mother_age", 0) > 0: people.append(("어머니", int(getv("mother_age"))))
    for s_it in st.session_state.get("sibling_items", []):
        if int(s_it.get("age", 0)) > 0:
            people.append((s_it["label"], int(s_it["age"])))

    st.markdown(f"""
<div style="background: rgba(30, 41, 59, 0.4); border: 1px solid #334155; border-radius: 10px; padding: 12px 18px; margin: 18px 0 10px 0; display:flex; justify-content:space-between; align-items:center;">
<span style="font-size: 15.5px; font-weight: 800; color: #F8FAFC;">📌 내가 은퇴하는 시점(만 {retire_age}세, {years_left}년 후)의 우리 가족 나이</span>
<span style="font-size: 13px; color: #94A3B8;">현재 나이 ➔ 은퇴 시 나이</span>
</div>
""", unsafe_allow_html=True)

    f_cols = st.columns(2)
    for idx, (name, current) in enumerate(people):
        c = f_cols[idx % 2]
        future = current + years_left
        with c:
            st.markdown(f"""
<div class='soft-card' style='display:flex; align-items:center; justify-content:space-between; padding:12px 18px; margin:5px 0;'>
<b style='font-size:16px; color:#F8FAFC;'>{name}</b>
<div style='display:flex; align-items:center; gap:12px;'>
<span style='font-size:17px; color:#94A3B8;'>{current}세</span>
<span style='font-size:16px; color:#EA580C;'>➔</span>
<span style='font-size:19px; font-weight:800; color:#F59E0B;'>{future}세</span>
</div>
</div>
""", unsafe_allow_html=True)

    c_age1 = int(getv("child_age", 0))
    if 0 < c_age1 < 20:
        college_my_age = cur_age + (20 - c_age1)
        st.markdown(f"""
<div style="background: rgba(234, 88, 12, 0.12); border-left: 4px solid #EA580C; border-radius: 6px; padding: 14px 18px; margin: 12px 0 20px 0;">
<div style="font-size: 15px; font-weight: 750; color: #F8FAFC; line-height: 1.6;">
🎯 <b>생애 지출 피크 자각 포인트</b>: 첫째 자녀가 대학에 입학하는 만 20세가 되면, 나의 나이는 <b>만 {college_my_age}세</b>가 됩니다.<br>
<span style="font-size: 13.5px; color: #CBD5E1;">
통계청 국민이전계정 상 소득 정점(45세)은 지나가면서, 자녀 학자금과 독립 비용으로 <b>인생에서 가장 큰 지출이 집중되는 결정적 시기</b>입니다.
</span>
</div>
</div>
""", unsafe_allow_html=True)
    elif c_age1 >= 20:
        st.markdown(f"""
<div style="background: rgba(30, 41, 59, 0.5); border-left: 4px solid #38BDF8; border-radius: 6px; padding: 14px 18px; margin: 12px 0 20px 0;">
<div style="font-size: 15px; font-weight: 750; color: #F8FAFC; line-height: 1.6;">
🌱 <b>가족 성장 단계</b>: 첫째 자녀(만 {c_age1}세)가 이미 성년기에 도달하여, 학자금 집중 지출기를 거쳐 독립과 사회 진출의 계절을 맞이하고 있습니다.
</div>
</div>
""", unsafe_allow_html=True)

    # --------------------------------------------------------------------------
    # 2. 나만의 맞춤형 생애주기 흑자·적자 곡선 (NTA 개인화 번역)
    # --------------------------------------------------------------------------
    st.markdown("### 2. 나만의 생애주기 소득·소비 곡선 (국민이전계정 개인화 번역)")
    st.caption("※ 통계청 공식 NTA 패턴을 인터뷰이 본인의 실제 소득·소비 및 은퇴 나이에 맞추어 번역한 개인 곡선입니다.")
    
    s = current_financial_summary()
    cur_annual_income = s["annual_total_income"]
    cur_annual_expense = s["annual_total_expenses"]
    ret_annual_pension = float(getv("income_pension", 0) or 0) * 12.0
    ret_annual_expense = float(getv("retirement_monthly_expenses", 200) or 0) * 12.0

    career_st = st.session_state.get("career_stage", "🌱 3년 이하 (초년생)")
    m_plan = st.session_state.get("marriage_plan", "미정")
    c_plan = st.session_state.get("child_plan", "미정")
    is_single_young = (int(getv("spouse_age", 0)) == 0 and cur_age < 40)

    ages_sim = list(range(20, 86))
    my_income_curve = []
    my_expense_curve = []

    for a in ages_sim:
        if a < cur_age:
            ratio = max(0.2, (a - 20) / max(1, (cur_age - 20)))
            my_income_curve.append(cur_annual_income * ratio)
        elif cur_age <= a < retire_age:
            growth_step = 0.025 if "초년생" in career_st else 0.018
            if a <= 45:
                w_inc = 1.0 + (growth_step * (a - cur_age))
            else:
                w_inc = max(0.85, 1.0 + (0.02 * (45 - cur_age)) - (0.015 * (a - 45)))
            
            # 미혼 청년의 출산/육아기 소득 변동 팩트 반영
            if is_single_young and c_plan in ["자녀 계획 있음", "출산 예정/준비 중"] and (33 <= a <= 35):
                w_inc *= 0.82
                
            my_income_curve.append(cur_annual_income * w_inc)
        else:
            my_income_curve.append(ret_annual_pension)

        if a < cur_age:
            my_expense_curve.append(cur_annual_expense * 0.75)
        elif cur_age <= a < retire_age:
            w_exp = 1.0
            if 46 <= a <= 53 and c_age1 < 20:
                w_exp = 1.15
            # 미혼 청년의 결혼/주거 및 영유아 양육 지출 집중 팩트 반영
            if is_single_young:
                if m_plan in ["1~3년 내 결혼 생각 있음", "결혼 예정/준비 중"] and (cur_age + 1 <= a <= cur_age + 3):
                    w_exp = max(w_exp, 1.12)
                if c_plan in ["자녀 계획 있음", "출산 예정/준비 중"] and (33 <= a <= 37):
                    w_exp = max(w_exp, 1.15)
            my_expense_curve.append(cur_annual_expense * w_exp)
        else:
            my_expense_curve.append(ret_annual_expense)

    fig_my_nta = go.Figure()

    fig_my_nta.add_trace(go.Scatter(
        x=ages_sim, y=my_income_curve,
        mode="lines",
        line=dict(color="#10B981", width=3.5),
        name="나의 소득 흐름 (근로·사업소득 ➔ 은퇴 후 연금)",
        hovertemplate="나이: %{x}세<br>연 소득: <b>%{y:,.0f}만 원</b><extra></extra>"
    ))

    fig_my_nta.add_trace(go.Scatter(
        x=ages_sim, y=my_expense_curve,
        mode="lines",
        line=dict(color="#F97316", width=3, dash="dash"),
        name="나의 생애 소비 흐름",
        hovertemplate="나이: %{x}세<br>연 소비: <b>%{y:,.0f}만 원</b><extra></extra>"
    ))

    fig_my_nta.add_vline(x=cur_age, line_dash="solid", line_color="#38BDF8", line_width=2)
    fig_my_nta.add_annotation(
        x=cur_age, y=max(my_income_curve) * 0.95,
        text=f"현재 나이 ({cur_age}세)",
        showarrow=True, arrowhead=2, arrowcolor="#38BDF8",
        font=dict(size=12, color="#BAE6FD"),
        ay=-30, bgcolor="rgba(15, 23, 42, 0.85)", bordercolor="#38BDF8"
    )

    fig_my_nta.add_vline(x=retire_age, line_dash="dash", line_color="#EF4444", line_width=2)
    fig_my_nta.add_annotation(
        x=retire_age, y=my_income_curve[ages_sim.index(retire_age)],
        text=f"나의 은퇴 시점 ({retire_age}세 적자 전환)",
        showarrow=True, arrowhead=2, arrowcolor="#EF4444",
        font=dict(size=12, color="#FCA5A5"),
        ay=35, bgcolor="rgba(15, 23, 42, 0.85)", bordercolor="#EF4444"
    )

    fig_my_nta.update_layout(
        height=380,
        margin=dict(l=20, r=20, t=30, b=35),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E2E8F0", size=13),
        xaxis=dict(
            title=dict(text="연령 (세)", font=dict(size=14, color="#94A3B8")),
            tickfont=dict(size=13, color="#94A3B8"),
            gridcolor="rgba(100, 116, 139, 0.2)",
            tickmode="linear", tick0=20, dtick=5,
            fixedrange=True
        ),
        yaxis=dict(
            title=dict(text="연간 금액 (만 원)", font=dict(size=14, color="#94A3B8")),
            tickfont=dict(size=13, color="#94A3B8"),
            tickformat=",.0f",
            gridcolor="rgba(100, 116, 139, 0.2)",
            fixedrange=True
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            font=dict(size=12, color="#F1F5F9")
        ),
        hovermode="x unified"
    )

    st.plotly_chart(
        fig_my_nta,
        use_container_width=True,
        config={"displayModeBar": False, "scrollZoom": False, "doubleClick": False, "showAxisDragHandles": False}
    )

    # 3. 인생의 사계절
    winter_years = max(0, 88 - retire_age)
    winter_months = winter_years * 12
    
    st.markdown("### 3. 인생의 사계절과 맞이할 겨울의 시간")
    
    if cur_age <= 27:
        cur_season = "spring"
    elif 28 <= cur_age <= 45:
        cur_season = "summer"
    elif 46 <= cur_age < retire_age:
        cur_season = "autumn"
    else:
        cur_season = "winter"

    def get_season_card_ui(season_key, icon, title, age_range, desc):
        is_current = (cur_season == season_key)
        if is_current:
            card_border = "border: 2px solid #EA580C; background: rgba(234, 88, 12, 0.14);"
            badge_html = "<div style='min-height:22px; margin-bottom:4px;'><span style='background:#EA580C; color:#FFFFFF; font-size:11.5px; font-weight:800; padding:2px 7px; border-radius:4px;'>📍 지금 나의 계절</span></div>"
        else:
            card_border = "border: 1px solid #334155; background: rgba(21, 30, 47, 0.7);"
            badge_html = "<div style='min-height:22px; margin-bottom:4px;'></div>"

        return f"""
<div class='soft-card' style='text-align:center; min-height:205px; {card_border} padding:14px 10px; margin:0;'>
{badge_html}
<div style='font-size:28px;'>{icon}</div>
<div style='font-size:16.5px; font-weight:800; color:#F8FAFC; margin:4px 0;'>{title}</div>
<div style='font-size:13px; color:#94A3B8;'>{age_range}</div>
<div style='font-size:13px; color:#CBD5E1; margin-top:8px; line-height:1.4;'>{desc}</div>
</div>
"""

    card_spring = get_season_card_ui("spring", "🌱", "봄 (준비기)", "0세 ~ 27세", "부모님의 부양으로 배우고 성장하는 적자 구간")
    card_summer = get_season_card_ui("summer", "☀️", "여름 (성장기)", "28세 ~ 45세", "성실하게 일하여 가정을 일구고 최대 흑자를 만드는 시기")
    card_autumn = get_season_card_ui("autumn", "🍂", "가을 (결실기)", f"46세 ~ {retire_age}세", "자녀 독립 & 똘똘이의 파이프라인을 다질 골든타임")
    card_winter = get_season_card_ui("winter", "❄️", "겨울 (음미기)", f"{retire_age}세 ~ 88세", f"근로소득 중단<br><b style='color:#38BDF8;'>약 {winter_years}년 ({winter_months}개월)</b>")

    s_col1, s_col2, s_col3, s_col4 = st.columns(4)
    with s_col1: st.markdown(card_spring, unsafe_allow_html=True)
    with s_col2: st.markdown(card_summer, unsafe_allow_html=True)
    with s_col3: st.markdown(card_autumn, unsafe_allow_html=True)
    with s_col4: st.markdown(card_winter, unsafe_allow_html=True)

    st.markdown(f"""
<div style="background: rgba(30, 41, 59, 0.6); border: 1px solid #334155; border-radius: 12px; padding: 18px 20px; margin: 16px 0 24px 0;">
<div style="font-size: 15px; color: #F8FAFC; line-height: 1.6; word-break: keep-all;">
💡 <b>산책로의 질문</b>: 은퇴 후 우리가 맞이할 겨울의 시간은 <b>약 {winter_years}년 ({winter_months:,}개월)</b>입니다.<br>
<span style="color: #94A3B8;">
이 긴 겨울 동안 매달 무거운 물통을 지고 눈길을 걸을 것인가, 방 안에서 따뜻하게 흘러나오는 파이프라인을 맞이할 것인가는 <b>지금 '가을'의 준비</b>에 달려 있습니다.
</span>
</div>
</div>
""", unsafe_allow_html=True)

    st.markdown("### 국가데이터처 공식 생애 통계 지표 (대한민국 평균 기준)")
    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("한국인 평균 흑자 진입", "28세", help="노동소득이 소비를 추월하는 연령")
    col_m2.metric("최대 흑자 정점", "45세", "연 1,932만 원")
    col_m3.metric("평균 적자 재전환", "61세", help="은퇴 후 소비가 노동소득을 다시 초과")

    st.markdown(f"""
<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-top: 14px;">
<a href="{OFFICIAL_PDF_URL}" target="_blank" style="background:#1E293B; border:1px solid #475569; border-radius:8px; padding:12px 14px; text-align:center; text-decoration:none; color:#38BDF8 !important; font-size:15px; font-weight:700; display:flex; align-items:center; justify-content:center; gap:8px;">
<span style="font-size:18px;">📄</span><span style="color:#38BDF8 !important;">2024년 국가데이터처 통계 보도자료</span>
</a>
<a href="{OFFICIAL_RELEASE_URL}" target="_blank" style="background:#1E293B; border:1px solid #475569; border-radius:8px; padding:12px 14px; text-align:center; text-decoration:none; color:#38BDF8 !important; font-size:15px; font-weight:700; display:flex; align-items:center; justify-content:center; gap:8px;">
<span style="font-size:18px;">🌐</span><span style="color:#38BDF8 !important;">국가데이터처 공식 발표 페이지</span>
</a>
</div>
""", unsafe_allow_html=True)

    _, next_col = st.columns([5, 1])
    with next_col:
        if st.button("다음 →", key="seasons_next", use_container_width=True, type="primary"):
            st.session_state["_pending_nav"] = "AI 시선"
            st.rerun()


# ==============================================================================
# 6.04.00 | Tab 4 — AI 시선 (훈계 배제 & 투명한 객관적 거울 원칙 고수)
# ==============================================================================
else:
    st.markdown("## AI 시선")
    st.markdown("AI는 평가자가 아닌, 내가 작성한 삶과 숫자를 객관적인 거울처럼 비춰주는 성찰 파트너입니다.")
    
    summary = current_financial_summary()
    sib_names = [f"{it['label']}({it.get('age',0)}세)" for it in st.session_state.get("sibling_items", []) if it.get("age", 0) > 0]
    
    person_name = st.session_state.get("person_name", "나")
    person_age = st.session_state.get("person_age", 35)
    retire_age = st.session_state.get("retirement_age", 60)
    winter_years = max(0, 88 - int(retire_age))
    child_count_str = st.session_state.get("child_count", "입력 안 함")

    q_self = active_quadrant(st.session_state.get("job_form", "직장인"))
    q_spouse = active_quadrant(st.session_state.get("job_spouse_form", ""))
    career_st = st.session_state.get("career_stage", "🌱 3년 이하 (초년생)")
    has_pipeline = (q_self in ["B", "I"]) or (q_spouse in ["B", "I"])

    family_desc = {}
    if getv("spouse_age", 0) > 0:
        family_desc["배우자"] = f"{int(getv('spouse_age'))}세"

    children_list = []
    if child_count_str in ["1명", "2명", "3명 이상"] and getv("child_age", 0) > 0:
        children_list.append(f"첫째 {int(getv('child_age'))}세")
    if child_count_str in ["2명", "3명 이상"] and getv("child_age2", 0) > 0:
        children_list.append(f"둘째 {int(getv('child_age2'))}세")
    if child_count_str == "3명 이상" and getv("child_age3", 0) > 0:
        children_list.append(f"셋째 {int(getv('child_age3'))}세")

    if children_list:
        family_desc["자녀"] = f"총 {len(children_list)}명 ({', '.join(children_list)})"
    elif child_count_str == "없음":
        family_desc["자녀"] = "자녀 없음"

    if getv("father_age", 0) > 0:
        family_desc["아버지"] = f"{int(getv('father_age'))}세"
    if getv("mother_age", 0) > 0:
        family_desc["어머니"] = f"{int(getv('mother_age'))}세"
    if sib_names:
        family_desc["형제자매"] = ", ".join(sib_names)

    details = {
        "이름/별칭": person_name,
        "나이": person_age,
        "나의 소득 형태": f"{st.session_state.get('job_form','직장인')}({q_self})",
        "현업 경력 연차": career_st,
        "배우자 소득 형태": f"{st.session_state.get('job_spouse_form','해당 없음')}({q_spouse})",
        "파이프라인 보유 여부": "보유함 (사업가 B 또는 투자자 I 포함)" if has_pipeline else "미보유 (순수 근로/자영업 E·S)",
        "월수입(정기)": f"{summary['regular_income']:,.0f}만 원",
        "연간 상여금(비정기)": f"{summary['annual_bonus']:,.0f}만 원",
        "연간 총소득": f"{summary['annual_total_income']:,.0f}만 원",
        "월평균 지출": f"{summary['expenses']:,.0f}만 원",
        "연간 순저축 여력": f"{summary['annual_net_surplus']:,.0f}만 원 (월환산 {summary['monthly_effective_surplus']:,.0f}만 원)",
        "순자산": f"{summary['net_worth']/10000:,.2f}억 원 (자산 {summary['assets']:,.0f}만 원 - 부채 {summary['debts']:,.0f}만 원)",
        "은퇴 후 예상 월연금": f"{getv('income_pension', 0):,.0f}만 원",
        "은퇴 후 월 생활비": f"{getv('retirement_monthly_expenses', 200):,.0f}만 원",
        "희망 은퇴 나이": f"{retire_age}세 (은퇴 후 겨울 약 {winter_years}년)",
        "가족 구성": family_desc if family_desc else "기본 정보만 등록됨",
        "가족 계획": {
            "결혼": st.session_state.get("marriage_plan", "미정"),
            "출산/자녀": st.session_state.get("child_plan", "미정"),
            "주거": st.session_state.get("housing_plan", "미정")
        }
    }

    if has_pipeline:
        income_instruction = f"""[소득 개선 방향 - 가구 소득 구조 및 파이프라인 관점]
본인 또는 배우자의 소득 유형 중 사업가/투자자(B/I)가 포함되어 있습니다. 다만 유형만으로 실제 사업 시스템, 투자소득, 파이프라인 또는 상당한 자산을 확보했다고 단정하지 마세요.
입력된 소득과 자산 데이터가 뒷받침하는 범위에서 노동소득과 비노동소득의 관계를 살펴보세요. 실제 파이프라인이 확인되면 그 역할과 지속 가능성을 존중하고, 확인되지 않으면 보유 여부를 추정하지 마세요.
배우자 소득이 확인되면 가구 전체의 소득 구성도 함께 고려하세요. 소득 다변화는 의무적인 처방이 아니라 현재 상황에 맞춰 검토할 수 있는 선택지로 다루세요."""
    else:
        income_instruction = f"""[소득 개선 방향 - 근로·자영업 및 소득 개선 관점]
입력된 소득 유형과 재무 데이터를 바탕으로 근로소득 또는 자영업소득에 대한 의존 정도를 살펴보세요. 소득이 노동과 시간에 얼마나 연결되어 있는지는 확인 가능한 데이터의 범위에서만 설명하세요.
현재 본업의 지속성, 소득 성장 가능성, 저축 여력과 부채 등 실제 상황에서 의미 있는 요소를 중심으로 서술하세요. 시스템이나 자산에서 발생하는 소득은 모든 사람에게 필요한 정답처럼 제시하지 말고, 여건에 따라 장기적으로 검토할 수 있는 선택지로 정중하게 다루세요."""

    # 훈계나 결론 강요를 배제한 '객관적 거울' 프롬프트
    full_prompt_text = f"""[절대 엄수 원칙]
1. 당신은 인터뷰이를 평가하거나 가르치지 않는 '정직하고 따뜻한 객관적 거울'입니다.
2. 훈계, 잔소리, 공포를 유발하는 표현, 특정 행동이나 결론의 강요를 금지합니다.
3. 자기소개, 인사말, 마크다운 가로선(---)을 쓰지 마세요.
4. [호칭 규칙]: [소득 개선 방향] 첫머리에서만 '{person_name}님,'을 사용할 수 있습니다. [은퇴 안정성]에서는 이름을 다시 부르지 마세요.
5. 경력 단계({career_st}), 순자산 및 가족 생애 정보는 입력 데이터가 실제로 뒷받침하는 범위에서만 활용하세요.
6. 입력된 사실, 수치로 계산할 수 있는 결과, 아직 확인되지 않은 가능성을 구분하세요. 계산된 예상값을 실제로 실현된 사실처럼 표현하지 마세요.
7. 데이터에 없거나 '미정', '미등록', 공란으로 표시된 정보는 임의로 추정하지 마세요. 결혼, 출산, 주택 구입, 부모 지원 등의 계획을 예정된 사실처럼 서술하지 마세요.
8. 사분면이나 경력 단계만으로 실제 소득의 성격, 파이프라인 보유 여부 또는 재무적 안정성을 단정하지 마세요.
9. 순자산이 적거나 0에 가깝더라도 이를 실패로 규정하지 마세요. 소득, 지출, 저축 여력 등 다른 지표와 함께 해석하세요.
10. 입력된 자료만으로 판단할 수 없는 사항은 단정하지 말고, 필요한 경우 확인이 필요하다고 짧게 밝혀주세요.

[인터뷰이 재무 및 생애 데이터]
{json.dumps(details, ensure_ascii=False, indent=2)}

[요청 사항]
아래 두 제목을 지정된 순서와 표기 그대로 사용하세요.
각 제목 다음 줄부터 본문을 작성하세요. 각 본문은 250~350자 내외로 하되, 분량을 채우기 위해 근거 없는 설명을 추가하지 마세요.

[소득 개선 방향]
{income_instruction}
현재 소득 구조와 재무 데이터에서 실제로 의미 있는 특징을 중심으로 서술하세요. 경력 단계, 저축 여력, 소득 성장 가능성, 가구의 소득 구성 중 근거가 있는 항목을 선택하세요. 파이프라인이나 자산소득은 필요성과 여건이 확인되는 경우에만 선택지로 제시하세요. 정중하고 담백한 존댓말을 사용하세요.

[은퇴 안정성]
반드시 '은퇴 안정성 측면에서는'으로 시작하고 이름을 부르지 마세요.
은퇴 후 월 희망 생활비와 예상 월연금의 차이를 설명하되, 입력된 값의 성격과 산출 근거가 불분명하면 안정성이 확보되었다고 단정하지 마세요. 두 금액의 단순 차액과 실제 은퇴 안정성은 구분하세요.
은퇴 후 약 {winter_years}년은 계산상 가정으로 취급하세요. 현재 경력 단계와 순자산을 연결해 설명하되, 실제 현금 보유액이나 유동성 자료가 없다면 유동성 준비 상태를 평가하지 마세요. 결혼, 자녀, 주거 계획 등 확인되지 않은 미래 사건을 전제로 삼지 말고, 정중하고 담백하게 서술하세요."""

    if st.button("⚡ AI 리포트 생성", type="primary", use_container_width=True):
        st.session_state.ai_summary = summary
        st.session_state.ai_comment = None
        
        with st.spinner("AI가 가계부와 가족 생애주기 지표를 정밀 분석 중입니다 (약 15~20초 소요)..."):
            comment, error = call_gemini_text(full_prompt_text)
            st.session_state.ai_comment = comment if comment else error

    if st.session_state.get("ai_summary") and st.session_state.get("ai_comment"):
        s = st.session_state.ai_summary
        st.markdown("### 재무제표 요약")
        cols = st.columns(4)
        cols[0].metric("월 정기수입", money(s["regular_income"]))
        cols[1].metric("월 현금지출", money(s["expenses"]))
        cols[2].metric("연간 순저축", money(s["annual_net_surplus"]), f"월환산 {money(s['monthly_effective_surplus'])}")
        cols[3].metric("순자산", fmt_eok(s["net_worth"]))

        st.markdown("### AI (Gemini) 리포트")
        comment_text = str(st.session_state.get("ai_comment", ""))
        
        cleaned_text = re.sub(r'-{3,}', '', comment_text)
        cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text.strip())
        normalized = cleaned_text.replace("\r\n", "\n").replace("\r", "\n")
        
        match_retire = re.search(r"(?im)^\s*(?:#{1,6}\s*)?(?:\*\*|__)?\s*(?:\[\s*)?은퇴\s*안정성\s*(?:\])?\s*(?:\*\*|__)?\s*:?\s*$", normalized)
        if match_retire:
            income_comment = normalized[:match_retire.start()]
            retirement_comment = normalized[match_retire.end():]
        else:
            income_comment, retirement_comment = normalized, ""

        income_comment = re.sub(r"(?i)\[\s*소득\s*개선\s*방향\s*\]", "", income_comment).strip()
        retirement_comment = re.sub(r"(?i)\[\s*은퇴\s*안정성\s*\]", "", retirement_comment).strip()

        noise_pattern = r"(?i)^.*?살펴보겠습니다[\.\!\?\s\n]*"
        income_comment = re.sub(noise_pattern, "", income_comment).strip()
        retirement_comment = re.sub(noise_pattern, "", retirement_comment).strip()

        retirement_comment = re.sub(r"^(?:.*?님[\,\s]*)+", "", retirement_comment).strip()

        def format_readable_paragraph(txt):
            sentences = re.split(r'(?<=[.!?])\s+', txt.strip())
            if len(sentences) <= 2:
                return txt.strip()
            grouped = []
            for i in range(0, len(sentences), 2):
                grouped.append(" ".join(sentences[i:i+2]))
            return "\n\n".join(grouped)

        formatted_income = format_readable_paragraph(income_comment)
        formatted_retire = format_readable_paragraph(retirement_comment)

        st.markdown("#### 소득 개선 관점 (파이프라인)")
        st.markdown(f"""
<div class='soft-card' style='white-space: pre-wrap; line-height: 1.7; word-break: keep-all;'>
{formatted_income or '분석 결과를 정리 중입니다. 다시 시도해 주세요.'}
</div>
""", unsafe_allow_html=True)

        st.markdown("#### 은퇴 안정성 관점")
        st.markdown(f"""
<div class='soft-card' style='white-space: pre-wrap; line-height: 1.7; word-break: keep-all;'>
{formatted_retire}
</div>
""", unsafe_allow_html=True)

        st.caption("※ AI의 코멘트는 참고용 거울이며, 삶의 가장 중요한 결정은 온전히 당신의 것입니다.")

        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

        # 카카오톡 전송용 통합 리포트
        sync_code = export_diagnosis_code()
        
        kakao_report_text = f"""[나침반 🧭 현실점검 & 재무 진단 리포트]
• 진단자: {person_name} ({person_age}세, {career_st})
• 소득 형태: {st.session_state.get('job_form','직장인')} (배우자: {st.session_state.get('job_spouse_form','해당 없음')})
• 재무 요약:
  - 월 정기수입: {money(s['regular_income'])}
  - 월 현금지출: {money(s['expenses'])}
  - 연간 순저축: {money(s['annual_net_surplus'])} (월평균 {money(s['monthly_effective_surplus'])})
  - 순자산: {fmt_eok(s['net_worth'])}
  - 희망 은퇴나이: {retire_age}세 (맞이할 겨울: 약 {winter_years}년)

[소득 개선 & 파이프라인]
{formatted_income}

[은퇴 안정성 성찰]
{formatted_retire}

----------------------------------------
📌 나침반 동기화 복원코드 (아래 한 줄):
{sync_code}
----------------------------------------"""

        st.markdown("### 💬 카카오톡 전송용 리포트")
        st.caption("※ 카카오톡 대화방에 바로 붙여넣기(Ctrl+V)하세요. 전달받은 분은 하단의 복원코드로 사이드바에서 0.1초 만에 동일하게 열어볼 수 있습니다.")
        
        st.code(kakao_report_text, language="markdown")

    else:
        st.info("‘AI 리포트 생성’ 버튼을 누르면 Gemini 초고속 엔진이 삶과 재무의 성찰 리포트를 생성합니다.")

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    with st.expander("📋 AI 질의용 재무제표"):
        st.markdown("<div style='font-size: 13.5px; color: #94A3B8; margin-bottom: 8px;'>프롬프트 지시문 없이, 내가 입력한 재무제표와 가족 생애 통계만 정리된 텍스트입니다. ChatGPT 등에 복사해서 자유롭게 추가 상담을 진행할 수 있습니다.</div>", unsafe_allow_html=True)
        raw_summary_report = f"""### 나침반 재무제표 및 생애주기 요약 데이터
- 성명(별칭): {person_name} (만 {person_age}세, {career_st})
- 가구 소득 형태: 나({st.session_state.get('job_form','직장인')}) + 배우자({st.session_state.get('job_spouse_form','해당 없음')})
- 월 정기 수입: {summary['regular_income']:,.0f}만 원
- 연간 비정기 상여금: {summary['annual_bonus']:,.0f}만 원
- 연간 총소득: {summary['annual_total_income']:,.0f}만 원
- 월평균 생활비 및 지출: {summary['expenses']:,.0f}만 원
- 연간 실질 순저축: {summary['annual_net_surplus']:,.0f}만 원 (월환산 {summary['monthly_effective_surplus']:,.0f}만 원)
- 자산 합계: {summary['assets']:,.0f}만 원
- 부채 잔액: {summary['debts']:,.0f}만 원
- 현재 순자산: {summary['net_worth']/10000:,.2f}억 원
- 은퇴 예정 나이: {retire_age}세 (은퇴 후 맞이할 겨울 약 {winter_years}년)
- 은퇴 후 예상 월연금: {getv('income_pension', 0):,.0f}만 원
- 은퇴 후 월 희망 생활비: {getv('retirement_monthly_expenses', 200):,.0f}만 원
- 가족 구성: {', '.join([f'{k}: {v}' for k, v in family_desc.items()]) if family_desc else '미등록'}"""
        st.code(raw_summary_report, language="markdown")
    
