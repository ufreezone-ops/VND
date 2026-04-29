# [Project: Global Travel Ledger (GTL) / Version: v26.04.29.005]
# [Strategic Partner: Gem / Core: Intelligent UI & Dynamic Asset Presets]
# [Status: Total System Restoration - NO COMPRESSION - 26.5 KB]

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date as dt_date
from streamlit_gsheets import GSheetsConnection
import time

# --- SECTION 1: Configuration & Global Initialization ---
st.set_page_config(page_title="여행 가계부 (GTL Platform)", layout="wide")

# [Safeguard] AttributeError 방지를 위한 전역 변수 초기화
if 'rate_names' not in st.session_state:
    st.session_state.rate_names = ['부산 1차', '머니박스', '트래블 2차', '에어텔', '기타']
if 'rates' not in st.session_state:
    st.session_state.rates = [0.0561, 0.0610, 0.0564, 0.0560, 0.0561]
if 'last_cat_idx' not in st.session_state: st.session_state.last_cat_idx = 0
if 'last_rate_idx' not in st.session_state: st.session_state.last_rate_idx = 0

TRAVEL_CURRENCY = "VND"
BASE_CURRENCY = "KRW"
BILLS = [500000, 200000, 100000, 50000, 20000, 10000, 5000, 2000, 1000]

EXPENSE_CATS = ["식사", "간식", "Grab", "VinBus", "마사지", "팁", "마트", "선물", "투어", "입장료", "통신", "수수료", "택시", "지하철", "항공권", "호텔", "보험", "입국", "출국"]
SURVIVAL_CATS = ["식사", "간식", "Grab", "VinBus", "마사지", "팁"]
FIXED_COST_CATS = ["항공권", "호텔", "보험"]
DOMESTIC_CATS = ["항공권", "호텔", "보험", "지하철", "택시"]
TRANSFER_CATS = ["충전", "ATM출금", "보증금", "환전", "직접환전"]

COLUMNS = ['Date', 'Category', 'Description', 'Currency', 'Amount', 'PaymentMethod', 'IsExpense', 'AppliedRate']
AUDIT_COLUMNS = ['Cum_Budget_KRW', 'Cum_Card_VND', 'Cum_Cash_VND']

# --- SECTION 2: [Module A] Data Engine ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    """구글 시트에서 데이터를 로드하고 정규화합니다."""
    try:
        df = conn.read(worksheet="ledger", ttl="0s")
        if df is None or df.empty: 
            return pd.DataFrame(columns=COLUMNS + AUDIT_COLUMNS)
        
        df = df.reindex(columns=COLUMNS + AUDIT_COLUMNS)
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
        df['AppliedRate'] = pd.to_numeric(df['AppliedRate'], errors='coerce').fillna(1.0)
        df['IsExpense'] = pd.to_numeric(df['IsExpense'], errors='coerce').fillna(0).astype(int)
        return df
    except Exception as e:
        if "429" in str(e):
            st.error("🚨 구글 서버 요청 한도 초과. 1분 뒤에 다시 시도하세요.")
        else:
            st.error(f"데이터 로드 실패: {e}")
        return pd.DataFrame(columns=COLUMNS + AUDIT_COLUMNS)

def calculate_running_totals(df):
    """구글 시트의 누계 컬럼을 계산합니다."""
    temp_df = df.copy()
    c_budget, c_card, c_cash = 0.0, 0.0, 0.0
    for i, row in temp_df.iterrows():
        qty, rate = row['Amount'], row['AppliedRate']
        desc, cat, method, curr, is_exp = str(row['Description']), row['Category'], row['PaymentMethod'], row['Currency'], row['IsExpense']
        if method == '원화계좌': c_budget += qty if curr == 'KRW' else qty * rate
        if cat in ['충전', '환전', '입금', '직접환전']:
            if "카드VND" in desc: c_card += qty
            elif "지폐VND" in desc: c_cash += qty
        elif cat == 'ATM출금':
            c_card -= qty; c_cash += qty
        elif is_exp == 1 and curr == TRAVEL_CURRENCY:
            if "트래블로그" in method: c_card -= qty
            elif "현금" in method: c_cash -= qty
        elif cat == '보증금': c_cash -= qty
        temp_df.at[i, 'Cum_Budget_KRW'] = round(c_budget, 0)
        temp_df.at[i, 'Cum_Card_VND'] = round(c_card, 0)
        temp_df.at[i, 'Cum_Cash_VND'] = round(c_cash, 0)
    return temp_df

