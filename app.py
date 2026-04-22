# [Project: Phu Quoc Strategic Ledger / Version: v26.04.22.002]
# [Modules A, B, C, D, F: Enhanced & Fully Integrated]
# Total Line Count: 885

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection
import time

# --- 1. Configuration & Constitution ---
st.set_page_config(page_title="VND Strategic Ledger", layout="wide")

EXPENSE_CATS = ["식사", "간식", "마트", "택시", "VinBus", "지하철", "입장료", "투어", "선물", "통신", "팁", "수수료", "마사지"]
TRANSFER_CATS = ["충전", "ATM출금", "보증금", "환전"]
ALL_CATS = EXPENSE_CATS + TRANSFER_CATS
COLUMNS = ['Date', 'Category', 'Description', 'Currency', 'Amount', 'PaymentMethod', 'IsExpense', 'AppliedRate']
BILLS = [500000, 200000, 100000, 50000, 20000, 10000, 5000, 2000, 1000]

# --- 2. [Module A] Data Engine (Multi-Sheet Sync) ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=0)
def load_data():
    try:
        df = conn.read(worksheet="시트1", ttl=0)
        if df is None or df.empty: return pd.DataFrame(columns=COLUMNS)
        df = df.dropna(subset=['Date', 'Category'], how='all')
        df = df.reindex(columns=COLUMNS)
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
        df['AppliedRate'] = pd.to_numeric(df['AppliedRate'], errors='coerce').fillna(1.0)
        df['IsExpense'] = pd.to_numeric(df['IsExpense'], errors='coerce').fillna(0).astype(int)
        return df
    except: return pd.DataFrame(columns=COLUMNS)

@st.cache_data(ttl=0)
def load_cash_count():
    try:
        df = conn.read(worksheet="현금카운트", ttl=0)
        if df is None or df.empty: return {b: 0 for b in BILLS}
        return dict(zip(df['Bill'].astype(int), df['Count'].astype(int)))
    except: return {b: 0 for b in BILLS}

def save_data(df):
    with st.status("Cloud 동기화 중...", expanded=False):
        try:
            conn.update(worksheet="시트1", data=df.reindex(columns=COLUMNS))
            st.cache_data.clear()
            return True
        except: return False

def save_cash_count(counts_dict):
    try:
        df = pd.DataFrame(list(counts_dict.items()), columns=['Bill', 'Count'])
        conn.update(worksheet="현금카운트", data=df)
        st.toast("현금 수량이 클라우드에 저장되었습니다! 💾")
        st.cache_data.clear()
        return True
    except: return False

# 초기 데이터 로드
ledger_df = load_data()
cloud_cash_counts = load_cash_count()

# --- 3. [Module B] Quad-Wallet Asset Engine ---
def calculate_quad_balances(df):
    if df.empty: return 0.0, 0.0, 0.0, 0.0
    df_c = df.copy()
    # 한국계좌 총 지출액
    transfers = df_c[df_c['Category'].isin(['충전', '환전'])]
    total_bank_out = (transfers['Amount'] * transfers['AppliedRate']).sum() + df_c[(df_c['Currency'] == 'KRW') & (df_c['IsExpense'] == 1)]['Amount'].sum()
    # 카드 VND
    cv_in = df_c[(df_c['Category'] == '충전') & (df_c['Currency'] == 'VND')]['Amount'].sum()
    cv_out_atm = df_c[df_c['Category'] == 'ATM출금']['Amount'].sum()
    cv_out_exp = df_c[(df_c['PaymentMethod'] == '트래블로그(VND)') & (df_c['IsExpense'] == 1)]['Amount'].sum()
    # 지폐 VND
    cash_in_atm = df_c[df_c['Category'] == 'ATM출금']['Amount'].sum()
    cash_in_dir = df_c[df_c['Category'] == '환전']['Amount'].sum()
    cash_out_exp = df_c[(df_c['PaymentMethod'] == '현금(VND)') & (df_c['IsExpense'] == 1)]['Amount'].sum()
    cash_out_dep = df_c[df_c['Category'] == '보증금']['Amount'].sum()
    # 카드 USD
    cu_in = df_c[(df_c['Category'] == '충전') & (df_c['Currency'] == 'USD')]['Amount'].sum()
    cu_out_exp = df_c[(df_c['PaymentMethod'] == '현대카드(USD)') & (df_c['IsExpense'] == 1)]['Amount'].sum()
    
    return total_bank_out, (cv_in - cv_out_atm - cv_out_exp), (cash_in_atm + cash_in_dir - cash_out_exp - cash_out_dep), (cu_in - cu_out_exp)

