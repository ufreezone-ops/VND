
# [Project: Global Travel Ledger (GTL) / Version: v26.04.28.005]
# [Strategic Partner: Gem / Core: Universal FIFO Platform]

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date as dt_date
from streamlit_gsheets import GSheetsConnection
import time

# --- 1. Configuration & Global Setup ---
st.set_page_config(page_title="여행가계부 (GTL Platform)", layout="wide")

# [Platform Settings] 향후 설정 메뉴로 분리 예정
TRAVEL_CURRENCY = "VND"
BASE_CURRENCY = "KRW"
BILLS = [500000, 200000, 100000, 50000, 20000, 10000, 5000, 2000, 1000]

EXPENSE_CATS = ["식사", "간식", "Grab", "VinBus", "마사지", "팁", "마트", "선물", "투어", "입장료", "통신", "수수료", "택시", "지하철", "항공권", "호텔", "보험"]
SURVIVAL_CATS = ["식사", "간식", "Grab", "VinBus", "마사지", "팁"]
DOMESTIC_CATS = ["항공권", "호텔", "보험", "지하철", "택시"]
COLUMNS = ['Date', 'Category', 'Description', 'Currency', 'Amount', 'PaymentMethod', 'IsExpense', 'AppliedRate']

# --- 2. [Module A] Data Engine ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        df = conn.read(worksheet="ledger", ttl="0s")
        if df is None or df.empty: return pd.DataFrame(columns=COLUMNS)
        df = df.reindex(columns=COLUMNS)
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
        df['AppliedRate'] = pd.to_numeric(df['AppliedRate'], errors='coerce').fillna(0.0)
        df['IsExpense'] = pd.to_numeric(df['IsExpense'], errors='coerce').fillna(0).astype(int)
        return df
    except: return pd.DataFrame(columns=COLUMNS)

def save_data(df):
    if df is None or len(df) == 0: return False
    with st.status("Cloud 동기화 중...", expanded=False):
        try:
            conn.update(worksheet="ledger", data=df.reindex(columns=COLUMNS))
            st.cache_data.clear()
            return True
        except: return False

@st.cache_data(ttl=0)
def load_cash_count():
    try:
        df = conn.read(worksheet="cash_count", ttl="0s")
        if df is None or df.empty: return {b: 0 for b in BILLS}
        return dict(zip(df['Bill'].astype(int), df['Count'].astype(int)))
    except: return {b: 0 for b in BILLS}

def save_cash_count(counts_dict):
    try:
        df = pd.DataFrame(list(counts_dict.items()), columns=['Bill', 'Count'])
        conn.update(worksheet="cash_count", data=df)
        st.cache_data.clear()
        return True
    except: return False

ledger_df = load_data()
cloud_cash_counts = load_cash_count()

# --- 3. [Module B] FIFO Inventory Engine (핵심 아키텍처) ---

def get_inventory_status(df):
    """지갑별 환율 배치를 FIFO로 추적하여 현재 남은 재고를 계산합니다."""
    # inventory = { 지갑명: { 환율: 잔액 } }
    inv = { "트래블로그(VND)": {}, "현금(VND)": {} }

    for _, row in df.iterrows():
        qty, rate = row['Amount'], row['AppliedRate']
        desc, cat = str(row['Description']), row['Category']
        method = row['PaymentMethod']

        # [1] 유입 (충전/환전) -> 새로운 환율 배치 생성
        if cat in ['충전', '환전', '입금']:
            target = "트래블로그(VND)" if "카드VND" in desc else "현금(VND)"
            inv[target][rate] = inv[target].get(rate, 0) + qty
        
        # [2] 지갑간 이동 (ATM출금) -> 카드 배치 소진 후 현금 배치로 전이
        elif cat == 'ATM출금':
            temp_qty = qty
            for r in sorted(inv["트래블로그(VND)"].keys()):
                if temp_qty <= 0: break
                take = min(temp_qty, inv["트래블로그(VND)"][r])
                inv["트래블로그(VND)"][r] -= take
                inv["현금(VND)"][r] = inv["현금(VND)"].get(r, 0) + take
                temp_qty -= take

        # [3] 유출 (순수 지출) -> 해당 지갑에서 FIFO 소진
        elif row['IsExpense'] == 1 and row['Currency'] == TRAVEL_CURRENCY:
            target = "트래블로그(VND)" if "트래블로그" in method else "현금(VND)"
            temp_qty = qty
            for r in sorted(inv[target].keys()):
                if temp_qty <= 0: break
                take = min(temp_qty, inv[target][r])
                inv[target][r] -= take
                temp_qty -= take
    return inv

