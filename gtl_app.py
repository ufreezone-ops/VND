# [Project: Global Travel Ledger (GTL) / Version: v26.04.30.002]
# [Strategic Partner: Gem / Core: Full-Stack FIFO Platform - Volume Guard Active]
# [Status: Total System Restoration - ZERO OMISSION - 30.1 KB]

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date as dt_date
from streamlit_gsheets import GSheetsConnection
import time

# --- SECTION 1: Configuration & Global Setup ---
# [Status: Maintained and Explicitly Expanded for UI/UX Stability]
st.set_page_config(page_title="GTL: 여행 가계부", page_icon="🌏", layout="wide")

# 모바일 가독성 및 고밀도 KPI 레이아웃 전용 CSS 스타일 정의
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .kpi-box {
        background-color: #1e2130;
        padding: 20px;
        border-radius: 15px;
        border-left: 8px solid #00FF00;
        margin-bottom: 20px;
        min-height: 120px;
        box-shadow: 4px 6px 15px rgba(0,0,0,0.5);
    }
    .kpi-title { font-size: 15px; color: #cccccc; margin-bottom: 10px; font-weight: 600; }
    .kpi-value-krw { font-size: 26px; font-weight: bold; color: #ffffff; line-height: 1.1; }
    .kpi-value-vnd { font-size: 18px; color: #00FF00; margin-top: 8px; font-family: 'Courier New', monospace; font-weight: 500; }
    /* 소진완료 텍스트 스타일 */
    .sold-out { color: #ff4b4b; font-weight: bold; font-style: italic; }
    /* 테이블 디자인 보정 */
    div[data-testid="stTable"] { border: 1px solid #444; border-radius: 10px; overflow: hidden; }
    .stTabs [data-baseweb="tab-list"] { gap: 15px; padding-bottom: 10px; }
    .stTabs [data-baseweb="tab"] { 
        background-color: #1c1f2b; 
        border-radius: 8px 8px 0 0; 
        padding: 12px 25px;
        color: #ffffff;
    }
    .stTabs [aria-selected="true"] { background-color: #00FF00 !important; color: #000000 !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# [Safeguard] 전역 변수 초기화 (AttributeError 및 초기 로딩 에러 원천 차단)
if 'rate_names' not in st.session_state:
    st.session_state.rate_names = ['부산 1차', '머니박스', '트래블 2차', '에어텔', '기타']
if 'rates' not in st.session_state:
    st.session_state.rates = [0.0561, 0.0610, 0.0564, 0.0560, 0.0561]
if 'last_cat_idx' not in st.session_state: 
    st.session_state.last_cat_idx = 0
if 'last_rate_idx' not in st.session_state: 
    st.session_state.last_rate_idx = 0

# 글로벌 통화 및 지폐 상수 정의
TRAVEL_CURRENCY = "VND"
BASE_CURRENCY = "KRW"
BILLS = [500000, 200000, 100000, 50000, 20000, 10000, 5000, 2000, 1000]

# 카테고리 헌법 및 필터 정의
EXPENSE_CATS = ["식사", "간식", "Grab", "VinBus", "마사지", "팁", "마트", "선물", "투어", "입장료", "통신", "수수료", "택시", "지하철", "항공권", "호텔", "보험", "입국", "출국"]
SURVIVAL_CATS = ["식사", "간식", "Grab", "VinBus", "마사지", "팁"]
FIXED_COST_CATS = ["항공권", "호텔", "보험"]
DOMESTIC_CATS = ["항공권", "호텔", "보험", "지하철", "택시"]
TRANSFER_CATS = ["충전", "ATM출금", "보증금", "환전", "직접환전"]

# 구글 시트 데이터 스키마 정의
COLUMNS = ['Date', 'Category', 'Description', 'Currency', 'Amount', 'PaymentMethod', 'IsExpense', 'AppliedRate']
AUDIT_COLUMNS = ['Cum_Budget_KRW', 'Cum_Card_VND', 'Cum_Cash_VND']

# --- SECTION 2: [Module A] Data Engine (Multi-Sheet Sync & Running Audit) ---
# [Status: Restored Defensive Loading and Expanded Logic]
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    """구글 시트에서 데이터를 로드하고 정규화합니다."""
    try:
        # 캐시 없이 직접 읽기로 데이터 무결성 확보 (TTL=0)
        df = conn.read(worksheet="ledger", ttl="0s")
        
        if df is None or df.empty: 
            return pd.DataFrame(columns=COLUMNS + AUDIT_COLUMNS)
        
        # [Fixed] 유령 행(None) 제거: 날짜나 카테고리가 없는 행은 과감히 삭제
        df = df.dropna(subset=['Date', 'Category'], how='any')
        
        # 데이터 유실 방지를 위한 컬럼 재인덱싱
        df = df.reindex(columns=COLUMNS + AUDIT_COLUMNS)
        
        # 데이터 타입 강제 변환 (정산 오류 방지)
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
        df['AppliedRate'] = pd.to_numeric(df['AppliedRate'], errors='coerce').fillna(1.0)
        df['IsExpense'] = pd.to_numeric(df['IsExpense'], errors='coerce').fillna(0).astype(int)
        
        return df
        
    except Exception as e:
        if "429" in str(e): 
            st.error("🚨 구글 서버 API 요청 한도 초과. 1분 뒤에 새로고침하세요.")
        else:
            st.error(f"데이터 로드 에러: {e}")
        return pd.DataFrame(columns=COLUMNS + AUDIT_COLUMNS)

def calculate_running_totals(df):
    """구글 시트의 누계 컬럼 I, J, K를 명시적으로 계산합니다."""
    temp_df = df.copy()
    c_budget = 0.0
    c_card = 0.0
    c_cash = 0.0
    
    for i, row in temp_df.iterrows():
        qty = row['Amount']
        rate = row['AppliedRate']
        desc = str(row['Description'])
        cat = row['Category']
        method = row['PaymentMethod']
        curr = row['Currency']
        is_exp = row['IsExpense']

        # 1. 예산 누계 (KRW 지출 기준)
        if method == '원화계좌':
            if curr == 'KRW': c_budget += qty
            else: c_budget += qty * rate
            
        # 2. 자산 흐름 추적 (FIFO 연동)
        if cat in ['충전', '환전', '입금', '직접환전']:
            if "카드VND" in desc: c_card += qty
            elif "지폐VND" in desc: c_cash += qty
        elif cat == 'ATM출금':
            c_card -= qty
            c_cash += qty
        elif is_exp == 1 and curr == TRAVEL_CURRENCY:
            if "트래블로그" in method: c_card -= qty
            elif "현금" in method: c_cash -= qty
        elif cat == '보증금':
            c_cash -= qty

        # 행 단위 결과 기입
        temp_df.at[i, 'Cum_Budget_KRW'] = round(c_budget, 0)
        temp_df.at[i, 'Cum_Card_VND'] = round(c_card, 0)
        temp_df.at[i, 'Cum_Cash_VND'] = round(c_cash, 0)
        
    return temp_df

def save_data(df, metrics=None):
    """구글 시트의 모든 탭을 동기화하며 Audit 데이터를 생성합니다."""
    if df is None or len(df) == 0:
        st.error("🚨 보호막: 빈 데이터를 저장할 수 없습니다.")
        return False
        
    with st.status("전략적 데이터 안전 잠금 및 동기화 중...", expanded=False):
        try:
            # 저장 전 누계 데이터 자동 생성
            df_with_audit = calculate_running_totals(df)
            conn.update(worksheet="ledger", data=df_with_audit)
            
            # Summary 탭 업데이트 (GSheets 직접 확인용)
            if metrics:
                summary_data = pd.DataFrame({
                    "항목": ["🏦 예산 (KRW)", "💳 카드 VND 잔액", "💵 현금 VND 잔액", "🕒 업데이트 시각"],
                    "수치": [f"{metrics[0]:,.0f} 원", f"{metrics[1]:,.0f} ₫", f"{metrics[2]:,.0f} ₫", datetime.now().strftime("%m/%d %H:%M")]
                })
                try: conn.update(worksheet="summary", data=summary_data)
                except: pass
            
            st.cache_data.clear() # 저장 후 캐시 초기화
            return True
            
        except Exception as e:
            st.error(f"Cloud 저장 실패: {e}")
            return False

@st.cache_data(ttl=0)
def load_cash_count():
    """현금 카운터의 마지막 저장 상태를 불러옵니다."""
    try:
        df = conn.read(worksheet="cash_count", ttl="0s")
        if df is not None and not df.empty:
            return dict(zip(df['Bill'].astype(int), df['Count'].astype(int)))
        return {b: 0 for b in BILLS}
    except:
        return {b: 0 for b in BILLS}

def save_cash_count(counts_dict):
    """현금 카운터의 현재 상태를 클라우드에 저장합니다."""
    try:
        df = pd.DataFrame(list(counts_dict.items()), columns=['Bill', 'Count'])
        conn.update(worksheet="cash_count", data=df)
        st.cache_data.clear()
        st.toast("현금 수량이 구글 시트에 저장되었습니다! 💾")
        return True
    except:
        return False

# 초기 데이터 실행
ledger_df = load_data()
cloud_cash_counts = load_cash_count()

# --- SECTION 3: [Module B] FIFO Inventory & Asset Engine ---
# [Status: Modified for Global Variable Stability]
def get_inventory_status(df):
    """지갑별 환율 배치를 FIFO로 정밀 추적하여 현재 잔액을 계산합니다."""
    inv = { "트래블로그(VND)": {}, "현금(VND)": {} }
    if df.empty: return inv

    for _, row in df.iterrows():
        qty, rate, desc, cat, method = row['Amount'], row['AppliedRate'], str(row['Description']), row['Category'], row['PaymentMethod']
        
        # 1. 유입 (충전/환전/직접환전)
        if cat in ['충전', '환전', '입금', '직접환전']:
            target = "트래블로그(VND)" if "카드VND" in desc else "현금(VND)"
            inv[target][rate] = inv[target].get(rate, 0) + qty
            
        # 2. ATM출금 (카드 배치 -> 현금 배치로 자동 전이)
        elif cat == 'ATM출금':
            temp_qty = qty
            for r in sorted(inv["트래블로그(VND)"].keys()):
                if temp_qty <= 0: break
                take = min(temp_qty, inv["트래블로그(VND)"][r])
                inv["트래블로그(VND)"][r] -= take
                inv["현금(VND)"][r] = inv["현금(VND)"].get(r, 0) + take
                temp_qty -= take
                
        # 3. 지출 (FIFO 소진)
        elif row['IsExpense'] == 1 and row['Currency'] == TRAVEL_CURRENCY:
            target = "트래블로그(VND)" if "트래블로그" in method else "현금(VND)"
            temp_qty = qty
            for r in sorted(inv.get(target, {}).keys()):
                if temp_qty <= 0: break
                take = min(temp_qty, inv[target][r]); inv[target][r] -= take; temp_qty -= take
    return inv

current_inventory = get_inventory_status(ledger_df)

# [CORE FIX] WAR를 전역 함수 외부에서도 접근 가능하도록 확실히 정의 (NameError 방지)
def calculate_global_war(df):
    swaps = df[(df['Category'].isin(['충전', '환전', '입금', '직접환전'])) & (df['Currency'] == TRAVEL_CURRENCY)]
    if swaps.empty or swaps['Amount'].sum() == 0:
        return 0.0561
    total_krw = (swaps['Amount'] * swaps['AppliedRate']).sum()
    total_vnd = swaps['Amount'].sum()
    return total_krw / total_vnd

# 전역 가중평균환율 상수로 고정
WAR = calculate_global_war(ledger_df)

def auto_calc_fifo_rate(amount, method):
    """현재 재고 상황을 바탕으로 가중평균 환율을 자동 도출합니다."""
    target = "트래블로그(VND)" if "트래블로그" in method else "현금(VND)"
    available = {r: q for r, q in current_inventory.get(target, {}).items() if q > 0}
    if not available: return WAR
    
    total_cost_krw, remaining = 0.0, amount
    for r in sorted(available.keys()):
        if remaining <= 0: break
        take = min(remaining, available[r]); total_cost_krw += take * r; remaining -= take
    if remaining > 0: total_cost_krw += remaining * max(available.keys())
    return total_cost_krw / amount if amount > 0 else 0

def calculate_summary_metrics(df):
    """사이드바 및 대시보드 표시용 최종 지표 산출"""
    if df.empty: return 0.0, 0.0, 0.0
    # 예산 계산: KRW 1:1, 외화는 AppliedRate 사용
    bank_actions = df[df['PaymentMethod'] == '원화계좌']
    b_total = (bank_actions[bank_actions['Currency'] == 'KRW']['Amount']).sum() + \
              (bank_actions[bank_actions['Currency'] != 'KRW']['Amount'] * bank_actions[bank_actions['Currency'] != 'KRW']['AppliedRate']).sum()
    card_v = sum(current_inventory["트래블로그(VND)"].values())
    cash_v = sum(current_inventory["현금(VND)"].values())
    return b_total, card_v, cash_v

# --- SECTION 4: [Module C] Intelligent Input (📝 입력) ---
# [Status: Restored Full UI Logic and Reactive Keys]
st.title("🌏 여행 가계부 (GTL Platform)")
tab_in, tab_his, tab_stats, tab_final = st.tabs(["📝 입력", "🔍 내역 조회", "📊 일일 결산", "🏁 종료 보고서"])

with tab_in:
    mode = st.radio("기록 모드 선택", ["일반 지출", "자산 이동"], horizontal=True, key="mode_radio")
    if mode == "일반 지출":
        # 항목 -> 통화 -> 환율 -> 결제수단 -> 금액 -> 내용
        cat = st.radio("항목 선택", EXPENSE_CATS, index=st.session_state.last_cat_idx, horizontal=True, key="exp_cat")
        st.session_state.last_cat_idx = EXPENSE_CATS.index(cat)
        
        # [Added] 입국/출국 전용 간소화 UI
        if cat in ["입국", "출국"]:
            st.info(f"✈️ {cat} 일정을 기록합니다. 금액 없이 날짜와 메모만 남기세요.")
            desc = st.text_input("내용 (메모)", placeholder="편명, 시간 등", key="exp_desc_diary")
            sel_date = st.date_input("날짜", datetime.now(), key="exp_date_diary")
            if st.button("🚀 일정 기록 완료", use_container_width=True):
                new_row = pd.DataFrame([{'Date': sel_date.strftime("%m/%d(%a)"), 'Category': cat, 'Description': desc, 'Currency': 'KRW', 'Amount': 0, 'PaymentMethod': '원화계좌', 'IsExpense': 1, 'AppliedRate': 1.0}])
                if save_data(pd.concat([ledger_df[COLUMNS], new_row], ignore_index=True)): st.rerun()
        else:
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                curr = st.selectbox("통화", ["VND", "KRW", "USD"], key="exp_curr")
                r_opts = [f"{st.session_state.rate_names[i]} ({st.session_state.rates[i]:.4f})" for i in range(5)]
                sel_r_str = st.selectbox("참조 환율 선택 (또는 자동)", r_opts, index=st.session_state.last_rate_idx, key="exp_rate_sel")
                st.session_state.last_rate_idx = r_opts.index(sel_r_str); rv = st.session_state.rates[st.session_state.last_rate_idx]
                met = st.selectbox("결제수단", ["현금(VND)", "트래블로그(VND)", "원화계좌"], key="exp_met")
            with col_m2:
                # 동적 포맷팅 적용 (정수 vs 소수점)
                if curr in ["VND", "KRW"]: amt = st.number_input("금액 (Amount)", min_value=0, step=1000 if curr=="VND" else 1, format="%d", key="exp_amt_int")
                else: amt = st.number_input("금액 (Amount)", min_value=0.0, step=1.0, format="%.2f", key="exp_amt_float")
                
                # [CORE FIX] FIFO 환율 자동 주입 (다이내믹 키 사용으로 갱신 보장)
                if curr == TRAVEL_CURRENCY and amt > 0:
                    calc_rate = auto_calc_fifo_rate(amt, met)
                    st.caption(f"💡 인벤토리 계산 환율: **{calc_rate:.5f}**")
                    cr_final = st.number_input("확정 환율", value=calc_rate, format="%.5f", key=f"exp_cr_auto_{met}_{amt}")
                else:
                    cr_final = st.number_input("확정 환율", value=(1.0 if curr=="KRW" else rv), format="%.5f", key=f"exp_cr_man_{curr}")
            
            desc = st.text_input("내용 (메모)", key="exp_desc"); sel_date = st.date_input("날짜", datetime.now(), key="exp_date")
            if st.button("🚀 지출 기록하기", use_container_width=True):
                if amt < 0: st.warning("음수는 입력할 수 없습니다.")
                else:
                    new_row = pd.DataFrame([{'Date': sel_date.strftime("%m/%d(%a)"), 'Category': cat, 'Description': desc, 'Currency': curr, 'Amount': amt, 'PaymentMethod': met, 'IsExpense': 1, 'AppliedRate': cr_final}])
                    b_now, card_now, cash_now = calculate_summary_metrics(ledger_df)
                    if save_data(pd.concat([ledger_df[COLUMNS], new_row], ignore_index=True), metrics=[b_now, card_now, cash_now]): st.rerun()
    else:
        # [Module C - 자산 이동 모드: ATM Rate Inheritance]
        st.subheader("🔁 자산 이동 및 환전 (ATM 환율 자동상속)")
        ty = st.selectbox("유형", ["직접환전 (원화계좌 -> 지폐VND)", "충전 (원화계좌 -> 카드VND)", "ATM출금 (카드VND -> 지폐VND)"], key="tr_type")
        c1, c2 = st.columns(2)
        with c1:
            t_amt = st.number_input("받은 금액 (VND)", min_value=0, step=1000, format="%d", key="tr_target")
            if "ATM" in ty:
                # ATM 출금 시 카드 재고에서 환율 자동 상속
                inherited_r = auto_calc_fifo_rate(t_amt, "트래블로그(VND)")
                st.info(f"💳 카드 재고로부터 계승된 환율: **{inherited_r:.5f}**")
                s_cost = st.number_input("인출 원금 확인 (VND)", value=int(t_amt), key="tr_source_atm")
                applied_tr_rate = inherited_r
            else:
                r_opts_tr = [f"{st.session_state.rate_names[i]} ({st.session_state.rates[i]:.4f})" for i in range(5)]
                sel_r_tr = st.selectbox("적용 환율 프리셋", r_opts_tr, key="tr_rate_preset"); rv_tr = st.session_state.rates[r_opts_tr.index(sel_r_tr)]
                s_cost = st.number_input("소요 원금 (지불 비용)", min_value=0, value=int(t_amt * rv_tr), step=1, format="%d", key="tr_source_swap")
                applied_tr_rate = s_cost / t_amt if t_amt > 0 else 0
        with c2:
            tr_date = st.date_input("이동 날짜", datetime.now(), key="tr_date")
            fee_amt = st.number_input("ATM 수수료 (VND)", min_value=0, step=1000, format="%d", key="tr_fee")
        if st.button("🔄 이동 실행", use_container_width=True):
            rate = applied_tr_rate
            dest = "카드VND" if "카드" in ty else "지폐VND"
            main_row = pd.DataFrame([{'Date': tr_date.strftime("%m/%d(%a)"), 'Category': ty.split(" ")[0], 'Description': f"{ty.split(' ')[0]} (-> {dest})", 'Currency': "VND", 'Amount': t_amt, 'PaymentMethod': "원화계좌" if "원화계좌" in ty else "트래블로그(VND)", 'IsExpense': 0, 'AppliedRate': rate}])
            final_entry = pd.concat([ledger_df[COLUMNS], main_row], ignore_index=True)
            if fee_amt > 0:
                fee_rate = auto_calc_fifo_rate(fee_amt, "트래블로그(VND)")
                fee_row = pd.DataFrame([{'Date': tr_date.strftime("%m/%d(%a)"), 'Category': "수수료", 'Description': f"{ty.split(' ')[0]} 수수료", 'Currency': "VND", 'Amount': fee_amt, 'PaymentMethod': "트래블로그(VND)", 'IsExpense': 1, 'AppliedRate': fee_rate}])
                final_entry = pd.concat([final_entry, fee_row], ignore_index=True)
            b_now, card_now, cash_now = calculate_summary_metrics(ledger_df); save_data(final_entry, metrics=[b_now, card_now, cash_now]); st.rerun()

# --- SECTION 5: [Sidebar & Module F: Cash Tool] ---
with st.sidebar:
    st.title("💰 Wallet Status")
    b_val, card_val, cash_val = calculate_summary_metrics(ledger_df)
    st.metric("🏦 인출 총 원화 (예산)", f"{b_val:,.0f} 원")
    st.caption(f"평균 적용 환율: 100₫ = {WAR*100:.2f}원")
    st.divider(); st.metric("💳 카드 VND 잔액", f"{card_val:,.0f} ₫"); st.metric("💵 현금 VND 잔액", f"{cash_val:,.0f} ₫")
    with st.expander("💵 실물 지폐 정산기"):
        total_ph = sum([b * st.number_input(f"{b:,.0f} ₫", min_value=0, step=1, value=int(cloud_cash_counts.get(b,0)), key=f"p_{b}") for b in BILLS])
        if st.button("💾 현금 수량 저장"): save_cash_count({b: st.session_state[f"p_{b}"] for b in BILLS}); st.rerun()
        st.write(f"실물 합계: {total_ph:,.0f} ₫ / 차액: {total_ph - cash_val:,.0f} ₫")
    with st.expander("💱 환율 매니저"):
        for i in range(5):
            st.session_state.rate_names[i] = st.text_input(f"이름 {i+1}", value=st.session_state.rate_names[i], key=f"rn_{i}")
            st.session_state.rates[i] = st.number_input(f"환율 {i+1}", value=st.session_state.rates[i], format="%.4f", key=f"rv_{i}")
    if st.button("🔄 Cloud Refresh", use_container_width=True): st.cache_data.clear(); st.rerun()

# --- SECTION 6: [Module D, E: History & Settlement] ---
with tab_his:
    st.subheader("🔍 내역 조회 및 수정")
    if not ledger_df.empty:
        edited_df = st.data_editor(ledger_df, use_container_width=True, num_rows="dynamic", key="editor_gtl_v120")
        col_ed1, col_ed2 = st.columns(2)
        with col_ed1:
            if not ledger_df.equals(edited_df) and st.button("💾 수정사항 저장", type="primary"):
                b_n, card_n, cash_n = calculate_summary_metrics(edited_df); save_data(edited_df[COLUMNS], metrics=[b_n, card_n, cash_n]); st.rerun()
        with col_ed2:
            if st.button("🗑️ 마지막 행 삭제", use_container_width=True):
                if save_data(ledger_df[COLUMNS][:-1]): st.rerun()

with tab_stats:
    # [Restored Variable Sync: tab_stats defined in tabs() above]
    if not ledger_df.empty:
        exp_df = ledger_df[ledger_df['IsExpense'] == 1].copy()
        if not exp_df.empty:
            exp_df['KRW_val'] = exp_df.apply(lambda r: r['Amount'] if r['Currency'] == 'KRW' else r['Amount'] * WAR, axis=1)
            exp_df['VND_val'] = exp_df.apply(lambda r: r['Amount'] if r['Currency'] == 'VND' else r['Amount'] / WAR if WAR>0 else 0, axis=1)
            exp_df['IsSurvival'] = exp_df['Category'].apply(lambda x: 1 if x in SURVIVAL_CATS else 0)

            # [Restored] FIFO 재고 현황판
            st.subheader("📦 환율별 재고 현황 (FIFO 히스토리)")
            inv_hist = get_inventory_status(ledger_df)
            for wallet, batches in inv_hist.items():
                st.write(f"**{wallet}**")
                inv_list = []
                for r in sorted(batches.keys()):
                    q = batches[r]
                    status_text = f"{q:,.0f} ₫" if q > 0 else "🚫 소진완료"
                    inv_list.append({"환율": f"{r:.4f}", "잔액 상태": status_text, "원화가치": f"{r*max(0,q):,.0f} 원"})
                st.table(inv_list)

            # 요약 섹션 (Descending Sort applied)
            st.subheader("🏁 여행 경제 요약")
            c1, c2 = st.columns(2)
            with c1:
                dom_df = exp_df[((exp_df['Currency'] == 'KRW') & (exp_df['PaymentMethod'] == '원화계좌')) & (~exp_df['Category'].isin(['입국','출국']))]
                st.info("🇰🇷 국내 지출"); st.metric("총액", f"{dom_df['KRW_val'].sum():,.0f} 원")
                with st.expander("세부 내역"):
                    dg = dom_df.groupby('Category').agg({'KRW_val':'sum', 'Date':'count'}).sort_values(by='KRW_val', ascending=False)
                    for cat, row in dg.iterrows(): st.write(f"- {cat}({int(row['Date'])}회): {row['KRW_val']:,.0f} 원")
            with c2:
                ovr_df = exp_df[~((exp_df['Currency'] == 'KRW') & (exp_df['PaymentMethod'] == '원화계좌'))]
                st.success("🇻🇳 해외 지출"); st.metric("총액", f"{ovr_df['KRW_val'].sum():,.0f} 원")
                with st.expander("해외 세부 내역"):
                    og = ovr_df.groupby('Category').agg({'VND_val':'sum', 'Date':'count'}).sort_values(by='VND_val', ascending=False)
                    for cat, row in og.iterrows(): st.write(f"- {cat}({int(row['Date'])}회): {row['VND_val']:,.0f} ₫")

            # 정산표 [Crash Fix]
            st.divider(); daily_set = exp_df.groupby('Date').agg({'KRW_val': 'sum', 'VND_val': 'sum'}).reset_index()
            surv_only = exp_df[exp_df['IsSurvival'] == 1].groupby('Date').agg({'KRW_val': 'sum', 'VND_val': 'sum'}).reset_index().rename(columns={'KRW_val': 'S_KRW', 'VND_val': 'S_VND'})
            daily_table = pd.merge(daily_set, surv_only, on='Date', how='left').fillna(0)
            # 숫자 컬럼만 선택하여 포맷팅
            numeric_labels = ['총(원)', '총(동)', '일상(원)', '일상(동)']
            table_display = daily_table.rename(columns={'Date':'날짜','KRW_val':'총(원)','VND_val':'총(동)','S_KRW':'일상(원)','S_VND':'일상(동)'})
            st.table(table_display.style.format({c: '{:,.0f}' for c in numeric_labels if c in table_display.columns}))

            # 이중 막대 차트
            c_mode = st.radio("차트 통화 선택", ["원화(KRW)", "동화(VND)"], horizontal=True, key="st_curr")
            chart_final = daily_table.copy(); chart_final['Date_Clean'] = chart_final['Date'].str.split('(').str[0]
            y_s, y_t = ('S_KRW', 'KRW_val') if "원화" in c_mode else ('S_VND', 'VND_val')
            fig = go.Figure()
            fig.add_trace(go.Bar(x=chart_final['Date_Clean'], y=chart_final[y_s], name='일상경비', marker_color='#00FF00', text=chart_final[y_s], texttemplate='%{text:,.0f}'))
            fig.add_trace(go.Bar(x=chart_final['Date_Clean'], y=chart_final[y_t].apply(lambda x: x if x > 0 else None), name='전체지출', marker_color='#FF00FF'))
            fig.update_layout(barmode='group', margin=dict(l=5, r=5, t=30, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig, use_container_width=True)

# --- SECTION 7: [Module G: Final Strategic Report] ---
with tab_final:
    # [Status: Restored and Scope-Safe]
    if not ledger_df.empty and not exp_df.empty:
        # [Strategy] 7-day Average Calculation (Apr 21-27)
        overseas_active = exp_df[~((exp_df['Currency'] == 'KRW') & (exp_df['PaymentMethod'] == '원화계좌'))]
        unique_days = len(overseas_active['Date'].unique())
        total_trip_krw = exp_df['KRW_val'].sum(); total_trip_vnd = exp_df['VND_val'].sum()
        dom_total_krw = exp_df[exp_df['Category'].isin(DOMESTIC_CATS)]['KRW_val'].sum()
        ovr_total_krw = total_trip_krw - dom_total_krw; ovr_total_vnd = exp_df[~exp_df['Category'].isin(DOMESTIC_CATS)]['VND_val'].sum()
        local_survival_krw = exp_df[(exp_df['IsSurvival'] == 1) & (~exp_df['Category'].isin(FIXED_COST_CATS))]['KRW_val'].sum()
        
        # [Added] KPI Metrics with Two-Line HTML Formatting
        def kpi_box(title, krw, vnd=None):
            vnd_str = f"<div class='kpi-value-vnd'>({vnd:,.0f} ₫)</div>" if vnd is not None else ""
            return f"<div class='kpi-box'><div class='kpi-title'>{title}</div><div class='kpi-value-krw'>{krw:,.0f} 원</div>{vnd_str}</div>"

        st.header("🏁 푸꾸옥 여행 최종 전략 리포트")
        k1, k2, k3, k4 = st.columns(4)
        with k1: st.markdown(kpi_box("여행 최종 총 지출", total_trip_krw, total_trip_vnd), unsafe_allow_html=True)
        with k2: st.markdown(kpi_box("국내 지출 총액", dom_total_krw), unsafe_allow_html=True)
        with k3: st.markdown(kpi_box("현지 지출 총액", ovr_total_krw, ovr_total_vnd), unsafe_allow_html=True)
        avg_v = (local_survival_krw / WAR) / unique_days if unique_days > 0 and WAR > 0 else 0
        with k4: st.markdown(kpi_box(f"현지 1일 평균 ({unique_days}일)", local_survival_krw/unique_days if unique_days > 0 else 0, avg_v), unsafe_allow_html=True)

        # 1. 트리맵 (Greens, Detailed Labels)
        st.subheader("🌳 지출 구조 상세 분석 (Treemap)")
        fig_tree = px.treemap(exp_df, path=['Category', 'Description'], values='KRW_val', color='KRW_val', color_continuous_scale='Greens')
        fig_tree.update_traces(texttemplate="<b>%{label}</b><br>%{value:,.0f}원<br>%{percentRoot:.1%}")
        fig_tree.update_layout(margin=dict(l=0, r=0, t=10, b=0), font=dict(size=14))
        st.plotly_chart(fig_tree, use_container_width=True)

        # 2. 도넛 차트 (Center Total Label)
        st.subheader("🍕 카테고리별 지출 비중")
        cat_pie = exp_df.groupby('Category')['KRW_val'].sum().reset_index().sort_values(by='KRW_val', ascending=False)
        fig_donut = px.pie(cat_pie, values='KRW_val', names='Category', hole=0.5, color_discrete_sequence=px.colors.qualitative.Set3)
        fig_donut.update_traces(textposition='inside', textinfo='label+value+percent', texttemplate='%{label}<br>%{value:,.0f}원<br>%{percent:.1%}')
        until_day = exp_df['Date'].max().split('(')[0]
        fig_donut.add_annotation(text=f"<b>총 지출</b><br>{total_trip_krw:,.0f} 원<br><span style='font-size:10px'>Until {until_day}</span>", showarrow=False, font=dict(size=16))
        fig_donut.update_layout(height=600, margin=dict(l=10, r=10, t=50, b=100), legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5), uniformtext_minsize=11, uniformtext_mode='hide')
        st.plotly_chart(fig_donut, use_container_width=True)
    else: st.info("데이터를 입력하면 최종 보고서가 활성화됩니다.")

st.caption(f"GTL Platform v1.20 | Volume: 26.6 KB | Sync: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Strategic Partner Gem")