def save_data(df, metrics=None):
    """Cloud 동기화 및 요약 탭 업데이트"""
    if df is None or len(df) == 0: return False
    with st.status("데이터 안전 잠금 및 동기화 중...", expanded=False):
        try:
            df_audit = calculate_running_totals(df)
            conn.update(worksheet="ledger", data=df_audit)
            if metrics:
                summary = pd.DataFrame({"항목": ["🏦 예산(KRW)", "💳 카드(VND)", "💵 현금(VND)"], "수치": [metrics[0], metrics[1], metrics[2]]})
                try: conn.update(worksheet="summary", data=summary)
                except: pass
            st.cache_data.clear()
            return True
        except Exception as e:
            st.error(f"저장 실패: {e}"); return False

@st.cache_data(ttl=0)
def load_cash_count():
    try:
        df = conn.read(worksheet="cash_count", ttl="0s")
        return dict(zip(df['Bill'].astype(int), df['Count'].astype(int))) if df is not None and not df.empty else {b: 0 for b in BILLS}
    except: return {b: 0 for b in BILLS}

def save_cash_count(counts_dict):
    try:
        df = pd.DataFrame(list(counts_dict.items()), columns=['Bill', 'Count'])
        conn.update(worksheet="cash_count", data=df)
        st.cache_data.clear(); return True
    except: return False

ledger_df = load_data()
cloud_cash_counts = load_cash_count()

# --- SECTION 3: [Module B] FIFO & Asset Engine ---
def get_inventory_status(df):
    inv = { "트래블로그(VND)": {}, "현금(VND)": {} }
    for _, row in df.iterrows():
        qty, rate, cat, desc, method = row['Amount'], row['AppliedRate'], row['Category'], str(row['Description']), row['PaymentMethod']
        if cat in ['충전', '환전', '입금', '직접환전']:
            target = "트래블로그(VND)" if "카드VND" in desc else "현금(VND)"
            inv[target][rate] = inv[target].get(rate, 0) + qty
        elif cat == 'ATM출금':
            temp_qty = qty
            for r in sorted(inv["트래블로그(VND)"].keys()):
                if temp_qty <= 0: break
                take = min(temp_qty, inv["트래블로그(VND)"][r]); inv["트래블로그(VND)"][r] -= take
                inv["현금(VND)"][r] = inv["현금(VND)"].get(r, 0) + take; temp_qty -= take
        elif row['IsExpense'] == 1 and row['Currency'] == TRAVEL_CURRENCY:
            target = "트래블로그(VND)" if "트래블로그" in method else "현금(VND)"
            temp_qty = qty
            for r in sorted(inv.get(target, {}).keys()):
                if temp_qty <= 0: break
                take = min(temp_qty, inv[target][r]); inv[target][r] -= take; temp_qty -= take
    return inv

current_inventory = get_inventory_status(ledger_df)
# 가중평균환율 (0으로 나누기 방지)
swaps_df = ledger_df[(ledger_df['Category'].isin(['충전','환전','직접환전'])) & (ledger_df['Currency'] == TRAVEL_CURRENCY)]
WAR = (swaps_df['Amount'] * swaps_df['AppliedRate']).sum() / swaps_df['Amount'].sum() if not swaps_df.empty else 0.0561

def auto_calc_fifo_rate(amount, method):
    target = "트래블로그(VND)" if "트래블로그" in method else "현금(VND)"
    available = {r: q for r, q in current_inventory.get(target, {}).items() if q > 0}
    if not available: return WAR
    total_cost, rem = 0.0, amount
    for r in sorted(available.keys()):
        if rem <= 0: break
        take = min(rem, available[r]); total_cost += take * r; rem -= take
    if rem > 0: total_cost += rem * max(available.keys())
    return total_cost / amount if amount > 0 else 0

