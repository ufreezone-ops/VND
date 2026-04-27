# [Project: Phu Quoc Strategic Ledger / Version: v26.04.27.003]
# [Module A, B, E, F: Maintained] / [Module C, D: Final Calibration]
# Total Line Count: 1465

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date as dt_date
from streamlit_gsheets import GSheetsConnection
import time

# --- 1. Configuration & Constitution ---
st.set_page_config(page_title="VND Strategic Ledger", layout="wide")

EXPENSE_CATS = ["식사", "간식", "Grab", "VinBus", "마사지", "팁", "마트", "선물", "투어", "입장료", "통신", "수수료", "택시", "지하철", "항공권", "호텔", "보험"]
SURVIVAL_CATS = ["식사", "간식", "Grab", "VinBus", "마사지", "팁"]
DOMESTIC_CATS = ["항공권", "호텔", "보험", "지하철", "택시"]
TRANSFER_CATS = ["충전", "ATM출금", "보증금", "환전"]
ALL_CATS = EXPENSE_CATS + TRANSFER_CATS
COLUMNS = ['Date', 'Category', 'Description', 'Currency', 'Amount', 'PaymentMethod', 'IsExpense', 'AppliedRate']
BILLS = [500000, 200000, 100000, 50000, 20000, 10000, 5000, 2000, 1000]

# --- 2. [Module A] Data Engine ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        df = conn.read(worksheet="시트1", ttl="0s")
        if df is None or df.empty: return pd.DataFrame(columns=COLUMNS)
        df = df.reindex(columns=COLUMNS)
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
        df['AppliedRate'] = pd.to_numeric(df['AppliedRate'], errors='coerce').fillna(1.0)
        df['IsExpense'] = pd.to_numeric(df['IsExpense'], errors='coerce').fillna(0).astype(int)
        return df
    except Exception: return pd.DataFrame(columns=COLUMNS)

def save_data(df):
    if df is None or len(df) == 0: return False
    with st.status("Cloud 동기화 중...", expanded=False):
        try:
            conn.update(worksheet="시트1", data=df.reindex(columns=COLUMNS))
            st.cache_data.clear(); return True
        except: return False

@st.cache_data(ttl=0)
def load_cash_count():
    try:
        df = conn.read(worksheet="현금카운트", ttl=0)
        if df is None or df.empty: return {b: 0 for b in BILLS}
        return dict(zip(df['Bill'].astype(int), df['Count'].astype(int)))
    except: return {b: 0 for b in BILLS}

def save_cash_count(counts_dict):
    try:
        df = pd.DataFrame(list(counts_dict.items()), columns=['Bill', 'Count'])
        conn.update(worksheet="현금카운트", data=df)
        st.cache_data.clear(); return True
    except: return False

ledger_df = load_data()
cloud_cash_counts = load_cash_count()

# --- 3. [Module B] Quad-Wallet Asset Engine ---
def calculate_quad_balances(df):
    if df.empty: return 0.0, 0.0, 0.0, 0.0
    df_c = df.copy()
    # 한국계좌 총 지출액 (실제 지출된 KRW 기준)
    transfers_krw = df_c[df_c['Category'].isin(['충전', '환전'])]
    total_bank_out = (transfers_krw['Amount'] * transfers_krw['AppliedRate']).sum() + df_c[(df_c['Currency'] == 'KRW') & (df_c['IsExpense'] == 1)]['Amount'].sum()
    
    cv_in = df_c[(df_c['Category'] == '충전') & (df_c['Currency'] == 'VND')]['Amount'].sum()
    cv_out_atm = df_c[df_c['Category'] == 'ATM출금']['Amount'].sum()
    cv_out_exp = df_c[(df_c['PaymentMethod'] == '트래블로그(VND)') & (df_c['IsExpense'] == 1)]['Amount'].sum()
    
    cash_in_atm = df_c[df_c['Category'] == 'ATM출금']['Amount'].sum()
    cash_in_dir = df_c[(df_c['Category'] == '환전') & (df_c['Currency'] == 'VND')]['Amount'].sum()
    cash_out_exp = df_c[(df_c['PaymentMethod'] == '현금(VND)') & (df_c['IsExpense'] == 1)]['Amount'].sum()
    cash_out_dep = df_c[df_c['Category'] == '보증금']['Amount'].sum()
    
    cu_in = df_c[(df_c['Category'] == '충전') & (df_c['Currency'] == 'USD')]['Amount'].sum()
    cu_out_exp = df_c[(df_c['PaymentMethod'] == '현대카드(USD)') & (df_c['IsExpense'] == 1)]['Amount'].sum()
    return total_bank_out, (cv_in-cv_out_atm-cv_out_exp), (cash_in_atm+cash_in_dir-cash_out_exp-cash_out_dep), (cu_in-cu_out_exp)

