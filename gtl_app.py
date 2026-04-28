# [Project: Global Travel Ledger (GTL) / Version: v26.04.28.002]
# [Strategic Partner: Gem / Core: Full-Stack FIFO Platform]

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date as dt_date
from streamlit_gsheets import GSheetsConnection
import time

# --- 1. Configuration & Global Setup ---
st.set_page_config(page_title="GTL: 여행가계부", layout="wide")

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
        df['AppliedRate'] = pd.to_numeric(df['AppliedRate'], errors='coerce').fillna(0.0)
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

# --- 3. [Module B] FIFO Inventory Engine ---
def get_inventory_status(df):
    inv = { "트래블로그(VND)": {}, "현금(VND)": {} }
    for _, row in df.iterrows():
        qty, rate = row['Amount'], row['AppliedRate']
        desc, cat, method = str(row['Description']), row['Category'], row['PaymentMethod']

        if cat in ['충전', '환전', '입금']:
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

def auto_calc_fifo_rate(amount, method):
    target = "트래블로그(VND)" if "트래블로그" in method else "현금(VND)"
    available = {r: q for r, q in current_inventory.get(target, {}).items() if q > 0}
    if not available: return 0.0566
    total_cost_krw, remaining = 0, amount
    for r in sorted(available.keys()):
        if remaining <= 0: break
        take = min(remaining, available[r])
        total_cost_krw += take * r
        remaining -= take
    if remaining > 0: total_cost_krw += remaining * max(available.keys())
    return total_cost_krw / amount if amount > 0 else 0

# --- 4. [Module C] UI: Sidebar & Cash Counter ---
with st.sidebar:
    st.title("💰 Wallet Status")
    t_bal = sum(current_inventory["트래블로그(VND)"].values())
    c_bal = sum(current_inventory["현금(VND)"].values())
    
    total_bank_out = (ledger_df[ledger_df['PaymentMethod'] == '원화계좌']['Amount'] * ledger_df[ledger_df['PaymentMethod'] == '원화계좌']['AppliedRate']).sum()

    st.metric("🏦 인출한 총 원화 (예산)", f"{total_bank_out:,.0f} 원")
    st.divider()
    st.metric("💳 카드 VND 잔액", f"{t_bal:,.0f} ₫")
    st.metric("💵 현금 VND 잔액", f"{c_bal:,.0f} ₫")
    
    with st.expander("💵 실물 지폐 정산기", expanded=False):
        total_ph = sum([b * st.number_input(f"{b:,.0f} ₫", min_value=0, step=1, value=int(cloud_cash_counts.get(b,0)), key=f"p_{b}") for b in BILLS])
        if st.button("💾 수량 저장"): 
            save_cash_count({b: st.session_state[f"p_{b}"] for b in BILLS})
        st.write(f"실물 합계: {total_ph:,.0f} ₫")
        st.caption(f"장부 차액: {total_ph - c_bal:,.0f} ₫")
    
    if st.button("🔄 Cloud Refresh", use_container_width=True): st.cache_data.clear(); st.rerun()

# --- 5. [Module Main UI] ---
tab_in, tab_his, tab_rpt, tab_final = st.tabs(["📝 입력", "🔍 내역 조회", "📊 지출 분석", "🏁 종료 보고서"])

with tab_in:
    mode = st.radio("모드", ["일반 지출", "자산 이동"], horizontal=True)
    if mode == "일반 지출":
        cat = st.radio("항목 선택", EXPENSE_CATS, horizontal=True, key="in_cat")
        c1, c2 = st.columns(2)
        with c1:
            curr = st.selectbox("통화", [TRAVEL_CURRENCY, BASE_CURRENCY, "USD"], key="in_curr")
            met = st.selectbox("결제수단", ["현금(VND)", "트래블로그(VND)", "원화계좌"], key="in_met")
        with c2:
            amt = st.number_input("금액 (정수)", min_value=0, step=1000, format="%d", key="in_amt")
            calc_rate = auto_calc_fifo_rate(amt, met) if curr == TRAVEL_CURRENCY and amt > 0 else (1.0 if curr == BASE_CURRENCY else 0.0)
            if curr == TRAVEL_CURRENCY: st.caption(f"💡 권장 환율: **{calc_rate:.5f}**")
        desc = st.text_input("내용", key="in_desc")
        s_date = st.date_input("날짜", datetime.now(), key="in_date")
        if st.button("🚀 지출 기록하기", use_container_width=True):
            if amt <= 0: st.warning("금액을 입력하세요.")
            else:
                new = pd.DataFrame([{'Date': s_date.strftime("%m/%d(%a)"), 'Category': cat, 'Description': desc, 'Currency': curr, 'Amount': amt, 'PaymentMethod': met, 'IsExpense': 1, 'AppliedRate': calc_rate}])
                if save_data(pd.concat([ledger_df, new], ignore_index=True)): st.rerun()
    else:
        ty = st.selectbox("유형", ["충전 (원화계좌 -> 카드VND)", "직접환전 (원화계좌 -> 지폐VND)", "ATM출금 (카드VND -> 지폐VND)"])
        c1, c2 = st.columns(2)
        with c1: t_amt = st.number_input("받은 금액", min_value=0, step=1000, format="%d", key="tr_target")
        with c2: s_cost = st.number_input("지불 비용", min_value=0, step=1000, format="%d", key="tr_source")
        if st.button("🔄 기록 실행", use_container_width=True):
            rate = s_cost / t_amt if t_amt > 0 else 0
            dest = "카드VND" if "카드" in ty else "지폐VND"
            new_desc = f"{ty.split(' ')[0]} (-> {dest})"
            new = pd.DataFrame([{'Date': datetime.now().strftime("%m/%d(%a)"), 'Category': ty.split(" ")[0], 'Description': new_desc, 'Currency': TRAVEL_CURRENCY, 'Amount': t_amt, 'PaymentMethod': "원화계좌" if "원화계좌" in ty else "트래블로그(VND)", 'IsExpense': 0, 'AppliedRate': rate}])
            if save_data(pd.concat([ledger_df, new], ignore_index=True)): st.rerun()

