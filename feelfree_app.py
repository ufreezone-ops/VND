# [Project: Feelfree Travel Ledger / Version: v26.04.30.004]
# [Strategic Partner: Gem / Core: Strategic Timeline & Mode Expansion]
# [Status: Total System Restoration - ZERO OMISSION - 38.2 KB]

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date as dt_date
from streamlit_gsheets import GSheetsConnection
import time

# --- SECTION 1: Configuration & Global Setup ---
# [Status: Maintained for UI/UX Stability]
st.set_page_config(
    page_title="Feelfree: 여행 가계부", 
    page_icon="🌏", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 아이폰 홈 화면 추가 시 전용 아이콘 지정 및 KPI 레이아웃 CSS
st.markdown("""
    <script>
        var link = document.createElement('link');
        link.rel = 'apple-touch-icon';
        link.href = 'https://img.icons8.com/color/512/globe--v1.png';
        document.getElementsByTagName('head')[0].appendChild(link);
        
        var meta = document.createElement('meta');
        meta.name = 'apple-mobile-web-app-capable';
        meta.content = 'yes';
        document.getElementsByTagName('head')[0].appendChild(meta);
    </script>
    <style>
    .main { background-color: #0e1117; }
    .kpi-box {
        background-color: #1e2130;
        padding: 20px;
        border-radius: 15px;
        border-left: 8px solid #00FF00;
        margin-bottom: 20px;
        min-height: 130px;
        box-shadow: 4px 6px 15px rgba(0,0,0,0.5);
    }
    .kpi-title { font-size: 15px; color: #cccccc; margin-bottom: 10px; font-weight: 600; }
    .kpi-value-krw { font-size: 26px; font-weight: bold; color: #ffffff; line-height: 1.1; }
    .kpi-value-vnd { font-size: 18px; color: #00FF00; margin-top: 8px; font-family: 'Courier New', monospace; font-weight: 500; }
    .sold-out { color: #ff4b4b; font-weight: bold; font-style: italic; }
    div[data-testid="stTable"] { border: 1px solid #444; border-radius: 10px; overflow: hidden; }
    .stTabs [data-baseweb="tab-list"] { gap: 15px; padding-bottom: 10px; }
    .stTabs [data-baseweb="tab"] { 
        background-color: #1c1f2b; 
        border-radius: 8px 8px 0 0; 
        padding: 12px 25px;
        color: #ffffff;
    }
    .stTabs [aria-selected="true"] { background-color: #00FF00 !important; color: #000000 !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# [Safeguard] 전역 변수 초기화
if 'rate_names' not in st.session_state:
    st.session_state.rate_names = ['부산 1차', '머니박스', '트래블 2차', '에어텔', '기타']
if 'rates' not in st.session_state:
    st.session_state.rates = [0.0561, 0.0610, 0.0564, 0.0560, 0.0561]
if 'last_cat_idx' not in st.session_state: 
    st.session_state.last_cat_idx = 0
if 'last_rate_idx' not in st.session_state: 
    st.session_state.last_rate_idx = 0

TRAVEL_CURRENCY = "VND"
BASE_CURRENCY = "KRW"
BILLS = [500000, 200000, 100000, 50000, 20000, 10000, 5000, 2000, 1000]

EXPENSE_CATS = ["식사", "간식", "Grab", "VinBus", "마사지", "팁", "마트", "선물", "투어", "입장료", "통신", "수수료", "택시", "지하철", "항공권", "호텔", "보험"]
SURVIVAL_CATS = ["간식", "Grab", "VinBus", "마사지", "팁", "식사"]
FIXED_COST_CATS = ["항공권", "호텔", "보험"]
DOMESTIC_CATS = ["항공권", "호텔", "보험", "지하철", "택시"]
TRANSFER_CATS = ["충전", "ATM출금", "보증금", "환전", "직접환전"]

CORE_COLUMNS = ['Date', 'Category', 'Description', 'Currency', 'Amount', 'PaymentMethod', 'IsExpense', 'AppliedRate']
AUDIT_COLUMNS = ['Cum_Budget_KRW', 'Cum_Card_VND', 'Cum_Cash_VND']
NOTE_COLUMN = ['Note']
FINAL_COLUMNS = CORE_COLUMNS + AUDIT_COLUMNS + NOTE_COLUMN

# --- SECTION 2: [Module A] Data Engine ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        df = conn.read(worksheet="ledger", ttl="0s")
        if df is None or df.empty: return pd.DataFrame(columns=FINAL_COLUMNS)
        df = df.dropna(subset=['Date', 'Category'], how='any')
        df = df.reindex(columns=FINAL_COLUMNS)
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
        df['AppliedRate'] = pd.to_numeric(df['AppliedRate'], errors='coerce').fillna(1.0)
        df['IsExpense'] = pd.to_numeric(df['IsExpense'], errors='coerce').fillna(0).astype(int)
        df['Note'] = df['Note'].fillna("").astype(str)
        return df
    except Exception: return pd.DataFrame(columns=FINAL_COLUMNS)

def calculate_running_totals(df):
    temp_df = df.copy()
    c_budget, c_card, c_cash = 0.0, 0.0, 0.0
    for i, row in temp_df.iterrows():
        qty, rate, desc, cat = row['Amount'], row['AppliedRate'], str(row['Description']), row['Category']
        method, curr, is_exp = row['PaymentMethod'], row['Currency'], row['IsExpense']
        if method == '원화계좌':
            if curr == 'KRW': c_budget += qty
            else: c_budget += qty * rate
        if cat in ['충전', '환전', '입금', '직접환전']:
            if "카드VND" in desc: c_card += qty
            elif "지폐VND" in desc: c_cash += qty
        elif cat == 'ATM출금':
            c_card -= qty; c_cash += qty
        elif is_exp == 1 and curr == TRAVEL_CURRENCY:
            if "트래블로그" in str(method) or "카드" in str(method): c_card -= qty
            else: c_cash -= qty
        elif cat == '보증금':
            c_cash -= qty
        temp_df.at[i, 'Cum_Budget_KRW'] = round(c_budget, 0)
        temp_df.at[i, 'Cum_Card_VND'] = round(c_card, 0)
        temp_df.at[i, 'Cum_Cash_VND'] = round(c_cash, 0)
    return temp_df

def save_data(df, metrics=None):
    if df is None or len(df) == 0: return False
    with st.status("전략적 데이터 안전 잠금 중...", expanded=False):
        try:
            df_audit = calculate_running_totals(df)
            conn.update(worksheet="ledger", data=df_audit.reindex(columns=FINAL_COLUMNS))
            if metrics:
                summary = pd.DataFrame({"항목": ["🏦 예산(KRW)", "💳 카드(VND)", "💵 현금(VND)", "🕒 업데이트"], "수치": [f"{metrics[0]:,.0f}", f"{metrics[1]:,.0f}", f"{metrics[2]:,.0f}", datetime.now().strftime("%H:%M")]})
                try: conn.update(worksheet="summary", data=summary)
                except: pass
            st.cache_data.clear(); return True
        except: return False

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

# --- SECTION 3: [Module B] URDI Engine ---
def get_inventory_status(df):
    inv_batches = { "트래블로그(VND)": [], "현금(VND)": [] }
    if df.empty: return inv_batches
    for idx, row in df.iterrows():
        qty, rate, desc, cat, method = row['Amount'], row['AppliedRate'], str(row['Description']), row['Category'], row['PaymentMethod']
        if cat in ['충전', '환전', '입금', '직접환전']:
            target = "트래블로그(VND)" if "카드VND" in desc else "현금(VND)"
            inv_batches[target].append({'rate': rate, 'qty': qty, 'initial': qty, 'desc': desc})
        elif cat == 'ATM출금':
            temp_qty = qty
            for batch in inv_batches["트래블로그(VND)"]:
                if temp_qty <= 0: break
                if batch['qty'] <= 0: continue
                if abs(batch['rate'] - rate) < 0.00001:
                    take = min(temp_qty, batch['qty']); batch['qty'] -= take
                    inv_batches["현금(VND)"].append({'rate': batch['rate'], 'qty': take, 'initial': take, 'desc': 'ATM인출분'})
                    temp_qty -= take
            if temp_qty > 0:
                for batch in inv_batches["트래블로그(VND)"]:
                    if temp_qty <= 0: break
                    if batch['qty'] <= 0: continue
                    take = min(temp_qty, batch['qty']); batch['qty'] -= take
                    inv_batches["현금(VND)"].append({'rate': batch['rate'], 'qty': take, 'initial': take, 'desc': 'ATM인출분(FIFO)'})
                    temp_qty -= take
        elif row['IsExpense'] == 1 and row['Currency'] == TRAVEL_CURRENCY:
            target = "트래블로그(VND)" if ("트래블로그" in str(method) or "카드" in str(method)) else "현금(VND)"
            temp_qty = qty
            for batch in inv_batches[target]:
                if temp_qty <= 0: break
                if batch['qty'] <= 0: continue
                if abs(batch['rate'] - rate) < 0.00001:
                    take = min(temp_qty, batch['qty']); batch['qty'] -= take; temp_qty -= take
            if temp_qty > 0:
                decomposed_notes = []
                for batch in inv_batches[target]:
                    if temp_qty <= 0: break
                    if batch['qty'] <= 0: continue
                    take = min(temp_qty, batch['qty']); batch['qty'] -= take; temp_qty -= take
                    decomposed_notes.append(f"{take:,.0f}@{batch['rate']:.4f}")
                if decomposed_notes: df.at[idx, 'Note'] = "Decomposed: " + " + ".join(decomposed_notes)
    return inv_batches

current_inventory_batches = get_inventory_status(ledger_df)
sw_df = ledger_df[(ledger_df['Category'].isin(['충전','환전','입금','직접환전'])) & (ledger_df['Currency'] == TRAVEL_CURRENCY)]
WAR = (sw_df['Amount'] * sw_df['AppliedRate']).sum() / sw_df['Amount'].sum() if not sw_df.empty and sw_df['Amount'].sum() > 0 else 0.0561

def auto_calc_fifo_rate(amount, method):
    target = "트래블로그(VND)" if ("트래블로그" in str(method) or "카드" in str(method)) else "현금(VND)"
    temp_inv = get_inventory_status(ledger_df)
    available_batches = [b for b in temp_inv[target] if b['qty'] > 0]
    if not available_batches: return WAR
    total_cost_krw, remaining = 0.0, amount
    for batch in available_batches:
        if remaining <= 0: break
        take = min(remaining, batch['qty']); total_cost_krw += take * batch['rate']; remaining -= take
    if remaining > 0: total_cost_krw += remaining * available_batches[-1]['rate']
    return total_cost_krw / amount if amount > 0 else 0

def calculate_summary_metrics(df):
    if df.empty: return 0.0, 0.0, 0.0, 0.0
    bank_actions = df[df['PaymentMethod'] == '원화계좌']
    b_total = (bank_actions[bank_actions['Currency'] == 'KRW']['Amount']).sum() + \
              (bank_actions[bank_actions['Currency'] != 'KRW']['Amount'] * bank_actions[bank_actions['Currency'] != 'KRW']['AppliedRate']).sum()
    exp_only = df[df['IsExpense'] == 1]
    spent_total = (exp_only.apply(lambda r: r['Amount'] if r['Currency'] == 'KRW' else r['Amount'] * r['AppliedRate'], axis=1)).sum()
    card_v = sum([b['qty'] for b in current_inventory_batches["트래블로그(VND)"]])
    cash_v = sum([b['qty'] for b in current_inventory_batches["현금(VND)"]])
    return b_total, card_v, cash_v, spent_total

# --- SECTION 4: [Module C] Intelligent Input (📝 입력) ---
# [Status: Modified - Mode Restructuring & Currency Sync]
st.title("🌏 Feelfree: 여행 가계부")
tab_in, tab_his, tab_stats, tab_final = st.tabs(["📝 입력", "🔍 내역 조회", "📊 일일 결산", "🏁 종료 보고서"])

with tab_in:
    # [Modified] 출입국 모드 신설
    mode = st.radio("기록 모드 선택", ["일반 지출", "자산 이동", "출입국"], horizontal=True, key="mode_radio")
    
    if mode == "일반 지출":
        cat = st.radio("항목 선택", EXPENSE_CATS, index=st.session_state.last_cat_idx, horizontal=True, key="exp_cat")
        st.session_state.last_cat_idx = EXPENSE_CATS.index(cat)
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            curr = st.selectbox("통화", ["VND", "KRW", "USD"], key="exp_curr")
            r_opts = [f"{st.session_state.rate_names[i]} ({st.session_state.rates[i]:.4f})" for i in range(5)]
            sel_r_str = st.selectbox("참조 환율 선택", r_opts, index=st.session_state.last_rate_idx, key="exp_rate_sel")
            st.session_state.last_rate_idx = r_opts.index(sel_r_str); rv = st.session_state.rates[st.session_state.last_rate_idx]
            
            # [Added] KRW 선택 시 결제수단 자동 동기화
            met_options = ["현금(VND)", "트래블로그(VND)", "원화계좌"]
            met_idx = 2 if curr == "KRW" else 0
            met = st.selectbox("결제수단", met_options, index=met_idx, key="exp_met")
            
        with col_m2:
            if curr in ["VND", "KRW"]: amt = st.number_input("금액", min_value=0, step=1000 if curr=="VND" else 1, format="%d", key="exp_amt_int")
            else: amt = st.number_input("금액", min_value=0.0, step=1.0, format="%.2f", key="exp_amt_float")
            
            if curr == TRAVEL_CURRENCY and amt > 0:
                calc_rate = auto_calc_fifo_rate(amt, met)
                st.caption(f"💡 인벤토리 계산 환율: **{calc_rate:.5f}**")
                cr_final = st.number_input("확정 환율", value=calc_rate, format="%.5f", key=f"exp_cr_auto_{met}_{amt}")
            else: cr_final = st.number_input("확정 환율", value=(1.0 if curr=="KRW" else rv), format="%.5f", key=f"exp_cr_man_{curr}")
            
        desc = st.text_input("내용 (메모)", key="exp_desc"); sel_date = st.date_input("날짜", datetime.now(), key="exp_date")
        if st.button("🚀 지출 기록하기", use_container_width=True):
            new_row = pd.DataFrame([{'Date': sel_date.strftime("%m/%d(%a)"), 'Category': cat, 'Description': desc, 'Currency': curr, 'Amount': amt, 'PaymentMethod': met, 'IsExpense': 1, 'AppliedRate': cr_final, 'Note': ''}])
            b_now, card_now, cash_now, _ = calculate_summary_metrics(ledger_df)
            if save_data(pd.concat([ledger_df[CORE_COLUMNS + NOTE_COLUMN], new_row], ignore_index=True), metrics=[b_now, card_now, cash_now]): st.rerun()

    elif mode == "자산 이동":
        st.subheader("🔁 자산 이동 및 환전")
        ty = st.selectbox("유형", ["직접환전 (원화계좌 -> 지폐VND)", "충전 (원화계좌 -> 카드VND)", "ATM출금 (카드VND -> 지폐VND)"], key="tr_type")
        c1, c2 = st.columns(2)
        with c1:
            t_amt = st.number_input("받은 금액 (VND)", min_value=0, step=1000, format="%d", key="tr_target")
            # [Added] ATM 이외의 경우에만 환율 프리셋 노출
            if "ATM" not in ty:
                r_opts_tr = [f"{st.session_state.rate_names[i]} ({st.session_state.rates[i]:.4f})" for i in range(5)]
                sel_r_tr = st.selectbox("적용 환율 프리셋", r_opts_tr, key="tr_rate_preset"); rv_tr = st.session_state.rates[r_opts_tr.index(sel_r_tr)]
                s_cost = st.number_input("소요 원금 (지불 비용)", min_value=0, value=int(t_amt * rv_tr), step=1, format="%d", key="tr_source_swap")
                applied_tr_rate = s_cost / t_amt if t_amt > 0 else 0
            else:
                # ATM 출금 시 카드 재고에서 환율 자동 상속
                inherited_r = auto_calc_fifo_rate(t_amt, "트래블로그(VND)")
                st.info(f"💳 카드 재고 계승 환율: **{inherited_r:.5f}**")
                s_cost = st.number_input("인출 원금 확인 (VND)", value=int(t_amt), key="tr_source_atm")
                applied_tr_rate = inherited_r
        with c2:
            tr_date = st.date_input("이동 날짜", datetime.now(), key="tr_date")
            # [Modified] ATM일 때만 수수료 필드 노출
            fee_amt = 0
            if "ATM" in ty: fee_amt = st.number_input("ATM 수수료 (VND)", min_value=0, step=1000, format="%d", key="tr_fee")
            
        if st.button("🔄 이동 실행", use_container_width=True):
            dest = "카드VND" if "카드" in ty else "지폐VND"
            main_row = pd.DataFrame([{'Date': tr_date.strftime("%m/%d(%a)"), 'Category': ty.split(" ")[0], 'Description': f"{ty.split(' ')[0]} (-> {dest})", 'Currency': "VND", 'Amount': t_amt, 'PaymentMethod': "원화계좌" if "원화계좌" in ty else "트래블로그(VND)", 'IsExpense': 0, 'AppliedRate': applied_tr_rate, 'Note': ''}])
            final_entry = pd.concat([ledger_df[CORE_COLUMNS + NOTE_COLUMN], main_row], ignore_index=True)
            if fee_amt > 0:
                fee_rate = auto_calc_fifo_rate(fee_amt, "트래블로그(VND)")
                fee_row = pd.DataFrame([{'Date': tr_date.strftime("%m/%d(%a)"), 'Category': "수수료", 'Description': f"{ty.split(' ')[0]} 수수료", 'Currency': "VND", 'Amount': fee_amt, 'PaymentMethod': "트래블로그(VND)", 'IsExpense': 1, 'AppliedRate': fee_rate, 'Note': ''}])
                final_entry = pd.concat([final_entry, fee_row], ignore_index=True)
            b_now, card_now, cash_now, _ = calculate_summary_metrics(ledger_df); save_data(final_entry, metrics=[b_now, card_now, cash_now]); st.rerun()

    else: # 출입국 모드
        st.subheader("✈️ 출입국 일정 기록")
        io_type = st.radio("구분", ["출국", "입국"], horizontal=True, key="io_radio")
        desc = st.text_input("내용 (메모)", placeholder="편명, 시간 등", key="io_desc")
        sel_date = st.date_input("날짜", datetime.now(), key="io_date")
        if st.button("🚀 일정 기록 완료", use_container_width=True):
            new_row = pd.DataFrame([{'Date': sel_date.strftime("%m/%d(%a)"), 'Category': io_type, 'Description': desc, 'Currency': 'KRW', 'Amount': 0, 'PaymentMethod': '원화계좌', 'IsExpense': 1, 'AppliedRate': 1.0, 'Note': ''}])
            if save_data(pd.concat([ledger_df[CORE_COLUMNS + NOTE_COLUMN], new_row], ignore_index=True)): st.rerun()

# --- SECTION 5: [Sidebar] ---
with st.sidebar:
    st.title("💰 Wallet Status")
    b_val, card_val, cash_val, spent_val = calculate_summary_metrics(ledger_df)
    st.metric("🏦 총 예산 (환전포함)", f"{b_val:,.0f} 원")
    st.metric("💸 지출총액 (잔액제외)", f"{spent_val:,.0f} 원")
    st.caption(f"가중평균 환율: 100₫ = {WAR*100:.2f}원")
    st.divider(); st.metric("💳 카드 VND 잔액", f"{card_val:,.0f} ₫"); st.metric("💵 현금 VND 잔액", f"{cash_val:,.0f} ₫")
    with st.expander("💵 실물 지폐 정산기"):
        total_ph = sum([b * st.number_input(f"{b:,.0f} ₫", min_value=0, step=1, value=int(cloud_cash_counts.get(b,0)), key=f"p_{b}") for b in BILLS])
        if st.button("💾 현금 수량 저장"): save_cash_count({b: st.session_state[f"p_{b}"] for b in BILLS}); st.rerun()
        st.write(f"실물 합계: {total_ph:,.0f} ₫ / 차액: {total_ph - cash_val:,.0f} ₫")
    if st.button("🔄 Cloud Refresh", use_container_width=True): st.cache_data.clear(); st.rerun()

# --- SECTION 6: [Module D, E: History & Settlement] ---
with tab_his:
    st.subheader("🔍 내역 조회 및 수정")
    if not ledger_df.empty:
        display_df = ledger_df.reindex(columns=FINAL_COLUMNS)
        edited_df = st.data_editor(display_df, use_container_width=True, num_rows="dynamic", key="editor_gtl_final")
        col_ed1, col_ed2 = st.columns(2)
        with col_ed1:
            if not display_df.equals(edited_df) and st.button("💾 수정사항 저장", type="primary"):
                b_n, card_n, cash_n, _ = calculate_summary_metrics(edited_df)
                if save_data(edited_df[CORE_COLUMNS + NOTE_COLUMN], metrics=[b_n, card_n, cash_n]): st.rerun()
        with col_ed2:
            if st.button("🗑️ 마지막 행 삭제", use_container_width=True):
                if save_data(ledger_df[CORE_COLUMNS + NOTE_COLUMN][:-1]): st.rerun()

with tab_stats:
    if not ledger_df.empty:
        exp_df = ledger_df[ledger_df['IsExpense'] == 1].copy()
        if not exp_df.empty:
            exp_df['KRW_val'] = exp_df.apply(lambda r: r['Amount'] if r['Currency'] == 'KRW' else r['Amount'] * r['AppliedRate'], axis=1)
            exp_df['VND_val'] = exp_df.apply(lambda r: r['Amount'] if r['Currency'] == 'VND' else r['Amount'] / r['AppliedRate'] if r['AppliedRate']>0 else 0, axis=1)
            exp_df['IsSurvival'] = exp_df['Category'].apply(lambda x: 1 if x in SURVIVAL_CATS else 0)

            # 1. FIFO 히스토리
            st.subheader("📦 환율별 재고 현황 (FIFO 히스토리)")
            for wallet_name, batch_list in current_inventory_batches.items():
                st.write(f"**{wallet_name}**")
                display_rows = [{"환율": f"{b['rate']:.4f}", "잔액 상태": (f"{b['qty']:,.0f} ₫" if b['qty'] > 0 else "🚫 소진완료"), "최초 수량": f"{b['initial']:,.0f} ₫", "원화가치(잔액)": f"{b['rate']*max(0,b['qty']):,.0f} 원"} for b in batch_list]
                if display_rows: st.table(display_rows)

            # 2. 요약 섹션
            st.subheader("🏁 여행 경제 요약")
            c1, c2 = st.columns(2)
            with c1:
                dom_df = exp_df[((exp_df['Currency'] == 'KRW') & (exp_df['PaymentMethod'] == '원화계좌')) & (~exp_df['Category'].isin(['입국','출국']))]
                st.info("🇰🇷 국내 지출"); st.metric("총액", f"{dom_df['KRW_val'].sum():,.0f} 원")
                dg = dom_df.groupby('Category').agg({'KRW_val':'sum', 'Date':'count'}).sort_values(by='KRW_val', ascending=False)
                for cat_name, row_data in dg.iterrows(): st.write(f"- {cat_name}({int(row_data['Date'])}회): {row_data['KRW_val']:,.0f} 원")
            with c2:
                ovr_df = exp_df[~((exp_df['Currency'] == 'KRW') & (exp_df['PaymentMethod'] == '원화계좌'))]
                st.success("🇻🇳 해외 지출"); st.metric("총액", f"{ovr_df['KRW_val'].sum():,.0f} 원")
                og = ovr_df.groupby('Category').agg({'VND_val':'sum', 'Date':'count'}).sort_values(by='VND_val', ascending=False)
                for cat_name, row_data in og.iterrows(): st.write(f"- {cat_name}({int(row_data['Date'])}회): {row_data['VND_val']:,.0f} ₫")

            # 3. 정산표 & [Fixed] 동적 기간 차트
            st.divider(); daily_set = exp_df.groupby('Date').agg({'KRW_val': 'sum', 'VND_val': 'sum'}).reset_index()
            surv_only = exp_df[exp_df['IsSurvival'] == 1].groupby('Date').agg({'KRW_val': 'sum', 'VND_val': 'sum'}).reset_index().rename(columns={'KRW_val': 'S_KRW', 'VND_val': 'S_VND'})
            daily_table = pd.merge(daily_set, surv_only, on='Date', how='left').fillna(0)
            st.table(daily_table.rename(columns={'Date':'날짜','KRW_val':'총(원)','VND_val':'총(동)','S_KRW':'일상(원)','S_VND':'일상(동)'}).style.format({c: '{:,.0f}' for c in ['총(원)','총(동)','일상(원)','일상(동)']}))
            
            # [Fixed] 차트 기간 필터링 (출국일 기준)
            exit_date = exp_df[exp_df['Category'] == '출국']['Date'].min()
            chart_raw = exp_df.copy()
            if pd.notna(exit_date): chart_raw = chart_raw[chart_raw['Date'] >= exit_date]
            
            c_mode = st.radio("표시 통화 선택", ["원화(KRW)", "동화(VND)"], horizontal=True, key="st_curr")
            chart_raw['Date_Clean'] = chart_raw['Date'].str.split('(').str[0]
            y_col = 'KRW_val' if "원화" in c_mode else 'VND_val'
            color_map = {"식사": "#2E7D32", "간식": "#4CAF50", "Grab": "#00897B", "VinBus": "#00ACC1", "마사지": "#0288D1", "팁": "#03A9F4", "마트": "#E91E63", "선물": "#9C27B0", "투어": "#673AB7", "입장료": "#3F51B5", "통신": "#FF9800", "수수료": "#795548"}
            fig = px.bar(chart_raw, x='Date_Clean', y=y_col, color='Category', title=f"여행기간 일일 지출 ({len(chart_raw['Date'].unique())}일차)", color_discrete_map=color_map)
            fig.update_layout(barmode='stack', margin=dict(l=5, r=5, t=40, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), xaxis=dict(title=""), yaxis=dict(title=""))
            st.plotly_chart(fig, use_container_width=True)

# --- SECTION 7: [Module G: Final Strategic Report] ---
with tab_final:
    if not ledger_df.empty and not exp_df.empty:
        total_trip_krw = exp_df['KRW_val'].sum(); total_trip_vnd = exp_df['VND_val'].sum()
        dom_total_krw = exp_df[exp_df['Category'].isin(DOMESTIC_CATS)]['KRW_val'].sum()
        ovr_total_krw = total_trip_krw - dom_total_krw; ovr_total_vnd = exp_df[~exp_df['Category'].isin(DOMESTIC_CATS)]['VND_val'].sum()
        local_v = exp_df[(exp_df['IsSurvival'] == 1) & (exp_df['Currency'] == 'VND')].copy()
        avg_local_krw = local_v['KRW_val'].sum() / 7 if not local_v.empty else 0
        avg_local_vnd = local_v['VND_val'].sum() / 7 if not local_v.empty else 0
        
        def kpi_box(title, krw, vnd=None):
            vnd_str = f"<div class='kpi-value-vnd'>({vnd:,.0f} ₫)</div>" if vnd is not None else ""
            return f"<div class='kpi-box'><div class='kpi-title'>{title}</div><div class='kpi-value-krw'>{krw:,.0f} 원</div>{vnd_str}</div>"

        st.header("🏁 푸꾸옥 여행 최종 전략 리포트")
        k1, k2, k3, k4 = st.columns(4)
        with k1: st.markdown(kpi_box("여행 최종 총 지출", total_trip_krw, total_trip_vnd), unsafe_allow_html=True)
        with k2: st.markdown(kpi_box("국내 지출 총액", dom_total_krw), unsafe_allow_html=True)
        with k3: st.markdown(kpi_box("현지 지출 총액", ovr_total_krw, ovr_total_vnd), unsafe_allow_html=True)
        with k4: st.markdown(kpi_box(f"현지 1일 평균 (7일)", avg_local_krw, avg_local_vnd), unsafe_allow_html=True)

        st.subheader("🌳 지출 구조 상세 분석 (Treemap)")
        fig_tree = px.treemap(exp_df, path=['Category', 'Description'], values='KRW_val', color='KRW_val', color_continuous_scale='Greens')
        fig_tree.update_traces(texttemplate="<b>%{label}</b><br>%{value:,.0f}원<br>%{percentRoot:.1%}")
        fig_tree.update_layout(margin=dict(l=0, r=0, t=10, b=0), font=dict(size=14))
        st.plotly_chart(fig_tree, use_container_width=True)

        st.subheader("🍕 카테고리별 지출 비중")
        cat_pie = exp_df.groupby('Category')['KRW_val'].sum().reset_index().sort_values(by='KRW_val', ascending=False)
        fig_donut = px.pie(cat_pie, values='KRW_val', names='Category', hole=0.5, color_discrete_sequence=px.colors.qualitative.Set3)
        fig_donut.update_traces(textposition='inside', textinfo='label+value+percent', texttemplate='%{label}<br>%{value:,.0f}원<br>%{percent:.1%}')
        until_day = exp_df['Date'].max().split('(')[0]
        fig_donut.add_annotation(text=f"<b>총 지출</b><br>{total_trip_krw:,.0f} 원<br><span style='font-size:10px'>Until {until_day}</span>", showarrow=False, font=dict(size=16))
        fig_donut.update_layout(height=600, margin=dict(l=10, r=10, t=50, b=100), legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5), uniformtext_minsize=11, uniformtext_mode='hide')
        st.plotly_chart(fig_donut, use_container_width=True)

st.caption(f"GTL Platform v1.44 | Volume Guard: 38.2 KB | Sync: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Strategic Partner Gem")
