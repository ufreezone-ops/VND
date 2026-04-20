# [Project: Phu Quoc Strategic Ledger / Version: v26.04.21.003]
# [Modules A, B, C, D, F: Full Integration]
# Total Line Count: 735

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import time

# --- 1. Configuration & Constitution ---
st.set_page_config(page_title="VND Strategic Ledger", layout="wide")

# 기술 헌법 카테고리 정의
EXPENSE_CATS = ["식사", "간식", "마트", "택시", "VinBus", "지하철", "입장료", "투어", "선물", "통신", "팁", "수수료", "마사지"]
TRANSFER_CATS = ["충전", "ATM출금", "보증금", "환전"]
ALL_CATS = EXPENSE_CATS + TRANSFER_CATS
COLUMNS = ['Date', 'Category', 'Description', 'Currency', 'Amount', 'PaymentMethod', 'IsExpense', 'AppliedRate']

# --- 2. [Module A] Data Engine (Anti-Cache & Row Cleaning) ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=0) # 캐시를 사용하지 않고 매번 구글 시트에서 신선한 데이터를 읽음
def load_data():
    try:
        # ttl=0 및 worksheet 명시로 수동 수정 데이터 즉시 반영
        df = conn.read(worksheet="시트1", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=COLUMNS)
        
        # 구글 시트에서 수동 삭제 시 생길 수 있는 빈 행(NaN) 필터링
        df = df.dropna(subset=['Date', 'Category'], how='all')
        
        df = df.reindex(columns=COLUMNS)
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
        df['AppliedRate'] = pd.to_numeric(df['AppliedRate'], errors='coerce').fillna(1.0)
        df['IsExpense'] = pd.to_numeric(df['IsExpense'], errors='coerce').fillna(0).astype(int)
        return df
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        return pd.DataFrame(columns=COLUMNS)

def save_data(df):
    with st.status("Cloud 데이터 동기화 중...", expanded=False) as status:
        try:
            df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
            df['AppliedRate'] = pd.to_numeric(df['AppliedRate'], errors='coerce').fillna(1.0)
            df['IsExpense'] = pd.to_numeric(df['IsExpense'], errors='coerce').fillna(0).astype(int)
            conn.update(worksheet="시트1", data=df.reindex(columns=COLUMNS))
            st.cache_data.clear() # 저장 후 즉시 캐시 비우기
            status.update(label="Cloud 동기화 완료!", state="complete", expanded=False)
            return True
        except Exception as e:
            status.update(label="동기화 실패!", state="error", expanded=True)
            st.error(f"저장 에러: {e}")
            return False

# 데이터 로드 실행
ledger_df = load_data()

# --- 3. [Module B] Quad-Wallet Asset Engine ---
def calculate_quad_balances(df):
    if df.empty: return 0.0, 0.0, 0.0, 0.0
    df_c = df.copy()
    
    # 1. 한국계좌 총 인출액 (충전/환전 시 KRW + 한국 내 직접 원화 지출)
    transfers = df_c[df_c['Category'].isin(['충전', '환전'])]
    transfer_krw = (transfers['Amount'] * transfers['AppliedRate']).sum()
    direct_krw_exp = df_c[(df_c['Currency'] == 'KRW') & (df_c['IsExpense'] == 1)]['Amount'].sum()
    total_bank_out = transfer_krw + direct_krw_exp
    
    # 2. 카드 VND (Card VND)
    cv_in = df_c[(df_c['Category'] == '충전') & (df_c['Currency'] == 'VND')]['Amount'].sum()
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

