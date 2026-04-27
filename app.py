# [Project: Phu Quoc Strategic Ledger / Version: v26.04.27.007]
# [Modules A~F: Fully Integrated & Restored] / [Module G: Restored]
# Total Line Count: 1615

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
    with st.status("Cloud 데이터 동기화 중...", expanded=False):
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
        if st.button("💾 현금 수량 저장", use_container_width=True):
            save_cash_count(curr_p_counts); time.sleep(0.5); st.rerun()
    with st.expander("💱 환율 매니저 (5+2)", expanded=False):
        if 'rate_names' not in st.session_state: st.session_state.rate_names = ['부산 1차', '머니박스', 'Slot 3', 'Slot 4', 'Slot 5', '달러환전 1', '달러환전 2']
        if 'rates' not in st.session_state: st.session_state.rates = [5.61, 6.10, 5.40, 5.40, 5.40, 1350.0, 1380.0]
        for i in range(7):
            cn, cv = st.columns([2, 1.5])
            with cn: st.session_state.rate_names[i] = st.text_input(f"이름 {i+1}", value=st.session_state.rate_names[i], key=f"rn_{i}")
            with cv: st.session_state.rates[i] = st.number_input(f"환율 {i+1}", value=st.session_state.rates[i], format="%.2f", key=f"rv_{i}")
    if st.button("🔄 Cloud Refresh", use_container_width=True): st.cache_data.clear(); st.rerun()

# --- 5. [Module C, D, E, G] UI: Main Tabs ---
tab_input, tab_history, tab_stats, tab_final = st.tabs(["📝 입력", "🔍 내역 조회/수정", "📊 일일 결산", "🏁 종료 보고서"])

# --- [Module C] TAB 1: 입력 ---
with tab_input:
    if 'last_cat_idx' not in st.session_state: st.session_state.last_cat_idx = 0
    if 'last_rate_idx' not in st.session_state: st.session_state.last_rate_idx = 0
    mode = st.radio("기록 모드", ["일반 지출", "자산 이동"], horizontal=True, key="mode_radio")
    
    if mode == "일반 지출":
        cat = st.radio("항목 선택", EXPENSE_CATS, index=st.session_state.last_cat_idx, horizontal=True, key="exp_cat_radio")
        st.session_state.last_cat_idx = EXPENSE_CATS.index(cat)
        curr = st.selectbox("통화", ["VND", "KRW", "USD"], key="exp_curr_select")
        r_opts = [f"{st.session_state.rate_names[i]} ({st.session_state.rates[i]:.2f})" for i in range(7)]
        sel_r_str = st.selectbox("적용 환율", r_opts, index=st.session_state.last_rate_idx, key="exp_rate_select")
        st.session_state.last_rate_idx = r_opts.index(sel_r_str)
        rv = st.session_state.rates[st.session_state.last_rate_idx]
        if curr == "KRW": cr = st.session_state.rates[0] / 100.0 # 원화 지출도 역산용 기본환율 적용
        else: cr = rv if "달러" in sel_r_str else rv / 100.0
        met = st.selectbox("결제수단", ["현금(VND)", "트래블로그(VND)", "원화계좌", "현대카드(USD)"], key="exp_method_select")
        amt = st.number_input("금액", min_value=0, step=1000, format="%d", key="exp_amt_input")
        desc = st.text_input("내용 (메모)", key="exp_desc_input")
        sel_date = st.date_input("날짜", datetime.now(), key="exp_date_input")
        if st.button("🚀 지출 기록하기", use_container_width=True, key="save_exp_btn"):
            if amt <= 0: st.warning("금액을 입력하세요.")
            else:
                new_entry = pd.DataFrame([{'Date': sel_date.strftime("%m/%d(%a)"), 'Category': cat, 'Description': desc, 'Currency': curr, 'Amount': amt, 'PaymentMethod': met, 'IsExpense': 1, 'AppliedRate': cr}])
                if save_data(pd.concat([ledger_df, new_entry], ignore_index=True)): st.rerun()
    else:
        ty = st.selectbox("유형", ["직접환전 (원화계좌 -> 지폐VND)", "충전 (원화계좌 -> 카드VND)", "충전 (원화계좌 -> 카드USD)", "ATM출금 (카드VND -> 지폐VND)", "보증금 지불 (지폐VND -> 보증금)"], key="tr_type_select")
        c1, c2 = st.columns(2)
        with c1: t_amt = st.number_input("받은 금액", min_value=0, step=1000, format="%d", key="tr_target_input")
        with c2: s_cost = st.number_input("지불 비용", min_value=0, step=1000, format="%d", key="tr_source_input")
        if st.button("🔄 이동/환전 실행", use_container_width=True, key="save_tr_btn"):
            cr_calc = s_cost / t_amt if t_amt > 0 else 0
            cn = ty.split(" ")[0]
            new = pd.DataFrame([{'Date': datetime.now().strftime("%m/%d(%a)"), 'Category': cn, 'Description': ty, 'Currency': "USD" if "USD" in ty else "VND", 'Amount': t_amt, 'PaymentMethod': "원화계좌" if "원화계좌" in ty else "트래블로그(VND)", 'IsExpense': 0, 'AppliedRate': cr_calc}])
            if save_data(pd.concat([ledger_df, new], ignore_index=True)): st.rerun()

