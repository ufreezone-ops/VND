# [Project: Phu Quoc Strategic Ledger / Version: v24.05.22.003]
# [Module A, C: Modified] / [Module B, D: Added]
# Total Line Count: 215

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- [Module A] Configuration & Styling [Modified] ---
st.set_page_config(page_title="VND Strategic Ledger", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 10px; border: 1px solid #333; }
    div[data-testid="stExpander"] { border: 1px solid #FF00FF; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# [Added] 기술 헌법 4, 5, 6항: 카테고리 정의
EXPENSE_CATS = ["식사", "간식", "마트", "지하철", "VinBus", "택시", "입장료", "투어신청", "선물", "통신", "팁", "수수료", "마사지"]
TRANSFER_CATS = ["충전", "ATM출금", "보증금"] # 지출 통계에서 제외되는 항목
ALL_CATS = EXPENSE_CATS + TRANSFER_CATS

VND_KRW_RATE = 0.054 # 기본 환율 (100 VND = 5.4 KRW)

# --- [Module A] Data Initialization [Modified] ---
if 'ledger' not in st.session_state:
    st.session_state.ledger = pd.DataFrame(columns=[
        'Date', 'Category', 'Description', 'Currency', 'Amount', 'PaymentMethod', 'IsExpense'
    ])

# --- [Module B] Asset Logic Engine [Added] ---
def calculate_balances(df):
    # 트래블로그(VND) 잔액 = 충전(+) - ATM출금(-) - 카드지출(-)
    travel_in = df[df['Category'] == '충전']['Amount'].sum()
    travel_out_atm = df[df['Category'] == 'ATM출금']['Amount'].sum()
    travel_out_card = df[(df['PaymentMethod'] == '트래블로그(VND)') & (df['IsExpense'] == True)]['Amount'].sum()
    travel_bal = travel_in - travel_out_atm - travel_out_card
    
    # 지폐(VND) 잔액 = ATM출금(+) - 현금지출(-)
    cash_in = df[df['Category'] == 'ATM출금']['Amount'].sum()
    cash_out = df[(df['PaymentMethod'] == '현금(VND)') & (df['IsExpense'] == True)]['Amount'].sum()
    cash_bal = cash_in - cash_out
    
    return travel_bal, cash_bal

# --- [Module C] UI: Sidebar & Real-time Status [Modified] ---
with st.sidebar:
    st.title("💰 Wallet Status")
    t_bal, c_bal = calculate_balances(st.session_state.ledger)
    
    st.metric("💳 트래블로그 (VND)", f"{t_bal:,.0f} ₫") # [Added]
    st.metric("💵 현금 지폐 (VND)", f"{c_bal:,.0f} ₫") # [Added]
    st.divider()
    
    # 환율 설정 도구
    custom_rate = st.number_input("적용 환율 (VND→KRW)", value=VND_KRW_RATE, format="%.4f")
    st.info(f"계산 기준: 10만동 = {100000 * custom_rate:,.0f}원")

# --- [Module C] UI: Input Section [Modified] ---
st.title("🌴 Phu Quoc Ledger")

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
        # [Added] 헌법 6항: 지출 포함 여부 자동 판별
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
        
        st.session_state.ledger = pd.concat([st.session_state.ledger, new_entry], ignore_index=True)
        st.success(f"{category} ({(amount):,.0f} {currency}) 기록되었습니다!")
        st.rerun()

# --- [Module D] Analytics: Dashboard [Added] ---
st.divider()
if not st.session_state.ledger.empty:
    # 데이터 전처리: 모든 지출을 KRW로 환산 (통계용)
    analysis_df = st.session_state.ledger[st.session_state.ledger['IsExpense'] == True].copy()
    
    def convert_to_krw(row):
        if row['Currency'] == 'VND': return row['Amount'] * custom_rate
        if row['Currency'] == 'USD': return row['Amount'] * 1350 # 임시 달러 환율
        return row['Amount']
    
    analysis_df['Amount_KRW'] = analysis_df.apply(convert_to_krw, axis=1)

    if not analysis_df.empty:
        st.subheader("📊 일별/항목별 지출 분석")
        tab1, tab2 = st.tabs(["📅 일별 결산", "🍱 항목별 비중"])
        
        with tab1:
            daily_sum = analysis_df.groupby('Date')['Amount_KRW'].sum().reset_index()
            fig_daily = px.bar(daily_sum, x='Date', y='Amount_KRW', 
                               text_auto=',.0f', title="일자별 순수 지출 (KRW)")
            fig_daily.update_traces(marker_color='#FF00FF')
            st.plotly_chart(fig_daily, use_container_width=True)
            
        with tab2:
            cat_sum = analysis_df.groupby('Category')['Amount_KRW'].sum().reset_index()
            fig_pie = px.pie(cat_sum, values='Amount_KRW', names='Category', 
                             hole=0.4, title="지출 카테고리 비중")
            st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("지출 내역(식사, 택시 등)이 입력되면 차트가 표시됩니다.")

# --- [Module C] Data Table & Management [Modified] ---
st.subheader("📋 전체 내역 (History)")
st.dataframe(st.session_state.ledger, use_container_width=True)

col_del, col_csv = st.columns([1, 4])
with col_del:
    if st.button("🗑️ 마지막 항목 삭제"):
        st.session_state.ledger = st.session_state.ledger[:-1]
        st.rerun()
with col_csv:
    # [Added] 데이터 백업용 CSV 다운로드
    csv = st.session_state.ledger.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 데이터 백업(CSV)", data=csv, file_name=f"PQ_Ledger_{datetime.now().strftime('%m%d')}.csv")

# --- Footer ---
st.caption("Strategic Partner Gem / Version v24.05.22.003")