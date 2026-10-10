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
# 5.00.00 | Main Navigation
# ==============================================================================

# ==============================================================================
# 5.01.00 | Navigation Branch Point
# ==============================================================================


# ==============================================================================
# 5.01.01 | Horizontal Navigation with streamlit-option-menu
# ==============================================================================

# 상단 여백과 가로 메뉴의 높이·가독성 개선
st.markdown("""
<style>
/* 본문 상단 여백 확보: 메뉴가 브라우저 상단에 붙는 현상 완화 */
.stAppViewBlockContainer,
div[data-testid="stMainBlockContainer"] {
    padding-top: 3.5rem !important;
}

/* 메뉴 바 */
div[data-testid="stAppViewContainer"] ul {
    margin-top: 0.4rem;
}

/* option_menu 전체 컨테이너 */
.nav-link-container {
    padding: 8px !important;
    border-radius: 12px !important;
}

/* 메뉴 글자와 아이콘의 터치 영역 확대 */
.nav-link {
    min-height: 48px !important;
    padding: 13px 10px !important;
    font-size: 15px !important;
    font-weight: 600 !important;
    line-height: 1.4 !important;
    border-radius: 9px !important;
}

/* 아이콘 크기 */
.nav-link i {
    font-size: 17px !important;
}

/* 모바일·좁은 화면에서도 메뉴 글자가 잘리기 어렵게 */
@media (max-width: 700px) {
    .nav-link {
        min-height: 52px !important;
        padding: 10px 4px !important;
        font-size: 12px !important;
    }

    .nav-link i {
        font-size: 15px !important;
    }
}
</style>
""", unsafe_allow_html=True)

selected_tab = option_menu(
    menu_title=None,
    options=[
        "우리집 가계부",
        "삶과 시간",
        "인생의 사계절",
        "나침판의 제안",
    ],
    icons=[
        "wallet2",
        "hourglass-split",
        "calendar-heart",
        "compass",
    ],
    menu_icon=None,
    default_index=0,
    orientation="horizontal",
    key="main_navigation",
    styles={
        "container": {
            "padding": "8px 8px",
            "background-color": "#0F172A",
            "border": "1px solid #263449",
            "border-radius": "12px",
            "margin-top": "8px",
            "margin-bottom": "24px",
            "width": "100%",
        },
        "icon": {
            "color": "#CBD5E1",
            "font-size": "17px",
        },
        "nav-link": {
            "font-size": "15px",
            "text-align": "center",
            "margin": "3px 4px",
            "padding": "13px 8px",
            "color": "#CBD5E1",
            "--hover-color": "#334155",
            "border-radius": "9px",
            "min-height": "48px",
        },
        "nav-link-selected": {
            "background-color": "#EA580C",
            "color": "#FFFFFF",
            "font-weight": "700",
            "box-shadow": "0 3px 10px rgba(234, 88, 12, 0.25)",
        },
    },
)



# ==============================================================================
# 5.01.02 | Navigation Initialization Complete
# ==============================================================================

# 중복 st.tabs() 선언 금지.
# 다음 블록부터 기존 Module 6.00.00 코드를 실행한다.


# ==============================================================================
# [Module 6.00.00] 4-Step Interactive Tabs (메인 인터뷰 4대 캔버스)
# ==============================================================================


