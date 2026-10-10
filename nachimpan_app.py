# ==============================================================================
# [Module 1.00.00] System Core & Global Config (나침판 환경 설정 및 테마 CSS)
# ==============================================================================
# 1.01.01 | Page Configurations & Libraries
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
from streamlit_option_menu import option_menu

# ⚙️ 페이지 기본 설정: 신뢰감 있는 나침판(🧭) 브랜딩
st.set_page_config(
    page_title="나침판: 라이프사이클 현실점검 & 재무 진단",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded"
)

TZ_KST = 9 # 대한민국 표준시 KST

# 1.01.02 | Mobile Web-App Capable & Warm Professional Theme CSS
st.markdown("""
    <!-- 모바일 홈 화면 추가(PWA) 시 진짜 앱처럼 실행되도록 설정 -->
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <link rel="apple-touch-icon" href="https://img.icons8.com/color/512/compass--v1.png">

    <style>
    /* 1. 기본 레이아웃 여백 최적화 (모바일 터치 및 한눈에 보기 최적화) */
    .block-container {
        padding-top: 2.2rem !important;
        padding-bottom: 2rem !important;
        padding-left: 0.9rem !important;
        padding-right: 0.9rem !important;
    }
    
    /* 2. 본문 배경: 신뢰감 있고 피로도가 낮은 차분한 딥 블랙네이비 */
    .main {
        background-color: #0B1120;
        color: #F8FAFC;
    }
    
    /* 3. 사이드바 스타일링 (인터뷰어와의 대화 공간) */
    section[data-testid="stSidebar"] {
        background-color: #0F172A !important;
        border-right: 1px solid #1E293B !important;
    }
    section[data-testid="stSidebar"] > div:first-child {
        padding-top: 1.2rem !important;
    }
    
    /* 4. 부드러운 위로의 카드 (Compassion Reassurance Card) */
    .compassion-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.8) 100%);
        border: 1px solid #334155;
        border-left: 5px solid #FBBF24;
        border-radius: 12px;
        padding: 14px 18px;
        margin-bottom: 16px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
    }
    .compassion-card h4 {
        margin: 0 0 6px 0;
        color: #FBBF24;
        font-size: 16.5px;
        font-weight: 700;
    }
    .compassion-card p {
        margin: 0;
        color: #CBD5E1;
        font-size: 14px;
        line-height: 1.6;
    }

    /* 5. 🌿 재정 안심 버퍼 (숨고르기 시간) KPI 카드 */
    .buffer-box {
        background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
        padding: 14px 16px;
        border-radius: 12px;
        border: 1.5px solid #334155;
        border-top: 5px solid #38BDF8;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    }
    .buffer-title {
        font-size: 13px;
        color: #94A3B8;
        margin-bottom: 4px;
        font-weight: 600;
    }
    .buffer-val {
        font-size: 24px;
        font-weight: 800;
        color: #38BDF8;
        letter-spacing: -0.5px;
    }
    .buffer-desc {
        font-size: 11.5px;
        color: #64748B;
        margin-top: 6px;
        line-height: 1.4;
    }

    /* 6. 스트림릿 입력 폼 다크 톤 깔끔하게 정돈 */
    div[data-baseweb="input"] {
        background-color: #1E293B !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
    }
    div[data-baseweb="input"] input {
        color: #FFFFFF !important;
        font-size: 14px !important;
    }
    div[data-testid="stNumberInput"] button {
        display: none !important;
    }
    
    /* 7. 탭 네비게이션: 여행가계부에서 검증된 은은한 회색 슬레이트 배지 형태 */
    div[data-baseweb="tab-list"] {
        gap: 8px !important;
        margin-bottom: 16px !important;
    }
    button[data-baseweb="tab"], [data-baseweb="tab"] {
        flex: 1 1 0% !important;
        height: 44px !important;
        background-color: #1E293B !important;
        border-radius: 10px !important;
        border: 1.5px solid #334155 !important;
        cursor: pointer !important;
    }
    button[data-baseweb="tab"]:hover {
        background-color: #334155 !important;
        border-color: #475569 !important;
    }
    button[data-baseweb="tab"] p, [data-baseweb="tab"] p {
        font-size: 14.5px !important;
        font-weight: 600 !important;
        color: #94A3B8 !important;
    }
    button[data-baseweb="tab"][aria-selected="true"], [aria-selected="true"] {
        background: linear-gradient(135deg, #FF9E00 0%, #EA580C 100%) !important;
        border: 1.5px solid #FFA500 !important;
        box-shadow: 0 4px 12px rgba(255, 158, 0, 0.25) !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] p, [aria-selected="true"] p {
        color: #FFFFFF !important;
        font-weight: 800 !important;
    }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 1.03.01 | Interviewee Profile & Financial State Initializer
# ==============================================================================
import random

def init_interviewee_session():
    """
    서버 DB 0회! 키패드 입력 없이 터치만으로 완성되는 익명 세션 오케스트레이터
    """
    if "starbucks_order_id" not in st.session_state:
        tag_letter = random.choice(["A", "B", "C", "D", "E"])
        tag_num = random.randint(101, 999)
        st.session_state["starbucks_order_id"] = f"#{tag_letter}-{tag_num}"

    defaults = {
        # 1. 익명 터치형 프로필
        "gender": "남성 👨",
        "age_selected": "38세",
        "marital_status": "기혼 💍",
        "children_status": "자녀 1명 👶",
        "parents_support": "독립 / 비부양",
        
        # 2. 로버트 기요사키 경제사분면
        "primary_quadrant": "💼 직장인 (E)",
        "has_side_gig": False,
        "side_quadrant": "자영업 / N잡 (S)",
        
        # 3. 소득 및 지출 흐름 (월 / 만원 단위)
        "monthly_labor_income": 350,
        "monthly_spouse_income": 150,
        "monthly_asset_income": 0,
        "monthly_living_cost": 280,
        "monthly_debt_payment": 90,
        "liquid_emergency_cash": 1200,

        # 4. 보유 자산 및 부채 (단위: 만원)
        "asset_invest": 3000,
        "asset_real_estate": 35000,
        "asset_other": 0,             # 💡 [신설] 암웨이 등 사업 파이프라인 / 기타 자산 가치
        "debt_mortgage": 15000,
        "debt_credit": 2000,
    }
    
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_interviewee_session()


# ==============================================================================
# [Module 2.00.00] Core Schema & National Benchmark Data (기초 메타데이터)
# ==============================================================================
# 2.01.01 | Robert Kiyosaki ESBI Quadrant Definitions
ESBI_QUADRANTS = {
    "E": {
        "badge": "💼 봉급생활자 (Employee)",
        "desc": "나의 시간과 가치를 1:1로 맞바꿔 급여 수입을 창출하는 영역",
        "philosophy": "성실하게 내 삶을 지켜오신 기반이며, 시간 대비 정직한 가치를 입증합니다."
    },
    "S": {
        "badge": "🩺 자영업자 / 전문직 (Self-employed)",
        "desc": "내가 곧 시스템이자 브랜드가 되어 주도적으로 가치를 창출하는 영역",
        "philosophy": "누구보다 강한 역량과 열정으로 스스로 고소득을 일구어내는 책임감의 영역입니다."
    },
    "B": {
        "badge": "🏢 사업가 (Business Owner)",
        "desc": "사람과 시스템이 유기적으로 가치를 만들어내도록 자산을 구축하는 영역",
        "philosophy": "처음에는 땀과 시간이 집중되나, 구축 후에는 일하지 않아도 흐르는 자산소득의 원천입니다."
    },
    "I": {
        "badge": "📈 투자가 (Investor)",
        "desc": "자본이 자본을 레버리지하여 스스로 일하게 만드는 영역",
        "philosophy": "지혜와 자금력을 기반으로 자산의 크기를 키우고 레버리지를 극대화하는 영역입니다."
    }
}

# 2.01.02 | 대한민국 통계청 국민이전계정 (1인당 연령별 표준 수입/지출 곡선 벤치마크)
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


# ==============================================================================
# [Module 3.00.00] Session State Orchestrator (Zero-Backend 데이터 연산 제어)
# ==============================================================================
def init_interviewee_session():
    """
    구글 시트 0회 접속! 오직 브라우저 메모리에만 상주하는 인터뷰 상담 데이터 초기화
    """
    defaults = {
        # 1. 기본 인적 사항
        "name": "성실한 이웃",
        "age": 38,
        "family_count": 3,
        "job_title": "제조업체 대리",
        "target_retirement_age": 60,
        
        # 2. 소득 흐름 (월 / 만원 단위)
        "monthly_labor_income": 380,
        "monthly_spouse_income": 150,
        "monthly_asset_income": 0,       # 연금, 배당, 시스템 소득 등 (처음엔 대부분 0)
        
        # 3. 지출 흐름 (월 / 만원 단위)
        "monthly_living_cost": 280,      # 필수 의식주, 공과금, 보육비 등 필수생활비
        "monthly_debt_payment": 90,      # 주택담보대출, 신용대출 등 매달 상환 원리금
        "monthly_consumable_spend": 35,  # 샴푸, 치약, 영양제 등 마트에서 어차피 쓸 생필품비
        
        # 4. 보유 비상금
        "liquid_emergency_cash": 1200,   # 당장 출금 가능한 예적금/현금자산
        
        # 5. 사분면 자가 진단
        "primary_quadrant": "E"
    }
    
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_interviewee_session()


# ==============================================================================
# [Module 4.00.00] Sidebar Console (터치형 익명 프로필 & 실시간 안심 버퍼 관제탑)
# ==============================================================================
with st.sidebar:
    # 💡 제목 '인터뷰 대상자 프로필' 삭제 -> 직관적인 상단 아이콘 셀렉터로 시작
    
    # 4.01.01 | 성별 선택 (아이콘 터치)
    gender_opts = ["남성 👨", "여성 👩"]
    cur_gender_idx = gender_opts.index(st.session_state.gender) if st.session_state.gender in gender_opts else 0
    st.session_state.gender = st.radio(
        "성별", gender_opts, index=cur_gender_idx, horizontal=True, label_visibility="collapsed"
    )
    
    # 4.01.02 | 연령 선택 (키패드 사절! 클릭-다운 선택창)
    age_list = [f"{a}세" for a in range(20, 76)]
    cur_age_idx = age_list.index(st.session_state.age_selected) if st.session_state.age_selected in age_list else 18
    st.session_state.age_selected = st.selectbox("연령 (나이)", age_list, index=cur_age_idx)

    # 4.01.03 | 가족 구성 (아이콘 기반 클릭 선택)
    c_fam1, c_fam2 = st.columns(2)
    with c_fam1:
        mar_opts = ["미혼 👤", "기혼 💍"]
        cur_mar_idx = mar_opts.index(st.session_state.marital_status) if st.session_state.marital_status in mar_opts else 1
        st.session_state.marital_status = st.selectbox("결혼 여부", mar_opts, index=cur_mar_idx)
    with c_fam2:
        child_opts = ["자녀 없음", "자녀 1명 👶", "자녀 2명 👧👦", "자녀 3명+ 👨‍👩‍👧‍👦"]
        cur_child_idx = child_opts.index(st.session_state.children_status) if st.session_state.children_status in child_opts else 1
        st.session_state.children_status = st.selectbox("자녀", child_opts, index=cur_child_idx)

    par_opts = ["독립 / 비부양", "부모님 부양 중 👵👴"]
    cur_par_idx = par_opts.index(st.session_state.parents_support) if st.session_state.parents_support in par_opts else 0
    st.session_state.parents_support = st.radio("부모님 부양 여부", par_opts, index=cur_par_idx, horizontal=True)

    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
    
    # 4.01.04 | 로버트 기요사키 경제사분면으로 직업 대치 (클릭 선택)
    quad_opts = ["💼 직장인 (E)", "🩺 자영업·전문직 (S)", "🏢 사업가 (B)", "📈 투자가 (I)"]
    cur_quad_idx = quad_opts.index(st.session_state.primary_quadrant) if st.session_state.primary_quadrant in quad_opts else 0
    st.session_state.primary_quadrant = st.selectbox("주 소득원 (경제사분면)", quad_opts, index=cur_quad_idx)

    # 부업 / N잡 여부 추가
    st.session_state.has_side_gig = st.checkbox("➕ 부업 / 투잡(N잡) 병행 중", value=st.session_state.has_side_gig)
    if st.session_state.has_side_gig:
        side_opts = ["자영업 / N잡 (S)", "플랫폼 / 사업 (B)", "투자 / 재테크 (I)", "시간제 알바 (E)"]
        cur_side_idx = side_opts.index(st.session_state.side_quadrant) if st.session_state.side_quadrant in side_opts else 0
        st.session_state.side_quadrant = st.selectbox("부업의 소득 성격", side_opts, index=cur_side_idx)

    st.divider()

    # 4.01.05 | 🌿 안심 버퍼 (숨고르기 시간) 실시간 연산 관제
    monthly_outgo = float(st.session_state.monthly_living_cost + st.session_state.monthly_debt_payment)
    liquid_cash = float(st.session_state.liquid_emergency_cash)
    
    if monthly_outgo > 0:
        buffer_months = liquid_cash / monthly_outgo
        if buffer_months >= 12:
            y_part = int(buffer_months // 12)
            m_part = int(round(buffer_months % 12))
            buffer_str = f"약 {y_part}년 {m_part}개월" if m_part > 0 else f"약 {y_part}년"
        else:
            buffer_str = f"약 {buffer_months:.1f}개월"
    else:
        buffer_str = "무제한 (지출 없음)"
        
    st.markdown(f"""
        <div class='buffer-box'>
            <div class='buffer-title'>🕊️ 잠시 멈춤을 보장하는 '안심 버퍼 시간'</div>
            <div class='buffer-val'>{buffer_str}</div>
            <div class='buffer-desc'>
                내일 당장 수입이 중단되어 일을 쉬더라도,<br>
                현재 보유하신 자산으로 가정이 평온하게<br>
                일상과 품위를 지켜낼 수 있는 여유 시간입니다.
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # 4.01.06 | ☕ 스타벅스 영수증 스타일의 고유 진단 번호 (제일 하단에 은은하게 배치)
    st.markdown(f"""
        <div style='text-align: center; margin-top: 15px; padding-top: 12px; border-top: 1px dashed #334155;'>
            <span style='font-size: 11px; color: #64748B;'>익명 진단 고유번호</span><br>
            <span style='font-family: monospace; font-size: 16px; font-weight: 800; color: #94A3B8; letter-spacing: 1px;'>
                {st.session_state.get('starbucks_order_id', '#A-101')}
            </span>
            <div style='font-size: 10.5px; color: #475569; margin-top: 4px; line-height: 1.4;'>
                🔒 서버에 저장되지 않는 일회성 휘발 세션입니다.
            </div>
        </div>
    """, unsafe_allow_html=True)



# ==============================================================================
# 5.00.00 | Main Navigation Tabs (Unified Segmented Tabs)
# ==============================================================================

st.markdown("""
<style>
div[data-testid="stTabs"] > div[role="tablist"] {
    background-color: #0F172A;
    padding: 6px;
    border-radius: 12px;
    border: 1px solid #334155;
    gap: 6px;
    display: flex;
    justify-content: stretch;
    margin-bottom: 20px;
}

div[data-testid="stTabs"] button[role="tab"] {
    flex: 1;
    background-color: #1E293B !important;
    color: #94A3B8 !important;
    border-radius: 8px !important;
    padding: 10px 14px !important;
    font-size: 0.95rem !important;
    font-weight: 500 !important;
    border: none !important;
    box-shadow: none !important;
    transition: all 0.2s ease-in-out !important;
    text-align: center;
}

div[data-testid="stTabs"] button[role="tab"]:hover {
    color: #F8FAFC !important;
    background-color: #334155 !important;
}

div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
    background: linear-gradient(135deg, #EA580C 0%, #C2410C 100%) !important;
    color: #FFFFFF !important;
    font-weight: 700 !important;
    box-shadow: 0 4px 12px rgba(194, 65, 12, 0.35) !important;
}

div[data-testid="stTabs"] div[role="tablist"] span {
    display: none !important;
}
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# 5.01.00 | Main Navigation Branch Point
# ==============================================================================

# 메인 탭은 이 위치에서 단 한 번만 생성한다.
# 각 탭 내부의 with tab1:, with tab2: 등은 기존 코드를 그대로 사용한다.

# ==============================================================================
# 5.01.01 | Four Main Tabs
# ==============================================================================

tab1, tab2, tab3, tab4 = st.tabs([
    "우리집 가계부",
    "삶과 시간",
    "인생의 사계절",
    "나침판의 제안"
])

# ==============================================================================
# 5.01.02 | Navigation Initialization Complete
# ==============================================================================

# 중복 st.tabs() 선언 금지.
# 다음 블록부터 기존 Module 6.00.00 코드를 실행한다.


# ==============================================================================
# [Module 6.00.00] 4-Step Interactive Tabs (메인 인터뷰 4대 캔버스)
# ==============================================================================

# ==============================================================================
# 6.01.00 | Tab 1: 나의 현재 좌표 (ESBI 사분면, 손익계산서 & 대차대조표)
# ==============================================================================
with tab1:
    # --------------------------------------------------------------------------
    # 6.01.01 | 오프닝 위로의 카드
    # --------------------------------------------------------------------------
    st.markdown("### 💼 나의 현재 수입 구조와 재무 현황")
    
    st.markdown("""
        <div class='compassion-card'>
            <h4>⚖️ 그동안 참 성실하고 치열하게 삶을 가꾸어 오셨습니다.</h4>
            <p>
                매달 가정을 지키기 위해 쏟아붓는 땀과 에너지는 과연 어떤 성격의 소득일까요? 
                나의 주 소득원이 머무는 사분면을 응시하고, 매달 들어오고 나가는 현금의 흐름과 순자산을 거울 보듯 조용히 마주해보는 시간입니다.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # --------------------------------------------------------------------------
    # 6.01.02 | 로버트 기요사키 2×2 십자 좌표계 (Cashflow Quadrant Matrix)
    # --------------------------------------------------------------------------
    st.markdown("#### 🧭 나의 에너지가 머무는 소득 사분면 (ESBI)")

    def get_quad_box_html(q_code, title, core_phrase, sub_desc):
        is_primary = (q_code in st.session_state.primary_quadrant)
        is_side = (st.session_state.has_side_gig and q_code in st.session_state.side_quadrant)
        
        if is_primary:
            border_css = "border: 2px solid #F59E0B; background: rgba(245, 158, 11, 0.16); box-shadow: 0 4px 14px rgba(245, 158, 11, 0.25);"
            tag_badge = "<span style='background:#F59E0B; color:#0B1120; font-size:10.5px; font-weight:800; padding:2px 7px; border-radius:4px;'>🌟 주 소득원</span>"
        elif is_side:
            border_css = "border: 2px dashed #38BDF8; background: rgba(56, 189, 248, 0.12); box-shadow: 0 4px 14px rgba(56, 189, 248, 0.15);"
            tag_badge = "<span style='background:#38BDF8; color:#0B1120; font-size:10.5px; font-weight:800; padding:2px 7px; border-radius:4px;'>➕ 부업 / N잡</span>"
        else:
            border_css = "border: 1px solid #334155; background: rgba(30, 41, 59, 0.45); opacity: 0.7;"
            tag_badge = "<span style='visibility:hidden; font-size:10.5px;'>빈칸</span>"

        return f"""
            <div style='{border_css} border-radius: 12px; padding: 14px 16px; min-height: 120px; transition: all 0.2s;'>
                <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom: 6px;'>
                    <span style='font-size: 20px; font-weight: 900; color: #F8FAFC; font-family: serif, sans-serif;'>{q_code}</span>
                    {tag_badge}
                </div>
                <div style='font-size: 14px; font-weight: bold; color: #E2E8F0; margin-bottom: 3px;'>{title}</div>
                <div style='font-size: 12px; font-weight: 600; color: #FBBF24; margin-bottom: 4px;'>"{core_phrase}"</div>
                <div style='font-size: 11px; color: #94A3B8; line-height: 1.4;'>{sub_desc}</div>
            </div>
        """

    # Row 1: 좌측 상단 [S 자영업]  |  우측 상단 [B 사업가]
    r1_col1, r1_col2 = st.columns(2, gap="medium")
    with r1_col1:
        st.markdown(get_quad_box_html(
            "S", "자영업자 / 전문직", 
            "일자리를 소유하고 있다", 
            "내가 곧 시스템. 일할 때 고소득이나 내가 멈추면 수입도 멈춤"
        ), unsafe_allow_html=True)
    with r1_col2:
        st.markdown(get_quad_box_html(
            "B", "사업가 (자산소유)", 
            "시스템을 소유하고 있다", 
            "나를 위해 일하는 시스템과 자산이 있어 시간과 소득이 분리됨"
        ), unsafe_allow_html=True)

    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)

    # Row 2: 좌측 하단 [E 직장인]  |  우측 하단 [I 투자가]
    r2_col1, r2_col2 = st.columns(2, gap="medium")
    with r2_col1:
        st.markdown(get_quad_box_html(
            "E", "직장인 / 봉급생활자", 
            "직장에 다닌다", 
            "나의 시간과 체력을 급여와 1:1로 정직하게 맞바꾸는 영역"
        ), unsafe_allow_html=True)
    with r2_col2:
        st.markdown(get_quad_box_html(
            "I", "투자가", 
            "돈이 당신을 위해 일한다", 
            "돈이 돈을 벌도록 자본을 레버리지하는 영역"
        ), unsafe_allow_html=True)

    st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
    st.divider()

    # --------------------------------------------------------------------------
    # 6.01.03 | 슬라이더 전용 CSS (두께 강화 & 둥둥 떠다니는 붉은 텍스트 완전 숨김)
    # --------------------------------------------------------------------------
    st.markdown("""
        <style>
        /* 1. 슬라이더 트랙 두께 도톰하게 확대 */
        div[data-testid="stSelectSlider"] div[data-baseweb="slider"] > div:first-child,
        div[data-testid="stSlider"] div[data-baseweb="slider"] > div:first-child {
            height: 18px !important;
            border-radius: 9px !important;
            background-color: #1E293B !important;
            border: 1px solid #334155 !important;
        }
        div[data-testid="stSelectSlider"] div[data-baseweb="slider"] > div:first-child > div,
        div[data-testid="stSlider"] div[data-baseweb="slider"] > div:first-child > div {
            height: 18px !important;
            border-radius: 9px !important;
            background: linear-gradient(90deg, #F59E0B 0%, #EA580C 100%) !important;
        }
        /* 2. 손잡이(Thumb) */
        div[data-testid="stSelectSlider"] div[role="slider"],
        div[data-testid="stSlider"] div[role="slider"] {
            height: 24px !important;
            width: 24px !important;
            top: -3px !important;
            background-color: #F59E0B !important;
            border: 2px solid #FFFFFF !important;
            box-shadow: 0 2px 6px rgba(0,0,0,0.5) !important;
        }
        /* 💡 3. [핵심] 슬라이더 위에 둥둥 떠서 시야를 어지럽히던 붉은색 글씨 숨김 (우측 네모칸과 100% 일치) */
        div[data-testid="stThumbValue"] {
            display: none !important;
        }
        div[data-baseweb="slider"] [role="slider"] > div {
            display: none !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # --------------------------------------------------------------------------
    # 6.01.04 | 로그 스케일 비선형 눈금 옵션 레지스트리
    # --------------------------------------------------------------------------
    # 💡 월수입/월지출: 300~500만 원이 정확히 중앙에 오는 0~2,000만 원 로그 눈금
    MONTHLY_FLOW_OPTIONS = [
        0, 50, 100, 150, 200, 250, 300, 350, 400, 450, 500, 
        600, 700, 800, 1000, 1200, 1500, 2000
    ]

    # 💡 자산/부채: 1천만 원 자석 스텝 + 현실적 중심 구간 반영 로그 눈금
    CASH_OPTIONS = [
        0, 500, 1000, 2000, 3000, 5000, 7000, 10000, 15000, 20000, 30000, 50000, 70000, 100000
    ] # 비상금/예적금: 최대 10억
    
    INVEST_OPTIONS = [
        0, 500, 1000, 2000, 3000, 5000, 7000, 10000, 15000, 20000, 30000, 50000, 70000, 100000
    ] # 주식/금융: 최대 10억
    
    REALESTATE_OPTIONS = [
        0, 5000, 10000, 20000, 30000, 40000, 50000, 60000, 70000, 80000, 100000, 150000, 200000, 300000, 500000, 1000000
    ] # 부동산 시세: 최대 100억 (4억~10억이 중앙)
    
    MORTGAGE_OPTIONS = [
        0, 2000, 5000, 7000, 10000, 15000, 20000, 25000, 30000, 40000, 50000, 70000, 100000
    ] # 주담대 원금: 최대 10억 (1.5억~3억이 중앙)
    
    CREDIT_OPTIONS = [
        0, 500, 1000, 1500, 2000, 2500, 3000, 4000, 5000, 6000, 7000, 8000, 10000
    ] # 신용대출/마통: 최대 1억 (2000~3000만이 중앙)

    # 💡 만 원 단위 숫자를 "1.5억", "10억" 형태로 품격 있게 포맷팅하는 함수
    def fmt_money_kr(v):
        if v == 0: return "0원"
        if v >= 10000:
            eok = v // 10000
            rem = v % 10000
            if rem == 0:
                return f"{eok}억 원"
            else:
                return f"{v/10000:.1f}억 원"
        return f"{v:,.0f}만 원"

    # --------------------------------------------------------------------------
    # 6.01.05 | 슬라이더 ↔ 네모칸 완전 종속 양방향 동기화 컨트롤러
    # --------------------------------------------------------------------------
    def _sync_from_slider(key):
        val = st.session_state[f"sld_{key}"]
        st.session_state[f"num_{key}"] = val
        st.session_state[key] = val

    def _sync_from_num(key, options):
        val = st.session_state[f"num_{key}"]
        st.session_state[key] = val
        # 직접 입력한 숫자와 가장 가까운 슬라이더 눈금 위치로 자석 이동
        nearest = min(options, key=lambda x: abs(x - val))
        st.session_state[f"sld_{key}"] = nearest

    def render_log_input(label_text, key_name, options, default_v=0, max_limit=2000):
        if key_name not in st.session_state:
            st.session_state[key_name] = default_v
        cur_val = int(st.session_state[key_name])
        
        nearest_opt = min(options, key=lambda x: abs(x - cur_val))
        if f"sld_{key_name}" not in st.session_state:
            st.session_state[f"sld_{key_name}"] = nearest_opt
        if f"num_{key_name}" not in st.session_state:
            st.session_state[f"num_{key_name}"] = cur_val

        st.markdown(f"<div style='font-size:13.5px; font-weight:600; color:#E2E8F0; margin-bottom:2px;'>{label_text}</div>", unsafe_allow_html=True)
        col_slider, col_box = st.columns([3.1, 1.3], gap="small")
        
        with col_slider:
            st.select_slider(
                label=label_text,
                options=options,
                format_func=fmt_money_kr,
                key=f"sld_{key_name}",
                on_change=_sync_from_slider,
                args=(key_name,),
                label_visibility="collapsed"
            )
        with col_box:
            st.number_input(
                label=f"{label_text}_빈칸",
                min_value=0,
                max_value=max_limit,
                step=1,
                key=f"num_{key_name}",
                on_change=_sync_from_num,
                args=(key_name, options),
                label_visibility="collapsed"
            )

    # --------------------------------------------------------------------------
    # 6.01.06 | 손익계산서: 월수입 vs 월지출 (300~500만 원 정중앙 로그 스케일)
    # --------------------------------------------------------------------------
    c_in, c_out = st.columns([1, 1], gap="large")
    
    with c_in:
        st.markdown("#### 📥 월수입")
        render_log_input("1. 본인 월 소득 (급여 / 사업소득)", "monthly_labor_income", MONTHLY_FLOW_OPTIONS, default_v=350, max_limit=2000)
        render_log_input("2. 배우자 월 소득 (맞벌이 등)", "monthly_spouse_income", MONTHLY_FLOW_OPTIONS, default_v=150, max_limit=2000)
        render_log_input("3. 일하지 않아도 나오는 소득 (연금/배당/임대)", "monthly_asset_income", MONTHLY_FLOW_OPTIONS, default_v=0, max_limit=2000)

    with c_out:
        st.markdown("#### 📤 월지출")
        render_log_input("1. 필수 생활비 (식비, 공과금, 보육/교육비)", "monthly_living_cost", MONTHLY_FLOW_OPTIONS, default_v=280, max_limit=2000)
        render_log_input("2. 대출 원리금 상환액 (주담대, 신용대출 등)", "monthly_debt_payment", MONTHLY_FLOW_OPTIONS, default_v=90, max_limit=2000)
        st.markdown("<div style='height: 48px;'></div>", unsafe_allow_html=True)

    total_income = st.session_state.monthly_labor_income + st.session_state.monthly_spouse_income + st.session_state.monthly_asset_income
    total_expense = st.session_state.monthly_living_cost + st.session_state.monthly_debt_payment

    # [수평 높이 100% 일치] 월수입 합계 vs 고정지출 합계
    st.markdown("<div style='margin-top:6px;'></div>", unsafe_allow_html=True)
    c_sum_in, c_sum_out = st.columns([1, 1], gap="large")
    
    with c_sum_in:
        st.markdown(f"""
            <div style='background:rgba(30, 41, 59, 0.6); padding:12px 16px; border-radius:10px; border:1px solid #334155; min-height:54px; display:flex; align-items:center; justify-content:space-between;'>
                <span style='font-size:13.5px; color:#94A3B8; font-weight:600;'>가정 총 월수입 합계:</span> 
                <b style='font-size:19px; color:#38BDF8;'>{total_income:,.0f}만 원</b>
            </div>
        """, unsafe_allow_html=True)

    with c_sum_out:
        st.markdown(f"""
            <div style='background:rgba(30, 41, 59, 0.6); padding:12px 16px; border-radius:10px; border:1px solid #334155; min-height:54px; display:flex; align-items:center; justify-content:space-between;'>
                <span style='font-size:13.5px; color:#94A3B8; font-weight:600;'>매달 빠져나가는 고정지출 합계:</span> 
                <b style='font-size:19px; color:#F87171;'>{total_expense:,.0f}만 원</b>
            </div>
        """, unsafe_allow_html=True)

    monthly_surplus = total_income - total_expense
    surplus_color = "#34D399" if monthly_surplus >= 0 else "#F87171"
    surplus_text = f"+{monthly_surplus:,.0f}만 원 (흑자 흐름)" if monthly_surplus >= 0 else f"{monthly_surplus:,.0f}만 원 (적자 흐름)"
    
    st.markdown(f"""
        <div style='background:linear-gradient(135deg, #1E293B 0%, #0F172A 100%); border:1.5px solid #334155; border-radius:12px; padding:14px 20px; text-align:center; margin-top:14px;'>
            <span style='font-size:13.5px; color:#94A3B8; font-weight:600;'>매달 가계에 남는 순수 여유 자금 (월 현금흐름 밸런스)</span>
            <div style='font-size:24px; font-weight:800; color:{surplus_color}; margin-top:2px;'>{surplus_text}</div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top:25px;'></div>", unsafe_allow_html=True)
    st.divider()

# ==============================================================================
# 6.01.07 | 대차대조표: 보유 자산 vs 보유 부채 (기타 자산 / 사업 파이프라인 신설)
# ==============================================================================
    st.markdown("#### 🏛️ 가계 자산 및 부채 현황 (대차대조표)")

    c_asset, c_debt = st.columns([1, 1], gap="large")

    with c_asset:
        st.markdown("##### 🏦 보유 자산 (Assets)")
        render_log_input("1. 비상 현금 / 예·적금 (최대 10억)", "liquid_emergency_cash", CASH_OPTIONS, default_v=1200, max_limit=100000)
        render_log_input("2. 주식 / 채권 / 펀드 (최대 10억)", "asset_invest", INVEST_OPTIONS, default_v=3000, max_limit=100000)
        render_log_input("3. 부동산 / 주택 시세 (최대 100억)", "asset_real_estate", REALESTATE_OPTIONS, default_v=35000, max_limit=1000000)
        # 💡 [신설] 암웨이 사업소득 등 지속적 로열티/자산 가치 입력 항목
        render_log_input("4. 기타 자산 / 사업·파이프라인 가치 (최대 100억)", "asset_other", REALESTATE_OPTIONS, default_v=0, max_limit=1000000)

    with c_debt:
        st.markdown("##### 💳 보유 부채 (Liabilities)")
        render_log_input("1. 주택담보대출 / 전세대출 원금 (최대 10억)", "debt_mortgage", MORTGAGE_OPTIONS, default_v=15000, max_limit=100000)
        render_log_input("2. 신용대출 / 마이너스통장 (최대 1억)", "debt_credit", CREDIT_OPTIONS, default_v=2000, max_limit=10000)
        # 좌우 대칭 높이 맞춤 여백
        st.markdown("<div style='height: 120px;'></div>", unsafe_allow_html=True)

    # 💡 총자산 합계에 asset_other(기타 자산 / 사업 파이프라인) 완벽 합산
    total_assets = (
        st.session_state.get('liquid_emergency_cash', 0) +
        st.session_state.get('asset_invest', 0) +
        st.session_state.get('asset_real_estate', 0) +
        st.session_state.get('asset_other', 0)
    )
    total_debts = (
        st.session_state.get('debt_mortgage', 0) +
        st.session_state.get('debt_credit', 0)
    )
    net_worth = total_assets - total_debts

    # [수평 높이 100% 일치] 총자산 합계 vs 총부채 합계
    st.markdown("<div style='margin-top:6px;'></div>", unsafe_allow_html=True)
    c_sum_ast, c_sum_dbt = st.columns([1, 1], gap="large")

    with c_sum_ast:
        st.markdown(f"""
            <div style='background:rgba(30, 41, 59, 0.6); padding:12px 16px; border-radius:10px; border:1px solid #334155; min-height:54px; display:flex; align-items:center; justify-content:space-between;'>
                <span style='font-size:13.5px; color:#94A3B8; font-weight:600;'>가계 총자산 합계:</span> 
                <b style='font-size:19px; color:#38BDF8;'>{total_assets:,.0f}만 원 ({fmt_money_kr(total_assets)})</b>
            </div>
        """, unsafe_allow_html=True)

    with c_sum_dbt:
        st.markdown(f"""
            <div style='background:rgba(30, 41, 59, 0.6); padding:12px 16px; border-radius:10px; border:1px solid #334155; min-height:54px; display:flex; align-items:center; justify-content:space-between;'>
                <span style='font-size:13.5px; color:#94A3B8; font-weight:600;'>가계 총부채 합계:</span> 
                <b style='font-size:19px; color:#F87171;'>{total_debts:,.0f}만 원 ({fmt_money_kr(total_debts)})</b>
            </div>
        """, unsafe_allow_html=True)

    # --------------------------------------------------------------------------
    # 6.01.08 | 💎 가계 순자산(Net Worth) 종합 평가 카드
    # --------------------------------------------------------------------------
    net_color = "#38BDF8" if net_worth >= 0 else "#F87171"
    debt_ratio = (total_debts / total_assets * 100) if total_assets > 0 else 0
    
    st.markdown(f"""
        <div style='background:linear-gradient(135deg, #1E293B 0%, #0F172A 100%); border:2px solid #F59E0B; border-radius:12px; padding:18px 24px; text-align:center; margin-top:16px; box-shadow:0 4px 16px rgba(245, 158, 11, 0.2);'>
            <span style='font-size:14px; color:#FBBF24; font-weight:700;'>💎 빚을 제외한 가계 진짜 순자산 (Net Worth)</span>
            <div style='font-size:28px; font-weight:900; color:{net_color}; margin-top:4px;'>{net_worth:,.0f}만 원 ({fmt_money_kr(net_worth)})</div>
            <div style='font-size:12.5px; color:#94A3B8; margin-top:6px;'>
                총자산 대비 부채 비율: <b style='color:#F87171;'>{debt_ratio:.1f}%</b> | 
                겉보기 자산이 아닌, <b>부채를 덜어낸 진짜 순수 자산</b>을 응시할 때 진짜 재무 나침반이 작동합니다.
            </div>
        </div>
    """, unsafe_allow_html=True)


    # ==============================================================================
    # 6.01.09 | Current Net Worth Review Complete
    # ==============================================================================

    # 탭 1에서는 현재 시점의 자산·부채·순자산만 확인한다.
    # 미래 순자산 시뮬레이션과 은퇴 후 생활비 계산은 탭 3에서 다룬다.
    st.caption(
        "현재의 재무 현황을 확인했습니다. "
        "미래의 은퇴 시점과 생활비 시나리오는 "
        "‘인생의 사계절’ 탭에서 별도로 살펴볼 수 있습니다."
    )


# ==============================================================================
# 6.02.00 | Tab 2: 삶과 시간 (시간의 물리적 한계 & 물통과 파이프라인)
# ==============================================================================
with tab2:
    st.markdown("### ⏳ 내 삶의 시간표와 소득의 교환 가치")
    
    st.markdown("""
        <div class='compassion-card'>
            <h4>⚖️ 시간은 누구에게나 하루 24시간 공평하게 주어집니다.</h4>
            <p>
                지금까지 가족을 위해, 그리고 나 자신을 위해 쉼 없이 달려온 시간의 발자취를 존중합니다. 
                이 탭에서는 내가 하루 중 일과 맞바꾸고 있는 소중한 시간의 실질적인 가치를 살펴보고, 
                '더 많은 시간 일하는 것(Hard Work)' 너머에 존재하는 '지혜로운 파이프라인의 가치'를 조용히 응시해 봅니다.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # --------------------------------------------------------------------------
    # 6.02.01 | 주당 노동 시간 입력 및 실질 시급 산출 (키패드 0%)
    # --------------------------------------------------------------------------
    st.markdown("#### ⏱️ 내가 일과 맞바꾸는 시간 (주당 기준)")
    
    c_time1, c_time2 = st.columns(2, gap="large")
    
    with c_time1:
        if "weekly_work_hours" not in st.session_state:
            st.session_state.weekly_work_hours = 40
            
        st.session_state.weekly_work_hours = st.slider(
            "1. 주당 순수 근무 시간 (정규직 40시간 기준 / 야근, 특근 포함)",
            min_value=10, max_value=80, value=int(st.session_state.weekly_work_hours), step=5, format="%d시간/주"
        )
        st.caption(f"💡 평일 하루 평균 약 {st.session_state.weekly_work_hours / 5:.1f}시간 집중 노동")

    with c_time2:
        if "weekly_commute_hours" not in st.session_state:
            st.session_state.weekly_commute_hours = 10
            
        st.session_state.weekly_commute_hours = st.slider(
            "2. 주당 출퇴근 및 일 준비/대기 시간 (왕복 이동, 주말 업무 대기 등)",
            min_value=0, max_value=30, value=int(st.session_state.weekly_commute_hours), step=2, format="%d시간/주"
        )
        st.caption("💡 이동 시간과 준비 시간도 사실상 일터에 구속된 내 소중한 생명 시간입니다.")

    # 실질 시간 연산 (한 달 = 4.33주 기준)
    total_weekly_hours = st.session_state.weekly_work_hours + st.session_state.weekly_commute_hours
    monthly_dedicated_hours = total_weekly_hours * 4.33
    
    # 내 노동소득 기준 실질 시급 계산
    my_income_won = float(st.session_state.monthly_labor_income * 10000)
    real_hourly_wage = (my_income_won / monthly_dedicated_hours) if monthly_dedicated_hours > 0 else 0
    
    # 깨어 있는 시간(하루 16시간, 월 480시간) 중 일에 바치는 비중
    monthly_awake_hours = 16 * 30 # 약 480시간
    life_labor_ratio = (monthly_dedicated_hours / monthly_awake_hours * 100) if monthly_awake_hours > 0 else 0

    st.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)

    # 시간 지표 3분할 팩트 카드
    c_w1, c_w2, c_w3 = st.columns(3)
    with c_w1:
        st.markdown(f"""
            <div style='background:#1E293B; border:1px solid #334155; border-radius:10px; padding:14px; text-align:center;'>
                <div style='font-size:12px; color:#94A3B8;'>월간 일터 구속 시간</div>
                <div style='font-size:22px; font-weight:800; color:#38BDF8; margin-top:3px;'>약 {monthly_dedicated_hours:.0f}시간</div>
                <div style='font-size:11px; color:#64748B; margin-top:3px;'>근무 {st.session_state.weekly_work_hours*4.33:.0f}h + 출퇴근 {st.session_state.weekly_commute_hours*4.33:.0f}h</div>
            </div>
        """, unsafe_allow_html=True)

    with c_w2:
        st.markdown(f"""
            <div style='background:#1E293B; border:1.5px solid #F59E0B; border-radius:10px; padding:14px; text-align:center;'>
                <div style='font-size:12px; color:#FBBF24;'>내 청춘 1시간의 '실질 시급'</div>
                <div style='font-size:22px; font-weight:900; color:#FBBF24; margin-top:3px;'>{real_hourly_wage:,.0f}원</div>
                <div style='font-size:11px; color:#94A3B8; margin-top:3px;'>월 소득 ÷ 일에 바친 총 시간</div>
            </div>
        """, unsafe_allow_html=True)

    with c_w3:
        st.markdown(f"""
            <div style='background:#1E293B; border:1px solid #334155; border-radius:10px; padding:14px; text-align:center;'>
                <div style='font-size:12px; color:#94A3B8;'>깨어 있는 삶의 일터 점유율</div>
                <div style='font-size:22px; font-weight:800; color:#F87171; margin-top:3px;'>{life_labor_ratio:.1f}%</div>
                <div style='font-size:11px; color:#64748B; margin-top:3px;'>수면 외 온전한 삶의 절반 가까이</div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top:25px;'></div>", unsafe_allow_html=True)
    st.divider()

# ==============================================================================
# 6.02.02 | 🛑 '잠시 멈춤' 시뮬레이션 (스위치 우측 배치 레이아웃)
# ==============================================================================
    st.markdown("#### 🛑 만약 내일 당장 노동을 멈춘다면? (수입 셧다운 시뮬레이션)")
    
    # 💡 텍스트는 좌측에 넓게 배치하고, 토글 스위치를 우측 끝에 직관적으로 배치
    c_tog_txt, c_tog_btn = st.columns([4.2, 1], gap="small")
    with c_tog_txt:
        st.markdown(
            "<div style='font-size:14.5px; font-weight:700; color:#F8FAFC; padding-top:6px;'>"
            "👉 '내일 아침 출근을 잠시 멈추고 1년간 푹 쉰다면?' 시뮬레이션 가동"
            "</div>", 
            unsafe_allow_html=True
        )
    with c_tog_btn:
        stop_simulation = st.toggle("시뮬레이션 가동 스위치", value=False, label_visibility="collapsed")
    
    monthly_fixed_outgo = float(st.session_state.monthly_living_cost + st.session_state.monthly_debt_payment)
    normal_income = float(st.session_state.monthly_labor_income + st.session_state.monthly_spouse_income + st.session_state.monthly_asset_income)
    
    if stop_simulation:
        # 노동 중단 시: 본인 노동소득 0원 소멸! (배우자 소득 + 자산 소득만 잔존)
        stopped_income = float(st.session_state.monthly_spouse_income + st.session_state.monthly_asset_income)
        stopped_deficit = stopped_income - monthly_fixed_outgo
        
        c_sim1, c_sim2 = st.columns(2, gap="large")
        with c_sim1:
            st.markdown(f"""
                <div style='background:rgba(239, 68, 68, 0.12); border:1.5px solid #EF4444; border-radius:12px; padding:16px; text-align:center;'>
                    <div style='font-size:13px; color:#FCA5A5;'>🛑 노동 중단 시 월 수입</div>
                    <div style='font-size:24px; font-weight:900; color:#EF4444; margin-top:4px;'>{stopped_income:,.0f}만 원</div>
                    <div style='font-size:11.5px; color:#94A3B8; margin-top:6px;'>
                        본인의 노동소득({st.session_state.monthly_labor_income}만 원)이 즉시 <b>0원으로 소멸</b>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
        with c_sim2:
            st.markdown(f"""
                <div style='background:rgba(239, 68, 68, 0.12); border:1.5px solid #EF4444; border-radius:12px; padding:16px; text-align:center;'>
                    <div style='font-size:13px; color:#FCA5A5;'>💸 멈추지 않는 매달 고정 지출</div>
                    <div style='font-size:24px; font-weight:900; color:#F87171; margin-top:4px;'>{monthly_fixed_outgo:,.0f}만 원</div>
                    <div style='font-size:11.5px; color:#94A3B8; margin-top:6px;'>
                        생활비와 대출이자는 내가 쉬어도 <b>단 1원도 멈추지 않고 청구됨</b>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
        st.markdown(f"""
            <div style='background:rgba(15, 23, 42, 0.8); border:1px dashed #EF4444; border-radius:10px; padding:12px 16px; margin-top:14px; text-align:center;'>
                <span style='font-size:13px; color:#E2E8F0;'>
                    매달 발생하는 순수 현금 적자: <b style='color:#EF4444; font-size:16px;'>{stopped_deficit:,.0f}만 원</b> | 
                    보유 비상금({st.session_state.liquid_emergency_cash:,.0f}만 원) 기준 <b>안심 버퍼 소진 시간: <span style='color:#FBBF24;'>{st.session_state.liquid_emergency_cash / monthly_fixed_outgo:.1f}개월</span></b>
                </span>
            </div>
        """, unsafe_allow_html=True)
        
    else:
        st.caption("💡 위 토글 스위치를 켜보시면, 노동이 멈추었을 때 가계 현금흐름이 마주하는 실제 변화를 체감하실 수 있습니다.")

    st.markdown("<div style='margin-top:25px;'></div>", unsafe_allow_html=True)
    st.divider()

    # --------------------------------------------------------------------------
    # 6.02.03 | 물통을 나르는 삶 vs 파이프라인을 묻는 삶 (인포그래픽 대비)
    # --------------------------------------------------------------------------
    st.markdown("#### 🚰 물통을 나르는 삶 vs 파이프라인을 구축하는 삶")
    
    col_pipe1, col_pipe2 = st.columns(2, gap="large")
    
    with col_pipe1:
        st.markdown("""
            <div style='background:rgba(30, 41, 59, 0.5); border:1.5px solid #475569; border-radius:12px; padding:16px 18px; min-height:220px;'>
                <div style='display:flex; justify-content:space-between; align-items:center;'>
                    <b style='font-size:16px; color:#E2E8F0;'>🪣 물통을 나르는 삶 (E / S 사분면)</b>
                    <span style='background:#475569; color:#FFFFFF; font-size:10px; font-weight:800; padding:2px 6px; border-radius:4px;'>레버리지 = 1.0</span>
                </div>
                <div style='font-size:12.5px; color:#94A3B8; margin-top:10px; line-height:1.6;'>
                    • <b>방식</b>: 물이 필요할 때마다 직접 산 너머 우물로 걸어가 물통을 져 나름<br>
                    • <b>한계</b>: 물통의 크기(월급)를 키울 수는 있지만, 몸이 아프거나 늙어서 발걸음을 멈추는 날 물 공급도 즉시 멈춤<br>
                    • <b>비극</b>: 평생 물통의 무게를 짊어지느라 가족과의 저녁과 자유를 반납해야 함
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col_pipe2:
        st.markdown("""
            <div style='background:rgba(245, 158, 11, 0.08); border:2px solid #F59E0B; border-radius:12px; padding:16px 18px; min-height:220px;'>
                <div style='display:flex; justify-content:space-between; align-items:center;'>
                    <b style='font-size:16px; color:#FBBF24;'>🚰 파이프라인을 묻는 삶 (B / I 사분면)</b>
                    <span style='background:#F59E0B; color:#0B1120; font-size:10px; font-weight:800; padding:2px 6px; border-radius:4px;'>레버리지 = N배 무한대</span>
                </div>
                <div style='font-size:12.5px; color:#E2E8F0; margin-top:10px; line-height:1.6;'>
                    • <b>방식</b>: 낮에는 물통을 나르더라도, 남는 자투리 시간에 마을로 이어지는 수도관(파이프)을 묻음<br>
                    • <b>열매</b>: 파이프라인이 완공되는 날, 수도꼭지만 틀면 내가 잠잘 때도, 아플 때도 맑은 물이 스스로 흘러들어옴<br>
                    • <b>가치</b>: 진정한 시간의 자유를 되찾고, 대물림되는 평온한 자산의 주인이 됨
                </div>
            </div>
        """, unsafe_allow_html=True)

    # --------------------------------------------------------------------------
    # 6.02.04 | 두 번째 탭의 핵심 깨달음 요약 카드 (Awakening Card)
    # --------------------------------------------------------------------------
    st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
    st.markdown("""
        <div style='background:linear-gradient(135deg, #1E293B 0%, #0F172A 100%); border:1.5px solid #38BDF8; border-radius:12px; padding:18px 22px; text-align:center;'>
            <div style='font-size:15px; font-weight:700; color:#38BDF8;'>💡 나침판이 전하는 결정적 자각</div>
            <div style='font-size:18px; font-weight:800; color:#FFFFFF; margin-top:6px;'>
                "문제는 수입의 '크기'가 아니라, 수입의 <b>'종류(어떻게 버는가)'</b>였습니다."
            </div>
            <div style='font-size:13px; color:#94A3B8; margin-top:8px; line-height:1.6;'>
                몸을 더 혹사시켜 더 큰 물통을 지는 것(Hard Work)은 유한한 인생의 영원한 해답이 될 수 없습니다.<br>
                지금 내 삶에는, 내가 쉬거나 아플 때도 <b>마르지 않고 물을 대줄 나만의 파이프라인</b>이 단 하나라도 준비되어 있습니까?
            </div>
        </div>
    """, unsafe_allow_html=True)

# ==============================================================================
# 6.03.00 | Tab 3: 인생의 사계절 (통계청 팩트 기반 생애 곡선)
# ==============================================================================
with tab3:
    import re
    import plotly.graph_objects as go

    # --------------------------------------------------------------------------
    # 6.03.01 | 인터뷰이 나이 파싱 및 사이드바 동기화 (첨부 2 완벽 연동)
    # --------------------------------------------------------------------------
    raw_age_val = st.session_state.get('user_age', "38세")
    if isinstance(raw_age_val, str):
        extracted_num = re.findall(r'\d+', raw_age_val)
        curr_age = int(extracted_num[0]) if extracted_num else 38
    else:
        curr_age = int(raw_age_val)

    # --------------------------------------------------------------------------
    # 6.03.02 | 상단 철학 안내 카드
    # --------------------------------------------------------------------------
    st.markdown("""
<div style="background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
            border: 1px solid #334155; border-radius: 14px; padding: 20px 22px; margin-bottom: 20px;">
    <div style="font-size: 1.1rem; font-weight: 700; color: #F8FAFC; margin-bottom: 6px;">
        🌾 봄에 씨를 뿌리고, 가을에 추수하여, 따뜻한 아랫목에서 맞이하는 겨울
    </div>
    <div style="font-size: 0.9rem; color: #94A3B8; line-height: 1.6;">
        자연에 사계절이 있듯, 사람의 삶에도 봄(준비) · 여름(성장) · 가을(비축) · 겨울(음미)이 있습니다.<br>
        <b style="color: #FBBF24;">겨울은 춥고 두려운 계절이 아닙니다.</b> 여름과 가을에 마련해 둔 땔감과 곡식이 있다면, 가장 평온하게 차 한 잔을 나누는 인생의 황금기입니다.
    </div>
</div>
""", unsafe_allow_html=True)

    # --------------------------------------------------------------------------
    # 6.03.03 | 컨트롤러 & '우리 가족의 은퇴 시점 나이' (코드 노출 버그 박멸)
    # --------------------------------------------------------------------------
    ctrl_col1, ctrl_col2 = st.columns([1, 1])
    with ctrl_col1:
        retire_age = st.slider("💼 내가 현업을 졸업할 나이", min_value=50, max_value=75, value=60, step=1, key="retire_age_slider")
    with ctrl_col2:
        life_expectancy = st.slider("🕊️ 나와 가족의 건강 기대수명", min_value=80, max_value=100, value=88, step=1, key="life_exp_slider")

    years_to_retire = max(0, retire_age - curr_age)
    winter_years = max(0, life_expectancy - retire_age)

    # 가족 구성원 은퇴 시점 나이 연산
    marital_status = st.session_state.get('user_marriage', '기혼')
    child_status = st.session_state.get('user_children', '자녀 1명')
    parent_status = st.session_state.get('user_parents', '독립 / 비부양')

    spouse_cur = curr_age
    spouse_ret = spouse_cur + years_to_retire

    child1_cur = max(1, curr_age - 32)
    child1_ret = child1_cur + years_to_retire

    parent_cur = curr_age + 29
    parent_ret = parent_cur + years_to_retire

    # 인덴트 버그 방지를 위해 한 줄 문자열로 배지 조합
    badges = []
    badges.append(f'<div style="display:inline-flex;align-items:center;background:#0F172A;padding:5px 12px;border-radius:6px;margin:3px;border:1px solid #334155;"><span style="color:#38BDF8;font-weight:700;margin-right:6px;">나</span><span style="color:#94A3B8;">{curr_age}세</span><span style="color:#EA580C;margin:0 5px;font-weight:800;">➔</span><span style="color:#F8FAFC;font-weight:700;">{retire_age}세</span></div>')

    if "기혼" in str(marital_status):
        badges.append(f'<div style="display:inline-flex;align-items:center;background:#0F172A;padding:5px 12px;border-radius:6px;margin:3px;border:1px solid #334155;"><span style="color:#F472B6;font-weight:700;margin-right:6px;">배우자</span><span style="color:#94A3B8;">약 {spouse_cur}세</span><span style="color:#EA580C;margin:0 5px;font-weight:800;">➔</span><span style="color:#F8FAFC;font-weight:700;">약 {spouse_ret}세</span></div>')

    if "자녀" in str(child_status) and "없음" not in str(child_status):
        badges.append(f'<div style="display:inline-flex;align-items:center;background:#0F172A;padding:5px 12px;border-radius:6px;margin:3px;border:1px solid #334155;"><span style="color:#34D399;font-weight:700;margin-right:6px;">자녀</span><span style="color:#94A3B8;">약 {child1_cur}세</span><span style="color:#EA580C;margin:0 5px;font-weight:800;">➔</span><span style="color:#FBBF24;font-weight:700;">약 {child1_ret}세 (대학/결혼기)</span></div>')

    if "부양" in str(parent_status):
        badges.append(f'<div style="display:inline-flex;align-items:center;background:#0F172A;padding:5px 12px;border-radius:6px;margin:3px;border:1px solid #334155;"><span style="color:#A78BFA;font-weight:700;margin-right:6px;">부모님</span><span style="color:#94A3B8;">약 {parent_cur}세</span><span style="color:#EA580C;margin:0 5px;font-weight:800;">➔</span><span style="color:#F8FAFC;font-weight:700;">약 {parent_ret}세 (간병/돌봄기)</span></div>')

    badges_joined = "".join(badges)

    st.markdown(f"""
<div style="background-color: #1E293B; border: 1px solid #334155; border-radius: 12px; padding: 16px 18px; margin-bottom: 22px;">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
        <span style="font-size: 0.95rem; font-weight: 700; color: #F1F5F9;">
            👨‍👩‍👧 내가 현업을 졸업할 때({retire_age}세), 우리 가족의 나이는?
        </span>
        <span style="font-size: 0.82rem; color: #F59E0B; font-weight: 600;">
            남은 준비 기간: {years_to_retire}년
        </span>
    </div>
    <div style="font-size: 0.8rem; color: #94A3B8; margin-bottom: 12px;">
        자신의 은퇴 나이만 보다가 가족들의 연령과 생애 이벤트(자녀 독립, 부모님 케어)를 대조해보면 준비의 무게가 새롭게 다가옵니다.
    </div>
    <div style="display: flex; flex-wrap: wrap;">
        {badges_joined}
    </div>
</div>
""", unsafe_allow_html=True)


    # --------------------------------------------------------------------------
    # 6.03.04 | 국가데이터처 2024년 국민이전계정 공식 통계
    # --------------------------------------------------------------------------

    st.markdown("### 📊 대한민국 생애주기적자: 공식 통계")

    st.markdown(
        "국민이전계정은 연령별 소비와 노동소득의 차이를 통해 "
        "생애주기의 경제적 흐름을 살펴보는 통계입니다. "
        "개인의 가계부와는 구분해서 해석해야 합니다."
    )

    official_pdf_url = (
        "https://mods.go.kr/boardDownload.es"
        "?bid=11898&list_no=447028&seq=3#page=4"
    )
    official_release_url = (
        "https://mods.go.kr/board.es"
        "?act=view&bid=11898&list_no=447028&mid=a10301130100"
    )

    stat_cols = st.columns(3)

    with stat_cols[0]:
        st.metric("흑자 전환 연령", "28세")
        st.caption("노동소득이 소비를 넘어서는 시점")

    with stat_cols[1]:
        st.metric("최대 흑자", "45세")
        st.caption("1인당 연간 1,932만 원")

    with stat_cols[2]:
        st.metric("적자 재전환 연령", "61세")
        st.caption("소비가 노동소득을 다시 넘어서는 시점")

    st.info(
        "생애주기적자는 소비에서 노동소득을 뺀 값입니다. "
        "개인의 실제 가계 적자나 은퇴 연령을 뜻하지 않습니다. "
        "위 수치는 연령별 평균 통계이며 개인의 미래를 예측하는 값이 아닙니다."
    )

    st.markdown(
        f"**공식 원문:** [2024년 국민이전계정 PDF 열기]({official_pdf_url})"
        f"\n\n[국가데이터처 공식 발표 페이지]({official_release_url})"
    )

    # 공식 원자료 전체의 연령별 수치가 코드에 포함되어 있지 않으므로
    # 수치를 보간하거나 추정해 공식 통계 곡선을 그리지 않는다.


    # --------------------------------------------------------------------------
    # 6.03.05 | 은퇴 후 희망 생활비와 필요 자금 계산
    # --------------------------------------------------------------------------

    st.markdown("---")
    st.markdown("### 🧮 내가 원하는 노후 생활비 계산")

    st.markdown(
        "은퇴 후 몇 년을 보내게 될지, 매달 어느 정도의 생활비를 "
        "원하는지 직접 선택해 보세요. 아래 계산은 물가 상승, 투자 수익, "
        "세금, 의료비 변동을 제외한 단순 계산입니다."
    )

    post_col1, post_col2 = st.columns([1, 1.5], gap="large")

    with post_col1:
        st.markdown("#### 🌙 나의 노후 기간")

        st.metric("현업 졸업 나이", f"{retire_age}세")
        st.metric("기대수명 설정", f"{life_expectancy}세")
        st.metric("노후 기간", f"{winter_years}년")
        st.caption(f"총 {winter_years * 12:,}개월 기준")

    with post_col2:
        st.markdown("#### 💰 월 생활비 설정")

        calc_monthly_expense = st.slider(
            "은퇴 후 희망 생활비 (월)",
            min_value=100,
            max_value=600,
            value=200,
            step=10,
            format="%d만 원",
            key="winter_expense_monthly_v3",
            help="현재 가치 기준으로 원하는 월 생활비를 선택하세요."
        )

        total_winter_fund = (
            winter_years * 12 * calc_monthly_expense / 10000.0
        )

        st.markdown(
            f"""
<div style="
    background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
    border: 1px solid #F59E0B;
    border-radius: 12px;
    padding: 18px;
    margin-top: 12px;
">
    <div style="font-size: 0.85rem; color: #CBD5E1;">
        선택한 월 생활비
    </div>
    <div style="
        font-size: 1.5rem;
        font-weight: 800;
        color: #38BDF8;
        margin: 4px 0 12px 0;
    ">
        월 {calc_monthly_expense:,}만 원
    </div>
    <div style="height: 1px; background: #334155; margin: 8px 0;"></div>
    <div style="font-size: 0.85rem; color: #CBD5E1;">
        노후 기간 전체의 단순 생활비 합계
    </div>
    <div style="
        font-size: 1.65rem;
        font-weight: 800;
        color: #FBBF24;
        margin-top: 4px;
    ">
        약 {total_winter_fund:.2f}억 원
    </div>
    <div style="font-size: 0.75rem; color: #94A3B8; margin-top: 8px;">
        월 생활비 × {winter_years * 12:,}개월
    </div>
</div>
""",
            unsafe_allow_html=True
        )

    st.caption(
        "※ 위 금액은 연금이나 다른 소득을 차감하기 전의 단순 합계입니다. "
        "실제로 준비해야 할 자금은 연금 수령액, 보유 자산, 물가 상승률, "
        "의료·간병비 등에 따라 달라집니다."
    )


    # --------------------------------------------------------------------------
    # 6.03.06 | 본질의 질문: 나에게 필요한 준비는 무엇일까?
    # --------------------------------------------------------------------------

    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

    st.markdown(
        f"""
<div style="
    background: linear-gradient(135deg, #0F172A 0%, #1E1B4B 100%);
    border: 1px solid #4338CA;
    border-radius: 14px;
    padding: 20px 22px;
">
    <div style="
        font-size: 1.02rem;
        font-weight: 700;
        color: #A5B4FC;
        margin-bottom: 8px;
    ">
        💡 노후 준비는 정답을 맞히는 일이 아니라,
        내 상황을 이해하는 일입니다.
    </div>
    <div style="
        font-size: 0.88rem;
        color: #CBD5E1;
        line-height: 1.8;
    ">
        선택하신 생활비를 기준으로 노후 기간 전체에 필요한
        단순 생활비 합계는 <b>약 {total_winter_fund:.2f}억 원</b>입니다.
        <br><br>
        이 금액이 곧 지금 당장 마련해야 할 자금이라는 뜻은 아닙니다.
        국민연금 등 예상 연금, 현재 자산, 은퇴 후에도 발생할 수 있는
        소득을 함께 고려해야 실제 부족분을 파악할 수 있습니다.
        <br><br>
        지금의 숫자를 불안의 근거로 삼기보다,
        앞으로 어떤 준비를 할 수 있을지 생각하는 출발점으로 활용해 보세요.
    </div>
    <div style="
        margin-top: 14px;
        text-align: right;
        color: #FBBF24;
        font-size: 0.85rem;
        font-weight: 600;
    ">
        👉 다음 탭에서 현실적인 선택지를 살펴보세요.
    </div>
</div>
""",
        unsafe_allow_html=True
    )


# ------------------------------------------------------------------------------
# 6.04.00 | Tab 4: 나침판의 제안 (AI 팩트체크 리포트 및 소비의 자산화 가이드)
# ------------------------------------------------------------------------------
with tab4:
    st.markdown("### 🧭 지혜로운 인생을 위한 나침판의 조언")
    
    st.markdown("""
        <div class='compassion-card'>
            <h4>🎁 일상 속 어차피 쓰던 소비가 가치 있는 장작으로 바뀌는 비밀</h4>
            <p>
                위기가 아닌 기회를 응시합니다. 
                매달 어차피 마트나 쿠팡에 지불하던 생필품비(월 30~50만원)가, 마트를 바꾸는 것만으로도 나에게 매달 평온한 파이프라인(자산소득)을 선물해 주는 아주 유연하고 가벼운 플랜 B로 이어지는 따뜻한 미래 로드맵을 선사합니다.
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    # 💡 [앞으로 구현될 Tab 4 스케치]:
    # - Gemini AI가 Tab 1~3의 입력 데이터를 요약해서 '따뜻한 멘토의 편지' 형식의 맞춤 재정 진단서 생성
    # - "카카오톡 결과 공유하기" (텍스트 복사 버튼) 제공
    # - "인터뷰 데이터 로컬 파일 저장 및 불러오기" 버튼 신설
    st.info("🚧 **[Tab 4 뼈대 준비 완공]** 이곳에 'Gemini AI 정밀 진단서'와 '카카오톡 원클릭 요약 복사 버튼', 그리고 '상담 데이터 파일(JSON)로 소장/불러오기 버튼'이 이식될 예정입니다.")