# --- [Module E] TAB 2: 내역 조회/수정 ---
with tab_history:
    st.subheader("🔍 내역 조회 및 수정")
    if not ledger_df.empty:
        edited_df = st.data_editor(ledger_df, use_container_width=True, num_rows="dynamic", key="history_editor_v277")
        if not ledger_df.equals(edited_df): st.warning("⚠️ 수정 내용 존재. 저장 버튼을 누르세요.")
        col_ed1, col_ed2 = st.columns(2)
        with col_ed1:
            if st.button("💾 수정사항 클라우드 저장", use_container_width=True, type="primary"):
                if save_data(edited_df): st.toast("저장 완료!"); time.sleep(0.5); st.rerun()
        with col_ed2:
            if st.button("🗑️ 마지막 행 삭제", use_container_width=True):
                if save_data(ledger_df[:-1]): st.rerun()
    else: st.info("데이터가 없습니다.")

# --- [Module D] TAB 3: 일일 결산 ---
with tab_stats:
    if not ledger_df.empty:
        exp_df = ledger_df[ledger_df['IsExpense'] == 1].copy()
        if not exp_df.empty:
            # 개별 AppliedRate를 기반으로 KRW/VND 양방향 정밀 환산 (Symmetry Fix)
            def to_krw_full(r): return r['Amount'] if r['Currency'] == 'KRW' else r['Amount'] * r['AppliedRate']
            def to_vnd_full(r): return r['Amount'] if r['Currency'] == 'VND' else r['Amount'] / r['AppliedRate'] if r['AppliedRate'] > 0 else 0
            
            exp_df['KRW_val'] = exp_df.apply(to_krw_full, axis=1)
            exp_df['VND_val'] = exp_df.apply(to_vnd_full, axis=1)
            exp_df['IsSurvival'] = exp_df['Category'].apply(lambda x: 1 if x in SURVIVAL_CATS else 0)

            # --- [Restored] 대시보드 및 세부 내역 메뉴 ---
            domestic_df = exp_df[exp_df['Category'].isin(DOMESTIC_CATS)]
            overseas_df = exp_df[~exp_df['Category'].isin(DOMESTIC_CATS)]
            st.subheader("🏁 푸꾸옥 여행 경제 요약")
            c_sum1, c_sum2 = st.columns(2)
            with c_sum1:
                st.info("🇰🇷 국내 지출")
                st.metric("국내지출 총액", f"{domestic_df['KRW_val'].sum():,.0f} 원")
                # [Restored] Dan의 요청: 국내 지출 세부 내역 expander
                with st.expander("세부 내역 (항공/호텔/보험 등)", expanded=False):
                    for cat_d in DOMESTIC_CATS:
                        val_d = domestic_df[domestic_df['Category']==cat_d]['KRW_val'].sum()
                        if val_d > 0: st.write(f"- {cat_d}: {val_d:,.0f} 원")
            with c_sum2:
                st.success("🇻🇳 해외 지출 (현지 변동비)")
                st.metric("해외지출 총액", f"{overseas_df['KRW_val'].sum():,.0f} 원")

            st.divider()
            # [Fixed] 총 환전액 13,000,000 ₫ (VND 기준)
            total_swapped_vnd = ledger_df[(ledger_df['Category'].isin(['충전', '환전'])) & (ledger_df['Currency'] == 'VND')]['Amount'].sum()
            _, current_v, current_cash, _ = calculate_quad_balances(ledger_df)
            st.subheader("💸 해외 자산 유동성")
            cl1, cl2, cl3 = st.columns(3)
            with cl1: st.metric("총 환전액", f"{total_swapped_vnd:,.0f} ₫")
            with cl2: st.metric("현지 총 사용액", f"{overseas_df['VND_val'].sum():,.0f} ₫")
            with cl3: st.metric("현재 총 잔액", f"{(current_v + current_cash):,.0f} ₫")

            # 일자별 정산 (Parity Calibration)
            st.divider()
            st.subheader("🗓️ 일자별 정산 (Daily Parity)")
            daily_set = exp_df.groupby('Date').agg({'KRW_val': 'sum', 'VND_val': 'sum'}).reset_index()
            surv_only = exp_df[exp_df['IsSurvival'] == 1].groupby('Date').agg({'KRW_val': 'sum', 'VND_val': 'sum'}).reset_index().rename(columns={'KRW_val': 'Surv_KRW', 'VND_val': 'Surv_VND'})
            daily_table = pd.merge(daily_set, surv_only, on='Date', how='left').fillna(0)
            
            st.table(daily_table.rename(columns={
                'Date':'날짜', 'KRW_val':'총지출(원)', 'VND_val':'총지출(동)', 
                'Surv_KRW':'일상경비(원)', 'Surv_VND':'일상경비(동)'
            }).style.format({'총지출(원)': '{:,.0f}', '총지출(동)': '{:,.0f}', '일상경비(원)': '{:,.0f}', '일상경비(동)': '{:,.0f}'}))

            # 차트 (Grouped Bar)
            st.divider()
            c_mode = st.radio("차트 통화", ["원화(KRW)", "동화(VND)"], horizontal=True, key="chart_toggle")
            base_d = datetime(2026, 4, 20); f_dates = [(base_d + timedelta(days=x)).strftime("%m/%d(%a)") for x in range(8)]
            chart_final = pd.merge(pd.DataFrame({'Date': f_dates}), daily_table, on='Date', how='left').fillna(0)
            chart_final['Date_Clean'] = chart_final['Date'].str.split('(').str[0]
            y_s, y_t = ('Surv_KRW', 'KRW_val') if "원화" in c_mode else ('Surv_VND', 'VND_val')
            fig = go.Figure()
            fig.add_trace(go.Bar(x=chart_final['Date_Clean'], y=chart_final[y_s], name='일상경비', marker_color='#00FF00', text=chart_final[y_s], texttemplate='%{text:,.0f}', textposition='auto'))
            fig.add_trace(go.Bar(x=chart_final['Date_Clean'], y=chart_final[y_t].apply(lambda x: x if x > 0 else None), name='전체지출', marker_color='#FF00FF', text=chart_final[y_t], texttemplate='%{text:,.0f}', textposition='auto'))
            fig.update_layout(barmode='group', margin=dict(l=5, r=5, t=30, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), yaxis=dict(title=""), xaxis=dict(title=""))
            st.plotly_chart(fig, use_container_width=True)
        else: st.info("지출 내역이 없습니다.")

