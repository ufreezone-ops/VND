# [Project: Phu Quoc Strategic Ledger / Version: v26.04.20.007]
# [Module A, B: Modified] / [Module C, D: Maintained]
# Total Line Count: 275

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. Configuration & Constitution ---
st.set_page_config(page_title="VND Strategic Ledger", layout="wide")

# [Maintained] 기술 헌법 4, 5, 6항: 카테고리 정의
EXPENSE_CATS = ["식사", "간식", "마트", "지하철", "VinBus", "택시", "입장료", "투어신청", "선물", "통신", "팁", "수수료", "마사지"]
TRANSFER_CATS = ["충전", "ATM출금", "보증금"]
ALL_CATS = EXPENSE_CATS + TRANSFER_CATS
COLUMNS = ['Date', 'Category', 'Description', 'Currency', 'Amount', 'PaymentMethod', 'IsExpense']

# --- 2. [Module A] Precision Data Engine [Modified] ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # [Modified] 시트명을 "시트1"로 고정하여 읽어옵니다.
        df = conn.read(worksheet="시트1", ttl="0m")
        if df is None or df.empty:
            return pd.DataFrame(columns=COLUMNS)
        # [Added] 열 순서를 헌법에 맞게 강제 재배열합니다.
        return df.reindex(columns=COLUMNS)
    except Exception:
        return pd.DataFrame(columns=COLUMNS)

def save_data(df):
    # [Modified] 데이터 형식을 정제하고 열 순서를 일치시킨 후 저장합니다.
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
    df_to_save = df.reindex(columns=COLUMNS)
    try:
        conn.update(worksheet="시트1", data=df_to_save)
    except Exception as e:
        st.error(f"구글 시트 저장 중 오류 발생: {e}")

# 데이터 동기화
ledger_df = load_data()

# --- 3. [Module B] Asset Logic Engine [Modified] ---
def calculate_balances(df):
    if df.empty: return 0.0, 0.0
    
    # 데이터 타입을 숫자로 변환하여 계산 오류 방지
    df_calc = df.copy()
    df_calc['Amount'] = pd.to_numeric(df_calc['Amount'], errors='coerce').fillna(0)
    
    # 트래블로그(VND) = 충전(+) - ATM출금(-) - 트래블로그 카드지출(-)
    travel_in = df_calc[df_calc['Category'] == '충전']['Amount'].sum()
    travel_out_atm = df_calc[df_calc['Category'] == 'ATM출금']['Amount'].sum()
    travel_out_card = df_calc[(df_calc['PaymentMethod'] == '트래블로그(VND)') & (df_calc['IsExpense'] == True)]['Amount'].sum()
    travel_bal = travel_in - travel_out_atm - travel_out_card
    
    # 지폐(VND) = ATM출금(+) - 현금지출(-) - 보증금(-)
    cash_in = df_calc[df_calc['Category'] == 'ATM출금']['Amount'].sum()
    cash_out = df_calc[(df_calc['PaymentMethod'] == '현금(VND)') & (df_calc['IsExpense'] == True)]['Amount'].sum()
    deposit_out = df_calc[df_calc['Category'] == '보증금']['Amount'].sum()
    cash_bal = cash_in - cash_out - deposit_out
    
    return travel_bal, cash_bal

# --- 4. [Module C] UI: Sidebar & Status [Maintained] ---
with st.sidebar:
    st.title("💰 Wallet Status")
    t_bal, c_bal = calculate_balances(ledger_df)
    
    st.metric("💳 트래블로그 (VND)", f"{t_bal:,.0f} ₫")
    st.metric("💵 현금 지폐 (VND)", f"{c_bal:,.0f} ₫")
    st.divider()
    
    VND_KRW_RATE = st.number_input("적용 환율 (VND→KRW)", value=0.0540, format="%.4f")
    st.info(f"계산 기준: 10만동 = {100000 * VND_KRW_RATE:,.0f}원")
    
    if st.button("🔄 Cloud Refresh"):
        st.cache_data.clear()
        st.rerun()

# --- 5. [Module C] UI: Input Section [Modified] ---
st.title("🌴 Phu Quoc Strategic Ledger")

with st.expander("📝 내역 입력 (Cloud Sync)", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        date = st.date_input("날짜", datetime.now())
        category = st.selectbox("항목", ALL_CATS)
        desc = st.text_input("상세 내용")
    with col2:
        currency = st.selectbox("통화", ["VND", "KRW", "USD"])
        amount = st.number_input("금액", min_value=0.0, format="%.2f")
        method = st.selectbox("결제수단", ["트래블로그(VND)", "현금(VND)", "원화계좌", "현대카드(USD)"])

    if st.button("🚀 기록하기 (Add Entry)"):
        is_expense = True if category in EXPENSE_CATS else False
        
        new_entry = pd.DataFrame([{
            'Date': date.strftime("%m/%d(%a)"),
            'Category': category,
            'Description': desc,
            'Currency': currency,
            'Amount': amount,
            'PaymentMethod': method,
            'IsExpense': is_expense
        }])
        
        # [Modified] 데이터 결합 및 클라우드 즉시 전송
        updated_df = pd.concat([ledger_df, new_entry], ignore_index=True)
        save_data(updated_df)
        st.success(f"{category} 기록 완료!")
        st.rerun()

# --- 6. [Module D] Analytics Dashboard [Maintained] ---
st.divider()
if not ledger_df.empty:
    exp_df = ledger_df[ledger_df['IsExpense'] == True].copy()
    exp_df['Amount'] = pd.to_numeric(exp_df['Amount'], errors='coerce').fillna(0)
    
    if not exp_df.empty:
        def to_krw(row):
            if row['Currency'] == 'VND': return row['Amount'] * VND_KRW_RATE
            if row['Currency'] == 'USD': return row['Amount'] * 1350 
            return row['Amount']
        
        exp_df['Amount_KRW'] = exp_df.apply(to_krw, axis=1)

        st.subheader("📊 Daily Settlement Analytics")
        tab1, tab2 = st.tabs(["📅 일별 결산", "🍱 항목별 비중"])
        
        with tab1:
            daily_sum = exp_df.groupby('Date')['Amount_KRW'].sum().reset_index()
            fig_daily = px.bar(daily_sum, x='Date', y='Amount_KRW', text_auto=',.0f')
            fig_daily.update_traces(marker_color='#FF00FF')
            st.plotly_chart(fig_daily, use_container_width=True)
            
        with tab2:
            cat_sum = exp_df.groupby('Category')['Amount_KRW'].sum().reset_index()
            fig_pie = px.pie(cat_sum, values='Amount_KRW', names='Category', hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)

# --- 7. Data Table Management ---
st.subheader("📋 Cloud History")
st.dataframe(ledger_df, use_container_width=True)

if st.button("🗑️ 마지막 항목 삭제"):
    if not ledger_df.empty:
        save_data(ledger_df[:-1])
        st.rerun()

st.caption(f"Status: Synchronized with GSheets | Strategic Partner Gem")