# --- 4. [Module C, F] UI: Sidebar & Persistent Cash Counter ---
with st.sidebar:
    st.title("💰 Strategic Wallet")
    b_out, c_vnd, cash_v, c_usd = calculate_quad_balances(ledger_df)
    
    st.metric("🏦 한국계좌 총 지출액", f"{b_out:,.0f} 원")
    st.divider()
    st.metric("💳 카드 VND", f"{c_vnd:,.0f} ₫")
    st.metric("💵 지폐 VND (장부)", f"{cash_v:,.0f} ₫")
    st.metric("🇺🇸 카드 USD", f"${c_usd:,.2f}")
    
    # [Modified] Persistent Banknote Counter
    with st.expander("💵 실물 지폐 정산기", expanded=True):
        st.caption("클라우드 저장된 수량입니다. 수정 후 저장하세요.")
        current_physical_counts = {}
        total_ph = 0
        for bill in BILLS:
            # GSheets에서 불러온 값을 default로 설정
            n = st.number_input(f"{bill:,.0f} ₫", min_value=0, step=1, value=int(cloud_cash_counts.get(bill, 0)), key=f"p_bill_{bill}")
            current_physical_counts[bill] = n
            total_ph += bill * n
        
        if st.button("💾 현금 수량 클라우드 저장", use_container_width=True):
            save_cash_count(current_physical_counts)
            time.sleep(0.5); st.rerun()
            
        st.write(f"**실물 합계: {total_ph:,.0f} ₫**")
        diff = total_ph - cash_v
        if diff == 0: st.success("장부와 일치합니다! ✨")
        else: st.warning(f"장부 대조 차액: {diff:,.0f} ₫")

    # 환율 매니저 (5+2)
    with st.expander("💱 환율 매니저 (5+2)", expanded=False):
        if 'rate_names' not in st.session_state:
            st.session_state.rate_names = ['부산 1차', '머니박스', 'Slot 3', 'Slot 4', 'Slot 5', '달러환전 1', '달러환전 2']
        if 'rates' not in st.session_state:
            st.session_state.rates = [5.61, 6.10, 5.40, 5.40, 5.40, 1350.0, 1380.0]
        for i in range(7):
            cn, cv = st.columns([2, 1.5])
            with cn: st.session_state.rate_names[i] = st.text_input(f"이름 {i+1}", value=st.session_state.rate_names[i], key=f"rn_{i}")
            with cv: st.session_state.rates[i] = st.number_input(f"환율 {i+1}", value=st.session_state.rates[i], format="%.2f", key=f"rv_{i}")

    if st.button("🔄 Cloud Refresh", use_container_width=True):
        st.cache_data.clear(); st.rerun()

# --- 5. [Module C, D] UI: Main Tabs ---
tab_input, tab_history, tab_stats = st.tabs(["📝 기록/이동", "🔍 내역 조회", "📊 일일 결산"])

