# [Project: Global Travel Ledger (GTL) / Version: v26.04.28.004]
# [Strategic Partner: Gem / Core: Fixed Budget & Multi-Trip Readiness]

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date as dt_date
from streamlit_gsheets import GSheetsConnection
import time

# --- 1. Configuration & Global Setup ---
st.set_page_config(page_title="여행 가계부 (GTL Platform)", layout="wide")

# [Added] AttributeError 방지를 위한 최상단 전역 초기화
if 'rate_names' not in st.session_state:
    st.session_state.rate_names = ['부산 1차', '머니박스', '트래블 2차', 'Slot 4', 'Slot 5']
if 'rates' not in st.session_state:
    st.session_state.rates = [0.0561, 0.0610, 0.0564, 0.0561, 0.0561]

TRAVEL_CURRENCY = "VND"
BASE_CURRENCY = "KRW"
BILLS = [500000, 200000, 100000, 50000, 20000, 10000, 5000, 2000, 1000]

EXPENSE_CATS = ["식사", "간식", "Grab", "VinBus", "마사지", "팁", "마트", "선물", "투어", "입장료", "통신", "수수료", "택시", "지하철", "항공권", "호텔", "보험"]
SURVIVAL_CATS = ["식사", "간식", "Grab", "VinBus", "마사지", "팁"]
FIXED_COST_CATS = ["항공권", "호텔", "보험"]
DOMESTIC_CATS = ["항공권", "호텔", "보험", "지하철", "택시"]
COLUMNS = ['Date', 'Category', 'Description', 'Currency', 'Amount', 'PaymentMethod', 'IsExpense', 'AppliedRate']

# --- 2. [Module A] Data Engine ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        df = conn.read(worksheet="ledger", ttl="0s")
        if df is None or df.empty: return pd.DataFrame(columns=COLUMNS)
        df = df.reindex(columns=COLUMNS)
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
        df['AppliedRate'] = pd.to_numeric(df['AppliedRate'], errors='coerce').fillna(1.0)
        df['IsExpense'] = pd.to_numeric(df['IsExpense'], errors='coerce').fillna(0).astype(int)
        return df
    except: return pd.DataFrame(columns=COLUMNS)

def save_data(df):
    if df is None or len(df) == 0: return False
    with st.status("Cloud 동기화 중...", expanded=False):
        try:
            conn.update(worksheet="ledger", data=df.reindex(columns=COLUMNS))
            st.cache_data.clear()
            return True
        except: return False

@st.cache_data(ttl=0)
def load_cash_count():
    try:
        df = conn.read(worksheet="cash_count", ttl="0s")
        if df is None or df.empty: return {b: 0 for b in BILLS}
        return dict(zip(df['Bill'].astype(int), df['Count'].astype(int)))
    except: return {b: 0 for b in BILLS}

def save_cash_count(counts_dict):
    try:
        df = pd.DataFrame(list(counts_dict.items()), columns=['Bill', 'Count'])
        conn.update(worksheet="cash_count", data=df)
        st.cache_data.clear(); return True
    except: return False

ledger_df = load_data()
cloud_cash_counts = load_cash_count()

# --- 3. [Module B] Quad-Wallet & FIFO Engine ---
def get_inventory_status(df):
    inv = { "트래블로그(VND)": {}, "현금(VND)": {} }
    for _, row in df.iterrows():
        qty, rate = row['Amount'], row['AppliedRate']
        desc, cat, method = str(row['Description']), row['Category'], row['PaymentMethod']
        if cat in ['충전', '환전', '입금', '직접환전']:
            target = "트래블로그(VND)" if "카드VND" in desc else "현금(VND)"
            inv[target][rate] = inv[target].get(rate, 0) + qty
        elif cat == 'ATM출금':
            temp_qty = qty
            for r in sorted(inv["트래블로그(VND)"].keys()):
                if temp_qty <= 0: break
                take = min(temp_qty, inv["트래블로그(VND)"][r])
                inv["트래블로그(VND)"][r] -= take
                inv["현금(VND)"][r] = inv["현금(VND)"].get(r, 0) + take
                temp_qty -= take
        elif row['IsExpense'] == 1 and row['Currency'] == TRAVEL_CURRENCY:
            target = "트래블로그(VND)" if "트래블로그" in method else "현금(VND)"
            temp_qty = qty
            for r in sorted(inv[target].keys()):
                if temp_qty <= 0: break
                take = min(temp_qty, inv[target][r])
                inv[target][r] -= take
                temp_qty -= take
    return inv

current_inventory = get_inventory_status(ledger_df)