def calculate_summary_metrics(df):
    if df.empty: return 0.0, 0.0, 0.0
    # [Restored] 예산: KRW 1:1, 외화는 AppliedRate
    bank_actions = df[df['PaymentMethod'] == '원화계좌']
    b_total = (bank_actions[bank_actions['Currency'] == 'KRW']['Amount']).sum() + \
              (bank_actions[bank_actions['Currency'] != 'KRW']['Amount'] * bank_actions[bank_actions['Currency'] != 'KRW']['AppliedRate']).sum()
    card_v = sum(current_inventory["트래블로그(VND)"].values())
    cash_v = sum(current_inventory["현금(VND)"].values())
    return b_total, card_v, cash_v

# --- SECTION 4: [Module C] Intelligent Input (📝 입력) ---
st.title("🌏 여행 가계부 (GTL v1.18)")
tab_in, tab_his, tab_rpt, tab_final = st.tabs(["📝 입력", "🔍 내역 조회", "📊 일일 결산", "🏁 종료 보고서"])

with tab_in:
    mode = st.radio("기록 모드 선택", ["일반 지출", "자산 이동"], horizontal=True, key="mode_radio")
    
    if mode == "일반 지출":
        cat = st.radio("항목 선택", EXPENSE_CATS, index=st.session_state.last_cat_idx, horizontal=True, key="exp_cat")
        st.session_state.last_cat_idx = EXPENSE_CATS.index(cat)
        
        # [Added] 입국/출국용 UI 간소화 (Hiding financial fields)
        if cat in ["입국", "출국"]:
            st.info(f"✈️ {cat} 일정을 기록합니다. 날짜와 메모만 입력하세요.")
            desc = st.text_input("내용 (메모)", placeholder=f"{cat} 시간, 편명 등", key="exp_desc_diary")
            sel_date = st.date_input("날짜", datetime.now(), key="exp_date_diary")
            if st.button("🚀 일정 기록하기", use_container_width=True):
                new_row = pd.DataFrame([{'Date': sel_date.strftime("%m/%d(%a)"), 'Category': cat, 'Description': desc, 'Currency': 'KRW', 'Amount': 0, 'PaymentMethod': '원화계좌', 'IsExpense': 1, 'AppliedRate': 1.0}])
                if save_data(pd.concat([ledger_df[COLUMNS], new_row], ignore_index=True)): st.rerun()
        else:
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                curr = st.selectbox("통화", ["VND", "KRW", "USD"], key="exp_curr")
                r_opts = [f"{st.session_state.rate_names[i]} ({st.session_state.rates[i]:.4f})" for i in range(5)]
                sel_r_str = st.selectbox("참조 환율 선택 (또는 자동)", r_opts, index=st.session_state.last_rate_idx, key="exp_rate_sel")
                st.session_state.last_rate_idx = r_opts.index(sel_r_str)
                rv = st.session_state.rates[st.session_state.last_rate_idx]
                met = st.selectbox("결제수단", ["현금(VND)", "트래블로그(VND)", "원화계좌"], key="exp_met")
            with col_m2:
                # 동적 포맷팅
                if curr in ["VND", "KRW"]: amt = st.number_input("금액 (Amount)", min_value=0.0, step=1000.0 if curr=="VND" else 1.0, format="%d", key="exp_amt_int")
                else: amt = st.number_input("금액 (Amount)", min_value=0.0, step=1.0, format="%.2f", key="exp_amt_float")
                
                if curr == TRAVEL_CURRENCY and amt > 0:
                    calc_rate = auto_calc_fifo_rate(amt, met)
                    st.caption(f"💡 인벤토리 재고 환율: **{calc_rate:.5f}**")
                    cr_final = st.number_input("확정 환율", value=calc_rate, format="%.5f", key="exp_cr_auto")
                else:
                    default_r = 1.0 if curr == BASE_CURRENCY else rv
                    cr_final = st.number_input("확정 환율", value=default_r, format="%.5f", key="exp_cr_man")
            desc = st.text_input("내용 (메모)", key="exp_desc")
            sel_date = st.date_input("날짜", datetime.now(), key="exp_date")
            if st.button("🚀 지출 기록하기", use_container_width=True):
                if amt < 0: st.warning("음수는 입력 불가합니다.")
                else:
                    new_row = pd.DataFrame([{'Date': sel_date.strftime("%m/%d(%a)"), 'Category': cat, 'Description': desc, 'Currency': curr, 'Amount': amt, 'PaymentMethod': met, 'IsExpense': 1, 'AppliedRate': cr_final}])
                    b_now, card_now, cash_now = calculate_summary_metrics(ledger_df)
                    if save_data(pd.concat([ledger_df[COLUMNS], new_row], ignore_index=True), metrics=[b_now, card_now, cash_now]):
                        st.toast("기록 완료! ✅"); time.sleep(0.5); st.rerun()
    else:
        # [Module C - 자산 이동 모드]
        st.subheader("🔁 자산 이동 (ATM/환전 프리셋 지원)")
        ty = st.selectbox("유형", ["직접환전 (원화계좌 -> 지폐VND)", "충전 (원화계좌 -> 카드VND)", "ATM출금 (카드VND -> 지폐VND)"], key="tr_type")
        
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            t_amt = st.number_input("받은 금액 (VND)", min_value=0, step=1000, format="%d", key="tr_target")
            # [Added] 자산 이동에도 환율 프리셋 적용
            r_opts_tr = [f"{st.session_state.rate_names[i]} ({st.session_state.rates[i]:.4f})" for i in range(5)]
            sel_r_tr = st.selectbox("적용할 환율 프리셋", r_opts_tr, key="tr_rate_preset")
            rv_tr = st.session_state.rates[r_opts_tr.index(sel_r_tr)]
            
            source_label = "인출 원금 확인 (VND)" if "ATM" in ty else "지불 비용 (KRW)"
            # 프리셋 환율로 자동 계산된 제안값 표시
            suggest_cost = int(t_amt * rv_tr) if "ATM" not in ty else t_amt
            s_cost = st.number_input(source_label, min_value=0, value=suggest_cost, step=1, format="%d", key="tr_source")
        with col_t2:
            tr_date = st.date_input("이동 날짜", datetime.now(), key="tr_date")
            fee_amt = st.number_input("환전/ATM 수수료 (VND)", min_value=0, step=1000, format="%d", key="tr_fee")
            
        if st.button("🔄 이동 실행", use_container_width=True):
            rate = s_cost / t_amt if t_amt > 0 else 0
            dest = "카드VND" if "카드" in ty else "지폐VND"
            main_row = pd.DataFrame([{'Date': tr_date.strftime("%m/%d(%a)"), 'Category': ty.split(" ")[0], 'Description': f"{ty.split(' ')[0]} (-> {dest})", 'Currency': "VND", 'Amount': t_amt, 'PaymentMethod': "원화계좌" if "원화계좌" in ty else "트래블로그(VND)", 'IsExpense': 0, 'AppliedRate': rate}])
            final_entry = pd.concat([ledger_df[COLUMNS], main_row], ignore_index=True)
            if fee_amt > 0:
                fee_rate = auto_calc_fifo_rate(fee_amt, "트래블로그(VND)")
                fee_row = pd.DataFrame([{'Date': tr_date.strftime("%m/%d(%a)"), 'Category': "수수료", 'Description': f"{ty.split(' ')[0]} 수수료", 'Currency': "VND", 'Amount': fee_amt, 'PaymentMethod': "트래블로그(VND)" if "원화계좌" not in ty else "원화계좌", 'IsExpense': 1, 'AppliedRate': fee_rate}])
                final_entry = pd.concat([final_entry, fee_row], ignore_index=True)
            b_now, card_now, cash_now = calculate_summary_metrics(ledger_df)
            if save_data(final_entry, metrics=[b_now, card_now, cash_now]): st.rerun()

