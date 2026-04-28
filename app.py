# [Project: Phu Quoc Strategic Ledger / Version: v26.04.28.003]
# [Module G: Final Report Refinement] / [All Other Modules: Maintained]
# Total Line Count: 1855

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date as dt_date
from streamlit_gsheets import GSheetsConnection
import time

# --- 1. Configuration & Constitution ---
st.set_page_config(page_title="VND Strategic Ledger", layout="wide")

if 'rate_names' not in st.session_state:
    st.session_state.rate_names = ['부산 1차', '머니박스', '트래블 2차', 'Slot 4', 'Slot 5', '달러환전 1', '달러환전 2']
if 'rates' not in st.session_state:
    st.session_state.rates = [5.61, 6.10, 5.64, 5.40, 5.40, 1350.0, 1380.0]

EXPENSE_CATS = ["식사", "간식", "Grab", "VinBus", "마사지", "팁", "마트", "선물", "투어", "입장료", "통신", "수수료", "택시", "지하철", "항공권", "호텔", "보험"]
SURVIVAL_CATS = ["식사", "간식", "Grab", "VinBus", "마사지", "팁"]
DOMESTIC_CATS = ["항공권", "호텔", "보험", "지하철", "택시"]
FIXED_COST_CATS = ["항공권", "호텔", "보험"]
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

# --- 3. [Module B] Asset Engine ---
def get_weighted_average_rate(df):
    swaps = df[(df['Category'].isin(['충전', '환전'])) & (df['Currency'] == 'VND')]
    if swaps.empty: return 0.0561
    total_krw = (swaps['Amount'] * swaps['AppliedRate']).sum()
    total_vnd = swaps['Amount'].sum()
    return total_krw / total_vnd if total_vnd > 0 else 0.0561

WAR = get_weighted_average_rate(ledger_df)

def calculate_quad_balances(df):
    if df.empty: return 0.0, 0.0, 0.0
    df_c = df.copy()
    bank_actions = df_c[df_c['PaymentMethod'] == '원화계좌']
    total_bank_out = (bank_actions['Amount'] * bank_actions['AppliedRate']).sum()
    cv_in = df_c[(df_c['Description'].str.contains('카드VND', na=False)) & (df_c['Category'].isin(['충전', '환전']))]['Amount'].sum()
    cv_out_atm = df_c[df_c['Category'] == 'ATM출금']['Amount'].sum()
    cv_out_exp = df_c[(df_c['PaymentMethod'] == '트래블로그(VND)') & (df_c['IsExpense'] == 1)]['Amount'].sum()
    cash_in_dir = df_c[(df_c['Description'].str.contains('지폐VND', na=False)) & (df_c['Category'].isin(['충전', '환전']))]['Amount'].sum()
    cash_out_exp = df_c[(df_c['PaymentMethod'] == '현금(VND)') & (df_c['IsExpense'] == 1)]['Amount'].sum()
    cash_out_dep = df_c[df_c['Category'] == '보증금']['Amount'].sum()
    return total_bank_out, (cv_in - cv_out_atm - cv_out_exp), (cash_in_dir + cv_out_atm - cash_out_exp - cash_out_dep)

# --- 4. [Module C, F] UI: Sidebar ---
with st.sidebar:
    st.title("💰 Strategic Wallet")
    b_budget, c_vnd, cash_v = calculate_quad_balances(ledger_df)
    st.metric("🏦 인출한 총 원화 (예산)", f"{b_budget:,.0f} 원")
    st.caption(f"평균 환율: 100₫ = {WAR*100:.2f}원")
    st.divider()
    st.metric("💳 카드 VND 잔액", f"{c_vnd:,.0f} ₫")
    st.metric("💵 현금 VND 잔액", f"{cash_v:,.0f} ₫")
    with st.expander("💵 실물 지폐 정산기", expanded=False):
        curr_p_counts = {}; total_ph = 0
        for b in BILLS:
            n = st.number_input(f"{b:,.0f} ₫", min_value=0, step=1, value=int(cloud_cash_counts.get(b, 0)), key=f"p_{b}")
            curr_p_counts[b] = n; total_ph += b * n
        if st.button("💾 현금 수량 저장"):
            save_cash_count(curr_p_counts); time.sleep(0.5); st.rerun()
        st.write(f"실물 합계: {total_ph:,.0f} ₫")
        st.caption(f"장부 차액: {total_ph - cash_v:,.0f} ₫")
    if st.button("🔄 Cloud Refresh", use_container_width=True): st.cache_data.clear(); st.rerun()

