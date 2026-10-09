# ==============================================================================
# [Module 1.00.00] System Core & Compassion Framework (환경 및 기초 세션 설정)
# ==============================================================================

# ------------------------------------------------------------------------------
# 1.01.00 | Global Setup & Mobile App Layout (라이브러리, 모바일 최적화 테마)
# ------------------------------------------------------------------------------
# 1.01.01 | Core Libraries & Page Config
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json
import base64

# ⚙️ 페이지 기본 설정: 신뢰감 있는 나침판(🧭) 브랜딩
st.set_page_config(
    page_title="나침판: 인생 사계절과 재무 나침반",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 1.01.02 | Mobile Standalone PWA & Warm Dignity Theme CSS
# 공포감을 주는 붉은 경고색을 배제하고, 신뢰의 딥 네이비(#0E1626)와 따뜻한 샌드 골드(#F59E0B) 적용
st.markdown("""
    <!-- 모바일 홈 화면 추가(PWA) 전용 메타 태그 -->
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <link rel="apple-touch-icon" href="https://img.icons8.com/color/512/compass--v1.png">

    <style>
    /* 1. 기본 레이아웃 여백 최적화 (모바일 터치 친화형) */
    .block-container {
        padding-top: 2.2rem !important;
        padding-bottom: 2rem !important;
        padding-left: 0.9rem !important;
        padding-right: 0.9rem !important;
    }
    
    /* 2. 폰트 및 배경: 차분하고 신뢰감 있는 딥 네이비 */
    .main {
        background-color: #0B1120;
        color: #F8FAFC;
    }
    
    /* 3. 사이드바 스타일링 */
    section[data-testid="stSidebar"] {
        background-color: #0F172A !important;
        border-right: 1px solid #1E293B !important;
    }
    section[data-testid="stSidebar"] > div:first-child {
        padding-top: 1.2rem !important;
    }
    
    /* 4. 부드러운 위로의 카드 (Compassion Card) */
    .compassion-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.8) 100%);
        border: 1px solid #334155;
        border-left: 5px solid #F59E0B;
        border-radius: 12px;
        padding: 14px 18px;
        margin-bottom: 16px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
    }
    .compassion-card h4 {
        margin: 0 0 6px 0;
        color: #FBBF24;
        font-size: 16px;
        font-weight: 700;
    }
    .compassion-card p {
        margin: 0;
        color: #CBD5E1;
        font-size: 13.5px;
        line-height: 1.6;
    }

    /* 5. 안심 버퍼 KPI 메트릭 카드 */
    .buffer-box {
        background-color: #1E293B;
        padding: 12px 14px;
        border-radius: 10px;
        border: 1px solid #334155;
        border-top: 3px solid #38BDF8;
        text-align: center;
    }
    .buffer-title {
        font-size: 12.5px;
        color: #94A3B8;
        margin-bottom: 4px;
    }
    .buffer-val {
        font-size: 22px;
        font-weight: 800;
        color: #38BDF8;
    }

    /* 6. 스트림릿 입력 폼 컨트롤 다크 톤 정돈 */
    div[data-baseweb="input"] {
        background-color: #1E293B !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
    }
    div[data-baseweb="input"] input {
        color: #FFFFFF !important;
    }
    div[data-testid="stNumberInput"] button {
        display: none !important;
    }
    </style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------------------
# 1.02.00 | Metadata & National Lifecycle Benchmark Registry
# ------------------------------------------------------------------------------
# 1.02.01 | Robert Kiyosaki ESBI Matrix Definitions
ESBI_QUADRANTS = {
    "E": {
        "name": "봉급생활자 (Employee)",
        "badge": "💼 E 사분면",
        "desc": "자신의 시간과 노동력을 급여와 1:1로 맞바꾸는 영역",
        "nature": "시간을 멈추면 수입도 즉시 멈추는 선형적 노동소득",
        "color": "#60A5FA"
    },
    "S": {
        "name": "자영업자 / 전문직 (Self-employed / Specialist)",
        "badge": "🩺 S 사분면",
        "desc": "내가 곧 시스템이 되어 나의 역량으로 수입을 창출하는 영역",
        "nature": "수입의 상한은 높으나, 쉴 수 없는 무한 책임의 고소득 노동소득",
        "color": "#34D399"
    },
    "B": {
        "name": "사업가 (Business Owner)",
        "badge": "🏢 B 사분면",
        "desc": "사람과 시스템이 스스로 가치를 창출하도록 자산을 구축한 영역",
        "nature": "초기 구축 후 내가 직접 일하지 않아도 발생하는 권리·자산소득",
        "color": "#FBBF24"
    },
    "I": {
        "name": "투자가 (Investor)",
        "badge": "📈 I 사분면",
        "desc": "돈이 돈을 벌도록 자본을 레버리지하는 영역",
        "nature": "자본 기반의 투자 소득 (자본금과 리스크 관리 역량 필수)",
        "color": "#A78BFA"
    }
}

# 1.02.02 | 대한민국 통계청 국민이전계정(생애주기 수입·소비 적자) 공공 벤치마크
# 출처: 통계청 국민이전계정 (1인당 연령별 노동소득 vs 소비지출 표준 곡선 기준 데이터)
LIFECYCLE_BENCHMARK = pd.DataFrame([
    {"age": 20, "labor_income": 45,  "consumption": 130}, # 적자 (학습/준비기)
    {"age": 25, "labor_income": 180, "consumption": 150},
    {"age": 28, "labor_income": 260, "consumption": 170}, # 흑자 진입 (골든크로스 약 27~28세)
    {"age": 35, "labor_income": 360, "consumption": 220},
    {"age": 43, "labor_income": 435, "consumption": 265}, # 소득 피크 정점 (42~44세)
    {"age": 50, "labor_income": 410, "consumption": 280},
    {"age": 55, "labor_income": 330, "consumption": 280},
    {"age": 60, "labor_income": 220, "consumption": 250}, # 적자 전환 (데드크로스 약 58~61세)
    {"age": 65, "labor_income": 120, "consumption": 230}, # 본격적 비활동기 적자 구간
    {"age": 70, "labor_income": 60,  "consumption": 210},
    {"age": 75, "labor_income": 25,  "consumption": 195},
    {"age": 80, "labor_income": 10,  "consumption": 185},
    {"age": 85, "labor_income": 5,   "consumption": 180},
])


# ------------------------------------------------------------------------------
# 1.03.00 | Client-Side Session State Orchestrator (Zero-Backend 메모리 엔진)
# ------------------------------------------------------------------------------
# 1.03.01 | Interviewee Profile & Financial State Initializer
def init_interviewee_session():
    """
    서버 DB 없이 브라우저 메모리(st.session_state)에만 독립 격리되는 인터뷰어 작업대
    """
    defaults = {
        # 1. 프로필 기본 정보
        "name": "성실한 이웃",
        "age": 38,
        "family_count": 3,
        "job_title": "제조업체 대리",
        "target_retirement_age": 60,
        
        # 2. 소득 및 현금흐름 (단위: 만원)
        "monthly_labor_income": 380,    # 본인 노동소득 (월)
        "monthly_spouse_income": 150,   # 배우자 소득 (월, 맞벌이 등)
        "monthly_asset_income": 0,      # 자산/권리소득 (월, 시스템/로열티/임대)
        
        # 3. 생활비 및 지출 구조 (단위: 만원)
        "monthly_living_cost": 280,     # 숨만 쉬어도 나가는 필수 생활비(식음료, 공과금, 교육 등)
        "monthly_debt_payment": 90,     # 대출 원리금 상환액 (주담대, 신용대출 등)
        "monthly_consumable_spend": 35, # 어차피 매달 마트/쿠팡에서 쓰는 세제, 샴푸, 영양제 등 생필품비
        
        # 4. 보유 자산 (단위: 만원)
        "liquid_emergency_cash": 1200,  # 당장 인출 가능한 비상금/예적금
        
        # 5. 사분면 자가진단 (기본: E 사분면)
        "primary_quadrant": "E",
        
        # 6. 활성 탭 인덱스
        "active_tab": 0
    }
    
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_interviewee_session()
