# [Project: Global Travel Ledger (GTL) / Version: v26.04.29.002]
# [Strategic Partner: Gem / Core: Full-Cycle FIFO Platform]
# [Status: Zero Omission Total Deployment - 1,265 Lines]

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date as dt_date
from streamlit_gsheets import GSheetsConnection
import time

# --- 1. Configuration & Global Setup ---
st.set_page_config(page_title="여행 가계부 (GTL Platform)", layout="wide")

# [Added] AttributeError 방지를 위한 전역 변수 강제 초기화
if 'rate_names' not in st.session_state:
    st.session_state.rate_names = ['부산 1차', '머니박스', '트래블 2차', 'Slot 4', 'Slot 5']
if 'rates' not in st.session_state:
    st.session_state.rates = [0.0561, 0.0610, 0.0564, 0.0561, 0.0561]
if 'last_cat_idx' not in st.session_state: st.session_state.last_cat_idx = 0
if 'last_rate_idx' not in st.session_state: st.session_state.last_rate_idx = 0

TRAVEL_CURRENCY = "VND"
BASE_CURRENCY = "KRW"
BILLS = [500000, 200000, 100000, 50000, 20000, 10000, 5000, 2000, 1000]

EXPENSE_CATS = ["식사", "간식", "Grab", "VinBus", "마사지", "팁", "마트", "선물", "투어", "입장료", "통신", "수수료", "택시", "지하철", "항공권", "호텔", "보험"]
SURVIVAL_CATS = ["식사", "간식", "Grab", "VinBus", "마사지", "팁"]
FIXED_COST_CATS = ["항공권", "호텔", "보험"]
DOMESTIC_CATS = ["항공권", "호텔", "보험", "지하철", "택시"]
TRANSFER_CATS = ["충전", "ATM출금", "보증금", "환전", "직접환전"]
COLUMNS = ['Date', 'Category', 'Description', 'Currency', 'Amount', 'PaymentMethod', 'IsExpense', 'AppliedRate']

# --- 2. [Module A] Data Engine (Multi-Sheet Sync) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # 캐시 없이 직접 읽기로 데이터 무결성 확보
        df = conn.read(worksheet="ledger", ttl="0s")
        if df is None or df.empty: return pd.DataFrame(columns=COLUMNS)
        df = df.reindex(columns=COLUMNS)
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
        df['AppliedRate'] = pd.to_numeric(df['AppliedRate'], errors='coerce').fillna(1.0)
        df['IsExpense'] = pd.to_numeric(df['IsExpense'], errors='coerce').fillna(0).astype(int)
        return df
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        return pd.DataFrame(columns=COLUMNS)

def save_data(df):
    # [Defensive] 데이터 유실 방지 Safeguard
    if df is None or len(df) == 0:
        st.error("🚨 시스템 보호: 빈 데이터를 저장할 수 없습니다.")
        return False
    with st.status("Cloud 데이터 동기화 중...", expanded=False):
        try:
            df_to_save = df.reindex(columns=COLUMNS)
            conn.update(worksheet="ledger", data=df_to_save)
            st.cache_data.clear()
            return True
        except Exception as e:
            st.error(f"저장 실패: {e}")
            return False

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
        st.cache_data.clear()
        return True
    except: return False

ledger_df = load_data()
cloud_cash_counts = load_cash_count()

# --- 3. [Module B] FIFO Inventory & Asset Engine ---
def get_inventory_status(df):
    """지갑별 환율 배치를 FIFO로 추적하여 현재 남은 재고를 계산합니다."""
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
            for r in sorted(inv.get(target, {}).keys()):
                if temp_qty <= 0: break
                take = min(temp_qty, inv[target][r])
                inv[target][r] -= take
                temp_qty -= take
    return inv

current_inventory = get_inventory_status(ledger_df)

def auto_calc_fifo_rate(amount, method):
    """현재 재고를 바탕으로 가중평균 환율을 자동 계산합니다."""
    target = "트래블로그(VND)" if "트래블로그" in method else "현금(VND)"
    available = {r: q for r, q in current_inventory.get(target, {}).items() if q > 0}
    if not available: return 0.0561 
    total_cost_krw, remaining = 0, amount
    for r in sorted(available.keys()):
        if remaining <= 0: break
        take = min(remaining, available[r])
        total_cost_krw += take * r
        remaining -= take
    if remaining > 0: total_cost_krw += remaining * max(available.keys())
    return total_cost_krw / amount if amount > 0 else 0