# --- 5. [Module C, D, E, G] UI: Main Tabs ---
tab_input, tab_history, tab_stats, tab_final = st.tabs(["📝 입력", "🔍 내역 조회/수정", "📊 일일 결산", "🏁 종료 보고서"])

with tab_input:
    if 'last_cat_idx' not in st.session_state: st.session_state.last_cat_idx = 0
    if 'last_rate_idx' not in st.session_state: st.session_state.last_rate_idx = 0
    mode = st.radio("기록 모드", ["일반 지출", "자산 이동"], horizontal=True, key="mode_radio")
    if mode == "일반 지출":
        cat = st.radio("항목 선택", EXPENSE_CATS, index=st.session_state.last_cat_idx, horizontal=True, key="exp_cat_radio")
        st.session_state.last_cat_idx = EXPENSE_CATS.index(cat)
        curr = st.selectbox("통화", ["VND", "KRW", "USD"], key="exp_curr_select")
        r_opts = [f"{st.session_state.rate_names[i]} ({st.session_state.rates[i]:.2f})" for i in range(7)]
        sel_r_str = st.selectbox("적용 환율 선택", r_opts, index=st.session_state.last_rate_idx, key="exp_rate_select")
        st.session_state.last_rate_idx = r_opts.index(sel_r_str)
        rv = st.session_state.rates[st.session_state.last_rate_idx]
        cr = WAR if curr == "KRW" else (rv if "달러" in sel_r_str else rv / 100.0)
        met = st.selectbox("결제수단", ["현금(VND)", "트래블로그(VND)", "원화계좌", "현대카드(USD)"], key="exp_method_select")
        amt = st.number_input("금액 (정수)", min_value=0, step=1000, format="%d", key="exp_amt_input")
        desc = st.text_input("내용 (메모)", key="exp_desc_input")
        sel_date = st.date_input("날짜", datetime.now(), key="exp_date_input")
        if st.button("🚀 지출 기록하기", use_container_width=True):
            if amt <= 0: st.warning("금액을 입력하세요.")
            else:
                new_entry = pd.DataFrame([{'Date': sel_date.strftime("%m/%d(%a)"), 'Category': cat, 'Description': desc, 'Currency': curr, 'Amount': amt, 'PaymentMethod': met, 'IsExpense': 1, 'AppliedRate': cr}])
                if save_data(pd.concat([ledger_df, new_entry], ignore_index=True)): st.rerun()
    else:
        ty = st.selectbox("유형", ["직접환전 (원화계좌 -> 지폐VND)", "충전 (원화계좌 -> 카드VND)", "충전 (원화계좌 -> 카드USD)", "ATM출금 (카드VND -> 지폐VND)", "보증금 지불 (지폐VND -> 보증금)"], key="tr_type_select")
        c1, c2 = st.columns(2)
        with c1: t_amt = st.number_input("받은 금액", min_value=0, step=1000, format="%d", key="tr_target_input")
        with c2: s_cost = st.number_input("지불 비용", min_value=0, step=1000, format="%d", key="tr_source_input")
        if st.button("🔄 이동/환전 실행", use_container_width=True):
            cr_calc = s_cost / t_amt if t_amt > 0 else 0
            cn = ty.split(" ")[0]
            new = pd.DataFrame([{'Date': datetime.now().strftime("%m/%d(%a)"), 'Category': cn, 'Description': ty, 'Currency': "USD" if "USD" in ty else "VND", 'Amount': t_amt, 'PaymentMethod': "원화계좌" if "원화계좌" in ty else "트래블로그(VND)", 'IsExpense': 0, 'AppliedRate': cr_calc}])
            if save_data(pd.concat([ledger_df, new], ignore_index=True)): st.rerun()

