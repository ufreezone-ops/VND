# [Project: Phu Quoc Strategic Ledger / Version: v26.04.20.027]
# [Module A, B, C, D: Modified]
# Total Line Count: 685

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

# --- 2. [Module A] Data Engine ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        df = conn.read(worksheet="시트1", ttl="0m")
        if df is None or df.empty: return pd.DataFrame(columns=COLUMNS)
        df = df.reindex(columns=COLUMNS)
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

# --- 3. [Module B] Quad-Wallet Asset Engine [Modified] ---
def calculate_quad_balances(df):
    if df.empty: return 0.0, 0.0, 0.0, 0.0
    df_c = df.copy()
    
    # [Modified] 한국계좌 총 인출액 계산 로직 정교화
    # 1. 충전/환전 시 사용한 원화 (Amount * AppliedRate)
    bank_transfer_out = df_c[df_c['Category'].isin(['충전', '환전'])]
    total_transfer_krw = (bank_transfer_out['Amount'] * bank_transfer_out['AppliedRate']).sum()
    
    # 2. 한국 내 원화 직접 지출 (Currency == 'KRW' & IsExpense == 1)
    # [Added] 원화 지출은 AppliedRate가 1.0이므로 바로 합산 가능
    direct_krw_expense = df_c[(df_c['Currency'] == 'KRW') & (df_c['IsExpense'] == 1)]['Amount'].sum()
    
    total_bank_out = total_transfer_krw + direct_krw_expense
    
    # 카드 VND 잔액
    cv_in = df_c[(df_c['Category'] == '충전') & (df_c['Currency'] == 'VND')]['Amount'].sum()
    cv_out_atm = df_c[df_c['Category'] == 'ATM출금']['Amount'].sum()
    cv_out_exp = df_c[(df_c['PaymentMethod'] == '트래블로그(VND)') & (df_c['IsExpense'] == 1)]['Amount'].sum()
    card_vnd = cv_in - cv_out_atm - cv_out_exp

    # 지폐 VND 잔액
    cash_in_atm = df_c[df_c['Category'] == 'ATM출금']['Amount'].sum()
    cash_in_direct = df_c[df_c['Category'] == '환전']['Amount'].sum()
    cash_out_exp = df_c[(df_c['PaymentMethod'] == '현금(VND)') & (df_c['IsExpense'] == 1)]['Amount'].sum()
    cash_out_dep = df_c[df_c['Category'] == '보증금']['Amount'].sum()
    cash_vnd = cash_in_atm + cash_in_direct - cash_out_exp - cash_out_dep

    # 카드 USD 잔액
    cu_in = df_c[(df_c['Category'] == '충전') & (df_c['Currency'] == 'USD')]['Amount'].sum()
    cu_out_exp = df_c[(df_c['PaymentMethod'] == '현대카드(USD)') & (df_c['IsExpense'] == 1)]['Amount'].sum()
    card_usd = cu_in - cu_out_exp

    return total_bank_out, card_vnd, cash_vnd, card_usd

# --- 4. [Module C] UI: Sidebar ---
with st.sidebar:
    st.title("💰 Strategic Wallet")
    b_out, c_vnd, cash_v, c_usd = calculate_quad_balances(ledger_df)
    
    st.metric("🏦 한국계좌 총 인출액", f"{b_out:,.0f} 원")
    st.divider()
    st.metric("💳 카드 VND", f"{c_vnd:,.0f} ₫")
    st.metric("💵 지폐 VND", f"{cash_v:,.0f} ₫")
    st.metric("🇺🇸 카드 USD", f"${c_usd:,.2f}")
    
    # 환율 매니저 (유지)
    st.divider()
    with st.expander("💱 환율 매니저 (5+2)", expanded=False):
        if 'rate_names' not in st.session_state:
            st.session_state.rate_names = ['부산 1차', '머니박스', 'Slot 3', 'Slot 4', 'Slot 5', '달러환전 1', '달러환전 2']
        if 'rates' not in st.session_state:
            st.session_state.rates = [5.61, 6.10, 5.40, 5.40, 5.40, 1350.0, 1380.0]
        for i in range(7):
            col_n, col_v = st.columns([2, 1.5])
            with col_n: st.session_state.rate_names[i] = st.text_input(f"이름 {i+1}", value=st.session_state.rate_names[i], key=f"rn_{i}")
            with col_v: st.session_state.rates[i] = st.number_input(f"환율 {i+1}", value=st.session_state.rates[i], format="%.2f", key=f"rv_{i}")

    # 실물 지폐 카운터 (유지)
    with st.expander("💵 실물 지폐 카운터", expanded=True):
        bills = [500000, 200000, 100000, 50000, 20000, 10000, 5000, 2000, 1000]
        total_ph = sum([b * st.number_input(f"{b:,.0f} ₫", min_value=0, step=1, key=f"b_{b}") for b in bills])
        st.write(f"실물 합계: {total_ph:,.0f} ₫ / 차액: {total_ph - cash_v:,.0f} ₫")