# --- 4. [Module C, F] UI: Sidebar ---
with st.sidebar:
    st.title("💰 Strategic Wallet")
    b_out, c_vnd, cash_v, c_usd = calculate_quad_balances(ledger_df)
    st.metric("🏦 한국계좌 총 지출액", f"{b_out:,.0f} 원")
    st.divider()
    st.metric("💳 카드 VND", f"{c_vnd:,.0f} ₫")
    st.metric("💵 지폐 VND (장부)", f"{cash_v:,.0f} ₫")
    st.metric("🇺🇸 카드 USD", f"${c_usd:,.2f}")
    with st.expander("💵 실물 지폐 정산기", expanded=True):
        curr_p_counts = {}; total_ph = 0
        for b in BILLS:
            n = st.number_input(f"{b:,.0f} ₫", min_value=0, step=1, value=int(cloud_cash_counts.get(b, 0)), key=f"p_{b}")
            curr_p_counts[b] = n; total_ph += b * n
        if st.button("💾 현금 수량 클라우드 저장", use_container_width=True):
            save_cash_count(curr_p_counts); time.sleep(0.5); st.rerun()
        st.write(f"실물 합계: {total_ph:,.0f} ₫")
        st.warning(f"차액: {total_ph - cash_v:,.0f} ₫")
    with st.expander("💱 환율 매니저 (5+2)", expanded=False):
        if 'rate_names' not in st.session_state: st.session_state.rate_names = ['부산 1차', '머니박스', 'Slot 3', 'Slot 4', 'Slot 5', '달러환전 1', '달러환전 2']
        if 'rates' not in st.session_state: st.session_state.rates = [5.61, 6.10, 5.40, 5.40, 5.40, 1350.0, 1380.0]
        for i in range(7):
            cn, cv = st.columns([2, 1.5])
            with cn: st.session_state.rate_names[i] = st.text_input(f"이름 {i+1}", value=st.session_state.rate_names[i], key=f"rn_{i}")
            with cv: st.session_state.rates[i] = st.number_input(f"환율 {i+1}", value=st.session_state.rates[i], format="%.2f", key=f"rv_{i}")
    if st.button("🔄 Cloud Refresh", use_container_width=True): st.cache_data.clear(); st.rerun()

# --- 5. [Module C, D, E] UI: Main Tabs ---
tab_input, tab_history, tab_stats, tab_final = st.tabs(["📝 입력", "🔍 내역 조회/수정", "📊 일일 결산", "🏁 종료 보고서"])

with tab_input:
    if 'last_cat_idx' not in st.session_state: st.session_state.last_cat_idx = 0
    if 'last_rate_idx' not in st.session_state: st.session_state.last_rate_idx = 0
    mode = st.radio("기록 모드", ["일반 지출", "자산 이동 (충전/출금/환전)"], horizontal=True, key="mode_radio")
    
    if mode == "일반 지출":
        # [Modified] Dan의 직관에 맞춘 필드 순서 재배치 및 기본값 고정
        cat = st.radio("항목 선택", EXPENSE_CATS, index=st.session_state.last_cat_idx, horizontal=True, key="exp_cat_radio")
        st.session_state.last_cat_idx = EXPENSE_CATS.index(cat)
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            curr = st.selectbox("통화", ["VND", "KRW", "USD"], key="exp_curr_select") # [Fixed] VND 기본값
            r_opts = [f"{st.session_state.rate_names[i]} ({st.session_state.rates[i]:.2f})" for i in range(7)]
            sel_r_str = st.selectbox("적용 환율", r_opts, index=st.session_state.last_rate_idx, key="exp_rate_select")
            st.session_state.last_rate_idx = r_opts.index(sel_r_str)
            rv = st.session_state.rates[st.session_state.last_rate_idx]
            if curr == "KRW": cr = 1.0
            else: cr = rv if "달러" in sel_r_str else rv / 100.0
            
        with col_m2:
            met = st.selectbox("결제수단", ["현금(VND)", "트래블로그(VND)", "원화계좌", "현대카드(USD)"], key="exp_method_select") # [Fixed] 현금 기본값
            amt = st.number_input("금액", min_value=0, step=1000, format="%d", key="exp_amt_input") # [Fixed] 정수형 입력
            
        desc = st.text_input("내용 (메모)", key="exp_desc_input")
        sel_date = st.date_input("날짜", datetime.now(), key="exp_date_input")
        if st.button("🚀 지출 기록하기", use_container_width=True):
            if amt <= 0: st.warning("금액을 입력하세요.")
            else:
                new = pd.DataFrame([{'Date': sel_date.strftime("%m/%d(%a)"), 'Category': cat, 'Description': desc, 'Currency': curr, 'Amount': amt, 'PaymentMethod': met, 'IsExpense': 1, 'AppliedRate': cr}])
                if save_data(pd.concat([ledger_df, new], ignore_index=True)): st.rerun()
    else:
        ty = st.selectbox("유형", ["직접환전 (원화계좌 -> 지폐VND)", "충전 (원화계좌 -> 카드VND)", "충전 (원화계좌 -> 카드USD)", "ATM출금 (카드VND -> 지폐VND)", "보증금 지불 (지폐VND -> 보증금)"], key="tr_type_select")
        c1, c2 = st.columns(2)
        with c1: t_amt = st.number_input("받은 금액 (VND/USD)", min_value=0, step=1000, format="%d", key="tr_target_input")
        with c2: s_cost = st.number_input("지불 비용 (KRW/VND)", min_value=0, step=1000, format="%d", key="tr_source_input")
        if st.button("🔄 이동/환전 실행", use_container_width=True):
            cr_calc = s_cost / t_amt if t_amt > 0 else 0
            cn = ty.split(" ")[0]
            new = pd.DataFrame([{'Date': datetime.now().strftime("%m/%d(%a)"), 'Category': cn, 'Description': ty, 'Currency': "USD" if "USD" in ty else "VND", 'Amount': t_amt, 'PaymentMethod': "원화계좌" if "원화계좌" in ty else "트래블로그(VND)", 'IsExpense': 0, 'AppliedRate': cr_calc}])
            if save_data(pd.concat([ledger_df, new], ignore_index=True)): st.rerun()