# ===== 6.01.00 | 우리집 가계부 (통째 교체 블록) =====
if selected_tab == "우리집 가계부":
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
    # 6.01.09 | Fact-Based Future Net Worth Trajectory & Pension Gap Analysis
    # ==============================================================================
    st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
    st.markdown("#### 📈 미래 순자산 궤적 및 노후 준비 팩트 분석 (사실 진단)")

    # 1. 인터뷰이 연령 추출 및 기간 산출
    try:
        cur_age_num = int(str(st.session_state.get('age_selected', '38세')).replace('세', '').strip())
    except:
        cur_age_num = 38
        
    retire_age_std = 60 # 표준 일선 은퇴 연령 (60세)
    years_to_retire = max(0, retire_age_std - cur_age_num)

    # --------------------------------------------------------------------------
    # 💡 [신설] 노후 예상 연금 수령액 (국민연금 + 퇴직연금 + 개인연금 합산)
    # --------------------------------------------------------------------------
    c_pen1, c_pen2 = st.columns([2.8, 1.2], gap="small")
    with c_pen1:
        if "expected_pension_monthly" not in st.session_state:
            st.session_state.expected_pension_monthly = 120 # 기본 120만원 (국민+퇴직연금 평균 수준)
        
        st.session_state.expected_pension_monthly = st.slider(
            "🛡️ 은퇴(60세) 후 부부 합산 예상 연금 수령액 (국민연금+퇴직+개인연금)",
            min_value=0, max_value=400, value=int(st.session_state.expected_pension_monthly), step=10, format="%d만 원/월"
        )
    with c_pen2:
        st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)
        st.caption(f"💡 월 {st.session_state.expected_pension_monthly}만 원은 연금으로 방어")

    # 2. 현실적인 은퇴 생활비 갭(Gap) 계산
    benchmark_monthly_living = 250 # 국민연금연구원 부부 적정 노후생활비 (월 250만원)
    net_monthly_deficit = max(0, benchmark_monthly_living - st.session_state.expected_pension_monthly)
    annual_retirement_burn = net_monthly_deficit * 12 # 은퇴 후 1년에 순수하게 까먹는 자산 규모

    # 3. 은퇴 전 축적액 (연간 저축 가능액)
    annual_savings = monthly_surplus * 12

    # 4. 나이대별(현재 -> +5년 -> +10년 -> 60세 -> 70세 -> 80세) 생애 순자산 궤적 시뮬레이션
    sim_ages = [cur_age_num, cur_age_num + 5, cur_age_num + 10]
    if 60 not in sim_ages and 60 > cur_age_num:
        sim_ages.append(60)
    sim_ages.extend([70, 80])
    sim_ages = sorted(list(set(sim_ages)))

    traj_net_worth = []
    current_sim_asset = float(net_worth)

    for a in sim_ages:
        if a <= cur_age_num:
            traj_net_worth.append(current_sim_asset)
        elif a <= retire_age_std:
            # 은퇴 전: 매년 저축액 축적
            years_passed = a - cur_age_num
            val = net_worth + (annual_savings * years_passed)
            traj_net_worth.append(val)
        else:
            # 은퇴 후: 60세 시점 자산에서 매년 생활비 적자(annual_retirement_burn)를 헐어 쓰며 소진!
            val_at_60 = net_worth + (annual_savings * years_to_retire)
            years_after_retire = a - retire_age_std
            burned_val = val_at_60 - (annual_retirement_burn * years_after_retire)
            traj_net_worth.append(burned_val)

    # 60세 시점 순자산 도달액 및 금융자산(부동산 제외) 팩트 분석
    net_worth_at_60 = net_worth + (annual_savings * years_to_retire)
    real_estate_val = st.session_state.get('asset_real_estate', 0)
    liquid_asset_at_60 = net_worth_at_60 - real_estate_val # 집 빼고 손에 쥔 현금 자산

    # --------------------------------------------------------------------------
    # 5. 📉 Plotly 생애 순자산 궤적 부드러운 꺾은선 그래프 (Spline Curve)
    # --------------------------------------------------------------------------
    traj_df = pd.DataFrame({"연령": sim_ages, "순자산": traj_net_worth})
    traj_df["연령_라벨"] = traj_df["연령"].apply(lambda x: f"{x}세(은퇴)" if x == retire_age_std else f"{x}세")

    fig_traj = go.Figure()

    # 1. 부드러운 자산 궤적 라인
    fig_traj.add_trace(go.Scatter(
        x=traj_df["연령"],
        y=traj_df["순자산"],
        mode='lines+markers+text',
        line=dict(color='#F59E0B', width=3.5, shape='spline'),
        marker=dict(size=9, color='#FFFFFF', line=dict(color='#EA580C', width=2)),
        text=traj_df["순자산"].apply(lambda v: fmt_money_kr(v)),
        textposition="top center",
        textfont=dict(size=12, color='#F8FAFC'),
        name="가계 순자산 궤적"
    ))

    # 2. 60세 은퇴 수직 기준선
    if retire_age_std > cur_age_num:
        fig_traj.add_vline(
            x=retire_age_std, line_dash="dash", line_color="#38BDF8", line_width=2,
            annotation_text=" 60세 일선 은퇴 시점 ", annotation_position="bottom right",
            annotation_font=dict(size=12, color="#38BDF8")
        )

    # 3. 0원 기준선 (자산 바닥선)
    fig_traj.add_hline(y=0, line_dash="dot", line_color="#EF4444", line_width=1.5)

    fig_traj.update_layout(
        height=330,
        margin=dict(l=10, r=20, t=30, b=30),
        paper_bgcolor='rgba(15, 23, 42, 0.4)',
        plot_bgcolor='rgba(15, 23, 42, 0.4)',
        xaxis=dict(
            tickmode='array', tickvals=sim_ages, ticktext=traj_df["연령_라벨"],
            fixedrange=True, gridcolor='#334155'
        ),
        yaxis=dict(fixedrange=True, showgrid=True, gridcolor='#334155', zeroline=False),
        showlegend=False
    )
    st.plotly_chart(fig_traj, use_container_width=True, config={'displayModeBar': False})

    # --------------------------------------------------------------------------
    # 6. 💎 7.5억의 허상과 부동산 착시 팩트체크 카드
    # --------------------------------------------------------------------------
    # 80세 시점에 자산이 남아있는지 여부
    net_at_80 = traj_net_worth[-1]
    
    if liquid_asset_at_60 <= 0 and real_estate_val > 0:
        insight_title = "🚨 '부동산 착시' 경고 (집 한 채의 함정)"
        insight_badge = "<span style='background:#EF4444; color:#FFFFFF; font-size:11.5px; font-weight:800; padding:3px 8px; border-radius:5px;'>하우스푸어 위험</span>"
        insight_msg = f"""
            • 60세 시점 가계 순자산은 <b>{fmt_money_kr(net_worth_at_60)}</b>에 달하지만, 
            살고 있는 <b>집(부동산 {fmt_money_kr(real_estate_val)})을 빼고 나면 통장에 남는 현금성 자산은 마이너스({fmt_money_kr(liquid_asset_at_60)})</b>입니다.<br>
            • 아파트를 헐어 먹고 살 수는 없습니다. 7.5억의 집이 있어도 마르지 않는 <b>'매달 나오는 현금흐름'</b>이 없다면 은퇴 직후부터 심각한 생활고에 직면합니다.
        """
    elif net_at_80 > 0:
        insight_title = "🟢 은퇴 후 기본 생활 유지권"
        insight_badge = "<span style='background:#10B981; color:#FFFFFF; font-size:11.5px; font-weight:800; padding:3px 8px; border-radius:5px;'>현금흐름 보완 필요</span>"
        insight_msg = f"""
            • 연금(월 {st.session_state.expected_pension_monthly}만 원)과 현재의 자산 축적 페이스 덕분에 80세 시점에도 자산이 유지되는 궤적입니다.<br>
            • 다만 자산의 대부분이 부동산에 묶여 있다면 의료비/간병비 등 예상치 못한 목돈 지출 시 유동성 위기가 올 수 있으므로, <b>매달 파이프처럼 들어오는 권리소득</b>으로 체질을 개선해야 안전합니다.
        """
    else:
        insight_title = "⚠️ 은퇴 후 자산 소진 곡선 발생"
        insight_badge = "<span style='background:#F59E0B; color:#0B1120; font-size:11.5px; font-weight:800; padding:3px 8px; border-radius:5px;'>자산 소진기 진입</span>"
        insight_msg = f"""
            • 60세 은퇴 후 연금 수령액을 제외한 부족분(월 {net_monthly_deficit:,.0f}만 원)을 모아둔 자산에서 메우다 보면, <b>노후 15~20년 차에 축적 자산이 급격히 바닥으로 꺾이는 궤적</b>이 나타납니다.<br>
            • 모아둔 돈을 까먹는 삶에서 벗어나, <b>평생 멈추지 않는 현금흐름 파이프라인(자산)</b>을 미리 구축해야 하는 이유가 바로 여기에 있습니다.
        """

    st.markdown(f"""
        <div style='background:rgba(30, 41, 59, 0.7); border:1.5px solid #334155; border-radius:12px; padding:16px 20px; margin-top:10px;'>
            <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;'>
                <b style='font-size:14.5px; color:#FBBF24;'>{insight_title}</b>
                {insight_badge}
            </div>
            <div style='font-size:13px; color:#CBD5E1; line-height:1.7;'>
                {insight_msg}
            </div>
        </div>
    """, unsafe_allow_html=True)


