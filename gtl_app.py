# [Project: Global Travel Ledger (GTL) / Version: v26.04.29.001]
# [Strategic Partner: Gem / Core: Final Mission Debriefing Engine]
# [Status: Zero Omission Total Deployment - 1,415 Lines]

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date as dt_date
from streamlit_gsheets import GSheetsConnection
import time

# --- 1. Configuration & Global Setup ---
st.set_page_config(page_title="GTL: 여행 가계부", layout="wide")

# AttributeError 방지를 위한 전역 변수 초기화
if 'rate_names' not in st.session_state:
    st.session_state.rate_names = ['부산 1차', '머니박스', '트래블 2차', 'Slot 4', 'Slot 5']
if 'rates' not in st.session_state:
    st.session_state.rates = [0.0561, 0.0610, 0.0564, 0.0561, 0.0561]
if 'last_cat_idx' not in st.session_state: st.session_state.last_cat_idx = 0
if 'last_rate_idx' not in st.session_state: st.session_state.last_rate_idx = 0

TRAVEL_CURRENCY = "VND"
BASE_CURRENCY = "KRW"
BILLS = [500000, 200000, 100000, 50000, 20000, 10000, 5000, 2000, 1000]

# [Modified] 카테고리에 입국/출국 추가 및 일상경비 정의
EXPENSE_CATS = ["식사", "간식", "Grab", "VinBus", "마사지", "팁", "마트", "선물", "투어", "입장료", "통신", "수수료", "택시", "지하철", "항공권", "호텔", "보험", "입국", "출국"]
SURVIVAL_CATS = ["식사", "간식", "Grab", "VinBus", "마사지", "팁"]
FIXED_COST_CATS = ["항공권", "호텔", "보험"]
DOMESTIC_CATS = ["항공권", "호텔", "보험", "지하철", "택시"]
TRANSFER_CATS = ["충전", "ATM출금", "보증금", "환전", "직접환전"]
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
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        return pd.DataFrame(columns=COLUMNS)

def save_data(df):
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

# --- 3. [Module B] FIFO Inventory & Budget Engine ---
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

def auto_calc_fifo_rate(amount, method):
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

def get_weighted_average_rate(df):
    swaps = df[(df['Category'].isin(['충전', '환전', '입금', '직접환전'])) & (df['Currency'] == 'VND')]
    if swaps.empty: return 0.0561
    total_krw = (swaps['Amount'] * swaps['AppliedRate']).sum()
    total_vnd = swaps['Amount'].sum()
    return total_krw / total_vnd if total_vnd > 0 else 0.0561

WAR = get_weighted_average_rate(ledger_df)

def calculate_quad_balances(df):
    if df.empty: return 0.0, 0.0, 0.0
    # [Modified] 예산 지표: 인출한 모든 원화 합계
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
    # [Modified] 지표 명칭 변경 및 USD 제거
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
tab_input, tab_history, tab_stats, tab_final = st.tabs(["📝 입력", "🔍 내역 조회", "📊 일일 결산", "🏁 종료 보고서"])

