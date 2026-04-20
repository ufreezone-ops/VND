# [Project: Phu Quoc Strategic Ledger / Version: v26.04.20.021]
# [Module C: Modified] / [Module D: Added/Modified]
# Total Line Count: 415

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import time

# --- 1. Configuration & Constitution ---
st.set_page_config(page_title="VND Strategic Ledger", layout="wide")

# 기술 헌법 카테고리
EXPENSE_CATS = ["식사", "간식", "마트", "택시", "VinBus", "지하철", "입장료", "투어", "선물", "통신", "팁", "수수료", "마사지"]
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

# --- 3. [Module C] UI: Sidebar (Rate Manager) [Maintained] ---
with st.sidebar:
    st.title("💰 Exchange Manager")
    if 'rate_names' not in st.session_state:
        st.session_state.rate_names = ['부산 1차', '머니박스'] + [f"Slot {i}" for i in range(3, 11)]
    if 'rates' not in st.session_state:
        st.session_state.rates = [5.61, 6.10] + [5.40] * 8
    
    for i in range(10):
        col_n, col_v = st.columns([2, 1.5])
        with col_n: st.session_state.rate_names[i] = st.text_input(f"이름 {i+1}", value=st.session_state.rate_names[i], key=f"rn_{i}")
        with col_v: st.session_state.rates[i] = st.number_input(f"환율 {i+1}", value=st.session_state.rates[i], format="%.2f", key=f"rv_{i}")
    
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

# --- 4. [Module C] UI: Main Tabs ---
tab_input, tab_history, tab_stats = st.tabs(["📝 기록하기", "🔍 내역 조회", "📊 지출 분석"])

# --- [TAB 1: 기록하기 (Modified for Mobile UX)] ---
with tab_input:
    if 'last_cat_idx' not in st.session_state: st.session_state.last_cat_idx = 0
    if 'last_rate_idx' not in st.session_state: st.session_state.last_rate_idx = 0

    with st.container():
        # [Modified] 카테고리를 라디오 버튼으로 변경 (키보드 간섭 방지)
        category = st.radio("항목 선택", ALL_CATS, index=st.session_state.last_cat_idx, horizontal=True, key="input_cat")
        st.session_state.last_cat_idx = ALL_CATS.index(category)
        
        col1, col2 = st.columns(2)
        with col1:
            # 환율 선택도 라디오나 짧은 리스트 권장
            rate_options = [f"{st.session_state.rate_names[i]} ({st.session_state.rates[i]:.2f})" for i in range(10)]
            selected_rate_str = st.selectbox("적용 환율", rate_options, index=st.session_state.last_rate_idx, key="input_rate")
            current_rate = st.session_state.rates[rate_options.index(selected_rate_str)] / 100.0
            st.session_state.last_rate_idx = rate_options.index(selected_rate_str)
            
            amount = st.number_input("금액", min_value=0.0, format="%.2f", key="input_amt")
            
        with col2:
            method = st.selectbox("결제수단", ["트래블로그(VND)", "현금(VND)", "원화계좌", "현대카드(USD)"], key="input_method")
            currency = st.selectbox("통화", ["VND", "KRW", "USD"], key="input_curr")
            
        desc = st.text_input("상세 내용 (메모)", key="input_desc")
        date = st.date_input("날짜", datetime.now(), key="input_date")

        if st.button("🚀 기록하기 (Add Entry)", use_container_width=True, key="submit_btn"):
            if amount <= 0:
                st.warning("금액을 입력해주세요.")
            else:
                is_expense = True if category in EXPENSE_CATS else False
                new_entry = pd.DataFrame([{
                    'Date': date.strftime("%m/%d(%a)"), 'Category': category, 'Description': desc,
                    'Currency': currency, 'Amount': amount, 'PaymentMethod': method,
                    'IsExpense': is_expense, 'AppliedRate': current_rate
                }])
                if save_data(pd.concat([ledger_df, new_entry], ignore_index=True)):
                    st.toast(f"저장 완료! ({category})", icon="✅")
                    time.sleep(0.5); st.rerun()

# --- [TAB 2: 내역 조회 (Added for Review)] ---
with tab_history:
    st.subheader("📋 상세 내역 조회")
    if not ledger_df.empty:
        # 필터 UI
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            f_date = st.multiselect("날짜 필터", options=ledger_df['Date'].unique(), default=None)
        with col_f2:
            f_cat = st.multiselect("항목 필터", options=ALL_CATS, default=None)
        
        filtered_df = ledger_df.copy()
        if f_date: filtered_df = filtered_df[filtered_df['Date'].isin(f_date)]
        if f_cat: filtered_df = filtered_df[filtered_df['Category'].isin(f_cat)]
        
        # 필터링된 결과 요약
        st.write(f"조회된 내역: {len(filtered_df)}건")
        st.dataframe(filtered_df.iloc[::-1], use_container_width=True)
        
        if st.button("🗑️ 선택된 필터의 마지막 항목 삭제", key="del_btn"):
            if not ledger_df.empty:
                if save_data(ledger_df[:-1]): st.rerun()
    else:
        st.info("기록된 내역이 없습니다.")

# --- [TAB 3: 지출 분석 (Maintained)] ---
with tab_stats:
    if not ledger_df.empty:
        exp_df = ledger_df[ledger_df['IsExpense'] == True].copy()
        exp_df['Amount'] = pd.to_numeric(exp_df['Amount'], errors='coerce').fillna(0)
        exp_df['AppliedRate'] = pd.to_numeric(exp_df['AppliedRate'], errors='coerce').fillna(0.054)
        
        def calculate_krw(row):
            if row['Currency'] == 'VND': return row['Amount'] * row['AppliedRate']
            if row['Currency'] == 'USD': return row['Amount'] * 1350 
            return row['Amount']
        
        exp_df['Amount_KRW'] = exp_df.apply(calculate_krw, axis=1)

        st.subheader("📊 지출 분석")
        daily_sum = exp_df.groupby('Date')['Amount_KRW'].sum().reset_index()
        st.plotly_chart(px.bar(daily_sum, x='Date', y='Amount_KRW', text_auto=',.0f', title="일별 지출(KRW)"), use_container_width=True)
        
        cat_sum = exp_df.groupby('Category')['Amount_KRW'].sum().reset_index()
        st.plotly_chart(px.pie(cat_sum, values='Amount_KRW', names='Category', hole=0.4, title="항목별 비중"), use_container_width=True)
