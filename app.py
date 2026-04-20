# [Project: Phu Quoc Strategic Ledger / Version: v26.04.20.020]
# [Module C: Modified] / [Module A, B, D: Maintained]
# Total Line Count: 362

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import time

# --- 1. Configuration & Constitution ---
st.set_page_config(page_title="VND Strategic Ledger", layout="wide")

EXPENSE_CATS = ["식사", "간식", "마트", "지하철", "VinBus", "택시", "입장료", "투어신청", "선물", "통신", "팁", "수수료", "마사지"]
TRANSFER_CATS = ["충전", "ATM출금", "보증금"]
ALL_CATS = EXPENSE_CATS + TRANSFER_CATS
COLUMNS = ['Date', 'Category', 'Description', 'Currency', 'Amount', 'PaymentMethod', 'IsExpense', 'AppliedRate']

# --- 2. [Module A] Data Engine [Maintained] ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        df = conn.read(worksheet="시트1", ttl="0m")
        if df is None or df.empty:
            return pd.DataFrame(columns=COLUMNS)
        return df.reindex(columns=COLUMNS)
    except Exception:
        return pd.DataFrame(columns=COLUMNS)

def save_data(df):
    with st.status("Cloud 데이터 동기화 중...", expanded=False) as status:
        try:
            df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
            df['AppliedRate'] = pd.to_numeric(df['AppliedRate'], errors='coerce').fillna(0.054)
            df_to_save = df.reindex(columns=COLUMNS)
            conn.update(worksheet="시트1", data=df_to_save)
            st.cache_data.clear()
            status.update(label="Cloud 동기화 완료!", state="complete", expanded=False)
            return True
        except Exception as e:
            status.update(label="동기화 실패!", state="error", expanded=True)
            st.error(f"에러 내역: {e}")
            return False

ledger_df = load_data()

# --- 3. [Module C] UI: Sidebar (Custom Rate Manager) [Modified] ---
with st.sidebar:
    st.title("💰 Exchange Manager")
    
    # [Added] 환율 이름과 값을 동시에 관리
    if 'rate_names' not in st.session_state:
        st.session_state.rate_names = ['부산 1차', '머니박스'] + [f"Slot {i}" for i in range(3, 11)]
    if 'rates' not in st.session_state:
        st.session_state.rates = [5.61, 6.10] + [5.40] * 8
    
    st.subheader("환율처 & 환율 (100VND당)")
    for i in range(10):
        col_n, col_v = st.columns([2, 1.5])
        with col_n:
            st.session_state.rate_names[i] = st.text_input(f"이름 {i+1}", value=st.session_state.rate_names[i], key=f"rn_{i}")
        with col_v:
            st.session_state.rates[i] = st.number_input(f"환율 {i+1}", value=st.session_state.rates[i], format="%.2f", key=f"rv_{i}")
    
    st.divider()
    
    def calculate_balances(df):
        if df.empty: return 0.0, 0.0
        df_c = df.copy()
        df_c['Amount'] = pd.to_numeric(df_c['Amount'], errors='coerce').fillna(0)
        t_in = df_c[df_c['Category'] == '충전']['Amount'].sum()
        t_out_a = df_c[df_c['Category'] == 'ATM출금']['Amount'].sum()
        t_out_c = df_c[(df_c['PaymentMethod'] == '트래블로그(VND)') & (df_c['IsExpense'] == True)]['Amount'].sum()
        c_in = df_c[df_c['Category'] == 'ATM출금']['Amount'].sum()
        c_out = df_c[(df_c['PaymentMethod'] == '현금(VND)') & (df_c['IsExpense'] == True)]['Amount'].sum()
        dep_out = df_c[df_c['Category'] == '보증금']['Amount'].sum()
        return (t_in - t_out_a - t_out_c), (c_in - c_out - dep_out)

    t_bal, c_bal = calculate_balances(ledger_df)
    st.metric("💳 트래블로그", f"{t_bal:,.0f} ₫")
    st.metric("💵 현금 지폐", f"{c_bal:,.0f} ₫")

# --- 4. [Module C] UI: Input Section [Modified] ---
st.title("🌴 Phu Quoc Strategic Ledger")