# ==============================================================================
# 6.02.00 | Tab 2: 삶과 시간 (시간의 물리적 한계 & 물통과 파이프라인)
# ==============================================================================


# ===== 6.02.00 | 삶과 시간 (통째 교체 블록) =====
if selected_tab == "삶과 시간":
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


# ===== 6.03.00 | 인생의 사계절 (통째 교체 블록) =====
if selected_tab == "인생의 사계절":
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
    # 6.03.04 | 국가데이터처 2024년 국민이전계정 공식 통계 및 출처
    # --------------------------------------------------------------------------
    st.markdown("### 📊 대한민국 생애주기적자: 국가데이터처 공식 통계")
    st.markdown(
        "2024년 국민이전계정에서 발표한 연령별 소비와 노동소득의 차이입니다. "
        "공식 통계는 원문 자료를 통해 확인할 수 있으며, "
        "개인의 가계부 수치나 은퇴 시점과는 구분해서 해석해야 합니다."
    )

    official_pdf_url = (
        "https://mods.go.kr/boardDownload.es?bid=11898&list_no=447028&seq=3#page=4"
    )
    official_release_url = (
        "https://mods.go.kr/board.es?act=view&bid=11898&list_no=447028&mid=a10301130100"
    )

    st.markdown("#### 핵심 수치 요약")
    stat_cols = st.columns(3)

    with stat_cols[0]:
        st.metric("흑자 전환", "28세")
        st.caption("노동소득이 소비를 넘어서는 시점")

    with stat_cols[1]:
        st.metric("최대 흑자", "45세 · 1,932만 원")
        st.caption("1인당 연간 생애주기흑자")

    with stat_cols[2]:
        st.metric("적자 재전환", "61세")
        st.caption("소비가 노동소득을 다시 넘어서는 시점")

    st.info(
        "여기서 ‘생애주기적자’는 소비에서 노동소득을 뺀 값입니다. "
        "개인의 가계부상 적자나 실제 은퇴 시점을 뜻하지 않으며, "
        "연령별 평균 통계입니다."
    )

    # iPhone의 PDF 미리보기 자동 실행·화면 전환 문제를 피하기 위해
    # PDF를 iframe으로 삽입하지 않고 사용자가 원할 때만 열도록 한다.
    st.markdown("#### 공식 원문 자료")

    st.link_button(
        "📄 2024년 국민이전계정 PDF 열기",
        official_pdf_url,
        use_container_width=True,
    )

    st.link_button(
        "🌐 국가데이터처 공식 발표 페이지",
        official_release_url,
        use_container_width=True,
    )


    # --------------------------------------------------------------------------
    # 6.03.05 | 은퇴 후 생활비 슬라이더 (200만 원 중심, 최대 600만 원, 공식 통계 제시)
    # --------------------------------------------------------------------------
    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
    post_col1, post_col2 = st.columns([1.15, 1.85])

    with post_col1:
        st.markdown(f"""
<div style="background-color: #1E293B; border: 1px solid #334155; border-radius: 12px; padding: 20px 18px; height: 100%;">
    <div style="font-size: 0.85rem; color: #94A3B8;">은퇴 후 맞이할 비활동기 (겨울)</div>
    <div style="font-size: 1.85rem; font-weight: 800; color: #F8FAFC; margin: 6px 0;">
        {winter_years}년 <span style="font-size: 0.95rem; font-weight: 500; color: #94A3B8;">({winter_years * 12:,}개월)</span>
    </div>
    <div style="font-size: 0.78rem; color: #64748B; line-height: 1.5;">
        {retire_age}세 현업 졸업부터 {life_expectancy}세까지,<br>
        정기 노동소득이 멈춘 상태에서 품위와 건강을 지켜내야 하는 소중한 시간입니다.
    </div>
</div>
""", unsafe_allow_html=True)

    with post_col2:
        # 공식 통계 팩트 뱃지 안내
        st.markdown("""
<div style="display: flex; gap: 8px; margin-bottom: 8px;">
    <span style="font-size: 0.75rem; background: #0F172A; color: #94A3B8; padding: 3px 8px; border-radius: 4px; border: 1px solid #334155;">
        📌 국민연금연구원 적정 노후생활비: 부부 <b>월 280~314만 원</b> / 1인 <b>월 180~195만 원</b>
    </span>
</div>
""", unsafe_allow_html=True)

        # 200만 원 정중앙 로그 스케일 슬라이더 (0~100)
        # s=0 -> 100만 원, s=50 -> 200만 원, s=100 -> 600만 원
        slider_val = st.slider(
            "은퇴 후 생활비(월)",
            min_value=0, max_value=100, value=50, step=1,
            format="",
            key="winter_expense_log_slider_v2",
            help="가운데가 200만 원이며, 100만 원부터 600만 원까지 부드럽게 조절됩니다."
        )

        if slider_val <= 50:
            calc_monthly_expense = int(round(100 + (slider_val / 50.0) * 100))  # 100 ~ 200만 원
        else:
            ratio = (slider_val - 50) / 50.0
            calc_monthly_expense = int(round(200 + (ratio ** 1.3) * 400))       # 200 ~ 600만 원

        # 10만 원 단위 정돈
        calc_monthly_expense = (calc_monthly_expense // 10) * 10

        # 총 필요 자금 계산
        total_winter_fund = (winter_years * 12 * calc_monthly_expense) / 10000.0  # 억원 단위

        # 실시간 생활비 & 필요 총자금 카드
        st.markdown(f"""
<div style="background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%);
            border: 1px solid #F59E0B; border-radius: 12px; padding: 14px 18px;">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <span style="font-size: 0.88rem; color: #CBD5E1;">선택하신 월 희망 생활비</span>
        <span style="font-size: 1.25rem; font-weight: 800; color: #38BDF8;">월 {calc_monthly_expense:,}만 원</span>
    </div>
    <div style="height: 1px; background-color: #334155; margin: 8px 0;"></div>
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <span style="font-size: 0.88rem; color: #E2E8F0;">평온한 노후를 위한 총 필요자금</span>
        <span style="font-size: 1.45rem; font-weight: 800; color: #F59E0B;">약 {total_winter_fund:.1f}억 원</span>
    </div>
    <div style="font-size: 0.76rem; color: #94A3B8; margin-top: 4px;">
        월 {calc_monthly_expense:,}만 원 × {winter_years * 12:,}개월 기준
    </div>
</div>
""", unsafe_allow_html=True)

    # --------------------------------------------------------------------------
    # 6.03.06 | 본질의 질문 (Plan B 브릿지)
    # --------------------------------------------------------------------------
    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
    st.markdown(f"""
<div style="background: linear-gradient(135deg, #0F172A 0%, #1E1B4B 100%);
            border: 1px solid #4338CA; border-radius: 14px; padding: 20px 22px; text-align: left;">
    <div style="font-size: 1.02rem; font-weight: 700; color: #A5B4FC; margin-bottom: 6px;">
        💡 모아둔 {total_winter_fund:.1f}억 원을 헐어 쓰는 삶 vs 매달 200만 원이 들어오는 자산의 샘물
    </div>
    <div style="font-size: 0.88rem; color: #CBD5E1; line-height: 1.7;">
        목돈 수억 원을 통장에 넣어두고 매달 쪼개어 쓰는 방식은 <b>'수명이 길어질수록 잔고가 바닥날까 불안한 마음'</b>을 지우기 어렵습니다.<br>
        하지만 내가 노동을 졸업해도 마당 한구석에서 <b>매달 150만~250만 원의 평생 지속되는 현금흐름</b>이 나온다면 어떨까요?<br>
        그것은 <b>수억 원의 원금을 단 1원도 축내지 않고 자녀에게 그대로 물려줄 수 있는 든든한 방패</b>가 됩니다.
    </div>
    <div style="margin-top: 14px; text-align: right;">
        <span style="font-size: 0.85rem; font-weight: 600; color: #F59E0B;">
            👉 상단 탭의 [나침판의 제안]에서 '생활비 지출을 자산으로 바꾸는 비밀'을 함께 확인해 보세요.
        </span>
    </div>
</div>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# 6.04.00 | Tab 4: 나침판의 제안 (AI 팩트체크 리포트 및 소비의 자산화 가이드)
# ------------------------------------------------------------------------------


# ===== 6.04.00 | 나침판의 제안 (통째 교체 블록) =====
if selected_tab == "나침판의 제안":
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