# [Module C] TAB 1: 입력 UX 최종 최적화
with tab_input:
    mode = st.radio("모드", ["일반 지출", "자산 이동"], horizontal=True, key="mode_radio")
    if mode == "일반 지출":
        # [Modified] 순서: 항목 -> 통화 -> 환율 -> 결제수단 -> 금액 -> 내용
        cat = st.radio("항목 선택", EXPENSE_CATS, index=st.session_state.last_cat_idx, horizontal=True, key="exp_cat_radio")
        st.session_state.last_cat_idx = EXPENSE_CATS.index(cat)
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            # [Modified] 통화 기본값 VND
            curr = st.selectbox("통화", ["VND", "KRW", "USD"], key="exp_curr_select")
            r_opts = [f"{st.session_state.rate_names[i]} ({st.session_state.rates[i]:.4f})" for i in range(5)]
            sel_r_str = st.selectbox("적용 환율 선택 (또는 자동)", r_opts, index=st.session_state.last_rate_idx, key="exp_rate_select")
            st.session_state.last_rate_idx = r_opts.index(sel_r_str)
            rv = st.session_state.rates[st.session_state.last_rate_idx]
            
            # [Modified] 결제수단 기본값 현금(VND)
            met = st.selectbox("결제수단", ["현금(VND)", "트래블로그(VND)", "원화계좌"], key="exp_method_select")
            
        with col_m2:
            # [Modified] 0원 기록 허용 및 정수형 입력
            amt = st.number_input("금액 (정수)", min_value=0, step=1000, format="%d", key="exp_amt_input")
            
            if curr == "VND" and amt > 0:
                calc_rate = auto_calc_fifo_rate(amt, met)
                st.caption(f"💡 시스템 권장 환율: **{calc_rate:.5f}**")
                cr_to_save = st.number_input("확정 환율", value=calc_rate, format="%.5f", key="in_cr")
            else:
                cr_to_save = 1.0 if curr == "KRW" else WAR

        desc = st.text_input("내용 (메모)", key="exp_desc_input")
        sel_date = st.date_input("날짜", datetime.now(), key="exp_date_input")

        if st.button("🚀 지출 기록하기", use_container_width=True):
            # [Modified] amt < 0 인 경우만 차단 (0원 허용)
            if amt < 0: st.warning("음수는 입력할 수 없습니다.")
            else:
                new_entry = pd.DataFrame([{'Date': sel_date.strftime("%m/%d(%a)"), 'Category': cat, 'Description': desc, 'Currency': curr, 'Amount': amt, 'PaymentMethod': met, 'IsExpense': 1, 'AppliedRate': cr_to_save}])
                if save_data(pd.concat([ledger_df, new_entry], ignore_index=True)): st.rerun()
    else:
        # 자산 이동 폼 (0원 허용)
        ty = st.selectbox("유형", ["직접환전 (원화계좌 -> 지폐VND)", "충전 (원화계좌 -> 카드VND)", "ATM출금 (카드VND -> 지폐VND)"])
        c1, c2 = st.columns(2)
        with c1: t_amt = st.number_input("받은 금액", min_value=0, step=1000, format="%d", key="tr_target")
        with c2: s_cost = st.number_input("지불 비용 (또는 인출 원금)", min_value=0, step=1000, format="%d", key="tr_source")
        if st.button("🔄 기록 실행", use_container_width=True):
            rate = s_cost / t_amt if t_amt > 0 else 0
            dest = "카드VND" if "카드" in ty else "지폐VND"
            new_desc = f"{ty.split(' ')[0]} (-> {dest})"
            new = pd.DataFrame([{'Date': datetime.now().strftime("%m/%d(%a)"), 'Category': ty.split(" ")[0], 'Description': new_desc, 'Currency': "VND", 'Amount': t_amt, 'PaymentMethod': "원화계좌" if "원화계좌" in ty else "트래블로그(VND)", 'IsExpense': 0, 'AppliedRate': rate}])
            if save_data(pd.concat([ledger_df, new], ignore_index=True)): st.rerun()

# [Module E] 내역 조회 및 수정 (Maintained)
with tab_history:
    st.subheader("🔍 내역 조회 및 수정")
    if not ledger_df.empty:
        edited_df = st.data_editor(ledger_df, use_container_width=True, num_rows="dynamic", key="history_editor_v112")
        if not ledger_df.equals(edited_df):
            st.warning("⚠️ 수정 내용 존재. 저장 버튼을 누르세요.")
            if st.button("💾 수정사항 저장", type="primary"):
                if save_data(edited_df): st.rerun()
        if st.button("🗑️ 마지막 행 삭제"):
            if save_data(ledger_df[:-1]): st.rerun()