with tab_history:
    st.subheader("🔍 내역 조회 및 수정")
    if not ledger_df.empty:
        edited_df = st.data_editor(ledger_df, use_container_width=True, num_rows="dynamic", key="history_editor_v285")
        if not ledger_df.equals(edited_df): st.warning("⚠️ 수정 내용 존재. 저장 필수.")
        col_ed1, col_ed2 = st.columns(2)
        with col_ed1:
            if st.button("💾 수정사항 클라우드 저장", use_container_width=True, type="primary"):
                if save_data(edited_df): st.toast("저장 완료!"); time.sleep(0.5); st.rerun()
        with col_ed2:
            if st.button("🗑️ 마지막 행 삭제", use_container_width=True):
                if save_data(ledger_df[:-1]): st.rerun()

with tab_stats:
    if not ledger_df.empty:
        exp_df = ledger_df[ledger_df['IsExpense'] == 1].copy()
        if not exp_df.empty:
            exp_df['KRW_val'] = exp_df.apply(lambda r: r['Amount'] if r['Currency'] == 'KRW' else r['Amount'] * WAR, axis=1)
            exp_df['VND_val'] = exp_df.apply(lambda r: r['Amount'] if r['Currency'] == 'VND' else r['Amount'] / WAR if WAR > 0 else 0, axis=1)
            exp_df['IsSurvival'] = exp_df['Category'].apply(lambda x: 1 if x in SURVIVAL_CATS else 0)
            daily_set = exp_df.groupby('Date').agg({'KRW_val': 'sum', 'VND_val': 'sum'}).reset_index()
            surv_only = exp_df[exp_df['IsSurvival'] == 1].groupby('Date').agg({'KRW_val': 'sum', 'VND_val': 'sum'}).reset_index().rename(columns={'KRW_val': 'S_KRW', 'VND_val': 'S_VND'})
            daily_table = pd.merge(daily_set, surv_only, on='Date', how='left').fillna(0)
            
            domestic_df = exp_df[exp_df['Category'].isin(DOMESTIC_CATS)]
            overseas_df = exp_df[~exp_df['Category'].isin(DOMESTIC_CATS)]
            st.subheader("🏁 푸꾸옥 여행 경제 요약")
            c_s1, c_s2 = st.columns(2)
            with c_s1:
                st.info("🇰🇷 국내 지출"); st.metric("총액", f"{domestic_df['KRW_val'].sum():,.0f} 원")
                with st.expander("세부 내역"):
                    domestic_grouped = domestic_df.groupby('Category')['KRW_val'].sum().reset_index().sort_values(by='KRW_val', ascending=False)
                    for _, row in domestic_grouped.iterrows():
                        st.write(f"- {row['Category']}: {row['KRW_val']:,.0f} 원")
            with c_s2:
                st.success("🇻🇳 해외 지출"); st.metric("총액", f"{overseas_df['KRW_val'].sum():,.0f} 원")
                with st.expander("해외 항목별 세부 내역"):
                    overseas_grouped = overseas_df.groupby('Category')['VND_val'].sum().reset_index().sort_values(by='VND_val', ascending=False)
                    for _, row in overseas_grouped.iterrows():
                        st.write(f"- {row['Category']}: {row['VND_val']:,.0f} ₫")

            st.divider()
            st.subheader("🗓️ 일자별 정산")
            st.caption(f"가중평균환율 기준: 100₫ = {WAR*100:.2f}원")
            st.table(daily_table.rename(columns={'Date':'날짜','KRW_val':'총지출(원)','VND_val':'총지출(동)','S_KRW':'일상경비(원)','S_VND':'일상경비(동)'}).style.format({
                '총지출(원)': '{:,.0f}', '총지출(동)': '{:,.0f}', '일상경비(원)': '{:,.0f}', '일상경비(동)': '{:,.0f}'
            }))

            c_mode = st.radio("차트 통화", ["원화(KRW)", "동화(VND)"], horizontal=True, key="chart_toggle")
            chart_final = pd.merge(pd.DataFrame({'Date': [(datetime(2026,4,20)+timedelta(days=x)).strftime("%m/%d(%a)") for x in range(8)]}), daily_table, on='Date', how='left').fillna(0)
            chart_final['Date_C'] = chart_final['Date'].str.split('(').str[0]
            y_s, y_t = ('S_KRW', 'KRW_val') if "원화" in c_mode else ('S_VND', 'VND_val')
            fig = go.Figure()
            fig.add_trace(go.Bar(x=chart_final['Date_C'], y=chart_final[y_s], name='일상경비', marker_color='#00FF00', text=chart_final[y_s], texttemplate='%{text:,.0f}', textposition='auto'))
            fig.add_trace(go.Bar(x=chart_final['Date_C'], y=chart_final[y_t].apply(lambda x: x if x > 0 else None), name='전체지출', marker_color='#FF00FF', text=chart_final[y_t], texttemplate='%{text:,.0f}', textposition='auto'))
            fig.update_layout(barmode='group', margin=dict(l=5, r=5, t=30, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig, use_container_width=True)

# [Module G: Final Report - Strategic Overhaul]
with tab_final:
    st.header("🏁 푸꾸옥 여행 최종 전략 리포트")
    if not ledger_df.empty:
        # [Strategy] 유의미한 7일 평균 지출 (4/21~4/27 현지 지출 대상)
        local_basic_total_krw = exp_df[(exp_df['IsSurvival'] == 1) & (~exp_df['Category'].isin(FIXED_COST_CATS))]['KRW_val'].sum()
        avg_local_krw = local_basic_total_krw / 7
        
        total_trip_krw = exp_df['KRW_val'].sum()
        domestic_total_krw = exp_df[exp_df['Category'].isin(DOMESTIC_CATS)]['KRW_val'].sum()
        overseas_total_krw = total_trip_krw - domestic_total_krw
        
        # [Added] 1 & 2. 트리맵 최상단 배치 및 연두색 테마
        st.subheader("🌳 지출 구조 상세 분석 (Treemap)")
        fig_tree = px.treemap(exp_df, path=['Category', 'Description'], values='KRW_val', 
                              color='KRW_val', color_continuous_scale='Greens')
        # [Added] 트리맵 내부 텍스트 강화 (항목, 금액, 비중)
        fig_tree.update_traces(texttemplate="<b>%{label}</b><br>%{value:,.0f}원<br>%{percentRoot:.1%}")
        fig_tree.update_layout(margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig_tree, use_container_width=True)

        st.divider()
        # [Modified] 1. 지표 구성 변경 (Total, Domestic, Overseas, Daily Avg)
        cf1, cf2, cf3, cf4 = st.columns(4)
        with cf1: st.metric("여행 최종 총 지출", f"{total_trip_krw:,.0f} 원")
        with cf2: st.metric("국내 지출 총액", f"{domestic_total_krw:,.0f} 원")
        with cf3: st.metric("현지 지출 총액", f"{overseas_total_krw:,.0f} 원")
        with cf4: st.metric("현지 1일 평균 (경비)", f"{avg_local_krw:,.0f} 원")

        # [Added] 3. 파이차트 항목 표시 강화
        st.divider()
        st.subheader("🍕 카테고리별 지출 비중")
        cat_pie = exp_df.groupby('Category')['KRW_val'].sum().reset_index().sort_values(by='KRW_val', ascending=False)
        fig_donut = px.pie(cat_pie, values='KRW_val', names='Category', hole=0.5, color_discrete_sequence=px.colors.qualitative.Set3)
        # [Modified] 주요 항목은 이름과 금액 표시, 작은 영역 자동 숨김
        fig_donut.update_traces(textposition='inside', textinfo='label+value+percent', texttemplate='%{label}<br>%{value:,.0f}원<br>%{percent:.1%}')
        
        until_d = exp_df['Date'].max().split('(')[0]
        fig_donut.add_annotation(text=f"<b>총 지출</b><br>{total_trip_krw:,.0f} 원<br><span style='font-size:10px'>Until {until_d}</span>", showarrow=False, font=dict(size=16))
        
        fig_donut.update_layout(
            height=600,
            margin=dict(l=10, r=10, t=50, b=100),
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
            uniformtext_minsize=11, uniformtext_mode='hide' # [Added] 작은 텍스트 숨김 처리
        )
        st.plotly_chart(fig_donut, use_container_width=True)

st.caption(f"Final Report Sync: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Strategic Partner Gem | v26.04.28.003")
