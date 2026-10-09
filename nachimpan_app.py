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
    # 💡 스타벅스 주문번호 스타일의 친근하고 익명성 높은 고유 진단 번호 자동 생성 (예: #C-408)
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
        
        # 2. 로버트 기요사키 경제사분면 (주 소득원 & 부업)
        "primary_quadrant": "💼 직장인 (E)",
        "has_side_gig": False,
        "side_quadrant": "자영업 / N잡 (S)",
        
        # 3. 소득 및 지출 흐름 (월 / 만원 단위)
        "monthly_labor_income": 380,
        "monthly_spouse_income": 150,
        "monthly_asset_income": 0,
        "monthly_living_cost": 280,
        "monthly_debt_payment": 90,
        "monthly_consumable_spend": 35,
        "liquid_emergency_cash": 1200,
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
# [Module 5.00.00] Main Header & Navigation Router (메인 화면 헤더 및 4대 탭 배치)
# ==============================================================================

# ==============================================================================
# 5.01.01 | 나침판 앱 오프닝 헤더
# ==============================================================================
st.title("🧭 나침판 (Compass)")

# 선택된 사분면과 연령에 기반한 자연스러운 맞춤 인사말
quad_label = st.session_state.primary_quadrant.split(" ")[1] if " " in st.session_state.primary_quadrant else "소중한 일터"
age_label = st.session_state.age_selected

st.markdown(f"""
    <div style='background-color: rgba(30, 41, 59, 0.4); border: 1px solid rgba(56, 189, 248, 0.15); border-radius: 10px; padding: 12px 16px; margin-bottom: 20px;'>
        <span style='font-size:15px; color:#F1F5F9; font-weight:bold;'>🌱 {quad_label}로서 소중한 삶의 계절({age_label})을 가꾸어 가시는 길벗님, 환영합니다.</span><br>
        <span style='font-size:13.5px; color:#94A3B8; line-height:1.6;'>
            본 진단은 누구를 평가하거나 미래를 위협하려는 도구가 아닙니다. 
            단지 망망대해 같은 인생의 바다 위에서, <b>나의 현재 좌표를 조용히 응시하고 다가올 계절을 지혜롭게 준비하기 위한 따뜻한 현실 거울</b>입니다. 
            조상들이 '산 입에 거미줄 치랴'고 유쾌하게 외쳤듯, 우리에겐 언제나 길이 있습니다. 가벼운 마음으로 나만의 좌표를 찾아보겠습니다.
        </span>
    </div>
""", unsafe_allow_html=True)

# 5.01.02 | 4대 핵심 현실점검 탭 네비게이션 생성
tab1, tab2, tab3, tab4 = st.tabs([
    "📂 1. 나의 현재 좌표 (재무현황)",
    "⏳ 2. 시간과 쉼표 (노동한계)",
    "🍂 3. 인생의 사계절 (생애주기)",
    "🧭 4. 나침판의 제안 (전략대안)"
])


# ==============================================================================
# [Module 6.00.00] 4-Step Interactive Tabs (메인 인터뷰 4대 캔버스)
# ==============================================================================

