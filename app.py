# [Project: Phu Quoc Strategic Ledger / Version: v26.04.20.004]
# [Module A, B, C, D: Modified]
# Total Line Count: 248

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from streamlit_gsheets import GSheetsConnection # [Added]

# --- 1. Configuration & Constitution ---
st.set_page_config(page_title="VND Strategic Ledger", layout="wide")

# [Modified] 지출 카테고리 (기술 헌법 4, 5, 6항 준수)
EXPENSE_CATS = ["식사", "간식", "마트", "지하철", "VinBus", "택시", "입장료", "투어신청", "선물", "통신", "팁", "수수료", "마사지"]
TRANSFER_CATS = ["충전", "ATM출금", "보증금"]
ALL_CATS = EXPENSE_CATS + TRANSFER_CATS

# --- 2. Data Engine (Google Sheets Integration) [Modified] ---
# [Module A: Modified - Robust Data Engine]
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # [Modified] 시트1(Sheet1)을 명시적으로 읽어옵니다.
        df = conn.read(worksheet="시트1", ttl="0m") 
        if df is None or df.empty:
            return pd.DataFrame(columns=['Date', 'Category', 'Description', 'Currency', 'Amount', 'PaymentMethod', 'IsExpense'])
        return df
    except Exception as e:
        # 시트 이름이 'Sheet1'일 경우를 대비한 예외 처리
        try:
            return conn.read(worksheet="Sheet1", ttl="0m")
        except:
            return pd.DataFrame(columns=['Date', 'Category', 'Description', 'Currency', 'Amount', 'PaymentMethod', 'IsExpense'])

def save_data(df):
    # [Modified] 데이터 형식을 정리하고 쓰기 작업을 수행합니다.
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
    # 시트 이름이 '시트1'인지 'Sheet1'인지 확인 후 업데이트
    try:
        conn.update(worksheet="시트1", data=df)
    except:
        conn.update(worksheet="Sheet1", data=df)
        
# 데이터 로드
ledger_df = load_data()

# --- 3. Asset Logic Engine [Modified] ---
def calculate_balances(df):
    if df.empty: return 0.0, 0.0
    
    # [Modified] 헌법 2항: 자산 흐름 계산
    # 트래블로그(VND) = 충전(+) - ATM출금(-) - 트래블로그 카드지출(-)
    travel_in = df[df['Category'] == '충전']['Amount'].astype(float).sum()
    travel_out_atm = df[df['Category'] == 'ATM출금']['Amount'].astype(float).sum()
    travel_out_card = df[(df['PaymentMethod'] == '트래블로그(VND)') & (df['IsExpense'] == True)]['Amount'].astype(float).sum()
    travel_bal = travel_in - travel_out_atm - travel_out_card
    
    # 지폐(VND) = ATM출금(+) - 현금지출(-) - 보증금 지출(-)
    cash_in = df[df['Category'] == 'ATM출금']['Amount'].astype(float).sum()
    cash_out = df[(df['PaymentMethod'] == '현금(VND)') & (df['IsExpense'] == True)]['Amount'].astype(float).sum()
    # 보증금은 지불 시 현금에서 빠져나감 (헌법 6항 반영)
    deposit_out = df[df['Category'] == '보증금']['Amount'].astype(float).sum()
    cash_bal = cash_in - cash_out - deposit_out
    
    return travel_bal, cash_bal

# --- 4. UI: Sidebar (Wallet Status) ---
with st.sidebar:
    st.title("💰 Wallet Status")
    t_bal, c_bal = calculate_balances(ledger_df)
    
    st.metric("💳 트래블로그 (VND)", f"{t_bal:,.0f} ₫")
    st.metric("💵 현금 지폐 (VND)", f"{c_bal:,.0f} ₫")
    st.divider()
    
    VND_KRW_RATE = st.number_input("적용 환율 (VND→KRW)", value=0.0540, format="%.4f")
    st.info(f"계산 기준: 10만동 = {100000 * VND_KRW_RATE:,.0f}원")
    
    if st.button("🔄 데이터 새로고침"):
        st.rerun()

# --- 5. UI: Main Input Form [Modified] ---
st.title("🌴 Phu Quoc Strategic Ledger")

with st.expander("📝 내역 입력 (New Transaction)", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        date = st.date_input("날짜", datetime.now())
        category = st.selectbox("항목", ALL_CATS)
        desc = st.text_input("상세 내용", placeholder="ex. 킹콩마트 망고")
    with col2:
        currency = st.selectbox("통화", ["VND", "KRW", "USD"])
        amount = st.number_input("금액", min_value=0.0, format="%.2f")
        method = st.selectbox("결제수단", ["트래블로그(VND)", "현금(VND)", "원화계좌", "현대카드(USD)"])

    if st.button("🚀 기록하기 (Add Entry)"):
        # [Modified] 헌법 6항: 지출 포함 여부 자동 판별 로직
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
        
        # 클라우드 업데이트
        updated_df = pd.concat([ledger_df, new_entry], ignore_index=True)
        save_data(updated_df)
        st.success(f"{category} 기록이 구글 시트에 저장되었습니다!")
        st.rerun()

# --- 6. Analytics: Dashboard [Modified] ---
st.divider()
if not ledger_df.empty:
    # 지출 데이터만 필터링하여 분석
    analysis_df = ledger_df[ledger_df['IsExpense'] == True].copy()
    analysis_df['Amount'] = analysis_df['Amount'].astype(float)
    
    if not analysis_df.empty:
        # 모든 지출을 KRW로 환산
        def to_krw(row):
            if row['Currency'] == 'VND': return row['Amount'] * VND_KRW_RATE
            if row['Currency'] == 'USD': return row['Amount'] * 1350 
            return row['Amount']
        
        analysis_df['Amount_KRW'] = analysis_df.apply(to_krw, axis=1)

        st.subheader("📊 일별/항목별 지출 분석 (Daily Settlement)")
        tab1, tab2 = st.tabs(["📅 일별 결산", "🍱 항목별 비중"])
        
        with tab1:
            daily_sum = analysis_df.groupby('Date')['Amount_KRW'].sum().reset_index()
            fig_daily = px.bar(daily_sum, x='Date', y='Amount_KRW', text_auto=',.0f', title="일자별 순수 지출 (KRW)")
            fig_daily.update_traces(marker_color='#FF00FF')
            st.plotly_chart(fig_daily, use_container_width=True)
            
        with tab2:
            cat_sum = analysis_df.groupby('Category')['Amount_KRW'].sum().reset_index()
            fig_pie = px.pie(cat_sum, values='Amount_KRW', names='Category', hole=0.4, title="지출 카테고리 비중")
            st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("지출 내역이 입력되면 분석 차트가 표시됩니다.")

# --- 7. UI: Data Table & Management ---
st.subheader("📋 전체 내역 (Cloud History)")
st.dataframe(ledger_df, use_container_width=True)

if st.button("🗑️ 마지막 항목 삭제"):
    if not ledger_df.empty:
        updated_df = ledger_df[:-1]
        save_data(updated_df)
        st.rerun()

st.caption(f"Last Sync: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Strategic Partner Gem")