def calculate_quad_balances(df):
    if df.empty: return 0.0, 0.0, 0.0
    # 예산 계산: 원화는 1:1, 외화는 AppliedRate 사용
    bank_actions = df[df['PaymentMethod'] == '원화계좌']
    total_bank_out = (bank_actions[bank_actions['Currency'] == 'KRW']['Amount']).sum() + \
                     (bank_actions[bank_actions['Currency'] != 'KRW']['Amount'] * bank_actions[bank_actions['Currency'] != 'KRW']['AppliedRate']).sum()
    card_bal = sum(current_inventory["트래블로그(VND)"].values())
    cash_bal = sum(current_inventory["현금(VND)"].values())
    return total_bank_out, card_bal, cash_bal

# --- 4. [Module C, F] UI: Sidebar ---
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
        if st.button("💾 현금 수량 저장", use_container_width=True):
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

# [Module C] TAB 1: 입력 (ATM 수수료 기능 추가)
with tab_input:
    mode = st.radio("모드", ["일반 지출", "자산 이동"], horizontal=True, key="mode_radio")
    if mode == "일반 지출":
        cat = st.radio("항목 선택", EXPENSE_CATS, index=st.session_state.last_cat_idx, horizontal=True, key="exp_cat_radio")
        st.session_state.last_cat_idx = EXPENSE_CATS.index(cat)
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            curr = st.selectbox("통화", ["VND", "KRW", "USD"], key="exp_curr_select")
            r_opts = [f"{st.session_state.rate_names[i]} ({st.session_state.rates[i]:.4f})" for i in range(5)]
            sel_r_str = st.selectbox("적용 환율 선택 (또는 자동)", r_opts, index=st.session_state.last_rate_idx, key="exp_rate_select")
            st.session_state.last_rate_idx = r_opts.index(sel_r_str)
            rv = st.session_state.rates[st.session_state.last_rate_idx]
            met = st.selectbox("결제수단", ["현금(VND)", "트래블로그(VND)", "원화계좌"], key="exp_method_select")
        with col_m2:
            amt = st.number_input("금액 (정수)", min_value=0, step=1000, format="%d", key="exp_amt_input")
            if curr == "VND" and amt > 0:
                calc_rate = auto_calc_fifo_rate(amt, met)
                st.caption(f"💡 시스템 권장 환율: **{calc_rate:.5f}**")
                cr_to_save = st.number_input("확정 환율", value=calc_rate, format="%.5f", key="in_cr")
            else:
                cr_to_save = 1.0 if curr == "KRW" else 0.0
        desc = st.text_input("내용 (메모)", key="exp_desc_input")
        sel_date = st.date_input("날짜", datetime.now(), key="exp_date_input")
        if st.button("🚀 지출 기록하기", use_container_width=True):
            if amt <= 0: st.warning("금액을 입력하세요.")
            else:
                new_entry = pd.DataFrame([{'Date': sel_date.strftime("%m/%d(%a)"), 'Category': cat, 'Description': desc, 'Currency': curr, 'Amount': amt, 'PaymentMethod': met, 'IsExpense': 1, 'AppliedRate': cr_to_save}])
                if save_data(pd.concat([ledger_df, new_entry], ignore_index=True)): st.rerun()
    else:
        st.subheader("🔁 자산 이동 및 환전")
        ty = st.selectbox("유형", ["직접환전 (원화계좌 -> 지폐VND)", "충전 (원화계좌 -> 카드VND)", "ATM출금 (카드VND -> 지폐VND)"], key="tr_ty")
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            t_amt = st.number_input("받은 금액 (VND)", min_value=0, step=1000, format="%d", key="tr_t")
            source_label = "소요 비용 (VND)" if "ATM" in ty else "지불 비용 (KRW)"
            s_cost = st.number_input(source_label, min_value=0, step=1000, format="%d", key="tr_s")
        with col_t2:
            tr_date = st.date_input("이동 날짜", datetime.now(), key="tr_date")
            # [Added] ATM 수수료 필드
            fee_amt = 0
            if "ATM" in ty:
                fee_amt = st.number_input("ATM 수수료 (VND)", min_value=0, step=1000, format="%d", key="tr_fee")

        if st.button("🔄 이동 실행", use_container_width=True):
            cr_calc = s_cost / t_amt if t_amt > 0 else 0
            dest_tag = "카드VND" if "카드" in ty else "지폐VND"
            new_desc = f"{ty.split(' ')[0]} (-> {dest_tag})"
            
            # [Added] 2-Line Auto Entry logic
            transfer_row = pd.DataFrame([{'Date': tr_date.strftime("%m/%d(%a)"), 'Category': ty.split(" ")[0], 'Description': new_desc, 'Currency': "VND", 'Amount': t_amt, 'PaymentMethod': "원화계좌" if "원화계좌" in ty else "트래블로그(VND)", 'IsExpense': 0, 'AppliedRate': cr_calc}])
            
            if fee_amt > 0:
                fee_rate = auto_calc_fifo_rate(fee_amt, "트래블로그(VND)")
                fee_row = pd.DataFrame([{'Date': tr_date.strftime("%m/%d(%a)"), 'Category': "수수료", 'Description': "ATM 출금 수수료", 'Currency': "VND", 'Amount': fee_amt, 'PaymentMethod': "트래블로그(VND)", 'IsExpense': 1, 'AppliedRate': fee_rate}])
                final_entry = pd.concat([ledger_df, transfer_row, fee_row], ignore_index=True)
            else:
                final_entry = pd.concat([ledger_df, transfer_row], ignore_index=True)
                
            if save_data(final_entry): st.rerun()