# [Added] 선택 상태 유지를 위한 Session State
if 'last_cat_idx' not in st.session_state: st.session_state.last_cat_idx = 0
if 'last_rate_idx' not in st.session_state: st.session_state.last_rate_idx = 0

with st.expander("📝 내역 입력 (Cloud Sync)", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        # [Modified] Key 추가로 선택 버그 수정
        date = st.date_input("날짜", datetime.now(), key="input_date")
        
        category = st.selectbox("항목", ALL_CATS, index=st.session_state.last_cat_idx, key="input_cat")
        st.session_state.last_cat_idx = ALL_CATS.index(category) # 선택 인덱스 기억
        
        # [Modified] 커스텀 이름을 반영한 환율 선택
        rate_options = [f"{st.session_state.rate_names[i]} ({st.session_state.rates[i]:.2f})" for i in range(10)]
        selected_rate_str = st.selectbox("적용 환율 선택", rate_options, index=st.session_state.last_rate_idx, key="input_rate")
        current_rate = st.session_state.rates[rate_options.index(selected_rate_str)] / 100.0
        st.session_state.last_rate_idx = rate_options.index(selected_rate_str) # 선택 인덱스 기억
        
    with col2:
        currency = st.selectbox("통화", ["VND", "KRW", "USD"], key="input_curr")
        amount = st.number_input("금액", min_value=0.0, format="%.2f", key="input_amt")
        method = st.selectbox("결제수단", ["트래블로그(VND)", "현금(VND)", "원화계좌", "현대카드(USD)"], key="input_method")
        desc = st.text_input("상세 내용", key="input_desc")

    if st.button("🚀 기록하기 (Add Entry)", key="submit_btn"):
        if amount <= 0:
            st.warning("금액을 입력해주세요.")
        else:
            is_expense = True if category in EXPENSE_CATS else False
            new_entry = pd.DataFrame([{
                'Date': date.strftime("%m/%d(%a)"),
                'Category': category,
                'Description': desc,
                'Currency': currency,
                'Amount': amount,
                'PaymentMethod': method,
                'IsExpense': is_expense,
                'AppliedRate': current_rate
            }])
            
            if save_data(pd.concat([ledger_df, new_entry], ignore_index=True)):
                st.toast(f"저장 완료! ({category})", icon="✅")
                time.sleep(0.5)
                st.rerun()

# --- 5. [Module D] Analytics [Maintained] ---
st.divider()
if not ledger_df.empty:
    exp_df = ledger_df[ledger_df['IsExpense'] == True].copy()
    exp_df['Amount'] = pd.to_numeric(exp_df['Amount'], errors='coerce').fillna(0)
    exp_df['AppliedRate'] = pd.to_numeric(exp_df['AppliedRate'], errors='coerce').fillna(0.054)
    
    def calculate_krw(row):
        if row['Currency'] == 'VND': return row['Amount'] * row['AppliedRate']
        if row['Currency'] == 'USD': return row['Amount'] * 1350 
        return row['Amount']
    
    exp_df['Amount_KRW'] = exp_df.apply(calculate_krw, axis=1)

    st.subheader("📊 지출 정산 (적용 환율 반영)")
    tab1, tab2 = st.tabs(["📅 일별 결산", "🍱 항목별 비중"])
    with tab1:
        daily_sum = exp_df.groupby('Date')['Amount_KRW'].sum().reset_index()
        st.plotly_chart(px.bar(daily_sum, x='Date', y='Amount_KRW', text_auto=',.0f'), use_container_width=True)
    with tab2:
        cat_sum = exp_df.groupby('Category')['Amount_KRW'].sum().reset_index()
        st.plotly_chart(px.pie(cat_sum, values='Amount_KRW', names='Category', hole=0.4), use_container_width=True)

st.subheader("📋 Cloud History")
st.dataframe(ledger_df.iloc[::-1], use_container_width=True)
if st.button("🗑️ 마지막 항목 삭제", key="del_btn"):
    if not ledger_df.empty:
        if save_data(ledger_df[:-1]): st.rerun()