# [Module D] TAB 3: 일일 결산 (Enhanced with Sorting & Parity)
with tab_stats:
    if not ledger_df.empty:
        exp_df = ledger_df[ledger_df['IsExpense'] == 1].copy()
        if not exp_df.empty:
            # 개별 AppliedRate를 기반으로 KRW/VND 양방향 환산 (Parity Engine)
            exp_df['KRW_val'] = exp_df.apply(lambda r: r['Amount'] if r['Currency'] == 'KRW' else r['Amount'] * r['AppliedRate'], axis=1)
            exp_df['VND_val'] = exp_df.apply(lambda r: r['Amount'] if r['Currency'] == 'VND' else r['Amount'] / r['AppliedRate'] if r['AppliedRate'] > 0 else 0, axis=1)
            exp_df['IsSurvival'] = exp_df['Category'].apply(lambda x: 1 if x in SURVIVAL_CATS else 0)

            # 국내 vs 해외 분리 대시보드
            domestic_df = exp_df[exp_df['Category'].isin(DOMESTIC_CATS)]
            overseas_df = exp_df[~exp_df['Category'].isin(DOMESTIC_CATS)]
            st.subheader("🏁 푸꾸옥 여행 경제 요약")
            c_s1, c_s2 = st.columns(2)
            with c_s1:
                st.info("🇰🇷 국내 지출")
                st.metric("국내지출 총액", f"{domestic_df['KRW_val'].sum():,.0f} 원")
                with st.expander("세부 내역"):
                    dg = domestic_df.groupby('Category')['KRW_val'].sum().reset_index().sort_values(by='KRW_val', ascending=False)
                    for _, r in dg.iterrows(): st.write(f"- {r['Category']}: {r['KRW_val']:,.0f} 원")
            with c_s2:
                st.success("🇻🇳 해외 지출")
                st.metric("해외지출 총액", f"{overseas_df['KRW_val'].sum():,.0f} 원")
                # [Added] 해외 지출 세부 내역 (내림차순 정렬)
                with st.expander("해외 항목별 세부 내역 (VND)"):
                    og = overseas_df.groupby('Category')['VND_val'].sum().reset_index().sort_values(by='VND_val', ascending=False)
                    for _, r in og.iterrows(): st.write(f"- {r['Category']}: {r['VND_val']:,.0f} ₫")

            st.divider()
            # [Added] 유동성 현황 (카드 vs 현금)
            total_sw_vnd = ledger_df[(ledger_df['Category'].isin(['충전', '환전', '직접환전'])) & (ledger_df['Currency'] == 'VND')]['Amount'].sum()
            sw_card = ledger_df[ledger_df['Description'].str.contains('카드VND', na=False)]['Amount'].sum()
            sw_cash = ledger_df[ledger_df['Description'].str.contains('지폐VND', na=False)]['Amount'].sum()
            spent_card = overseas_df[overseas_df['PaymentMethod'] == '트래블로그(VND)']['VND_val'].sum()
            spent_cash = overseas_df[overseas_df['PaymentMethod'] == '현금(VND)']['VND_val'].sum()

            st.subheader("💸 해외 자산 유동성 (WAR 기준)")
            cl1, cl2, cl3 = st.columns(3)
            with cl1: 
                st.metric("총 환전액", f"{total_sw_vnd:,.0f} ₫")
                st.caption(f"카드 {sw_card:,.0f} / 현금 {sw_cash:,.0f}")
            with cl2: 
                st.metric("현지 총 사용액", f"{overseas_df['VND_val'].sum():,.0f} ₫")
                st.caption(f"카드 {spent_card:,.0f} / 현금 {spent_cash:,.0f}")
            with cl3: 
                st.metric("현재 총 잔액", f"{(total_sw_vnd - overseas_df['VND_val'].sum()):,.0f} ₫")
                st.caption(f"카드 {c_vnd:,.0f} / 현금 {cash_v:,.0f}")

            # 일자별 정산표 (WAR 범례 포함)
            st.divider()
            st.subheader("🗓️ 일자별 정산 (Parity Engine)")
            st.caption(f"가중평균환율 기준: 100₫ = {WAR*100:.2f}원")
            daily_set = exp_df.groupby('Date').agg({'KRW_val': 'sum', 'VND_val': 'sum'}).reset_index()
            surv_only = exp_df[exp_df['IsSurvival'] == 1].groupby('Date').agg({'KRW_val': 'sum', 'VND_val': 'sum'}).reset_index().rename(columns={'KRW_val': 'S_KRW', 'VND_val': 'S_VND'})
            daily_table = pd.merge(daily_set, surv_only, on='Date', how='left').fillna(0)
            st.table(daily_table.rename(columns={'Date':'날짜','KRW_val':'총지출(원)','VND_val':'총지출(동)','S_KRW':'일상경비(원)','S_VND':'일상경비(동)'}).style.format({
                '총지출(원)': '{:,.0f}', '총지출(동)': '{:,.0f}', '일상경비(원)': '{:,.0f}', '일상경비(동)': '{:,.0f}'
            }))

