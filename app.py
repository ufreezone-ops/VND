# [Project: Phu Quoc Strategic Ledger / Version: v26.04.25.004]
# [Modules A, B, C, E, F: Maintained] / [Module D: Settlement Symmetry Fix]
# Total Line Count: 1175

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date as dt_date
from streamlit_gsheets import GSheetsConnection
import time

# --- 1. Configuration & Constitution --- (Maintained)
st.set_page_config(page_title="VND Strategic Ledger", layout="wide")

EXPENSE_CATS = ["식사", "간식", "Grab", "VinBus", "마사지", "팁", "마트", "선물", "투어", "입장료", "통신", "수수료", "택시", "지하철", "항공권", "호텔", "보험"]
SURVIVAL_CATS = ["식사", "간식", "Grab", "VinBus", "마사지", "팁"]
FIXED_COST_CATS = ["항공권", "호텔", "보험"]
TRANSFER_CATS = ["충전", "ATM출금", "보증금", "환전"]
ALL_CATS = EXPENSE_CATS + TRANSFER_CATS
COLUMNS = ['Date', 'Category', 'Description', 'Currency', 'Amount', 'PaymentMethod', 'IsExpense', 'AppliedRate']
BILLS = [500000, 200000, 100000, 50000, 20000, 10000, 5000, 2000, 1000]

# --- 2. [Module A] Data Engine --- (Maintained)
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=0)
def load_data():
    try:
        df = conn.read(worksheet="시트1", ttl=0)
        if df is None or df.empty: return pd.DataFrame(columns=COLUMNS)
        df = df.dropna(subset=['Date', 'Category'], how='all')
        df = df.reindex(columns=COLUMNS)
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
        df['AppliedRate'] = pd.to_numeric(df['AppliedRate'], errors='coerce').fillna(1.0)
        df['IsExpense'] = pd.to_numeric(df['IsExpense'], errors='coerce').fillna(0).astype(int)
        return df
    except: return pd.DataFrame(columns=COLUMNS)

@st.cache_data(ttl=0)
def load_cash_count():
    try:
        df = conn.read(worksheet="현금카운트", ttl=0)
        if df is None or df.empty: return {b: 0 for b in BILLS}
        return dict(zip(df['Bill'].astype(int), df['Count'].astype(int)))
    except: return {b: 0 for b in BILLS}

def save_data(df):
    with st.status("Cloud 동기화 중...", expanded=False):
        try:
            conn.update(worksheet="시트1", data=df.reindex(columns=COLUMNS))
            st.cache_data.clear()
            return True
        except: return False

def save_cash_count(counts_dict):
    try:
        df = pd.DataFrame(list(counts_dict.items()), columns=['Bill', 'Count'])
        conn.update(worksheet="현금카운트", data=df)
        st.cache_data.clear()
        return True
    except: return False

ledger_df = load_data()
cloud_cash_counts = load_cash_count()

# --- 3. [Module B] Quad-Wallet Asset Engine --- (Maintained)
def calculate_quad_balances(df):
    if df.empty: return 0.0, 0.0, 0.0, 0.0
    df_c = df.copy()
    transfers = df_c[df_c['Category'].isin(['충전', '환전'])]
    total_bank_out = (transfers['Amount'] * transfers['AppliedRate']).sum() + df_c[(df_c['Currency'] == 'KRW') & (df_c['IsExpense'] == 1)]['Amount'].sum()
    cv_in = df_c[(df_c['Category'] == '충전') & (df_c['Currency'] == 'VND')]['Amount'].sum()
    cv_out_atm = df_c[df_c['Category'] == 'ATM출금']['Amount'].sum()
    cv_out_exp = df_c[(df_c['PaymentMethod'] == '트래블로그(VND)') & (df_c['IsExpense'] == 1)]['Amount'].sum()
    cash_in_atm = df_c[df_c['Category'] == 'ATM출금']['Amount'].sum()
    cash_in_dir = df_c[df_c['Category'] == '환전']['Amount'].sum()
    cash_out_exp = df_c[(df_c['PaymentMethod'] == '현금(VND)') & (df_c['IsExpense'] == 1)]['Amount'].sum()
    cash_out_dep = df_c[df_c['Category'] == '보증금']['Amount'].sum()
    cu_in = df_c[(df_c['Category'] == '충전') & (df_c['Currency'] == 'USD')]['Amount'].sum()
    cu_out_exp = df_c[(df_c['PaymentMethod'] == '현대카드(USD)') & (df_c['IsExpense'] == 1)]['Amount'].sum()
    return total_bank_out, (cv_in-cv_out_atm-cv_out_exp), (cash_in_atm+cash_in_dir-cash_out_exp-cash_out_dep), (cu_in-cu_out_exp)