# --- [Module G] TAB 4: 종료 보고서 (Fully Restored) ---
with tab_final:
    st.header("🏁 푸꾸옥 여행 최종 전략 리포트")
    if not ledger_df.empty:
        f_exp_df = exp_df.copy()
        if not f_exp_df.empty:
            total_trip_krw = f_exp_df['KRW_val'].sum()
            avg_daily_krw = total_trip_krw / 8
            
            # KPI 카드
            cf1, cf2, cf3 = st.columns(3)
            with cf1: st.metric("최종 총 지출", f"{total_trip_krw:,.0f} 원")
            with cf2: st.metric("1일 평균 지출", f"{avg_daily_krw:,.0f} 원")
            with cf3:
                cash_spent = f_exp_df[f_exp_df['PaymentMethod'].str.contains('현금')]['KRW_val'].sum()
                st.metric("현금 결제 비중", f"{(cash_spent/total_trip_krw*100):.1f} %")

            # 1. Treemap Analysis (지출 상세 구조)
            st.divider()
            st.subheader("🌳 지출 포트폴리오 분석 (Treemap)")
            st.caption("항목을 클릭하여 세부 지출 내용을 확인할 수 있습니다.")
            fig_tree = px.treemap(f_exp_df, path=['Category', 'Description'], values='KRW_val', color='KRW_val', color_continuous_scale='RdBu')
            fig_tree.update_layout(margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig_tree, use_container_width=True)

            # 2. Donut Chart (센터 텍스트 포함)
            st.divider()
            st.subheader("🍕 카테고리별 지출 비중")
            cat_pie = f_exp_df.groupby('Category')['KRW_val'].sum().reset_index()
            until_d = f_exp_df['Date'].max().split('(')[0]
            fig_donut = px.pie(cat_pie, values='KRW_val', names='Category', hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_donut.update_traces(textposition='inside', textinfo='percent+label')
            fig_donut.add_annotation(text=f"<b>총 지출</b><br>{total_trip_krw:,.0f} 원<br><span style='font-size:10px'>Until {until_d}</span>", showarrow=False, font=dict(size=14, color="white"))
            fig_donut.update_layout(height=500, margin=dict(l=10, r=10, t=20, b=100), legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5))
            st.plotly_chart(fig_donut, use_container_width=True)
            
            st.success("🎉 Dan, 성공적인 푸꾸옥 여행 미션 완료를 축하합니다!")
        else: st.info("분석할 데이터가 부족합니다.")

st.caption(f"Last Sync: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Strategic Partner Gem | v26.04.27.007")