with tab_his:
    st.subheader("🔍 내역 조회 및 수정")
    if not ledger_df.empty:
        edited_df = st.data_editor(ledger_df, use_container_width=True, num_rows="dynamic", key="editor_gtl_v102")
        if not ledger_df.equals(edited_df):
            st.warning("⚠️ 수정된 내용이 있습니다!")
            if st.button("💾 수정사항 저장", type="primary"):
                if save_data(edited_df): st.rerun()
        if st.button("🗑️ 마지막 행 삭제"):
            if save_data(ledger_df[:-1]): st.rerun()
    else: st.info("데이터가 없습니다.")

with tab_rpt:
    if not ledger_df.empty:
        exp_df = ledger_df[ledger_df['IsExpense'] == 1].copy()
        if not exp_df.empty:
            exp_df['KRW_val'] = exp_df.apply(lambda r: r['Amount'] if r['Currency'] == 'KRW' else r['Amount'] * r['AppliedRate'], axis=1)
            exp_df['VND_val'] = exp_df.apply(lambda r: r['Amount'] if r['Currency'] == 'VND' else r['Amount'] / r['AppliedRate'] if r['AppliedRate']>0 else 0, axis=1)
            exp_df['IsSurvival'] = exp_df['Category'].apply(lambda x: 1 if x in SURVIVAL_CATS else 0)

            st.subheader("📦 현재 환율별 재고 현황 (FIFO)")
            for wallet, batches in current_inventory.items():
                active_batches = {r: q for r, q in batches.items() if q > 0}
                if active_batches:
                    st.write(f"**{wallet}**")
                    inv_data = [{"환율": f"{r:.4f}", "잔액": f"{q:,.0f} ₫", "원화가치": f"{r*q:,.0f} 원"} for r, q in active_batches.items()]
                    st.table(inv_data)

            st.divider()
            st.subheader("🗓️ 일자별 정산")
            daily_set = exp_df.groupby('Date').agg({'KRW_val': 'sum', 'VND_val': 'sum'}).reset_index()
            surv_only = exp_df[exp_df['IsSurvival'] == 1].groupby('Date').agg({'KRW_val': 'sum', 'VND_val': 'sum'}).reset_index().rename(columns={'KRW_val': 'S_KRW', 'VND_val': 'S_VND'})
            daily_table = pd.merge(daily_set, surv_only, on='Date', how='left').fillna(0)
            
            # [Core Fix] 날짜 제외, 숫자 컬럼만 지정하여 포맷팅
            st.table(daily_table.rename(columns={'Date':'날짜','KRW_val':'총지출(원)','VND_val':'총지출(동)','S_KRW':'일상경비(원)','S_VND':'일상경비(동)'}).style.format({
                '총지출(원)': '{:,.0f}', '총지출(동)': '{:,.0f}', '일상경비(원)': '{:,.0f}', '일상경비(동)': '{:,.0f}'
            }))

            st.divider()
            st.subheader("📈 지출 추이 분석")
            c_mode = st.radio("통화", ["원화(KRW)", "동화(VND)"], horizontal=True)
            y_s, y_t = ('S_KRW', 'KRW_val') if "원화" in c_mode else ('S_VND', 'VND_val')
            fig = go.Figure()
            fig.add_trace(go.Bar(x=daily_table['Date'], y=daily_table[y_s], name='일상경비', marker_color='#00FF00', text=daily_table[y_s], texttemplate='%{text:,.0f}', textposition='auto'))
            fig.add_trace(go.Bar(x=daily_table['Date'], y=daily_table[y_t].apply(lambda x: x if x > 0 else None), name='전체지출', marker_color='#FF00FF', text=daily_table[y_t], texttemplate='%{text:,.0f}', textposition='auto'))
            fig.update_layout(barmode='group', margin=dict(l=0, r=0, t=30, b=0), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig, use_container_width=True)

with tab_final:
    if not ledger_df.empty and not exp_df.empty:
        st.header("🏁 최종 전략 리포트")
        st.subheader("🌳 지출 구조 상세 (Treemap)")
        fig_tree = px.treemap(exp_df, path=['Category', 'Description'], values='KRW_val', color='KRW_val', color_continuous_scale='Greens')
        fig_tree.update_traces(texttemplate="<b>%{label}</b><br>%{value:,.0f}원")
        st.plotly_chart(fig_tree, use_container_width=True)

        st.divider()
        st.subheader("🍕 카테고리별 비중")
        cat_pie = exp_df.groupby('Category')['KRW_val'].sum().reset_index()
        fig_donut = px.pie(cat_pie, values='KRW_val', names='Category', hole=0.5, color_discrete_sequence=px.colors.qualitative.Set3)
        fig_donut.update_traces(textinfo='label+percent', texttemplate='%{label}<br>%{percent:.1%}')
        fig_donut.add_annotation(text=f"<b>총 지출</b><br>{exp_df['KRW_val'].sum():,.0f} 원", showarrow=False, font=dict(size=16))
        fig_donut.update_layout(height=500, margin=dict(l=10, r=10, t=50, b=50), legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5))
        st.plotly_chart(fig_donut, use_container_width=True)
    else: st.info("보고서를 생성할 데이터가 부족합니다.")

st.caption(f"GTL Platform v1.02 | Sync: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Strategic Partner Gem")