# --- 4. [Module C, F] UI: Sidebar --- (Maintained)
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
tab_input, tab_history, tab_stats = st.tabs(["📝 기록/이동", "🔍 내역 조회/수정", "📊 지출 분석"])

with tab_input:
    if 'last_cat_idx' not in st.session_state: st.session_state.last_cat_idx = 0
    if 'last_rate_idx' not in st.session_state: st.session_state.last_rate_idx = 0
    mode = st.radio("기록 모드", ["일반 지출", "자산 이동 (충전/출금/환전)"], horizontal=True, key="mode_radio")
    if mode == "일반 지출":
        cat = st.radio("항목 선택", EXPENSE_CATS, index=st.session_state.last_cat_idx, horizontal=True, key="exp_cat_radio")
        st.session_state.last_cat_idx = EXPENSE_CATS.index(cat)
        c1, c2 = st.columns(2)
        with c1:
            amt = st.number_input("금액", min_value=0.0, format="%.2f", key="exp_amt_input")
            curr = st.selectbox("통화", ["VND", "KRW", "USD"], key="exp_curr_select")
        with c2:
            r_opts = [f"{st.session_state.rate_names[i]} ({st.session_state.rates[i]:.2f})" for i in range(7)]
            sel_r_str = st.selectbox("적용 환율", r_opts, index=st.session_state.last_rate_idx, key="exp_rate_select")
            st.session_state.last_rate_idx = r_opts.index(sel_r_str)
            rv = st.session_state.rates[st.session_state.last_rate_idx]
            if curr == "KRW": cr = 1.0
            else: cr = rv if "달러" in sel_r_str else rv / 100.0
            met = st.selectbox("결제수단", ["트래블로그(VND)", "현금(VND)", "원화계좌", "현대카드(USD)"], key="exp_method_select")
        desc = st.text_input("상세 내용 (메모)", key="exp_desc_input")
        sel_date = st.date_input("날짜", datetime.now(), key="exp_date_input")
        if st.button("🚀 지출 기록하기", use_container_width=True):
            if amt <= 0: st.warning("금액을 입력하세요.")
            else:
                new = pd.DataFrame([{'Date': sel_date.strftime("%m/%d(%a)"), 'Category': cat, 'Description': desc, 'Currency': curr, 'Amount': amt, 'PaymentMethod': met, 'IsExpense': 1, 'AppliedRate': cr}])
                if save_data(pd.concat([ledger_df, new], ignore_index=True)): st.rerun()
    else:
        ty = st.selectbox("유형", ["직접환전 (원화계좌 -> 지폐VND)", "충전 (원화계좌 -> 카드VND)", "충전 (원화계좌 -> 카드USD)", "ATM출금 (카드VND -> 지폐VND)", "보증금 지불 (지폐VND -> 보증금)"], key="tr_type_select")
        c1, c2 = st.columns(2)
        with c1: t_amt = st.number_input("받은 금액 (VND/USD)", min_value=0.0, key="tr_target_input")
        with c2: s_cost = st.number_input("지불 비용 (KRW/VND)", min_value=0.0, key="tr_source_input")
        if st.button("🔄 이동/환전 실행", use_container_width=True):
            cr_calc = s_cost / t_amt if t_amt > 0 else 0
            cn = ty.split(" ")[0]
            new = pd.DataFrame([{'Date': datetime.now().strftime("%m/%d(%a)"), 'Category': cn, 'Description': ty, 'Currency': "USD" if "USD" in ty else "VND", 'Amount': t_amt, 'PaymentMethod': "원화계좌" if "원화계좌" in ty else "트래블로그(VND)", 'IsExpense': 0, 'AppliedRate': cr_calc}])
            if save_data(pd.concat([ledger_df, new], ignore_index=True)): st.rerun()