# --- 5. [Module C] UI: Main Input Tabs ---
tab_input, tab_history, tab_stats = st.tabs(["📝 기록/이동", "🔍 내역 조회", "📊 지출 분석"])

with tab_input:
    mode = st.radio("기록 모드 선택", ["일반 지출", "자산 이동 (충전/출금/환전)"], horizontal=True)
    
    if mode == "일반 지출":
        category = st.radio("항목 선택", EXPENSE_CATS, horizontal=True, key="exp_cat")
        col1, col2 = st.columns(2)
        with col1:
            amount = st.number_input("금액", min_value=0.0, format="%.2f", key="exp_amt")
            currency = st.selectbox("통화", ["VND", "KRW", "USD"], key="exp_curr")
        with col2:
            rate_opts = [f"{st.session_state.rate_names[i]} ({st.session_state.rates[i]:.2f})" for i in range(7)]
            sel_rate_str = st.selectbox("적용 환율 선택", rate_opts, key="exp_rate")
            rate_val = st.session_state.rates[rate_opts.index(sel_rate_str)]
            
            # [Modified] 통화가 KRW일 경우 환율을 1.0으로 강제 고정
            if currency == "KRW":
                current_rate = 1.0
                st.caption("ℹ️ 원화 지출은 환율이 1.0으로 자동 적용됩니다.")
            else:
                current_rate = rate_val if "달러" in sel_rate_str else rate_val / 100.0
            
            method = st.selectbox("결제수단", ["트래블로그(VND)", "현금(VND)", "원화계좌", "현대카드(USD)"], key="exp_method")
            
        desc = st.text_input("상세 내용", key="exp_desc")
        date = st.date_input("날짜", datetime.now(), key="exp_date")

        if st.button("🚀 지출 기록하기", use_container_width=True):
            if amount <= 0: st.warning("금액을 입력하세요.")
            else:
                new_entry = pd.DataFrame([{
                    'Date': date.strftime("%m/%d(%a)"), 'Category': category, 'Description': desc,
                    'Currency': currency, 'Amount': amount, 'PaymentMethod': method,
                    'IsExpense': 1, 'AppliedRate': current_rate
                }])
                if save_data(pd.concat([ledger_df, new_entry], ignore_index=True)): st.rerun()

    else:
        # [Modified] 자산 이동 모드: '보증금 반환' 유형 추가 제안
        st.subheader("🔁 자산 이동 및 환전")
        trans_type = st.selectbox("유형", ["직접환전 (원화계좌 -> 지폐VND)", "충전 (원화계좌 -> 카드VND)", "충전 (원화계좌 -> 카드USD)", "ATM출금 (카드VND -> 지폐VND)", "보증금 지불 (지폐VND -> 보증금)"])
        col1, col2 = st.columns(2)
        with col1: target_amt = st.number_input("받은 금액 (VND/USD)", min_value=0.0, key="tr_target")
        with col2: source_cost = st.number_input("지불 비용 (KRW/VND)", min_value=0.0, key="tr_source")
        
        if st.button("🔄 이동/환전 실행", use_container_width=True):
            calc_rate = source_cost / target_amt if target_amt > 0 else 0
            cat_name = "환전" if "직접환전" in trans_type else trans_type.split(" ")[0]
            new_entry = pd.DataFrame([{
                'Date': datetime.now().strftime("%m/%d(%a)"), 'Category': cat_name, 'Description': trans_type,
                'Currency': "USD" if "USD" in trans_type else "VND", 'Amount': target_amt,
                'PaymentMethod': "원화계좌" if "원화계좌" in trans_type else "트래블로그(VND)",
                'IsExpense': 0, 'AppliedRate': calc_rate
            }])
            if save_data(pd.concat([ledger_df, new_entry], ignore_index=True)): st.rerun()

# --- [TAB 2 & 3: Maintained] ---
with tab_history:
    st.subheader("🔍 내역 조회")
    st.dataframe(ledger_df.iloc[::-1], use_container_width=True)
    if st.button("🗑️ 마지막 항목 삭제"):
        if not ledger_df.empty:
            if save_data(ledger_df[:-1]): st.rerun()

with tab_stats:
    if not ledger_df.empty:
        exp_df = ledger_df[ledger_df['IsExpense'] == 1].copy()
        if not exp_df.empty:
            # [Modified] KRW 지출은 환율 곱하지 않고 그대로 유지하는 로직
            def to_krw(row):
                if row['Currency'] == 'KRW': return row['Amount']
                return row['Amount'] * row['AppliedRate']
            exp_df['Amount_KRW'] = exp_df.apply(to_krw, axis=1)
            st.plotly_chart(px.bar(exp_df.groupby('Date')['Amount_KRW'].sum().reset_index(), x='Date', y='Amount_KRW', text_auto=',.0f', title="일별 지출(KRW)"), use_container_width=True)