def calculate_quad_balances(df):
    if df.empty: return 0.0, 0.0, 0.0
    df_c = df.copy()
    
    # [Modified] 예산 계산 로직: 원화는 1:1, 외화는 AppliedRate 곱함
    bank_actions = df_c[df_c['PaymentMethod'] == '원화계좌']
    total_bank_out = 0
    for _, row in bank_actions.iterrows():
        if row['Currency'] == 'KRW':
            total_bank_out += row['Amount']
        else:
            total_bank_out += row['Amount'] * row['AppliedRate']
    
    cv_in = df_c[(df_c['Description'].str.contains('카드VND', na=False)) & (df_c['Category'].isin(['충전', '환전']))]['Amount'].sum()
    cv_out_atm = df_c[df_c['Category'] == 'ATM출금']['Amount'].sum()
    cv_out_exp = df_c[(df_c['PaymentMethod'] == '트래블로그(VND)') & (df_c['IsExpense'] == 1)]['Amount'].sum()
    
    cash_in_dir = df_c[(df_c['Description'].str.contains('지폐VND', na=False)) & (df_c['Category'].isin(['충전', '환전']))]['Amount'].sum()
    cash_out_exp = df_c[(df_c['PaymentMethod'] == '현금(VND)') & (df_c['IsExpense'] == 1)]['Amount'].sum()
    cash_out_dep = df_c[df_c['Category'] == '보증금']['Amount'].sum()
    
    return total_bank_out, (cv_in - cv_out_atm - cv_out_exp), (cash_in_dir + cv_out_atm - cash_out_exp - cash_out_dep)

# --- 4. [Module C, F] UI: Sidebar (Renamed Platform Title) ---
with st.sidebar:
    st.title("🌏 여행 가계부")
    b_budget, c_vnd, cash_v = calculate_quad_balances(ledger_df)
    st.metric("🏦 인출한 총 원화 (예산)", f"{b_budget:,.0f} 원")
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

    with st.expander("💱 환율 매니저 (Presets)", expanded=False):
        for i in range(5):
            cn, cv = st.columns([2, 1.5])
            with cn: st.session_state.rate_names[i] = st.text_input(f"이름 {i+1}", value=st.session_state.rate_names[i], key=f"rn_{i}")
            with cv: st.session_state.rates[i] = st.number_input(f"환율 {i+1}", value=st.session_state.rates[i], format="%.4f", key=f"rv_{i}")

    if st.button("🔄 Cloud Refresh", use_container_width=True): st.cache_data.clear(); st.rerun()

# --- 5. [Module C, D, E, G] UI: Main Tabs ---
tab_input, tab_history, tab_stats, tab_final = st.tabs(["📝 입력", "🔍 내역 조회", "📊 지출 분석", "🏁 종료 보고서"])

with tab_input:
    if 'last_cat_idx' not in st.session_state: st.session_state.last_cat_idx = 0
    if 'last_rate_idx' not in st.session_state: st.session_state.last_rate_idx = 0
    mode = st.radio("모드", ["일반 지출", "자산 이동"], horizontal=True, key="mode_radio")
    
    if mode == "일반 지출":
        cat = st.radio("항목 선택", EXPENSE_CATS, index=st.session_state.last_cat_idx, horizontal=True, key="in_cat")
        st.session_state.last_cat_idx = EXPENSE_CATS.index(cat)
        
        col1, col2 = st.columns(2)
        with col1:
            curr = st.selectbox("통화", [TRAVEL_CURRENCY, BASE_CURRENCY, "USD"], key="in_curr")
            r_opts = [f"{st.session_state.rate_names[i]} ({st.session_state.rates[i]:.4f})" for i in range(5)]
            sel_r_str = st.selectbox("적용 환율 선택", r_opts, index=st.session_state.last_rate_idx, key="in_rate")
            st.session_state.last_rate_idx = r_opts.index(sel_r_str)
            rv = st.session_state.rates[st.session_state.last_rate_idx]
            manual_rate = st.number_input("또는 직접 입력", value=rv, format="%.4f", key="in_manual_rate")
            
        with col2:
            met = st.selectbox("결제수단", ["현금(VND)", "트래블로그(VND)", "원화계좌"], key="in_met")
            amt = st.number_input("금액 (정수)", min_value=0, step=1000, format="%d", key="in_amt")
            
        desc = st.text_input("내용 (메모)", key="in_desc")
        s_date = st.date_input("날짜", datetime.now(), key="in_date")

        if st.button("🚀 지출 기록하기", use_container_width=True):
            if amt <= 0: st.warning("금액을 입력하세요.")
            else:
                new = pd.DataFrame([{'Date': s_date.strftime("%m/%d(%a)"), 'Category': cat, 'Description': desc, 'Currency': curr, 'Amount': amt, 'PaymentMethod': met, 'IsExpense': 1, 'AppliedRate': manual_rate}])
                if save_data(pd.concat([ledger_df, new], ignore_index=True)): st.rerun()
    else:
        ty = st.selectbox("유형", ["충전 (원화계좌 -> 카드VND)", "직접환전 (원화계좌 -> 지폐VND)", "ATM출금 (카드VND -> 지폐VND)"])
        c1, c2 = st.columns(2)
        with c1: t_amt = st.number_input("받은 금액", min_value=0, step=1000, format="%d", key="tr_target")
        with c2: s_cost = st.number_input("지불 비용", min_value=0, step=1000, format="%d", key="tr_source")
        if st.button("🔄 기록 실행", use_container_width=True):
            rate = s_cost / t_amt if t_amt > 0 else 0
            cat_name = "직접환전" if "직접환전" in ty else ty.split(" ")[0]
            new_desc = f"{cat_name} (-> {'카드VND' if '카드' in ty else '지폐VND'})"
            new = pd.DataFrame([{'Date': datetime.now().strftime("%m/%d(%a)"), 'Category': cat_name, 'Description': new_desc, 'Currency': TRAVEL_CURRENCY, 'Amount': t_amt, 'PaymentMethod': "원화계좌" if "원화계좌" in ty else "트래블로그(VND)", 'IsExpense': 0, 'AppliedRate': rate}])
            if save_data(pd.concat([ledger_df, new], ignore_index=True)): st.rerun()