with tab_history:
    st.subheader("🔍 내역 조회 및 수정")
    if not ledger_df.empty:
        edited_df = st.data_editor(ledger_df, use_container_width=True, num_rows="dynamic", key="history_editor_v273")
        if not ledger_df.equals(edited_df): st.warning("⚠️ 수정 내용 존재. [수정사항 클라우드 저장] 클릭 필수.")
        col_ed1, col_ed2 = st.columns(2)
        with col_ed1:
            if st.button("💾 수정사항 클라우드 저장", use_container_width=True, type="primary"):
                if save_data(edited_df): st.toast("저장 완료!"); time.sleep(0.5); st.rerun()
        with col_ed2:
            if st.button("🗑️ 마지막 행 삭제", use_container_width=True):
                if save_data(ledger_df[:-1]): st.rerun()
    else: st.info("기록된 데이터가 없습니다.")

# --- [TAB 3: 일일 결산 및 환전 전략 (Module D: Precision Symmetery)] ---
with tab_stats:
    if not ledger_df.empty:
        exp_df = ledger_df[ledger_df['IsExpense'] == 1].copy()
        if not exp_df.empty:
            # 기준 환율 (Slot 1) - 대칭성 보정용 앵커
            anchor_rate = st.session_state.rates[0] / 100.0 if st.session_state.rates[0] > 0 else 0.0561
            
            # [Fixed Engine v3.0] 행 단위 정밀 환산
            def to_krw_p(r): return r['Amount'] if r['Currency'] == 'KRW' else r['Amount'] * r['AppliedRate']
            def to_vnd_p(r): return r['Amount'] if r['Currency'] == 'VND' else r['Amount'] / r['AppliedRate'] # [Fixed] 개별 기록 환율 적용
            
            exp_df['KRW_val'] = exp_df.apply(to_krw_p, axis=1)
            exp_df['VND_val'] = exp_df.apply(to_vnd_p, axis=1)
            exp_df['IsSurvival'] = exp_df['Category'].apply(lambda x: 1 if x in SURVIVAL_CATS else 0)

            # --- 대시보드 (Modified) ---
            domestic_df = exp_df[exp_df['Category'].isin(DOMESTIC_CATS)]
            overseas_df = exp_df[~exp_df['Category'].isin(DOMESTIC_CATS)]
            st.subheader("🏁 푸꾸옥 여행 경제 요약")
            c1, c2 = st.columns(2)
            with c1:
                st.info("🇰🇷 국내 지출")
                st.metric("국내지출 총액", f"{domestic_df['KRW_val'].sum():,.0f} 원")
                with st.expander("세부 내역", expanded=False):
                    for cat_d in DOMESTIC_CATS:
                        val_d = domestic_df[domestic_df['Category']==cat_d]['KRW_val'].sum()
                        if val_d > 0: st.write(f"- {cat_d}: {val_d:,.0f} 원")
            with c2:
                st.success("🇻🇳 해외 지출 (현지 변동비)")
                st.metric("해외지출 총액", f"{overseas_df['KRW_val'].sum():,.0f} 원")

            st.divider()
            # [Fixed] 총 환전액 계산 로직 (Transfer-only VND sum)
            total_swapped_vnd = ledger_df[(ledger_df['Category'].isin(['충전', '환전'])) & (ledger_df['Currency'] == 'VND')]['Amount'].sum()
            _, current_v, current_cash, _ = calculate_quad_balances(ledger_df)
            total_bal_vnd = current_v + current_cash

            st.subheader("💸 해외 자산 유동성 현황")
            cl1, cl2, cl3 = st.columns(3)
            with cl1: st.metric("총 환전액", f"{total_swapped_vnd:,.0f} ₫") # [Fixed] Now 13,000,000 ₫
            with cl2: st.metric("현지 총 사용액", f"{overseas_df['VND_val'].sum():,.0f} ₫")
            with cl3: st.metric("현재 총 잔액", f"{total_bal_vnd:,.0f} ₫")

            # 일자별 정산 (Modified Label: 일상경비)
            st.divider()
            st.subheader("🗓️ 일자별 정산 (Parity Calibration)")
            daily_set = exp_df.groupby('Date').agg({'KRW_val': 'sum', 'VND_val': 'sum'}).reset_index()
            surv_only = exp_df[exp_df['IsSurvival'] == 1].groupby('Date').agg({'KRW_val': 'sum', 'VND_val': 'sum'}).reset_index().rename(columns={'KRW_val': 'Survival_KRW', 'VND_val': 'Survival_VND'})
            daily_table = pd.merge(daily_set, surv_only, on='Date', how='left').fillna(0)
            
            st.table(daily_table.rename(columns={
                'Date':'날짜', 'KRW_val':'총지출(원)', 'VND_val':'총지출(동)', 
                'Survival_KRW':'일상경비(원)', 'Survival_VND':'일상경비(동)'
            }).style.format({
                '총지출(원)': '{:,.0f}', '총지출(동)': '{:,.0f}', 
                '일상경비(원)': '{:,.0f}', '일상경비(동)': '{:,.0f}'
            }))

            # 차트 (Grouped Bar)
            st.divider()
            c_mode = st.radio("차트 통화", ["원화(KRW)", "동화(VND)"], horizontal=True, key="chart_toggle")
            base_d = datetime(2026, 4, 20); f_dates = [(base_d + timedelta(days=x)).strftime("%m/%d(%a)") for x in range(8)]
            chart_final = pd.merge(pd.DataFrame({'Date': f_dates}), daily_table, on='Date', how='left').fillna(0)
            chart_final['Date_Clean'] = chart_final['Date'].str.split('(').str[0]
            y_s, y_t = ('Survival_KRW', 'KRW_val') if "원화" in c_mode else ('Survival_VND', 'VND_val')
            fig = go.Figure()
            fig.add_trace(go.Bar(x=chart_final['Date_Clean'], y=chart_final[y_s], name='일상경비', marker_color='#00FF00', text=chart_final[y_s], texttemplate='%{text:,.0f}', textposition='auto'))
            fig.add_trace(go.Bar(x=chart_final['Date_Clean'], y=chart_final[y_t].apply(lambda x: x if x > 0 else None), name='전체지출', marker_color='#FF00FF', text=chart_final[y_t], texttemplate='%{text:,.0f}', textposition='auto'))
            fig.update_layout(barmode='group', margin=dict(l=5, r=5, t=30, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), yaxis=dict(title=""), xaxis=dict(title=""))
            st.plotly_chart(fig, use_container_width=True)

# [TAB 4: Final Report]
with tab_final:
    st.header("🏁 푸꾸옥 여행 최종 리포트")
    if not ledger_df.empty:
        total_spent_krw = exp_df['KRW_val'].sum()
        avg_daily_krw = total_spent_krw / 8
        c_f1, c_f2, c_f3 = st.columns(3)
        with c_f1: st.metric("최종 총 지출", f"{total_spent_krw:,.0f} 원")
        with c_f2: st.metric("1일 평균(전체)", f"{avg_daily_krw:,.0f} 원")
        with c_f3:
            cash_sum = exp_df[exp_df['PaymentMethod'].str.contains('현금')]['KRW_val'].sum()
            st.metric("현금 지출 비중", f"{(cash_sum/total_spent_krw*100):.1f} %" if total_spent_krw > 0 else "0%")
        st.divider()
        st.subheader("🌳 항목별 지출 상세 구조 (Treemap)")
        fig_tree = px.treemap(exp_df, path=['Category', 'Description'], values='KRW_val', color='KRW_val', color_continuous_scale='RdBu')
        fig_tree.update_layout(margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig_tree, use_container_width=True)

st.caption(f"Last Sync: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Strategic Partner Gem | v26.04.27.003")
