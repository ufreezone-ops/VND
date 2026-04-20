# [Project: Phu Quoc Strategic Ledger / Version: v26.04.20.009]
# [Module A, B, C, D: Modified]
# Total Line Count: 292

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import time

# --- 1. Configuration & Constitution ---
st.set_page_config(page_title="VND Strategic Ledger", layout="wide")

# 기술 헌법 준수 카테고리 정의
EXPENSE_CATS = ["식사", "간식", "마트", "지하철", "VinBus", "택시", "입장료", "투어신청", "선물", "통신", "팁", "수수료", "마사지"]
TRANSFER_CATS = ["충전", "ATM출금", "보증금"]
ALL_CATS = EXPENSE_CATS + TRANSFER_CATS
COLUMNS = ['Date', 'Category', 'Description', 'Currency', 'Amount', 'PaymentMethod', 'IsExpense']

# --- 2. [Module A] Precision Data Engine [Modified] ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=0) # 캐시를 사용하지 않고 항상 최신 데이터를 읽어옴
def load_data():
    try:
        # [Modified] Dan의 시트명 "시트1"에 직접 연결
        df = conn.read(worksheet="시트1", ttl="0m")
        if df is None or df.empty:
            return pd.DataFrame(columns=COLUMNS)
        # 열 순서 강제 정렬 (ValueError 방지)
        return df.reindex(columns=COLUMNS)
    except Exception:
        return pd.DataFrame(columns=COLUMNS)

def save_data(df):
    # [Added] 동기화 상태 가시화
    with st.status("Cloud 데이터 동기화 중...", expanded=False) as status:
        try:
            # 데이터 정제
            df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
            df_to_save = df.reindex(columns=COLUMNS)
            
            # Google Sheets 업데이트
            conn.update(worksheet="시트1", data=df_to_save)
            
            status.update(label="Cloud 동기화 완료!", state="complete", expanded=False)
            st.cache_data.clear() # 캐시 강제 삭제
            return True
        except Exception as e:
            status.update(label="동기화 실패!", state="error", expanded=True)
            st.error(f"에러 내역: {e}")
            return False

# 데이터 동기화 로드
ledger_df = load_data()

# --- 3. [Module B] Asset Logic Engine [Modified] ---
def calculate_balances(df):
    if df.empty: return 0.0, 0.0
    
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

# --- 4. [Module C] UI: Sidebar & Status ---
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
        desc = st.text_input("상세 내용", placeholder="ex. 킹콩마트 망고")
    with col2:
        currency = st.selectbox("통화", ["VND", "KRW", "USD"])
        amount = st.number_input("금액", min_value=0.0, format="%.2f")
        method = st.selectbox("결제수단", ["트래블로그(VND)", "현금(VND)", "원화계좌", "현대카드(USD)"])

    # [Modified] 기록하기 버튼 로직 강화
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
                'IsExpense': is_expense
            }])
            
            updated_df = pd.concat([ledger_df, new_entry], ignore_index=True)
            if save_data(updated_df):
                st.toast(f"{category} 저장 완료!", icon="✅")
                time.sleep(1) # 동기화 후 잠시 대기
                st.rerun()

# --- 6. [Module D] Analytics Dashboard ---
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

        st.subheader("📊 일별/항목별 지출 분석")
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
# 최신 데이터가 위로 오게 표시
st.dataframe(ledger_df.iloc[::-1], use_container_width=True)

if st.button("🗑️ 마지막 항목 삭제"):
    if not ledger_df.empty:
        if save_data(ledger_df[:-1]):
            st.rerun()

st.caption(f"Status: Connected to '시트1' | Strategic Partner Gem")