with tab_history:
    st.subheader("🔍 내역 조회 및 수정")
    if not ledger_df.empty:
        edited_df = st.data_editor(ledger_df, use_container_width=True, num_rows="dynamic", key="editor_gtl_v106")
        if not ledger_df.equals(edited_df):
            st.warning("⚠️ 수정된 내용 존재. 저장 필수.")
            if st.button("💾 수정사항 저장", type="primary"):
                if save_data(edited_df): st.rerun()
        if st.button("🗑️ 마지막 행 삭제"):
            if save_data(ledger_df[:-1]): st.rerun()

with tab_stats:
    if not ledger_df.empty:
        exp_df = ledger_df[ledger_df['IsExpense'] == 1].copy()
        if not exp_df.empty:
            exp_df['KRW_val'] = exp_df.apply(lambda r: r['Amount'] if r['Currency'] == 'KRW' else r['Amount'] * r['AppliedRate'], axis=1)
            exp_df['VND_val'] = exp_df.apply(lambda r: r['Amount'] if r['Currency'] == 'VND' else r['Amount'] / r['AppliedRate'] if r['AppliedRate']>0 else 0, axis=1)
            exp_df['IsSurvival'] = exp_df['Category'].apply(lambda x: 1 if x in SURVIVAL_CATS else 0)

            # --- 대시보드 ---
            domestic_df = exp_df[exp_df['Category'].isin(DOMESTIC_CATS)]
            overseas_df = exp_df[~exp_df['Category'].isin(DOMESTIC_CATS)]
            st.subheader("🏁 푸꾸옥 여행 경제 요약")
            c_s1, c_s2 = st.columns(2)
            with c_s1:
                st.info("🇰🇷 국내 지출")
                st.metric("총액", f"{domestic_df['KRW_val'].sum():,.0f} 원")
                with st.expander("세부 내역"):
                    dg = domestic_df.groupby('Category')['KRW_val'].sum().reset_index().sort_values(by='KRW_val', ascending=False)
                    for _, row in dg.iterrows(): st.write(f"- {row['Category']}: {row['KRW_val']:,.0f} 원")
            with c_s2:
                st.success("🇻🇳 해외 지출")
                st.metric("총액", f"{overseas_df['KRW_val'].sum():,.0f} 원")
                with st.expander("해외 세부 내역"):
                    og = overseas_df.groupby('Category')['VND_val'].sum().reset_index().sort_values(by='VND_val', ascending=False)
                    for _, row in og.iterrows(): st.write(f"- {row['Category']}: {row['VND_val']:,.0f} ₫")

            st.divider()
            st.subheader("🗓️ 일자별 정산")
            daily_set = exp_df.groupby('Date').agg({'KRW_val': 'sum', 'VND_val': 'sum'}).reset_index()
            surv_only = exp_df[exp_df['IsSurvival'] == 1].groupby('Date').agg({'KRW_val': 'sum', 'VND_val': 'sum'}).reset_index().rename(columns={'KRW_val': 'S_KRW', 'VND_val': 'S_VND'})
            daily_table = pd.merge(daily_set, surv_only, on='Date', how='left').fillna(0)
            st.table(daily_table.rename(columns={'Date':'날짜','KRW_val':'총지출(원)','VND_val':'총지출(동)','S_KRW':'일상경비(원)','S_VND':'일상경비(동)'}).style.format({
                '총지출(원)': '{:,.0f}', '총지출(동)': '{:,.0f}', '일상경비(원)': '{:,.0f}', '일상경비(동)': '{:,.0f}'
            }))

            c_mode = st.radio("차트 통화", ["원화(KRW)", "동화(VND)"], horizontal=True)
            chart_final = pd.merge(pd.DataFrame({'Date': [(datetime(2026,4,20)+timedelta(days=x)).strftime("%m/%d(%a)") for x in range(8)]}), daily_table, on='Date', how='left').fillna(0)
            chart_final['Date_C'] = chart_final['Date'].str.split('(').str[0]
            y_s, y_t = ('S_KRW', 'KRW_val') if "원화" in c_mode else ('S_VND', 'VND_val')
            fig = go.Figure()
            fig.add_trace(go.Bar(x=chart_final['Date_C'], y=chart_final[y_s], name='일상경비', marker_color='#00FF00', text=chart_final[y_s], texttemplate='%{text:,.0f}', textposition='auto'))
            fig.add_trace(go.Bar(x=chart_final['Date_C'], y=chart_final[y_t].apply(lambda x: x if x > 0 else None), name='전체지출', marker_color='#FF00FF', text=chart_final[y_t], texttemplate='%{text:,.0f}', textposition='auto'))
            fig.update_layout(barmode='group', margin=dict(l=5, r=5, t=30, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig, use_container_width=True)

with tab_final:
    if not ledger_df.empty:
        # [Strategy] 7일 평균 (4/21~27 현지 지출 대상)
        local_total_krw = exp_df[(exp_df['IsSurvival'] == 1) & (~exp_df['Category'].isin(FIXED_COST_CATS))]['KRW_val'].sum()
        avg_local_krw = local_total_krw / 7
        total_trip_krw = exp_df['KRW_val'].sum()
        dom_total_krw = exp_df[exp_df['Category'].isin(DOMESTIC_CATS)]['KRW_val'].sum()
        ovr_total_krw = total_trip_krw - dom_total_krw

        st.header("🏁 푸꾸옥 여행 최종 전략 리포트")
        st.subheader("🌳 지출 구조 상세 분석 (Treemap)")
        fig_tree = px.treemap(exp_df, path=['Category', 'Description'], values='KRW_val', color='KRW_val', color_continuous_scale='Greens')
        fig_tree.update_traces(texttemplate="<b>%{label}</b><br>%{value:,.0f}원<br>%{percentRoot:.1%}")
        st.plotly_chart(fig_tree, use_container_width=True)

        st.divider()
        cf1, cf2, cf3, cf4 = st.columns(4)
        with cf1: st.metric("여행 최종 총 지출", f"{total_trip_krw:,.0f} 원")
        with cf2: st.metric("국내 지출 총액", f"{dom_total_krw:,.0f} 원")
        with cf3: st.metric("현지 지출 총액", f"{ovr_total_krw:,.0f} 원")
        with cf4: st.metric("현지 1일 평균 (경비)", f"{avg_local_krw:,.0f} 원")

        st.divider()
        st.subheader("🍕 카테고리별 지출 비중")
        cat_pie = exp_df.groupby('Category')['KRW_val'].sum().reset_index().sort_values(by='KRW_val', ascending=False)
        fig_donut = px.pie(cat_pie, values='KRW_val', names='Category', hole=0.5, color_discrete_sequence=px.colors.qualitative.Set3)
        fig_donut.update_traces(textposition='inside', textinfo='label+value+percent', texttemplate='%{label}<br>%{value:,.0f}원<br>%{percent:.1%}')
        fig_donut.add_annotation(text=f"<b>총 지출</b><br>{total_trip_krw:,.0f} 원", showarrow=False, font=dict(size=16))
        fig_donut.update_layout(height=600, margin=dict(l=10, r=10, t=50, b=100), legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5), uniformtext_minsize=11, uniformtext_mode='hide')
        st.plotly_chart(fig_donut, use_container_width=True)

st.caption(f"Last Sync: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | v26.04.28.004 | Gem")