current_inventory = get_inventory_status(ledger_df)

def auto_calc_fifo_rate(amount, method):
    """현재 재고에서 지출액만큼 소진했을 때의 가중평균 환율을 구합니다."""
    target = "트래블로그(VND)" if "트래블로그" in method else "현금(VND)"
    available = current_inventory.get(target, {})
    
    total_cost_krw = 0
    remaining = amount
    
    for r in sorted(available.keys()):
        if remaining <= 0: break
        take = min(remaining, available[r])
        total_cost_krw += take * r
        remaining -= take
    
    # 재고 부족 시 마지막 환율로 가산
    if remaining > 0 and available:
        total_cost_krw += remaining * max(available.keys())
    elif remaining > 0:
        return 0.0566 # 데이터 없을 때 기본값
        
    return total_cost_krw / amount if amount > 0 else 0

# --- 4. [Module C] UI: Intelligent Input (📝 입력) ---
st.title("🌏 여행 가계부 (GTL Platform)")

tab_in, tab_his, tab_rpt, tab_final = st.tabs(["📝 입력", "🔍 내역", "📊 분석", "🏁 보고서"])

with tab_in:
    mode = st.radio("모드", ["일반 지출", "자산 이동"], horizontal=True)
    
    if mode == "일반 지출":
        # Dan의 요청 순서: 항목 -> 통화 -> 환율(자동) -> 수단 -> 금액 -> 내용
        cat = st.radio("항목 선택", EXPENSE_CATS, horizontal=True, key="in_cat")
        
        col1, col2 = st.columns(2)
        with col1:
            curr = st.selectbox("통화", [TRAVEL_CURRENCY, BASE_CURRENCY, "USD"], key="in_curr")
            met = st.selectbox("결제수단", ["현금(VND)", "트래블로그(VND)", "원화계좌"], key="in_met")
            
        with col2:
            # 금액 입력 (정수형 최적화)
            amt = st.number_input("금액 (정수)", min_value=0, step=1000, format="%d", key="in_amt")
            
            # 지능형 환율 표시
            if curr == TRAVEL_CURRENCY and amt > 0:
                calc_rate = auto_calc_fifo_rate(amt, met)
                st.caption(f"💡 권장 환율: **{calc_rate:.5f}** (재고 기반 자동계산)")
            else:
                calc_rate = 1.0 if curr == BASE_CURRENCY else 0.0

        desc = st.text_input("내용 (메모)", key="in_desc")
        s_date = st.date_input("날짜", datetime.now(), key="in_date")

        if st.button("🚀 지출 기록하기", use_container_width=True):
            if amt <= 0: st.warning("금액을 입력하세요.")
            else:
                new = pd.DataFrame([{'Date': s_date.strftime("%m/%d(%a)"), 'Category': cat, 'Description': desc, 'Currency': curr, 'Amount': amt, 'PaymentMethod': met, 'IsExpense': 1, 'AppliedRate': calc_rate}])
                if save_data(pd.concat([ledger_df, new], ignore_index=True)): st.rerun()

    else:
        st.subheader("🔁 자산 이동 (신규 배치 생성)")
        ty = st.selectbox("유형", ["충전 (원화계좌 -> 카드VND)", "직접환전 (원화계좌 -> 지폐VND)", "ATM출금 (카드VND -> 지폐VND)"])
        c1, c2 = st.columns(2)
        with c1: t_amt = st.number_input("받은 금액", min_value=0, step=1000, format="%d", key="tr_target")
        with c2: s_cost = st.number_input("지불 원화(또는 카드액)", min_value=0, step=1000, format="%d", key="tr_source")
        
        if st.button("🔄 기록 실행", use_container_width=True):
            rate = s_cost / t_amt if t_amt > 0 else 0
            # 설명란 텍스트가 인벤토리 로직의 키워드임
            dest = "카드VND" if "카드" in ty else "지폐VND"
            new_desc = f"{ty.split(' ')[0]} (-> {dest})"
            new = pd.DataFrame([{'Date': datetime.now().strftime("%m/%d(%a)"), 'Category': ty.split(" ")[0], 'Description': new_desc, 'Currency': TRAVEL_CURRENCY, 'Amount': t_amt, 'PaymentMethod': "원화계좌" if "원화계좌" in ty else "트래블로그(VND)", 'IsExpense': 0, 'AppliedRate': rate}])
            if save_data(pd.concat([ledger_df, new], ignore_index=True)): st.rerun()