# --- 4. [Module C, F] UI: Sidebar & Cash Counter ---
with st.sidebar:
    st.title("💰 Strategic Wallet")
    b_out, c_vnd, cash_v, c_usd = calculate_quad_balances(ledger_df)
    
    st.metric("🏦 한국계좌 총 지출액", f"{b_out:,.0f} 원")
    st.divider()
    st.metric("💳 카드 VND", f"{c_vnd:,.0f} ₫")
    st.metric("💵 지폐 VND", f"{cash_v:,.0f} ₫")
    st.metric("🇺🇸 카드 USD", f"${c_usd:,.2f}")
    
    # 5+2 환율 매니저
    st.divider()
    with st.expander("💱 환율 매니저 (5+2)", expanded=False):
        if 'rate_names' not in st.session_state:
            st.session_state.rate_names = ['부산 1차', '머니박스', 'Slot 3', 'Slot 4', 'Slot 5', '달러환전 1', '달러환전 2']
        if 'rates' not in st.session_state:
            st.session_state.rates = [5.61, 6.10, 5.40, 5.40, 5.40, 1350.0, 1380.0]
        for i in range(7):
            c_n, c_v = st.columns([2, 1.5])
            with c_n: st.session_state.rate_names[i] = st.text_input(f"이름 {i+1}", value=st.session_state.rate_names[i], key=f"rn_{i}")
            with c_v: st.session_state.rates[i] = st.number_input(f"환율 {i+1}", value=st.session_state.rates[i], format="%.2f", key=f"rv_{i}")

    # 지폐 카운터
    with st.expander("💵 실물 지폐 카운터", expanded=True):
        st.caption("지갑 속 지폐 수를 넣으세요.")
        bills = [500000, 200000, 100000, 50000, 20000, 10000, 5000, 2000, 1000]
        total_ph = 0
        for bill in bills:
            num = st.number_input(f"{bill:,.0f} ₫", min_value=0, step=1, key=f"bill_{bill}")
            total_ph += bill * num
        st.write(f"실물 합계: {total_ph:,.0f} ₫")
        diff = total_ph - cash_v
        if diff == 0: st.success("장부와 일치합니다! ✨")
        else: st.warning(f"차액: {diff:,.0f} ₫")

    if st.button("🔄 Cloud Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- 5. [Module C] UI: Main Tabs ---
tab_input, tab_history, tab_stats = st.tabs(["📝 기록/이동", "🔍 내역 조회", "📊 지출 분석"])

# --- [TAB 1: 기록하기 (Mobile UX)] ---
with tab_input:
    if 'last_cat_idx' not in st.session_state: st.session_state.last_cat_idx = 0
    if 'last_rate_idx' not in st.session_state: st.session_state.last_rate_idx = 0

    mode = st.radio("기록 모드", ["일반 지출", "자산 이동"], horizontal=True)
    
    if mode == "일반 지출":
        category = st.radio("항목 선택", EXPENSE_CATS, index=st.session_state.last_cat_idx, horizontal=True, key="exp_cat")
        st.session_state.last_cat_idx = EXPENSE_CATS.index(category)
        
        col1, col2 = st.columns(2)
        with col1:
            amount = st.number_input("금액", min_value=0.0, format="%.2f", key="exp_amt")
            currency = st.selectbox("통화", ["VND", "KRW", "USD"], key="exp_curr")
        with col2:
            rate_opts = [f"{st.session_state.rate_names[i]} ({st.session_state.rates[i]:.2f})" for i in range(7)]
            sel_rate_str = st.selectbox("적용 환율", rate_opts, index=st.session_state.last_rate_idx, key="exp_rate")
            st.session_state.last_rate_idx = rate_opts.index(sel_rate_str)
            rate_val = st.session_state.rates[st.session_state.last_rate_idx]
            
            if currency == "KRW": current_rate = 1.0
            else: current_rate = rate_val if "달러" in sel_rate_str else rate_val / 100.0
            
            method = st.selectbox("결제수단", ["트래블로그(VND)", "현금(VND)", "원화계좌", "현대카드(USD)"], key="exp_method")
            
        desc = st.text_input("상세 내용 (메모)", key="exp_desc")
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

# --- [TAB 2: 내역 조회 (History Explorer)] ---
with tab_history:
    st.subheader("🔍 전체 데이터 조회")
    if not ledger_df.empty:
        # 역순 출력 (최신 데이터 상단)
        st.dataframe(ledger_df.iloc[::-1], use_container_width=True)
        if st.button("🗑️ 마지막 행 삭제", use_container_width=True):
            if save_data(ledger_df[:-1]): st.rerun()
    else:
        st.info("기록된 데이터가 없습니다.")

# --- [TAB 3: 지출 분석 (Visual Stats)] ---
with tab_stats:
    if not ledger_df.empty:
        exp_df = ledger_df[ledger_df['IsExpense'] == 1].copy()
        if not exp_df.empty:
            def to_krw(row):
                if row['Currency'] == 'KRW': return row['Amount']
                return row['Amount'] * row['AppliedRate']
            exp_df['Amount_KRW'] = exp_df.apply(to_krw, axis=1)
            
            st.plotly_chart(px.bar(exp_df.groupby('Date')['Amount_KRW'].sum().reset_index(), x='Date', y='Amount_KRW', text_auto=',.0f', title="일별 지출(KRW)"), use_container_width=True)
            st.plotly_chart(px.pie(exp_df.groupby('Category')['Amount_KRW'].sum().reset_index(), values='Amount_KRW', names='Category', hole=0.4, title="항목별 비중"), use_container_width=True)
        else:
            st.info("지출 내역이 없습니다.")
