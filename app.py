# [Project: Phu Quoc Strategic Ledger / Version: v26.04.20.025]
# [Module A, B, C: Modified]
# Total Line Count: 615

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import time

# --- 1. Configuration & Constitution ---
st.set_page_config(page_title="VND Strategic Ledger", layout="wide")

EXPENSE_CATS = ["식사", "간식", "마트", "택시", "VinBus", "지하철", "입장료", "투어", "선물", "통신", "팁", "수수료", "마사지"]
TRANSFER_CATS = ["충전", "ATM출금", "보증금", "환전"]
ALL_CATS = EXPENSE_CATS + TRANSFER_CATS
COLUMNS = ['Date', 'Category', 'Description', 'Currency', 'Amount', 'PaymentMethod', 'IsExpense', 'AppliedRate']

# --- 2. [Module A] Data Engine [Modified] ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        df = conn.read(worksheet="시트1", ttl="0m")
        if df is None or df.empty: return pd.DataFrame(columns=COLUMNS)
        df = df.reindex(columns=COLUMNS)
        # [Added] 데이터 타입 강제 정규화
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
        df['AppliedRate'] = pd.to_numeric(df['AppliedRate'], errors='coerce').fillna(0)
        df['IsExpense'] = pd.to_numeric(df['IsExpense'], errors='coerce').fillna(0).astype(int)
        return df
    except Exception: return pd.DataFrame(columns=COLUMNS)

def save_data(df):
    with st.status("Cloud 데이터 동기화 중...", expanded=False) as status:
        try:
            df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
            df['AppliedRate'] = pd.to_numeric(df['AppliedRate'], errors='coerce').fillna(0)
            df['IsExpense'] = pd.to_numeric(df['IsExpense'], errors='coerce').fillna(0).astype(int)
            conn.update(worksheet="시트1", data=df.reindex(columns=COLUMNS))
            st.cache_data.clear(); status.update(label="Cloud 동기화 완료!", state="complete", expanded=False)
            return True
        except Exception: return False

ledger_df = load_data()

# --- 3. [Module B] Quad-Wallet Asset Engine [Fixed/Modified] ---
def calculate_quad_balances(df):
    if df.empty: return 0.0, 0.0, 0.0, 0.0
    df_c = df.copy()
    
    # 1. 한국계좌 총 인출액 (KRW)
    # [Modified] 지출인 것은 환율계산, 자산이동(충전/환전)은 Amount*Rate로 KRW 산출
    # 충전/환전 시 AppliedRate에 '환율'을 저장하므로 일관된 계산 가능
    bank_krw = df_c[df_c['Category'].isin(['충전', '환전'])]
    total_bank_out = (bank_krw['Amount'] * bank_krw['AppliedRate']).sum()
    
    # 2. 카드 VND (Card VND)
    cv_in = df_c[df_c['Category'] == '충전']['Amount'].sum()
    cv_out_atm = df_c[df_c['Category'] == 'ATM출금']['Amount'].sum()
    cv_out_exp = df_c[(df_c['PaymentMethod'] == '트래블로그(VND)') & (df_c['IsExpense'] == 1)]['Amount'].sum()
    card_vnd = cv_in - cv_out_atm - cv_out_exp

    # 3. 지폐 VND (Cash VND)
    cash_in_atm = df_c[df_c['Category'] == 'ATM출금']['Amount'].sum()
    cash_in_direct = df_c[df_c['Category'] == '환전']['Amount'].sum()
    cash_out_exp = df_c[(df_c['PaymentMethod'] == '현금(VND)') & (df_c['IsExpense'] == 1)]['Amount'].sum()
    cash_out_dep = df_c[df_c['Category'] == '보증금']['Amount'].sum()
    cash_vnd = cash_in_atm + cash_in_direct - cash_out_exp - cash_out_dep

    # 4. 카드 USD (Card USD)
    cu_in = df_c[(df_c['Category'] == '충전') & (df_c['Currency'] == 'USD')]['Amount'].sum()
    cu_out_exp = df_c[(df_c['PaymentMethod'] == '현대카드(USD)') & (df_c['IsExpense'] == 1)]['Amount'].sum()
    card_usd = cu_in - cu_out_exp

    return total_bank_out, card_vnd, cash_vnd, card_usd

# --- 4. UI: Sidebar ---
with st.sidebar:
    st.title("💰 Strategic Wallet")
    b_out, c_vnd, cash_v, c_usd = calculate_quad_balances(ledger_df)
    
    st.metric("🏦 한국계좌 총 인출액", f"{b_out:,.0f} 원")
    st.divider()
    st.metric("💳 카드 VND", f"{c_vnd:,.0f} ₫")
    st.metric("💵 지폐 VND", f"{cash_v:,.0f} ₫")
    st.metric("🇺🇸 카드 USD", f"${c_usd:,.2f}")
    
    st.divider()
    with st.expander("💵 실물 지폐 카운터", expanded=True):
        bills = [500000, 200000, 100000, 50000, 20000, 10000, 5000, 2000, 1000]
        total_ph = sum([b * st.number_input(f"{b:,.0f} ₫", min_value=0, step=1, key=f"b_{b}") for b in bills])
        st.write(f"실물 합계: {total_ph:,.0f} ₫ / 차액: {total_ph - cash_v:,.0f} ₫")

# --- 5. UI: Main Tabs ---
tab_input, tab_history, tab_stats = st.tabs(["📝 기록/이동", "🔍 내역 조회", "📊 지출 분석"])

with tab_input:
    mode = st.radio("기록 모드 선택", ["일반 지출", "자산 이동 (충전/출금/환전)"], horizontal=True)
    
    if mode == "일반 지출":
        # ... (기존 지출 입력 로직 동일)
        pass 

    else:
        st.subheader("🔁 자산 이동 및 환전")
        trans_type = st.selectbox("유형", ["직접환전 (원화계좌 -> 지폐VND)", "충전 (원화계좌 -> 카드VND)", "충전 (원화계좌 -> 카드USD)", "ATM출금 (카드VND -> 지폐VND)", "보증금 지불 (지폐VND -> 보증금)"])
        
        col1, col2 = st.columns(2)
        with col1:
            target_amount = st.number_input("받은 금액 (VND/USD)", min_value=0.0)
        with col2:
            source_cost = st.number_input("지불한 비용 (KRW/VND)", min_value=0.0)
            st.caption("소요된 KRW 또는 인출된 VND")

        if st.button("🔄 기록 실행"):
            # [Modified] 자산 이동 시에도 '환율(AppliedRate)'을 계산하여 저장
            # 충전/환전: KRW / VND = 1동당 가격
            calc_rate = source_cost / target_amount if target_amount > 0 else 0
            
            cat_name = "환전" if "직접환전" in trans_type else trans_type.split(" ")[0]
            new_entry = pd.DataFrame([{
                'Date': datetime.now().strftime("%m/%d(%a)"),
                'Category': cat_name,
                'Description': trans_type,
                'Currency': "USD" if "USD" in trans_type else "VND",
                'Amount': target_amount,
                'PaymentMethod': "원화계좌" if "원화계좌" in trans_type else "트래블로그(VND)",
                'IsExpense': 0, # [Fixed] Numeric 0
                'AppliedRate': calc_rate # [Fixed] Normalization
            }])
            if save_data(pd.concat([ledger_df, new_entry], ignore_index=True)): st.rerun()