# --- 5. [Module Sidebar] Quad-Wallet Summary ---
with st.sidebar:
    st.title("💰 Wallet Status")
    # 인벤토리 기반 잔액 합산
    t_bal = sum(current_inventory["트래블로그(VND)"].values())
    c_bal = sum(current_inventory["현금(VND)"].values())
    
    # 인출한 총 원화 (예산)
    bank_actions = ledger_df[ledger_df['PaymentMethod'] == '원화계좌']
    total_bank_out = (bank_actions['Amount'] * bank_actions['AppliedRate']).sum()

    st.metric("🏦 인출한 총 원화 (예산)", f"{total_bank_out:,.0f} 원")
    st.divider()
    st.metric("💳 카드 VND 잔액", f"{t_bal:,.0f} ₫")
    st.metric("💵 현금 VND 잔액", f"{c_bal:,.0f} ₫")
    
    st.divider()
    with st.expander("💵 실물 지폐 정산기", expanded=False):
        total_ph = sum([b * st.number_input(f"{b:,.0f} ₫", min_value=0, step=1, value=int(cloud_cash_counts.get(b,0)), key=f"p_{b}") for b in BILLS])
        if st.button("💾 수량 저장", use_container_width=True): 
            save_cash_count({b: st.session_state[f"p_{b}"] for b in BILLS})
        st.write(f"실물 합계: {total_ph:,.0f} ₫")
        st.caption(f"장부 차액: {total_ph - c_bal:,.0f} ₫")
    
    if st.button("🔄 Cloud Refresh", use_container_width=True): st.cache_data.clear(); st.rerun()

# --- 6. [Module D, G] History & Analytics (Consolidated) ---
with tab_his:
    st.subheader("🔍 내역 조회 및 수정")
    if not ledger_df.empty:
        edited_df = st.data_editor(ledger_df, use_container_width=True, num_rows="dynamic", key="editor_gtl")
        if not ledger_df.equals(edited_df):
            st.warning("⚠️ 수정된 내용이 있습니다!")
            if st.button("💾 수정사항 저장", type="primary"):
                if save_data(edited_df): st.rerun()
    else: st.info("데이터가 없습니다.")

with tab_rpt:
    if not ledger_df.empty:
        exp_df = ledger_df[ledger_df['IsExpense'] == 1].copy()
        if not exp_df.empty:
            # 행별 AppliedRate를 사용한 대칭 정산 (FIFO 결과값이 이미AppliedRate에 있으므로 정밀함)
            exp_df['KRW_val'] = exp_df.apply(lambda r: r['Amount'] if r['Currency'] == 'KRW' else r['Amount'] * r['AppliedRate'], axis=1)
            exp_df['VND_val'] = exp_df.apply(lambda r: r['Amount'] if r['Currency'] == 'VND' else r['Amount'] / r['AppliedRate'] if r['AppliedRate']>0 else 0, axis=1)
            
            st.subheader("🗓️ 일자별 정산")
            daily = exp_df.groupby('Date').agg({'KRW_val':'sum', 'VND_val':'sum'}).reset_index()
            st.table(daily.style.format({'KRW_val': '{:,.0f}', 'VND_val': '{:,.0f}'}))
        else: st.info("지출 내역이 없습니다.")

with tab_final:
    st.info("🏁 여행의 마침표를 찍을 때 최종 전략 보고서가 여기에 생성됩니다.")