# --- SECTION 5: [Sidebar & Module F] ---
with st.sidebar:
    st.title("💰 Wallet Status")
    b_val, card_val, cash_val = calculate_summary_metrics(ledger_df)
    st.metric("🏦 인출 총 원화 (예산)", f"{b_val:,.0f} 원")
    total_foreign = card_val + cash_val
    implied_rate = (b_val / total_foreign * 100) if total_foreign > 0 else 0
    st.caption(f"기준 환율: 100₫ = {implied_rate:.2f}원 (실효추정)")
    st.divider()
    st.metric("💳 카드 VND 잔액", f"{card_val:,.0f} ₫")
    st.metric("💵 현금 VND 잔액", f"{cash_val:,.0f} ₫")
    with st.expander("💵 실물 지폐 정산기", expanded=False):
        curr_p_counts = {}; total_ph = 0
        for b in BILLS:
            n = st.number_input(f"{b:,.0f} ₫", min_value=0, step=1, value=int(cloud_cash_counts.get(b,0)), key=f"p_{b}")
            curr_p_counts[b] = n; total_ph += b * n
        if st.button("💾 현금 수량 저장"): save_cash_count(curr_p_counts); st.rerun()
        st.caption(f"장부 차액: {total_ph - cash_val:,.0f} ₫")
    with st.expander("💱 환율 매니저", expanded=False):
        for i in range(5):
            st.session_state.rate_names[i] = st.text_input(f"이름 {i+1}", value=st.session_state.rate_names[i], key=f"rn_{i}")
            st.session_state.rates[i] = st.number_input(f"환율 {i+1}", value=st.session_state.rates[i], format="%.4f", key=f"rv_{i}")
    if st.button("🔄 Cloud Refresh", use_container_width=True): st.cache_data.clear(); st.rerun()

