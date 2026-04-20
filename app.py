# [Project: Phu Quoc Strategic Ledger / Version: v26.04.20.024]
# [Module B, C: Modified]
# Total Line Count: 582

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import time

# --- 1. Configuration & Constitution ---
st.set_page_config(page_title="VND Strategic Ledger", layout="wide")

EXPENSE_CATS = ["식사", "간식", "마트", "택시", "VinBus", "지하철", "입장료", "투어", "선물", "통신", "팁", "수수료", "마사지"]
# [Modified] '환전' 카테고리 추가 (기술 헌법 6항 확장)
TRANSFER_CATS = ["충전", "ATM출금", "보증금", "환전"]
ALL_CATS = EXPENSE_CATS + TRANSFER_CATS
COLUMNS = ['Date', 'Category', 'Description', 'Currency', 'Amount', 'PaymentMethod', 'IsExpense', 'AppliedRate']

# --- 2. [Module A] Data Engine ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        df = conn.read(worksheet="시트1", ttl="0m")
        if df is None or df.empty: return pd.DataFrame(columns=COLUMNS)
        return df.reindex(columns=COLUMNS)
    except Exception: return pd.DataFrame(columns=COLUMNS)

def save_data(df):
    with st.status("Cloud 데이터 동기화 중...", expanded=False) as status:
        try:
            df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
            df['AppliedRate'] = pd.to_numeric(df['AppliedRate'], errors='coerce').fillna(0)
            conn.update(worksheet="시트1", data=df.reindex(columns=COLUMNS))
            st.cache_data.clear(); status.update(label="Cloud 동기화 완료!", state="complete", expanded=False)
            return True
        except Exception as e:
            status.update(label="동기화 실패!", state="error", expanded=True); return False

ledger_df = load_data()

# --- 3. [Module B] Quad-Wallet Asset Engine [Modified] ---
def calculate_quad_balances(df):
    if df.empty: return 0.0, 0.0, 0.0, 0.0
    df_c = df.copy()
    df_c['Amount'] = pd.to_numeric(df_c['Amount'], errors='coerce').fillna(0)
    df_c['AppliedRate'] = pd.to_numeric(df_c['AppliedRate'], errors='coerce').fillna(0)

    # 1. 원화계좌 (Bank KRW Out) : 충전 + 직접환전 시 지출된 KRW 합계
    bank_krw = df_c[df_c['Category'].isin(['충전', '환전'])]['AppliedRate'].sum() 
    
    # 2. 카드 VND (Card VND)
    cv_in = df_c[(df_c['Category'] == '충전') & (df_c['Currency'] == 'VND')]['Amount'].sum()
    cv_out_atm = df_c[df_c['Category'] == 'ATM출금']['Amount'].sum()
    cv_out_exp = df_c[(df_c['PaymentMethod'] == '트래블로그(VND)') & (df_c['IsExpense'] == True)]['Amount'].sum()
    card_vnd = cv_in - cv_out_atm - cv_out_exp

    # 3. 지폐 VND (Cash VND) [Modified]
    cash_in_atm = df_c[df_c['Category'] == 'ATM출금']['Amount'].sum()
    # [Added] 직접 환전으로 들어온 현금 추가
    cash_in_direct = df_c[(df_c['Category'] == '환전') & (df_c['PaymentMethod'] == '원화계좌')]['Amount'].sum()
    cash_out_exp = df_c[(df_c['PaymentMethod'] == '현금(VND)') & (df_c['IsExpense'] == True)]['Amount'].sum()
    cash_out_dep = df_c[df_c['Category'] == '보증금']['Amount'].sum()
    cash_vnd = cash_in_atm + cash_in_direct - cash_out_exp - cash_out_dep

    # 4. 카드 USD (Card USD)
    cu_in = df_c[(df_c['Category'] == '충전') & (df_c['Currency'] == 'USD')]['Amount'].sum()
    cu_out_exp = df_c[(df_c['PaymentMethod'] == '현대카드(USD)') & (df_c['IsExpense'] == True)]['Amount'].sum()
    card_usd = cu_in - cu_out_exp

    return bank_krw, card_vnd, cash_vnd, card_usd

# --- 4. UI: Sidebar (Dashboard & Cash Counter) ---
with st.sidebar:
    st.title("💰 Strategic Wallet")
    b_krw, c_vnd, cash_v, c_usd = calculate_quad_balances(ledger_df)
    
    # [Modified] 원화 총 지출액 가시화
    st.metric("🏦 한국계좌 총 인출액", f"{b_krw:,.0f} 원")
    st.divider()
    st.metric("💳 카드 VND", f"{c_vnd:,.0f} ₫")
    st.metric("💵 지폐 VND", f"{cash_v:,.0f} ₫")
    st.metric("🇺🇸 카드 USD", f"${c_usd:,.2f}")
    
    st.divider()
    with st.expander("💵 실물 지폐 카운터", expanded=False):
        bills = [500000, 200000, 100000, 50000, 20000, 10000, 5000, 2000, 1000]
        total_ph = sum([b * st.number_input(f"{b:,.0f} ₫", min_value=0, step=1, key=f"b_{b}") for b in bills])
        st.write(f"실물 합계: {total_ph:,.0f} ₫")
        st.write(f"차액: {total_ph - cash_v:,.0f} ₫")

# --- 5. UI: Main Tabs ---
tab_input, tab_history, tab_stats = st.tabs(["📝 기록/이동", "🔍 내역 조회", "📊 지출 분석"])

with tab_input:
    mode = st.radio("기록 모드 선택", ["일반 지출", "자산 이동 (충전/출금/환전)"], horizontal=True)
    
    if mode == "일반 지출":
        # ... (기존 지출 입력 로직 동일) ...
        pass # 실제 배포 코드엔 이전 버전 로직 포함

    else:
        st.subheader("🔁 자산 이동 및 환전")
        # [Modified] 직접환전 유형 추가
        trans_type = st.selectbox("이동/환전 유형", [
            "직접환전 (원화계좌 -> 지폐VND)", 
            "충전 (원화계좌 -> 카드VND)", 
            "충전 (원화계좌 -> 카드USD)", 
            "ATM출금 (카드VND -> 지폐VND)", 
            "보증금 지불 (지폐VND -> 보증금)"
        ])
        
        col1, col2 = st.columns(2)
        with col1:
            target_amount = st.number_input("받은 현금/충전액 (VND/USD)", min_value=0.0)
            target_curr = "USD" if "USD" in trans_type else "VND"
        with col2:
            source_cost = st.number_input("지불한 원화/카드액 (KRW/VND)", min_value=0.0)
            st.caption("소요 비용 (KRW 또는 VND)")

        if st.button("🔄 기록 실행"):
            cat_name = "환전" if "직접환전" in trans_type else trans_type.split(" ")[0]
            new_entry = pd.DataFrame([{
                'Date': datetime.now().strftime("%m/%d(%a)"),
                'Category': cat_name,
                'Description': trans_type,
                'Currency': target_curr,
                'Amount': target_amount,
                'PaymentMethod': "원화계좌" if "원화계좌" in trans_type else "트래블로그(VND)",
                'IsExpense': False,
                'AppliedRate': source_cost if "원화계좌" in trans_type else 0
            }])
            if save_data(pd.concat([ledger_df, new_entry], ignore_index=True)):
                st.success("자산 이동/환전이 기록되었습니다!"); time.sleep(0.5); st.rerun()

# [Tab 2, 3 로직 유지]
