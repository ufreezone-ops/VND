# [Project: Phu Quoc Strategic Ledger / Version: v26.04.20.019]
# [Module A, C, D: Modified]
# Total Line Count: 338

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
# [Modified] AppliedRate 열 추가
COLUMNS = ['Date', 'Category', 'Description', 'Currency', 'Amount', 'PaymentMethod', 'IsExpense', 'AppliedRate']

# --- 2. Data Engine ---
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

# --- 3. UI: Sidebar (Exchange Rate Manager) [Modified] ---
with st.sidebar:
    st.title("💰 Exchange Manager")
    
    # [Added] 10개의 환율 슬롯 관리
    if 'rates' not in st.session_state:
        # Dan의 현재 상황 반영 초기값
        st.session_state.rates = [5.61, 6.10, 5.40, 5.40, 5.40, 5.40, 5.40, 5.40, 5.40, 5.40]
    
    st.subheader("환율 슬롯 (100VND당 KRW)")
    for i in range(10):
        st.session_state.rates[i] = st.number_input(f"Slot {i+1}", value=st.session_state.rates[i], format="%.2f", key=f"rate_{i}")
    
    st.divider()
    # 잔액 계산 로직 (유지)
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

# --- 4. UI: Input Section [Modified] ---
st.title("🌴 Phu Quoc Strategic Ledger")

# [Added] 환율 선택 유지 로직 (Session State)
if 'last_rate_idx' not in st.session_state:
    st.session_state.last_rate_idx = 0

with st.expander("📝 내역 입력 (Cloud Sync)", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        date = st.date_input("날짜", datetime.now())
        category = st.selectbox("항목", ALL_CATS)
        # [Added] 환율 선택 풀다운
        rate_options = [f"Slot {i+1}: {r:.2f}" for i, r in enumerate(st.session_state.rates)]
        selected_rate_str = st.selectbox("적용 환율 선택", rate_options, index=st.session_state.last_rate_idx)
        current_rate = float(selected_rate_str.split(": ")[1]) / 100.0 # 0.0561 형식으로 변환
        st.session_state.last_rate_idx = rate_options.index(selected_rate_str) # 인덱스 저장
        
    with col2:
        currency = st.selectbox("통화", ["VND", "KRW", "USD"])
        amount = st.number_input("금액", min_value=0.0, format="%.2f")
        method = st.selectbox("결제수단", ["트래블로그(VND)", "현금(VND)", "원화계좌", "현대카드(USD)"])
        desc = st.text_input("상세 내용")

    if st.button("🚀 기록하기 (Add Entry)"):
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
                'AppliedRate': current_rate # [Added] 선택된 환율 저장
            }])
            
            if save_data(pd.concat([ledger_df, new_entry], ignore_index=True)):
                st.toast(f"저장 완료! (환율: {current_rate*100:.2f})", icon="✅")
                time.sleep(0.5)
                st.rerun()

# --- 5. Analytics Dashboard [Modified] ---
st.divider()
if not ledger_df.empty:
    exp_df = ledger_df[ledger_df['IsExpense'] == True].copy()
    exp_df['Amount'] = pd.to_numeric(exp_df['Amount'], errors='coerce').fillna(0)
    # [Modified] 저장된 개별 환율을 사용하여 KRW 계산
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
if st.button("🗑️ 마지막 항목 삭제"):
    if not ledger_df.empty:
        if save_data(ledger_df[:-1]): st.rerun()