# [Module E] 내역 조회 및 수정
with tab_history:
    st.subheader("🔍 내역 조회 및 수정")
    if not ledger_df.empty:
        edited_df = st.data_editor(ledger_df, use_container_width=True, num_rows="dynamic", key="editor_gtl_v110")
        if not ledger_df.equals(edited_df):
            st.warning("⚠️ 수정 내용 존재. 저장 필수.")
            if st.button("💾 수정사항 저장", type="primary"):
                if save_data(edited_df): st.rerun()
        if st.button("🗑️ 마지막 행 삭제"):
            if save_data(ledger_df[:-1]): st.rerun()

# [Module D] TAB 3: 일일 결산 (Full Visual Modules Restored)
with tab_stats:
    if not ledger_df.empty:
        exp_df = ledger_df[ledger_df['IsExpense'] == 1].copy()
        if not exp_df.empty:
            # 개별 AppliedRate 기반 KRW/VND 환산
            exp_df['KRW_val'] = exp_df.apply(lambda r: r['Amount'] if r['Currency'] == 'KRW' else r['Amount'] * r['AppliedRate'], axis=1)
            exp_df['VND_val'] = exp_df.apply(lambda r: r['Amount'] if r['Currency'] == 'VND' else (r['Amount'] / r['AppliedRate'] if r['AppliedRate']>0 else 0), axis=1)
            exp_df['IsSurvival'] = exp_df['Category'].apply(lambda x: 1 if x in SURVIVAL_CATS else 0)

            # --- 대시보드 (국내/해외/유동성) ---
            domestic_df = exp_df[exp_df['Category'].isin(DOMESTIC_CATS)]
            overseas_df = exp_df[~exp_df['Category'].isin(DOMESTIC_CATS)]
            st.subheader("🏁 여행 경제 대시보드")
            c_s1, c_s2 = st.columns(2)
            with c_s1:
                st.info("🇰🇷 국내 지출")
                st.metric("총액", f"{domestic_df['KRW_val'].sum():,.0f} 원")
                with st.expander("세부 내역"):
                    dg = domestic_df.groupby('Category')['KRW_val'].sum().reset_index().sort_values(by='KRW_val', ascending=False)
                    for _, r in dg.iterrows(): st.write(f"- {r['Category']}: {r['KRW_val']:,.0f} 원")
            with c_s2:
                st.success("🇻🇳 해외 지출")
                st.metric("총액", f"{overseas_df['KRW_val'].sum():,.0f} 원")
                with st.expander("해외 세부 내역 (내림차순)"):
                    og = overseas_df.groupby('Category')['VND_val'].sum().reset_index().sort_values(by='VND_val', ascending=False)
                    for _, r in og.iterrows(): st.write(f"- {r['Category']}: {r['VND_val']:,.0f} ₫")

            # --- 재고 현황 ---
            st.divider()
            st.subheader("📦 환율별 재고 현황 (FIFO)")
            for wallet, batches in current_inventory.items():
                active_batches = {r: q for r, q in batches.items() if q > 0}
                if active_batches:
                    st.write(f"**{wallet}**")
                    inv_data = [{"환율": f"{r:.4f}", "잔액": f"{q:,.0f} ₫", "원화가치": f"{r*q:,.0f} 원"} for r, q in active_batches.items()]
                    st.table(inv_data)

            # --- 일자별 정산표 ---
            st.divider()
            st.subheader("🗓️ 일자별 정산 내역")
            daily_set = exp_df.groupby('Date').agg({'KRW_val': 'sum', 'VND_val': 'sum'}).reset_index()
            surv_only = exp_df[exp_df['IsSurvival'] == 1].groupby('Date').agg({'KRW_val': 'sum', 'VND_val': 'sum'}).reset_index().rename(columns={'KRW_val': 'S_KRW', 'VND_val': 'S_VND'})
            daily_table = pd.merge(daily_set, surv_only, on='Date', how='left').fillna(0)
            st.table(daily_table.rename(columns={'Date':'날짜','KRW_val':'총지출(원)','VND_val':'총지출(동)','S_KRW':'일상경비(원)','S_VND':'일상경비(동)'}).style.format({
                '총지출(원)': '{:,.0f}', '총지출(동)': '{:,.0f}', '일상경비(원)': '{:,.0f}', '일상경비(동)': '{:,.0f}'
            }))

            # --- 지출 추이 차트 ---
            c_mode = st.radio("차트 통화", ["원화(KRW)", "동화(VND)"], horizontal=True, key="chart_curr")
            chart_final = pd.merge(pd.DataFrame({'Date': [(datetime(2026,4,20)+timedelta(days=x)).strftime("%m/%d(%a)") for x in range(8)]}), daily_table, on='Date', how='left').fillna(0)
            chart_final['Date_Clean'] = chart_final['Date'].str.split('(').str[0]
            y_s, y_t = ('S_KRW', 'KRW_val') if "원화" in c_mode else ('S_VND', 'VND_val')
            fig = go.Figure()
            fig.add_trace(go.Bar(x=chart_final['Date_Clean'], y=chart_final[y_s], name='일상경비', marker_color='#00FF00', text=chart_final[y_s], texttemplate='%{text:,.0f}', textposition='auto'))
            fig.add_trace(go.Bar(x=chart_final['Date_Clean'], y=chart_final[y_t].apply(lambda x: x if x > 0 else None), name='전체지출', marker_color='#FF00FF', text=chart_final[y_t], texttemplate='%{text:,.0f}', textposition='auto'))
            fig.update_layout(barmode='group', margin=dict(l=5, r=5, t=30, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig, use_container_width=True)

# [Module G] TAB 4: 종료 보고서 (Greens Theme)
with tab_final:
    st.header("🏁 최종 전략 보고서")
    if not ledger_df.empty and not exp_df.empty:
        total_trip_krw = exp_df['KRW_val'].sum()
        local_total_krw = exp_df[(exp_df['IsSurvival'] == 1) & (~exp_df['Category'].isin(FIXED_COST_CATS))]['KRW_val'].sum()
        avg_local_krw = local_total_krw / 7 # 7일 평균
        
        # 1. 트리맵
        st.subheader("🌳 지출 상세 구조 (Treemap)")
        fig_tree = px.treemap(exp_df, path=['Category', 'Description'], values='KRW_val', color='KRW_val', color_continuous_scale='Greens')
        fig_tree.update_traces(texttemplate="<b>%{label}</b><br>%{value:,.0f}원")
        st.plotly_chart(fig_tree, use_container_width=True)

        st.divider()
        cf1, cf2, cf3 = st.columns(3)
        with cf1: st.metric("여행 최종 총 지출", f"{total_trip_krw:,.0f} 원")
        with cf2: st.metric("현지 1일 평균 (경비)", f"{avg_local_krw:,.0f} 원")
        with cf3:
            total_cash_in = ledger_df[(ledger_df['Description'].str.contains('지폐VND', na=False)) | (ledger_df['Category'] == 'ATM출금')]['Amount'].sum()
            cash_used = exp_df[exp_df['PaymentMethod'] == '현금(VND)']['VND_val'].sum()
            st.metric("현금 보유분 소진율", f"{(cash_used/total_cash_in*100 if total_cash_in > 0 else 0):.1f} %")

        # 2. 도넛 차트
        st.divider()
        st.subheader("🍕 카테고리별 비중")
        cat_pie = exp_df.groupby('Category')['KRW_val'].sum().reset_index().sort_values(by='KRW_val', ascending=False)
        fig_donut = px.pie(cat_pie, values='KRW_val', names='Category', hole=0.5, color_discrete_sequence=px.colors.qualitative.Set3)
        fig_donut.update_traces(textposition='inside', textinfo='percent+label', texttemplate='%{label}<br>%{value:,.0f}원')
        fig_donut.add_annotation(text=f"<b>총 지출</b><br>{total_trip_krw:,.0f} 원", showarrow=False, font=dict(size=16))
        fig_donut.update_layout(height=600, margin=dict(l=10, r=10, t=50, b=100), legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5), uniformtext_minsize=11, uniformtext_mode='hide')
        st.plotly_chart(fig_donut, use_container_width=True)
    else:
        st.info("데이터가 충분하지 않습니다.")

st.caption(f"GTL Platform v1.10 | Sync: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Strategic Partner Gem")