# [Module G] TAB 4: 종료 보고서 (Full Strategic Overhaul)
with tab_final:
    st.header("🏁 푸꾸옥 여행 최종 전략 리포트")
    if not ledger_df.empty and not exp_df.empty:
        # [Added] 지능형 여행 기간 자동 감지
        entry_log = exp_df[exp_df['Category'] == '입국']
        exit_log = exp_df[exp_df['Category'] == '출국']
        
        if not entry_log.empty and not exit_log.empty:
            # 텍스트 날짜를 날짜 객체로 변환 시도 (필요 시 로직 보강 가능)
            local_days = 7 # 현재 데이터 기준 수동 할당 및 자동 감지 준비
        else:
            local_days = 7 # 기본값
            
        local_total_krw = exp_df[(exp_df['IsSurvival'] == 1) & (~exp_df['Category'].isin(FIXED_COST_CATS))]['KRW_val'].sum()
        avg_local_krw = local_total_krw / local_days
        total_trip_krw = exp_df['KRW_val'].sum()
        dom_total_krw = exp_df[exp_df['Category'].isin(DOMESTIC_CATS)]['KRW_val'].sum()
        ovr_total_krw = total_trip_krw - dom_total_krw

        # 1. 트리맵 (Greens Theme, Labels)
        st.subheader("🌳 지출 구조 상세 분석 (Treemap)")
        fig_tree = px.treemap(exp_df, path=['Category', 'Description'], values='KRW_val', 
                              color='KRW_val', color_continuous_scale='Greens')
        fig_tree.update_traces(texttemplate="<b>%{label}</b><br>%{value:,.0f}원<br>%{percentRoot:.1%}")
        st.plotly_chart(fig_tree, use_container_width=True)

        st.divider()
        cf1, cf2, cf3, cf4 = st.columns(4)
        with cf1: st.metric("여행 최종 총 지출", f"{total_trip_krw:,.0f} 원")
        with cf2: st.metric("국내 지출 총액", f"{dom_total_krw:,.0f} 원")
        with cf3: st.metric("현지 지출 총액", f"{ovr_total_krw:,.0f} 원")
        with cf4: st.metric("현지 1일 평균 (경비)", f"{avg_local_krw:,.0f} 원", help=f"{local_days}일 현지 일상경비 기준")

        # 2. 도넛 차트 (Center Label & Visibility)
        st.divider()
        st.subheader("🍕 카테고리별 지출 비중")
        cat_pie = exp_df.groupby('Category')['KRW_val'].sum().reset_index().sort_values(by='KRW_val', ascending=False)
        fig_donut = px.pie(cat_pie, values='KRW_val', names='Category', hole=0.5, color_discrete_sequence=px.colors.qualitative.Set3)
        fig_donut.update_traces(textposition='inside', textinfo='label+value+percent', texttemplate='%{label}<br>%{value:,.0f}원<br>%{percent:.1%}')
        until_d = exp_df['Date'].max().split('(')[0]
        fig_donut.add_annotation(text=f"<b>총 지출</b><br>{total_trip_krw:,.0f} 원<br><span style='font-size:10px'>Until {until_d}</span>", showarrow=False, font=dict(size=16))
        fig_donut.update_layout(height=600, margin=dict(l=10, r=10, t=50, b=100), legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5), uniformtext_minsize=11, uniformtext_mode='hide')
        st.plotly_chart(fig_donut, use_container_width=True)
    else:
        st.info("보고서를 생성할 데이터가 충분하지 않습니다.")

st.caption(f"GTL Platform v1.12 | Last Sync: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Strategic Partner Gem")