# --- SECTION 6: [Module D, E, G: History & Analytics] ---
with tab_his:
    st.subheader("🔍 내역 조회 및 수정")
    if not ledger_df.empty:
        edited_df = st.data_editor(ledger_df, use_container_width=True, num_rows="dynamic", key="editor_gtl_final")
        col_ed1, col_ed2 = st.columns(2)
        with col_ed1:
            if not ledger_df.equals(edited_df) and st.button("💾 수정사항 저장", type="primary"):
                b_n, card_n, cash_n = calculate_summary_metrics(edited_df)
                if save_data(edited_df[COLUMNS], metrics=[b_n, card_n, cash_n]): st.rerun()
        with col_ed2:
            if st.button("🗑️ 마지막 행 삭제", use_container_width=True):
                if save_data(ledger_df[COLUMNS][:-1]): st.rerun()
    else: st.info("기록된 데이터가 없습니다.")

with tab_stats:
    if not ledger_df.empty:
        exp_df = ledger_df[ledger_df['IsExpense'] == 1].copy()
        if not exp_df.empty:
            exp_df['KRW_val'] = exp_df.apply(lambda r: r['Amount'] if r['Currency'] == 'KRW' else r['Amount'] * r['AppliedRate'], axis=1)
            exp_df['VND_val'] = exp_df.apply(lambda r: r['Amount'] if r['Currency'] == 'VND' else r['Amount'] / r['AppliedRate'] if r['AppliedRate']>0 else 0, axis=1)
            exp_df['IsSurvival'] = exp_df['Category'].apply(lambda x: 1 if x in SURVIVAL_CATS else 0)

            # 1. 인벤토리 재고
            st.subheader("📦 환율별 재고 현황 (FIFO)")
            for wallet, batches in current_inventory.items():
                active = {r: q for r, q in batches.items() if q > 0}
                if active:
                    st.write(f"**{wallet}**")
                    st.table([{"환율": f"{r:.4f}", "잔액": f"{q:,.0f} ₫", "원화가치": f"{r*q:,.0f} 원"} for r, q in active.items()])

            # 2. 일자별 정산
            st.divider(); st.subheader("🗓️ 일자별 정산")
            daily_set = exp_df.groupby('Date').agg({'KRW_val': 'sum', 'VND_val': 'sum'}).reset_index()
            surv_only = exp_df[exp_df['IsSurvival'] == 1].groupby('Date').agg({'KRW_val': 'sum', 'VND_val': 'sum'}).reset_index().rename(columns={'KRW_val': 'S_KRW', 'VND_val': 'S_VND'})
            daily_table = pd.merge(daily_set, surv_only, on='Date', how='left').fillna(0)
            if not daily_table.empty:
                st.table(daily_table.rename(columns={'Date':'날짜','KRW_val':'총(원)','VND_val':'총(동)','S_KRW':'일상(원)','S_VND':'일상(동)'}).style.format({c: '{:,.0f}' for c in ['총(원)','총(동)','일상(원)','일상(동)']}))

            # 3. 이중 막대 차트 (동적 가로축)
            st.divider(); c_mode = st.radio("표시 통화 선택", ["원화(KRW)", "동화(VND)"], horizontal=True, key="st_curr")
            # [Fixed] 기록이 있는 날짜만 가로축에 표시
            active_dates = daily_table['Date'].tolist()
            chart_final = daily_table.copy()
            chart_final['Date_Clean'] = chart_final['Date'].str.split('(').str[0]
            y_s, y_t = ('S_KRW', 'KRW_val') if "원화" in c_mode else ('S_VND', 'VND_val')
            fig = go.Figure()
            fig.add_trace(go.Bar(x=chart_final['Date_Clean'], y=chart_final[y_s], name='일상경비', marker_color='#00FF00', text=chart_final[y_s], texttemplate='%{text:,.0f}'))
            fig.add_trace(go.Bar(x=chart_final['Date_Clean'], y=chart_final[y_t], name='전체지출', marker_color='#FF00FF'))
            fig.update_layout(barmode='group', margin=dict(l=5, r=5, t=30, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig, use_container_width=True)

with tab_final:
    if not ledger_df.empty and not exp_df.empty:
        st.header("🏁 푸꾸옥 여행 최종 전략 리포트")
        # [Fixed] 국내/해외 판별 기준 보정 (Currency & PaymentMethod 기반)
        dom_df = exp_df[(exp_df['Currency'] == 'KRW') & (exp_df['PaymentMethod'] == '원화계좌')]
        ovr_df = exp_df[~((exp_df['Currency'] == 'KRW') & (exp_df['PaymentMethod'] == '원화계좌'))]
        
        st.subheader("🌳 지출 구조 상세 분석 (Treemap)")
        fig_tree = px.treemap(exp_df, path=['Category', 'Description'], values='KRW_val', color='KRW_val', color_continuous_scale='Greens')
        fig_tree.update_traces(texttemplate="<b>%{label}</b><br>%{value:,.0f}원<br>%{percentRoot:.1%}")
        st.plotly_chart(fig_tree, use_container_width=True)
        
        st.divider(); cf1, cf2, cf3, cf4 = st.columns(4)
        local_total_krw = exp_df[(exp_df['IsSurvival'] == 1) & (exp_df['Currency'] == 'VND')].copy()
        avg_local_krw = local_total_krw['KRW_val'].sum() / 7 if not local_total_krw.empty else 0
        total_spent = exp_df['KRW_val'].sum()
        with cf1: st.metric("여행 최종 총 지출", f"{total_spent:,.0f} 원")
        with cf2: st.metric("국내 지출 총액", f"{dom_df['KRW_val'].sum():,.0f} 원")
        with cf3: st.metric("현지 지출 총액", f"{ovr_df['KRW_val'].sum():,.0f} 원")
        with cf4: st.metric("현지 1일 평균", f"{avg_local_krw:,.0f} 원")

        st.subheader("🍕 카테고리별 지출 비중")
        cat_pie = exp_df.groupby('Category')['KRW_val'].sum().reset_index().sort_values(by='KRW_val', ascending=False)
        fig_donut = px.pie(cat_pie, values='KRW_val', names='Category', hole=0.5, color_discrete_sequence=px.colors.qualitative.Set3)
        fig_donut.update_traces(textposition='inside', textinfo='label+value+percent', texttemplate='%{label}<br>%{value:,.0f}원<br>%{percent:.1%}')
        fig_donut.add_annotation(text=f"<b>총 지출</b><br>{total_spent:,.0f} 원", showarrow=False, font=dict(size=16))
        fig_donut.update_layout(height=600, margin=dict(l=10, r=10, t=50, b=100), legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5), uniformtext_minsize=11, uniformtext_mode='hide')
        st.plotly_chart(fig_donut, use_container_width=True)

st.caption(f"GTL Platform v1.18 | Last Sync: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Strategic Partner Gem")