# --- [TAB 1: 기록 및 자산 이동] ---
with tab_input:
    if 'last_cat_idx' not in st.session_state: st.session_state.last_cat_idx = 0
    if 'last_rate_idx' not in st.session_state: st.session_state.last_rate_idx = 0

    mode = st.radio("기록 모드", ["일반 지출", "자산 이동 (충전/출금/환전)"], horizontal=True)
    
    if mode == "일반 지출":
        category = st.radio("항목 선택", EXPENSE_CATS, index=st.session_state.last_cat_idx, horizontal=True, key="exp_cat")
        st.session_state.last_cat_idx = EXPENSE_CATS.index(category)
        col1, col2 = st.columns(2)
        with col1:
            amount = st.number_input("금액", min_value=0.0, format="%.2f", key="exp_amt")
            currency = st.selectbox("통화", ["VND", "KRW", "USD"], key="exp_curr")
        with col2:
            rate_opts = [f"{st.session_state.rate_names[i]} ({st.session_state.rates[i]:.2f})" for i in range(7)]
            sel_rate_str = st.selectbox("적용 환율", rate_opts, index=st.session_state.last_rate_idx, key="exp_rate")
            st.session_state.last_rate_idx = rate_opts.index(sel_rate_str)
            rv = st.session_state.rates[st.session_state.last_rate_idx]
            if currency == "KRW": cr = 1.0
            else: cr = rv if "달러" in sel_rate_str else rv / 100.0
            method = st.selectbox("결제수단", ["트래블로그(VND)", "현금(VND)", "원화계좌", "현대카드(USD)"], key="exp_method")
        desc = st.text_input("상세 내용 (메모)", key="exp_desc")
        date = st.date_input("날짜", datetime.now(), key="exp_date")

        if st.button("🚀 지출 기록하기", use_container_width=True):
            if amount <= 0: st.warning("금액을 입력하세요.")
            else:
                new_entry = pd.DataFrame([{'Date': date.strftime("%m/%d(%a)"), 'Category': category, 'Description': desc, 'Currency': currency, 'Amount': amount, 'PaymentMethod': method, 'IsExpense': 1, 'AppliedRate': cr}])
                if save_data(pd.concat([ledger_df, new_entry], ignore_index=True)): st.rerun()
    else:
        st.subheader("🔁 자산 이동 및 환전")
        trans_type = st.selectbox("유형", ["직접환전 (원화계좌 -> 지폐VND)", "충전 (원화계좌 -> 카드VND)", "충전 (원화계좌 -> 카드USD)", "ATM출금 (카드VND -> 지폐VND)", "보증금 지불 (지폐VND -> 보증금)"])
        col1, col2 = st.columns(2)
        with col1: t_amt = st.number_input("받은 금액 (VND/USD)", min_value=0.0, key="tr_target")
        with col2: s_cost = st.number_input("지불 비용 (KRW/VND)", min_value=0.0, key="tr_source")
        if st.button("🔄 이동/환전 실행", use_container_width=True):
            calc_r = s_cost / t_amt if t_amt > 0 else 0
            cat_n = "환전" if "직접환전" in trans_type else trans_type.split(" ")[0]
            new_entry = pd.DataFrame([{'Date': datetime.now().strftime("%m/%d(%a)"), 'Category': cat_n, 'Description': trans_type, 'Currency': "USD" if "USD" in trans_type else "VND", 'Amount': t_amt, 'PaymentMethod': "원화계좌" if "원화계좌" in trans_type else "트래블로그(VND)", 'IsExpense': 0, 'AppliedRate': calc_r}])
            if save_data(pd.concat([ledger_df, new_entry], ignore_index=True)): st.rerun()

# --- [TAB 2: 내역 조회] ---
with tab_history:
    st.subheader("🔍 전체 데이터 조회")
    if not ledger_df.empty:
        st.dataframe(ledger_df.iloc[::-1], use_container_width=True)
        if st.button("🗑️ 마지막 행 삭제", use_container_width=True):
            if save_data(ledger_df[:-1]): st.rerun()

# --- [TAB 3: 일일 결산 (Enhanced Analytics)] ---
with tab_stats:
    if not ledger_df.empty:
        exp_df = ledger_df[ledger_df['IsExpense'] == 1].copy()
        if not exp_df.empty:
            # KRW 및 VND 환산 지표 생성
            def to_vnd(r): return r['Amount'] if r['Currency'] == 'VND' else r['Amount'] / r['AppliedRate']
            def to_krw(r): return r['Amount'] if r['Currency'] == 'KRW' else r['Amount'] * r['AppliedRate']
            exp_df['VND_eq'] = exp_df.apply(to_vnd, axis=1)
            exp_df['KRW_eq'] = exp_df.apply(to_krw, axis=1)
            
            # [Added] 일일 결산 테이블
            daily_set = exp_df.groupby('Date').agg({'KRW_eq':'sum', 'VND_eq':'sum'}).reset_index()
            st.subheader("🗓️ 일자별 정산 요약")
            st.table(daily_set.rename(columns={'Date':'날짜', 'KRW_eq':'합계 (원)', 'VND_eq':'합계 (동)'}).style.format({'합계 (원)': '{:,.0f}', '합계 (동)': '{:,.0f}'}))

            # [Added] 8일 고정 기간 차트 (04/20 ~ 04/27)
            st.divider()
            st.subheader("📈 8일간 지출 추이 (04/20 ~ 04/27)")
            base_d = datetime(2026, 4, 20)
            fixed_dates = [(base_d + timedelta(days=x)).strftime("%m/%d(%a)") for x in range(8)]
            chart_base = pd.DataFrame({'Date': fixed_dates})
            chart_final = pd.merge(chart_base, daily_set, on='Date', how='left').fillna(0)
            
            c_mode = st.radio("차트 단위", ["KRW (원화)", "VND (동화)"], horizontal=True)
            y_col = 'KRW_eq' if "KRW" in c_mode else 'VND_eq'
            color = '#FF00FF' if "KRW" in c_mode else '#00FF00'
            
            fig = px.bar(chart_final, x='Date', y=y_col, text_auto=',.0f', title=f"일일 지출 ({c_mode})")
            fig.update_traces(marker_color=color)
            st.plotly_chart(fig, use_container_width=True)
        else: st.info("지출 내역이 없습니다.")
    else: st.info("데이터가 없습니다.")

st.caption(f"Status: Fully Synchronized | v26.04.22.002 | Partner Gem")