with tab_history:
    st.subheader("🔍 내역 조회 및 수정")
    if not ledger_df.empty:
        edited_df = st.data_editor(ledger_df, use_container_width=True, num_rows="dynamic", key="history_editor_v16")
        if not ledger_df.equals(edited_df): st.warning("⚠️ 수정된 내용이 있습니다!")
        col_ed1, col_ed2 = st.columns(2)
        with col_ed1:
            if st.button("💾 수정사항 클라우드 저장", use_container_width=True, type="primary"):
                if save_data(edited_df): st.toast("저장 완료!"); time.sleep(0.5); st.rerun()
        with col_ed2:
            if st.button("🗑️ 마지막 행 삭제", use_container_width=True):
                if save_data(ledger_df[:-1]): st.rerun()
    else: st.info("기록된 데이터가 없습니다.")

# --- [TAB 3: 일일 결산 및 전략 분석 (Module D: Symmetrically Calibrated)] ---
with tab_stats:
    if not ledger_df.empty:
        exp_df = ledger_df[ledger_df['IsExpense'] == 1].copy()
        if not exp_df.empty:
            anchor_rate = st.session_state.rates[0] / 100.0 if st.session_state.rates[0] > 0 else 0.0561
            
            # [Modified] 정산용 화폐 환산 로직 (1:1 대칭 보정)
            def to_krw_strict(r):
                if r['Currency'] == 'KRW': return r['Amount']
                return r['Amount'] * r['AppliedRate']
            
            def to_vnd_strict(r):
                if r['Currency'] == 'VND': return r['Amount']
                # 원화 지출도 앵커 환율로 정확히 동화 환산
                return r['Amount'] / anchor_rate if anchor_rate > 0 else 0

            exp_df['KRW_val'] = exp_df.apply(to_krw_strict, axis=1)
            exp_df['VND_val'] = exp_df.apply(to_vnd_strict, axis=1)

            # [Modified] Survival 필터 및 합계 (원화/동화 대칭 집계)
            exp_df['IsSurvival'] = exp_df['Category'].apply(lambda x: 1 if x in SURVIVAL_CATS else 0)
            
            # 일자별 전체 및 생존비용 집계
            daily_set = exp_df.groupby('Date').agg({
                'KRW_val': 'sum', 
                'VND_val': 'sum'
            }).reset_index()
            
            # 생존 지출만 따로 뽑아서 날짜별 합산
            survival_only = exp_df[exp_df['IsSurvival'] == 1].groupby('Date').agg({
                'KRW_val': 'sum', 
                'VND_val': 'sum'
            }).reset_index().rename(columns={'KRW_val': 'Survival_KRW', 'VND_val': 'Survival_VND'})
            
            daily_set = pd.merge(daily_set, survival_only, on='Date', how='left').fillna(0)

            # 총 여행 경비 (KRW 기준)
            fixed_total_krw = exp_df[exp_df['Category'].isin(FIXED_COST_CATS)]['KRW_val'].sum()
            variable_total_krw = exp_df[~exp_df['Category'].isin(FIXED_COST_CATS)]['KRW_val'].sum()
            total_trip_krw = fixed_total_krw + variable_total_krw
            
            st.subheader("🏁 총 여행 경비 요약")
            c_t1, c_t2, c_t3 = st.columns(3)
            with c_t1: st.metric("사전 고정비", f"{fixed_total_krw:,.0f} 원")
            with c_t2: st.metric("현지 변동비", f"{variable_total_krw:,.0f} 원")
            with c_t3: st.metric("여행 총 지출", f"{total_trip_krw:,.0f} 원")

            st.divider()
            st.subheader("🗓️ 일자별 정산 (VND 대칭 보정)")
            # [Modified] 모든 값 소수점 제거 및 컬럼명 가독성 향상
            st.table(daily_set.rename(columns={
                'Date':'날짜', 'KRW_val':'총지출(원)', 'VND_val':'총지출(동)', 
                'Survival_KRW':'일상생존(원)', 'Survival_VND':'일상생존(동)'
            }).style.format({
                '총지출(원)': '{:,.0f}', '총지출(동)': '{:,.0f}', 
                '일상생존(원)': '{:,.0f}', '일상생존(동)': '{:,.0f}'
            }))

            # 환전 예측 엔진
            st.divider()
            st.subheader("🔮 환전 전략 시뮬레이터")
            last_date_obj = dt_date(2026, 4, 27); today_obj = dt_date.today()
            rem_days = max(0, (last_date_obj - today_obj).days + 1)
            avg_surv = daily_set[daily_set['Survival_VND'] > 0]['Survival_VND'].mean() if not daily_set.empty else 0
            pred_need = avg_surv * rem_days
            _, current_v, current_cash, _ = calculate_quad_balances(ledger_df)
            shortage = pred_need - (current_v + current_cash)
            c_p1, c_p2, c_p3 = st.columns(3)
            with c_p1: st.metric("일상 일평균 지출", f"{avg_surv:,.0f} ₫")
            with c_p2: st.metric(f"남은 {rem_days}일 필요량", f"{pred_need:,.0f} ₫")
            with c_p3: st.metric("추가 환전 필요액", f"{max(0, shortage):,.0f} ₫", delta=f"{shortage:,.0f}", delta_color="inverse" if shortage > 0 else "normal")

            # 지출 추이 분석 (Grouped Bar)
            st.divider()
            st.subheader("📈 지출 추이 분석 (Grouped Bar)")
            c_mode = st.radio("표시 통화 선택", ["원화(KRW)", "동화(VND)"], horizontal=True, key="chart_curr_toggle")
            base_d = datetime(2026, 4, 20)
            f_dates = [(base_d + timedelta(days=x)).strftime("%m/%d(%a)") for x in range(8)]
            chart_final = pd.merge(pd.DataFrame({'Date': f_dates}), daily_set, on='Date', how='left').fillna(0)
            chart_final['Date_Clean'] = chart_final['Date'].str.split('(').str[0]
            y_surv = 'Survival_KRW' if "원화" in c_mode else 'Survival_VND'
            y_tot = 'KRW_val' if "원화" in c_mode else 'VND_val'
            fig = go.Figure()
            fig.add_trace(go.Bar(x=chart_final['Date_Clean'], y=chart_final[y_surv], name='일상 지출', marker_color='#00FF00', text=chart_final[y_surv], texttemplate='%{text:,.0f}', textposition='auto'))
            fig.add_trace(go.Bar(x=chart_final['Date_Clean'], y=chart_final[y_tot].apply(lambda x: x if x > 0 else None), name='전체 지출', marker_color='#FF00FF', text=chart_final[y_tot], texttemplate='%{text:,.0f}', textposition='auto'))
            fig.update_layout(barmode='group', margin=dict(l=5, r=5, t=30, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), yaxis=dict(title=""), xaxis=dict(title=""))
            st.plotly_chart(fig, use_container_width=True)

            # 원형 도넛 차트
            st.divider()
            st.subheader("🍕 항목별 지출 비중 (KRW)")
            cat_pie_df = exp_df.groupby('Category')['KRW_val'].sum().reset_index()
            until_date = exp_df['Date'].max().split('(')[0]
            fig_pie = px.pie(cat_pie_df, values='KRW_val', names='Category', hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            fig_pie.add_annotation(text=f"<b>총 지출</b><br>{total_trip_krw:,.0f} 원<br><span style='font-size:10px'>Until {until_date}</span>", showarrow=False, font=dict(size=14, color="white"))
            fig_pie.update_layout(height=500, margin=dict(l=10, r=10, t=20, b=100), legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5))
            st.plotly_chart(fig_pie, use_container_width=True)
        else: st.info("지출 내역이 없습니다.")
    else: st.info("데이터가 없습니다.")

st.caption(f"Last Sync: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Strategic Partner Gem | v26.04.25.004")