# ------------------------------------------------------------------------------
# 6.01.00 | Tab 1: 나의 현재 좌표 (ESBI 사분면 및 자산 현황 상세 입력)
# ------------------------------------------------------------------------------
with tab1:
    st.markdown("### 💼 나의 현재 수입 구조와 재무 현황")
    
    st.markdown("""
        <div class='compassion-card'>
            <h4>⚖️ 그동안 참 열심히 성실하게 삶을 가꾸어 오셨습니다.</h4>
            <p>
                우리가 매달 가정을 위해 얻는 소득은 어떤 성격을 띠고 있을까요? 
                자신의 에너지가 주로 머무는 소득 영역(사분면)을 들여다보고, 숨 가쁘게 지나치던 소득원과 지출의 크기를 거울 보듯 조용히 적어보는 단계입니다.
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    # 💡 [앞으로 구현될 Tab 1 스케치]:
    # - 로버트 기요사키 사분면(E/S/B/I) 선택 라디오 버튼
    # - 본인 소득, 배우자 소득, 자산 소득 슬라이더 입력기
    # - 필수 생활비, 대출 원리금, 숨겨진 생필품 마트 소비비 입력기
    st.info("🚧 **[Tab 1 뼈대 준비 완공]** 이곳에 'ESBI 경제사분면 자가 선택기'와 '소득/지출 상세 입력 슬라이더'가 이식될 예정입니다. 편안한 마음으로 다음 탭들을 차례로 구경해 보세요.")

# ==============================================================================
# 6.01.00 | Tab 1: 나의 현재 좌표 (ESBI 사분면 및 자산 현황 상세 입력)
# ==============================================================================
with tab1:
    st.markdown("### 💼 나의 현재 수입 구조와 재무 현황")
    
    st.markdown("""
        <div class='compassion-card'>
            <h4>⚖️ 그동안 참 성실하고 치열하게 삶을 가꾸어 오셨습니다.</h4>
            <p>
                매달 가정을 지키기 위해 흘리는 땀과 에너지는 어떤 성격을 띠고 있을까요? 
                나의 주 소득원이 머무는 사분면을 응시하고, 매달 들어오고 나가는 현금의 흐름을 슬라이더를 통해 거울 보듯 조용히 마주해보는 시간입니다.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # --------------------------------------------------------------------------
    # 6.01.01 | 로버트 기요사키 ESBI 4사분면 현황 미니 맵
    # --------------------------------------------------------------------------
    st.markdown("#### 🧭 나의 에너지가 머무는 소득 사분면")
    
    col_e, col_s, col_b, col_i = st.columns(4)
    
    # 선택된 사분면 하이라이트 함수
    def get_quad_style(q_code):
        is_primary = (q_code in st.session_state.primary_quadrant)
        is_side = (st.session_state.has_side_gig and q_code in st.session_state.side_quadrant)
        
        if is_primary:
            return "border: 2px solid #F59E0B; background: rgba(245, 158, 11, 0.12);", "🌟 주 소득원"
        elif is_side:
            return "border: 2px dashed #38BDF8; background: rgba(56, 189, 248, 0.10);", "➕ 부업/N잡"
        else:
            return "border: 1px solid #334155; background: rgba(30, 41, 59, 0.4); opacity: 0.6;", ""

    for col, (q_code, q_info) in zip([col_e, col_s, col_b, col_i], ESBI_QUADRANTS.items()):
        border_style, tag = get_quad_style(q_code)
        tag_html = f"<div style='font-size:11px; font-weight:800; color:#FBBF24; margin-bottom:4px;'>{tag}</div>" if tag else "<div style='height:18px;'></div>"
        
        col.markdown(f"""
            <div style='{border_style} border-radius:10px; padding:12px 10px; min-height:130px; text-align:center;'>
                {tag_html}
                <div style='font-size:14px; font-weight:bold; color:#F8FAFC;'>{q_info['badge'].split(' ')[1]} ({q_code})</div>
                <div style='font-size:11.5px; color:#94A3B8; margin-top:6px; line-height:1.4;'>{q_info['desc']}</div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top:25px;'></div>", unsafe_allow_html=True)
    st.divider()

    # --------------------------------------------------------------------------
    # 6.01.02 | 수입 & 지출 슬라이더 컨트롤러 (키패드 0% 터치 인터랙션)
    # --------------------------------------------------------------------------
    c_in, c_out = st.columns([1, 1], gap="large")
    
    with c_in:
        st.markdown("#### 📥 매달 들어오는 수입 (월 단위)")
        
        # 1. 본인 노동소득
        st.session_state.monthly_labor_income = st.slider(
            "1. 본인 월 소득 (급여 / 사업소득)",
            min_value=0, max_value=2000, value=int(st.session_state.monthly_labor_income), step=10, format="%d만 원"
        )
        
        # 2. 배우자 소득
        st.session_state.monthly_spouse_income = st.slider(
            "2. 배우자 월 소득 (맞벌이 등)",
            min_value=0, max_value=1500, value=int(st.session_state.monthly_spouse_income), step=10, format="%d만 원"
        )
        
        # 3. 자산/권리 소득 (일하지 않아도 나오는 돈)
        st.session_state.monthly_asset_income = st.slider(
            "3. 일하지 않아도 나오는 소득 (연금/배당/임대/로열티)",
            min_value=0, max_value=1000, value=int(st.session_state.monthly_asset_income), step=10, format="%d만 원"
        )

        total_income = st.session_state.monthly_labor_income + st.session_state.monthly_spouse_income + st.session_state.monthly_asset_income
        st.markdown(f"""
            <div style='background:rgba(30, 41, 59, 0.6); padding:10px 14px; border-radius:8px; border:1px solid #334155; margin-top:14px;'>
                <span style='font-size:13px; color:#94A3B8;'>가정 총 월수입 합계:</span> 
                <b style='font-size:18px; color:#38BDF8; float:right;'>{total_income:,.0f}만 원</b>
            </div>
        """, unsafe_allow_html=True)

    with c_out:
        st.markdown("#### 📤 매달 나가는 지출 & 보유 자산")
        
        # 1. 필수 생활비
        st.session_state.monthly_living_cost = st.slider(
            "1. 필수 생활비 (식비, 공과금, 보육/교육비 등)",
            min_value=50, max_value=1500, value=int(st.session_state.monthly_living_cost), step=10, format="%d만 원"
        )
        
        # 2. 대출 상환액
        st.session_state.monthly_debt_payment = st.slider(
            "2. 대출 원리금 상환액 (주담대, 신용대출 등)",
            min_value=0, max_value=1000, value=int(st.session_state.monthly_debt_payment), step=10, format="%d만 원"
        )
        
        # 3. 💡 [핵심 복선] 매달 마트/쿠팡에 지불하는 생필품비
        st.session_state.monthly_consumable_spend = st.slider(
            "3. 어차피 마트/쿠팡에서 쓰는 생필품비 (세제, 치약, 영양제 등)",
            min_value=10, max_value=200, value=int(st.session_state.monthly_consumable_spend), step=5, format="%d만 원"
        )
        st.caption("💡 이 생필품비는 필수 생활비 안에 이미 포함되어 있으나, 나중에 '자산의 씨앗'이 될 소중한 금액입니다.")

        # 4. 비상금
        st.session_state.liquid_emergency_cash = st.slider(
            "4. 당장 인출 가능한 비상 현금 / 예적금",
            min_value=0, max_value=10000, value=int(st.session_state.liquid_emergency_cash), step=50, format="%d만 원"
        )

        total_expense = st.session_state.monthly_living_cost + st.session_state.monthly_debt_payment
        st.markdown(f"""
            <div style='background:rgba(30, 41, 59, 0.6); padding:10px 14px; border-radius:8px; border:1px solid #334155; margin-top:14px;'>
                <span style='font-size:13px; color:#94A3B8;'>매달 빠져나가는 고정지출 합계:</span> 
                <b style='font-size:18px; color:#F87171; float:right;'>{total_expense:,.0f}만 원</b>
            </div>
        """, unsafe_allow_html=True)

    # --------------------------------------------------------------------------
    # 6.01.03 | 실시간 현금흐름 요약 밸런스 카드
    # --------------------------------------------------------------------------
    st.markdown("<div style='margin-top:25px;'></div>", unsafe_allow_html=True)
    monthly_surplus = total_income - total_expense
    
    surplus_color = "#34D399" if monthly_surplus >= 0 else "#F87171"
    surplus_text = f"+{monthly_surplus:,.0f}만 원 (흑자 흐름)" if monthly_surplus >= 0 else f"{monthly_surplus:,.0f}만 원 (적자 흐름)"
    
    st.markdown(f"""
        <div style='background:linear-gradient(135deg, #1E293B 0%, #0F172A 100%); border:1.5px solid #334155; border-radius:12px; padding:16px 20px; text-align:center;'>
            <span style='font-size:14px; color:#94A3B8; font-weight:600;'>매달 가계에 남는 순수 여유 자금 (월 현금흐름 밸런스)</span>
            <div style='font-size:26px; font-weight:800; color:{surplus_color}; margin-top:4px;'>{surplus_text}</div>
            <div style='font-size:12px; color:#64748B; margin-top:6px;'>
                수입 슬라이더나 지출 슬라이더를 조절하시면 왼쪽 사이드바의 <b>'안심 버퍼 시간(개월 수)'</b>이 실시간으로 함께 변화합니다.
            </div>
        </div>
    """, unsafe_allow_html=True)


# ------------------------------------------------------------------------------
# 6.02.00 | Tab 2: 시간과 쉼표 (노동수입 한계 자각 및 숨고르기 시간 관제)
# ------------------------------------------------------------------------------
with tab2:
    st.markdown("### ⏳ 내 인생의 자유를 위한 숨고르기 시간")
    
    st.markdown("""
        <div class='compassion-card'>
            <h4>🕊️ '산 입에 거미줄 치랴'의 해학과 여유</h4>
            <p>
                우리의 몸과 에너지는 한계가 있기에, 때로는 쉬고 싶고 멈춰 서야 할 때도 찾아옵니다. 
                이 탭에서는 내가 일하지 않고 쉴 수 있는 시간(버퍼)을 통해, 노동 수입 너머에서 가정을 지켜줄 지혜로운 장작(자산 수입)이 왜 필요한지 가볍게 마주해 봅니다.
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    # 💡 [앞으로 구현될 Tab 2 스케치]:
    # - "수입 중단 시 생존 일수"를 시각적 게이지 및 모래시계 차트로 변환
    # - 나의 소득 중 '내가 일하지 않아도 돌아가는 시스템 소득(Amway 등)' 비중을 도넛 차트로 실시간 렌더링
    st.info("🚧 **[Tab 2 뼈대 준비 완공]** 이곳에 '노동수입 대비 자산소득 비율 분석 그래프'와 '재정 활주로 시각화 모래시계 차트'가 이식될 예정입니다.")


# ------------------------------------------------------------------------------
# 6.03.00 | Tab 3: 인생의 사계절 (생애주기 수입·지출 흐름 및 적자 절벽 대비)
# ------------------------------------------------------------------------------
with tab3:
    st.markdown("### 🍂 인생 사계절의 자연스러운 흐름")
    
    st.markdown("""
        <div class='compassion-card'>
            <h4>🍁 낙엽이 지고 겨울이 오는 것은 결코 두려운 일이 아닙니다.</h4>
            <p>
                봄에 씨를 뿌려 풍요로운 가을을 수확하듯, 누구에게나 땀 흘릴 수 있는 계절과 필연적으로 맞이하는 은퇴기(겨울)가 있습니다. 
                통계청 공식 데이터가 보여주는 대한민국 평균 수입/지출 교차점을 내 삶과 대조해 보며, 인생 겨울을 따뜻하게 지켜줄 장작을 준비할 시점을 자각합니다.
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    # 💡 [앞으로 구현될 Tab 3 스케치]:
    # - 통계청 생애주기 적자/흑자 데이터셋 로딩
    # - 인터뷰이의 현재 나이(age)와 은퇴목표나이를 반영하여, '인생 수입-지출 골든크로스 & 데드크로스 곡선'을 아름다운 라인 차트로 실시간 드로잉
    st.info("🚧 **[Tab 3 뼈대 준비 완공]** 이곳에 '대한민국 통계청 평균 인생 곡선'과 나의 '예상 은퇴 적자 시점 시뮬레이션 곡선 그래프'가 이식될 예정입니다.")


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
