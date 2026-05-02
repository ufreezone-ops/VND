#[Project: Feelfree Travel Ledger / Version: v26.05.02.004]
#[Strategic Partner: Gem / Core: Force Rate Re-Induction Engine]
#[Status: Phase 2 Deployed (ImgBB API Receipt Linking) & Sidebar UX - 51.2 KB]

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, timezone, date as dt_date
from streamlit_gsheets import GSheetsConnection
import time
import requests
import base64

# --- SECTION 1: Configuration & Global Setup ---
st.set_page_config(
    page_title="Feelfree: 여행 가계부", 
    page_icon="🌏", 
    layout="wide",
    initial_sidebar_state="expanded"
)

TZ_KST = timezone(timedelta(hours=9))
TZ_ICT = timezone(timedelta(hours=7))

CORE_COLUMNS =['Date', 'Category', 'Description', 'Currency', 'Amount', 'PaymentMethod', 'Receipt_URL']
SYSTEM_LOGIC_COLUMNS =['IsExpense', 'AppliedRate', 'Cum_Budget_KRW', 'Cum_Card_VND', 'Cum_Cash_VND', 'Note']
FINAL_COLUMNS = CORE_COLUMNS + SYSTEM_LOGIC_COLUMNS

#[Added] ImgBB API Key
IMGBB_API_KEY = "81181bf834001b6191aaa90fa772c6f9"

#[Modified] 업데이트 로그
VERSION = "v26.05.02.004"
UPDATE_LOG_TEXT = """* `[Added]` Phase 2 영수증 링킹 완료: ImgBB API 통신 모듈을 탑재하여, 스마트폰으로 촬영한 영수증이 클라우드에 자동 업로드되고 장부에 URL로 맵핑됨.
* `[Modified]` 사이드바 UX: 현장 사용성을 고려하여 현금(Cash) 잔액을 카드(Card) 잔액보다 상단으로 배치."""

conn = st.connection("gsheets", type=GSheetsConnection)

def auto_update_log_to_gsheets():
    try:
        log_df = conn.read(worksheet="version_log", ttl="0s")
        if log_df is None or log_df.empty: log_df = pd.DataFrame(columns=["Version", "Date", "Log"])
    except: log_df = pd.DataFrame(columns=["Version", "Date", "Log"])
    
    if VERSION not in log_df['Version'].values:
        new_log = pd.DataFrame([{"Version": VERSION, "Date": datetime.now(TZ_KST).strftime("%Y-%m-%d %H:%M:%S"), "Log": UPDATE_LOG_TEXT}])
        log_df = pd.concat([new_log, log_df], ignore_index=True)
        try: conn.update(worksheet="version_log", data=log_df)
        except: pass

auto_update_log_to_gsheets()

st.markdown("""
    <script>
        var link = document.createElement('link');
        link.rel = 'apple-touch-icon';
        link.href = 'https://img.icons8.com/color/512/globe--v1.png';
        document.getElementsByTagName('head')[0].appendChild(link);
    </script>
    <style>
    .main { background-color: #0e1117; }
    .kpi-box { background-color: #1e2130; padding: 20px; border-radius: 15px; border-left: 8px solid #00FF00; margin-bottom: 20px; min-height: 130px; box-shadow: 4px 6px 15px rgba(0,0,0,0.5); }
    .kpi-title { font-size: 15px; color: #cccccc; margin-bottom: 10px; font-weight: 600; }
    .kpi-value-krw { font-size: 26px; font-weight: bold; color: #ffffff; line-height: 1.1; }
    .kpi-value-vnd { font-size: 18px; color: #00FF00; margin-top: 8px; font-family: 'Courier New', monospace; font-weight: 500; }
    div[data-testid="stTable"] { border: 1px solid #444; border-radius: 10px; overflow: hidden; }
    .stTabs[data-baseweb="tab-list"] { gap: 15px; padding-bottom: 10px; }
    .stTabs[data-baseweb="tab"] { background-color: #1c1f2b; border-radius: 8px 8px 0 0; padding: 12px 25px; color: #ffffff; }
    .stTabs[aria-selected="true"] { background-color: #00FF00 !important; color: #000000 !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

if 'current_tz' not in st.session_state: st.session_state.current_tz = TZ_KST
if 'shared_date' not in st.session_state: st.session_state.shared_date = datetime.now(st.session_state.current_tz).date()
if 'last_cat_idx' not in st.session_state: st.session_state.last_cat_idx = 0

TRAVEL_CURRENCY = "VND"
BASE_CURRENCY = "KRW"
BILLS =[500000, 200000, 100000, 50000, 20000, 10000, 5000, 2000, 1000]

EXPENSE_CATS =["식사", "간식", "Grab", "VinBus", "마사지", "팁", "마트", "선물", "투어", "입장료", "통신", "수수료", "택시", "지하철", "항공권", "호텔", "보험"]
SURVIVAL_CATS =["간식", "Grab", "VinBus", "마사지", "팁", "식사"]
FIXED_COST_CATS =["항공권", "호텔", "보험"]
DOMESTIC_CATS =["항공권", "호텔", "보험", "지하철", "택시"]
TRANSFER_CATS =["충전", "ATM출금", "보증금", "환전", "직접환전"]

# --- SECTION 2:[Module A] Data Engine ---
def load_data():
    try:
        df = conn.read(worksheet="ledger", ttl="0s")
        if df is None or df.empty: return pd.DataFrame(columns=FINAL_COLUMNS)
        
        if 'Receipt_URL' not in df.columns:
            df['Receipt_URL'] = ""
            
        df = df.dropna(subset=['Date', 'Category'], how='any')
        df = df.reindex(columns=FINAL_COLUMNS)
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
        df['AppliedRate'] = pd.to_numeric(df['AppliedRate'], errors='coerce').fillna(0.0)
        df['IsExpense'] = pd.to_numeric(df['IsExpense'], errors='coerce').fillna(0).astype(int)
        df['Note'] = df['Note'].fillna("").astype(str)
        df['Receipt_URL'] = df['Receipt_URL'].fillna("").astype(str)
        return df
    except Exception: return pd.DataFrame(columns=FINAL_COLUMNS)

def recalculate_entire_ledger(df):
    temp_df = df.copy()
    temp_df = temp_df.sort_values(by='Date', kind='mergesort', ignore_index=True)
    
    for i, row in temp_df.iterrows():
        if row['Category'] in EXPENSE_CATS: temp_df.at[i, 'AppliedRate'] = 0.0
        temp_df.at[i, 'Note'] = ""; temp_df.at[i, 'Cum_Budget_KRW'] = 0.0; temp_df.at[i, 'Cum_Card_VND'] = 0.0; temp_df.at[i, 'Cum_Cash_VND'] = 0.0
    
    inv_batches = { "트래블로그(VND)":[], "현금(VND)":[], "트래블로그(USD)":[], "현금(USD)":[] }
    c_budget = 0.0
    
    for i, row in temp_df.iterrows():
        qty, curr = row['Amount'], row['Currency']
        cat, method, desc = row['Category'], row['PaymentMethod'], str(row['Description'])
        is_exp = 1 if cat in EXPENSE_CATS and cat != '환불' else 0
        temp_df.at[i, 'IsExpense'] = is_exp
        
        rate = temp_df.at[i, 'AppliedRate'] 
        
        if cat in['충전', '환전', '입금', '직접환전', '환불']:
            if curr == 'VND' and (pd.isna(rate) or rate <= 0.0 or rate == 1.0): rate = 0.0561
            elif curr == 'USD' and (pd.isna(rate) or rate <= 0.0 or rate == 1.0): rate = 1350.0

            target = f"트래블로그({curr})" if ("카드" in desc or "카드" in method or "트래블로그" in method) else f"현금({curr})"
            if curr != 'KRW': inv_batches[target].append({'rate': rate, 'qty': qty})
            
            if method == '원화계좌':
                if cat == '환불': c_budget -= qty if curr == 'KRW' else qty * rate
                else: c_budget += qty if curr == 'KRW' else qty * rate
        
        elif cat == 'ATM출금':
            temp_qty = qty; total_inherited_krw = 0.0
            target_from = f"트래블로그({curr})"; target_to = f"현금({curr})"
            for batch in inv_batches[target_from]:
                if temp_qty <= 0: break
                if batch['qty'] <= 0: continue
                take = min(temp_qty, batch['qty']); batch['qty'] -= take
                inv_batches[target_to].append({'rate': batch['rate'], 'qty': take}); total_inherited_krw += take * batch['rate']; temp_qty -= take
            if qty > 0: rate = total_inherited_krw / qty if total_inherited_krw > 0 else 0.0561
        
        elif is_exp == 1 and curr in[TRAVEL_CURRENCY, 'USD']:
            target = f"트래블로그({curr})" if ("트래블로그" in str(method) or "카드" in str(method)) else f"현금({curr})"
            temp_qty = qty; total_cost_krw = 0.0; decomposed =[]
            for batch in inv_batches[target]:
                if temp_qty <= 0: break
                if batch['qty'] <= 0: continue
                take = min(temp_qty, batch['qty']); batch['qty'] -= take; temp_qty -= take
                total_cost_krw += take * batch['rate']
                decomposed.append(f"{take:,.0f}@{batch['rate']:.4f}")
            if qty > 0:
                rate = total_cost_krw / qty
                if decomposed: temp_df.at[i, 'Note'] = "Decomposed: " + " + ".join(decomposed)
            else: rate = 0.0
        
        elif method == '원화계좌' and is_exp == 1:
            c_budget += qty; rate = 1.0

        temp_df.at[i, 'AppliedRate'] = rate
        temp_df.at[i, 'Cum_Budget_KRW'] = round(c_budget, 0)
        temp_df.at[i, 'Cum_Card_VND'] = round(sum([b['qty'] for b in inv_batches["트래블로그(VND)"]]), 0)
        temp_df.at[i, 'Cum_Cash_VND'] = round(sum([b['qty'] for b in inv_batches["현금(VND)"]]), 0)
        
    return temp_df

def save_data(df, metrics=None):
    if df is None or len(df) == 0: return False
    with st.status("데이터 정합성 복구 및 클라우드 동기화 중...", expanded=False):
        try:
            final_df = recalculate_entire_ledger(df)
            conn.update(worksheet="ledger", data=final_df.reindex(columns=FINAL_COLUMNS))
            if metrics:
                current_time_str = datetime.now(st.session_state.current_tz).strftime("%H:%M")
                summary = pd.DataFrame({"항목":["🏦 예산(KRW)", "💳 카드(VND)", "💵 현금(VND)", "🕒 업데이트"], "수치": [f"{metrics[0]:,.0f}", f"{metrics[1]:,.0f}", f"{metrics[2]:,.0f}", current_time_str]})
                try: conn.update(worksheet="summary", data=summary)
                except: pass
            st.cache_data.clear(); return True
        except Exception as e:
            st.error(f"Cloud 저장 실패: {e}"); return False

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

# --- SECTION 3:[Module B] URDI Engine ---
def get_inventory_status(df):
    temp_df = df.sort_values(by='Date', kind='mergesort', ignore_index=True) if not df.empty else df
    inv_batches = { "트래블로그(VND)":[], "현금(VND)":[], "트래블로그(USD)":[], "현금(USD)":[] }
    if temp_df.empty: return inv_batches
    for _, row in temp_df.iterrows():
        qty, rate, desc, cat, method, curr = row['Amount'], row['AppliedRate'], str(row['Description']), row['Category'], row['PaymentMethod'], row['Currency']
        if cat in['충전', '환전', '입금', '직접환전', '환불']:
            target = f"트래블로그({curr})" if ("카드" in desc or "카드" in method or "트래블로그" in method) else f"현금({curr})"
            if curr != 'KRW': inv_batches[target].append({'rate': rate, 'qty': qty, 'initial': qty})
        elif cat == 'ATM출금':
            temp_qty = qty; target_from = f"트래블로그({curr})"; target_to = f"현금({curr})"
            for batch in inv_batches[target_from]:
                if temp_qty <= 0: break
                if batch['qty'] <= 0: continue
                take = min(temp_qty, batch['qty']); batch['qty'] -= take
                inv_batches[target_to].append({'rate': batch['rate'], 'qty': take, 'initial': take}); temp_qty -= take
        elif row['IsExpense'] == 1 and curr in[TRAVEL_CURRENCY, 'USD']:
            target = f"트래블로그({curr})" if ("트래블로그" in str(method) or "카드" in str(method)) else f"현금({curr})"
            temp_qty = qty
            for batch in inv_batches[target]:
                if temp_qty <= 0: break
                if batch['qty'] <= 0: continue
                take = min(temp_qty, batch['qty']); batch['qty'] -= take; temp_qty -= take
    return inv_batches

current_inventory_batches = get_inventory_status(ledger_df)

sw_df_vnd = ledger_df[(ledger_df['Category'].isin(['충전','환전','입금','직접환전'])) & (ledger_df['Currency'] == 'VND')]
WAR_VND = (sw_df_vnd['Amount'] * sw_df_vnd['AppliedRate']).sum() / sw_df_vnd['Amount'].sum() if not sw_df_vnd.empty and sw_df_vnd['Amount'].sum() > 0 else 0.0561

sw_df_usd = ledger_df[(ledger_df['Category'].isin(['충전','환전','입금','직접환전'])) & (ledger_df['Currency'] == 'USD')]
WAR_USD = (sw_df_usd['Amount'] * sw_df_usd['AppliedRate']).sum() / sw_df_usd['Amount'].sum() if not sw_df_usd.empty and sw_df_usd['Amount'].sum() > 0 else 1350.0

def auto_calc_fifo_rate(amount, method, curr="VND"):
    target = f"트래블로그({curr})" if ("트래블로그" in str(method) or "카드" in str(method)) else f"현금({curr})"
    temp_inv = get_inventory_status(ledger_df)
    available_batches =[b for b in temp_inv[target] if b['qty'] > 0]
    if not available_batches: return WAR_USD if curr == 'USD' else WAR_VND
    total_cost_krw, remaining = 0.0, amount
    for batch in available_batches:
        if remaining <= 0: break
        take = min(remaining, batch['qty']); total_cost_krw += take * batch['rate']; remaining -= take
    if remaining > 0: total_cost_krw += remaining * available_batches[-1]['rate']
    return total_cost_krw / amount if amount > 0 else 0

def calculate_summary_metrics(df):
    if df.empty: return 0.0, 0.0, 0.0, 0.0
    temp_df = df.sort_values(by='Date', kind='mergesort', ignore_index=True)
    b_total = temp_df['Cum_Budget_KRW'].iloc[-1] if 'Cum_Budget_KRW' in temp_df.columns else 0
    spent_total = (temp_df[temp_df['IsExpense'] == 1].apply(lambda r: r['Amount'] if r['Currency'] == 'KRW' else r['Amount'] * r['AppliedRate'], axis=1)).sum()
    card_v = sum([b['qty'] for b in current_inventory_batches["트래블로그(VND)"]])
    cash_v = sum([b['qty'] for b in current_inventory_batches["현금(VND)"]])
    return b_total, card_v, cash_v, spent_total

# --- SECTION 5: [Sidebar] ---
with st.sidebar:
    st.title("⚙️ GTL Settings")
    tz_sel = st.radio("📍 현재 위치 (Timezone)",["🇰🇷 한국 (KST)", "🇻🇳 베트남 (ICT)"], horizontal=True, index=0 if "Seoul" in str(st.session_state.current_tz) else 1)
    st.session_state.current_tz = TZ_KST if "한국" in tz_sel else TZ_ICT
    
    st.divider()
    st.title("💰 Wallet Status")
    b_val, card_val, cash_val, spent_val = calculate_summary_metrics(ledger_df)
    
    # [Modified] 현금 지갑을 최상단으로 끌어올림
    st.metric("💵 현금 VND 잔액", f"{cash_val:,.0f} ₫")
    if current_inventory_batches.get("현금(VND)"):
        with st.expander("↳ 현금 환율 배치", expanded=False):
            for b in current_inventory_batches["현금(VND)"]:
                status = f"{b['qty']:,.0f}" if b['qty'] > 0 else "소진"
                st.caption(f"• {b['rate']:.4f}원 : {status}₫")
                
    st.metric("💳 카드 VND 잔액", f"{card_val:,.0f} ₫")
    if current_inventory_batches.get("트래블로그(VND)"):
        with st.expander("↳ 카드 환율 배치", expanded=False):
            for b in current_inventory_batches["트래블로그(VND)"]:
                status = f"{b['qty']:,.0f}" if b['qty'] > 0 else "소진"
                st.caption(f"• {b['rate']:.4f}원 : {status}₫")
    
    usd_card = sum([b['qty'] for b in current_inventory_batches["트래블로그(USD)"]])
    usd_cash = sum([b['qty'] for b in current_inventory_batches["현금(USD)"]])
    if usd_cash > 0 or usd_card > 0:
        st.divider()
        st.metric("💵 현금 USD 잔액", f"${usd_cash:,.2f}")
        if current_inventory_batches.get("현금(USD)"):
            with st.expander("↳ USD 현금 배치", expanded=False):
                for b in current_inventory_batches["현금(USD)"]:
                    status = f"{b['qty']:,.2f}" if b['qty'] > 0 else "소진"
                    st.caption(f"• {b['rate']:.2f}원 : ${status}")
                    
        st.metric("💳 카드 USD 잔액", f"${usd_card:,.2f}")
        if current_inventory_batches.get("트래블로그(USD)"):
            with st.expander("↳ USD 카드 배치", expanded=False):
                for b in current_inventory_batches["트래블로그(USD)"]:
                    status = f"{b['qty']:,.2f}" if b['qty'] > 0 else "소진"
                    st.caption(f"• {b['rate']:.2f}원 : ${status}")

    st.divider()
    st.metric("🏦 총 예산 (환전포함)", f"{b_val:,.0f} 원")
    st.metric("💸 지출총액 (잔액제외)", f"{spent_val:,.0f} 원")
    st.caption(f"VND 가중평균: 100₫ = {WAR_VND*100:.2f}원")

    st.divider()
    with st.expander("💵 실물 지폐 정산기"):
        total_ph = sum([b * st.number_input(f"{b:,.0f} ₫", min_value=0, step=1, value=int(cloud_cash_counts.get(b,0)), key=f"p_{b}") for b in BILLS])
        if st.button("💾 현금 수량 저장"): save_cash_count({b: st.session_state[f"p_{b}"] for b in BILLS}); st.rerun()
        st.write(f"실물 합계: {total_ph:,.0f} ₫ / 차액: {total_ph - cash_val:,.0f} ₫")
    if st.button("🔄 Cloud Refresh", use_container_width=True): st.cache_data.clear(); st.rerun()

# --- SECTION 4:[Module C] Intelligent Input (📝 입력) ---
# [Added] ImgBB 클라우드 전송 함수
def upload_image_to_imgbb(image_file):
    url = "https://api.imgbb.com/1/upload"
    try:
        payload = {
            "key": IMGBB_API_KEY,
            "image": base64.b64encode(image_file.read()).decode("utf-8")
        }
        res = requests.post(url, data=payload)
        if res.status_code == 200:
            return res.json()['data']['url']
    except Exception as e:
        st.error(f"이미지 서버 통신 오류: {e}")
    return ""

st.title("🌏 Feelfree: 글로벌 여행 가계부")
tab_in, tab_his, tab_stats, tab_final = st.tabs(["📝 입력", "🔍 조회", "📊 일일", "🏁 리포트"])

with tab_in:
    mode = st.radio("기록 모드 선택",["일반 지출", "자산 이동", "환불(취소)", "출입국"], horizontal=True, key="mode_radio")
    sel_date = st.date_input("날짜 선택", value=datetime.now(st.session_state.current_tz).date(), key="shared_date_input")
    
    if mode == "일반 지출":
        cat = st.radio("항목 선택", EXPENSE_CATS, index=st.session_state.last_cat_idx, horizontal=True, key="exp_cat")
        st.session_state.last_cat_idx = EXPENSE_CATS.index(cat)
        
        col_desc, col_receipt = st.columns([3, 1])
        with col_desc:
            desc = st.text_input("내용 (상호명 및 상세메모)", placeholder="예: 안바카페 - 소고기버거, 반미정식", key="exp_desc")
        with col_receipt:
            # [Modified] 영수증 사진 업로더 UI (카메라 연동)
            uploaded_file = st.file_uploader("📸 영수증 사진", type=['png', 'jpg', 'jpeg'], key="exp_receipt")
            
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            curr = st.selectbox("통화",["VND", "KRW", "USD"], key="exp_curr")
            met_options =[f"현금({curr})", f"트래블로그({curr})", "원화계좌"] if curr != "KRW" else ["원화계좌"]
            met = st.selectbox("결제수단", met_options, index=0, key="exp_met")
        with col_m2:
            amt = st.number_input("금액", min_value=0, step=1000 if curr=="VND" else 1, format="%d", key="exp_amt_int") if curr in["VND", "KRW"] else st.number_input("금액", min_value=0.0, step=1.0, format="%.2f", key="exp_amt_float")
            if curr in [TRAVEL_CURRENCY, 'USD'] and amt > 0:
                calc_rate = auto_calc_fifo_rate(amt, met, curr)
                st.caption(f"💡 {curr} 인벤토리 계산 환율: **{calc_rate:.5f}**")
                cr_final = st.number_input("확정 환율", value=float(calc_rate), format="%.5f", key=f"exp_cr_auto_{met}_{amt}")
            else: cr_final = st.number_input("확정 환율", value=(1.0 if curr=="KRW" else 0.0561), format="%.5f", key=f"exp_cr_man_{curr}")
            
        if st.button("🚀 지출 기록하기", use_container_width=True):
            # [Added] 사진이 있으면 클라우드로 쏘고 URL을 받아옴
            receipt_url = ""
            if uploaded_file is not None:
                with st.spinner("📸 영수증을 클라우드로 안전하게 전송 중입니다..."):
                    receipt_url = upload_image_to_imgbb(uploaded_file)
                    if receipt_url: st.toast("✅ 영수증 링킹 완료!")
            
            new_row = pd.DataFrame([{'Date': sel_date.strftime("%m/%d(%a)"), 'Category': cat, 'Description': desc, 'Currency': curr, 'Amount': amt, 'PaymentMethod': met, 'IsExpense': 1, 'AppliedRate': cr_final, 'Note': '', 'Receipt_URL': receipt_url}])
            b_now, card_now, cash_now, _ = calculate_summary_metrics(ledger_df)
            if save_data(pd.concat([ledger_df, new_row], ignore_index=True), metrics=[b_now, card_now, cash_now]): st.rerun()

    elif mode == "자산 이동":
        st.subheader("🔁 자산 이동 및 환전")
        ty = st.selectbox("유형",["직접환전 (원화계좌 -> 지폐)", "충전 (원화계좌 -> 카드)", "ATM출금 (카드 -> 지폐)"], key="tr_type")
        c1, c2 = st.columns(2)
        with c1:
            curr_tr = st.selectbox("대상 통화",["VND", "USD"], key="tr_curr")
            t_amt = st.number_input(f"받은 금액 ({curr_tr})", min_value=0, step=1000 if curr_tr=="VND" else 10, format="%d" if curr_tr=="VND" else "%.2f", key="tr_target")
            if "ATM" in ty:
                inherited_r = auto_calc_fifo_rate(t_amt, f"트래블로그({curr_tr})", curr_tr)
                st.info(f"💳 카드 재고 계승 환율: **{inherited_r:.5f}**")
                s_cost = st.number_input("인출 원금 확인", value=float(t_amt), key="tr_source_atm")
                applied_tr_rate = inherited_r
            else:
                s_cost = st.number_input("소요 원금 (KRW)", min_value=0, step=1, format="%d", key="tr_source_swap")
                applied_tr_rate = s_cost / t_amt if t_amt > 0 else 0
        with c2:
            fee_amt = st.number_input(f"ATM 수수료 ({curr_tr})", min_value=0, step=1000 if curr_tr=="VND" else 1, key="tr_fee") if "ATM" in ty else 0
        if st.button("🔄 이동 실행", use_container_width=True):
            dest = f"트래블로그({curr_tr})" if "카드" in ty else f"현금({curr_tr})"
            source = "원화계좌" if "원화계좌" in ty else f"트래블로그({curr_tr})"
            main_row = pd.DataFrame([{'Date': sel_date.strftime("%m/%d(%a)"), 'Category': ty.split(" ")[0], 'Description': f"{ty.split(' ')[0]} (-> {dest})", 'Currency': curr_tr, 'Amount': t_amt, 'PaymentMethod': source, 'IsExpense': 0, 'AppliedRate': applied_tr_rate, 'Note': '', 'Receipt_URL': ''}])
            final_entry = pd.concat([ledger_df, main_row], ignore_index=True)
            if fee_amt > 0:
                fee_rate = auto_calc_fifo_rate(fee_amt, f"트래블로그({curr_tr})", curr_tr)
                fee_row = pd.DataFrame([{'Date': sel_date.strftime("%m/%d(%a)"), 'Category': "수수료", 'Description': f"{ty.split(' ')[0]} 수수료", 'Currency': curr_tr, 'Amount': fee_amt, 'PaymentMethod': f"트래블로그({curr_tr})", 'IsExpense': 1, 'AppliedRate': fee_rate, 'Note': '', 'Receipt_URL': ''}])
                final_entry = pd.concat([final_entry, fee_row], ignore_index=True)
            b_now, card_now, cash_now, _ = calculate_summary_metrics(ledger_df); save_data(final_entry, metrics=[b_now, card_now, cash_now]); st.rerun()

    elif mode == "환불(취소)":
        st.subheader("🔙 결제 취소 및 환불 (Rollback)")
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            r_curr = st.selectbox("취소된 통화",["VND", "KRW", "USD"], key="rf_curr")
            r_met = st.selectbox("돌려받을 지갑",[f"현금({r_curr})", f"트래블로그({r_curr})", "원화계좌"] if r_curr != "KRW" else["원화계좌"], key="rf_met")
            r_amt = st.number_input("환불 금액", min_value=0.0, step=1.0, format="%.2f", key="rf_amt")
        with col_r2:
            r_rate = st.number_input("과거 결제 시 적용됐던 환율", value=(1.0 if r_curr=="KRW" else 0.0561), format="%.5f", key="rf_rate")
            r_desc = st.text_input("취소 내역 메모", placeholder="예: 호텔 보증금 반환", key="rf_desc")
        if st.button("🔙 환불 인벤토리 롤백 실행", use_container_width=True):
            new_row = pd.DataFrame([{'Date': sel_date.strftime("%m/%d(%a)"), 'Category': '환불', 'Description': f"취소: {r_desc}", 'Currency': r_curr, 'Amount': r_amt, 'PaymentMethod': r_met, 'IsExpense': 0, 'AppliedRate': r_rate, 'Note': 'Rollback', 'Receipt_URL': ''}])
            b_now, card_now, cash_now, _ = calculate_summary_metrics(ledger_df)
            if save_data(pd.concat([ledger_df, new_row], ignore_index=True), metrics=[b_now, card_now, cash_now]): st.rerun()

    else:
        st.subheader("✈️ 출입국 일정 기록")
        io_type = st.radio("구분",["출국", "입국"], horizontal=True, key="io_radio")
        desc = st.text_input("내용 (메모)", placeholder="편명, 시간 등", key="io_desc")
        if st.button("🚀 일정 기록 완료", use_container_width=True):
            new_row = pd.DataFrame([{'Date': sel_date.strftime("%m/%d(%a)"), 'Category': io_type, 'Description': desc, 'Currency': 'KRW', 'Amount': 0, 'PaymentMethod': '원화계좌', 'IsExpense': 1, 'AppliedRate': 1.0, 'Note': '', 'Receipt_URL': ''}])
            if save_data(pd.concat([ledger_df, new_row], ignore_index=True)): st.rerun()

# --- SECTION 6:[Module D, E: History & Settlement] ---
with tab_his:
    st.subheader("🔍 내역 조회 및 수정")
    
    search_query = st.text_input("🔎 검색어 입력 (입력 후 Enter를 누르면 모바일 키보드가 내려갑니다)", placeholder="상호명, 메모, 카테고리 등", key="his_search")
    edit_mode = st.toggle("✏️ 장부 직접 수정 모드 켜기", value=False, key="his_edit_toggle")

    if st.button("🔄 장부 전체 다시 계산 (Recalculate All)", use_container_width=True, type="primary"):
        if save_data(ledger_df):
            st.success("데이터 정합성 복구 및 전체 장부 재건축이 완료되었습니다!"); time.sleep(1); st.rerun()
            
    if not ledger_df.empty:
        display_df = ledger_df.sort_values(by='Date', kind='mergesort', ignore_index=True)
        display_df = display_df.reindex(columns=FINAL_COLUMNS)
        
        if search_query.strip():
            mask = (
                display_df['Category'].str.contains(search_query, case=False, na=False) |
                display_df['Description'].str.contains(search_query, case=False, na=False) |
                display_df['Note'].str.contains(search_query, case=False, na=False)
            )
            filtered_df = display_df[mask]
            st.info(f"🔎 '{search_query}' 검색 결과: 총 {len(filtered_df)}건 (데이터 보호를 위해 읽기 전용 모드로 표시됩니다.)")
            st.dataframe(filtered_df, use_container_width=True, column_config={"Receipt_URL": st.column_config.LinkColumn("영수증 📸")})
            
        elif edit_mode:
            st.warning("⚠️ 현재 장부 수정 모드입니다. 셀을 직접 클릭하여 수정할 수 있습니다.")
            edited_df = st.data_editor(display_df, use_container_width=True, num_rows="dynamic", key="editor_gtl_final", column_config={"Receipt_URL": st.column_config.LinkColumn("영수증 📸")})
            if not display_df.equals(edited_df) and st.button("💾 데이터베이스 수정사항 저장", use_container_width=True):
                b_n, card_n, cash_n, _ = calculate_summary_metrics(edited_df)
                if save_data(edited_df, metrics=[b_n, card_n, cash_n]): st.rerun()
                
        else:
            st.dataframe(display_df, use_container_width=True, column_config={"Receipt_URL": st.column_config.LinkColumn("영수증 📸")})

with tab_stats:
    if not ledger_df.empty:
        exp_df = ledger_df.sort_values(by='Date', kind='mergesort', ignore_index=True)
        exp_df = exp_df[exp_df['IsExpense'] == 1].copy()
        
        if not exp_df.empty:
            def get_krw_val(r):
                if r['Currency'] == 'KRW': return r['Amount']
                elif r['Currency'] == 'VND': return r['Amount'] * WAR_VND
                elif r['Currency'] == 'USD': return r['Amount'] * WAR_USD
                return 0
                
            exp_df['KRW_val'] = exp_df.apply(get_krw_val, axis=1)
            exp_df['VND_val'] = exp_df.apply(lambda r: r['Amount'] if r['Currency'] == 'VND' else r['Amount'] / WAR_VND if WAR_VND>0 else 0, axis=1)
            exp_df['IsSurvival'] = exp_df['Category'].apply(lambda x: 1 if x in SURVIVAL_CATS else 0)
            
            st.subheader("🏁 여행 경제 요약")
            c1, c2 = st.columns(2)
            with c1:
                dom_df = exp_df[((exp_df['Currency'] == 'KRW') & (exp_df['PaymentMethod'] == '원화계좌')) & (~exp_df['Category'].isin(['입국','출국']))]
                st.info("🇰🇷 사전 결제 및 고정 지출"); st.metric("총액", f"{dom_df['KRW_val'].sum():,.0f} 원")
                dg = dom_df.groupby('Category').agg({'KRW_val':'sum', 'Date':'count'}).sort_values(by='KRW_val', ascending=False)
                for cat_name, row_data in dg.iterrows(): st.write(f"- {cat_name}({int(row_data['Date'])}회): {row_data['KRW_val']:,.0f} 원")
            with c2:
                ovr_df = exp_df[~((exp_df['Currency'] == 'KRW') & (exp_df['PaymentMethod'] == '원화계좌'))]
                st.success("🇻🇳 현지 체류 지출 (USD 포함)"); st.metric("총액 (원화환산)", f"{ovr_df['KRW_val'].sum():,.0f} 원")
                og = ovr_df.groupby('Category').agg({'KRW_val':'sum', 'Date':'count'}).sort_values(by='KRW_val', ascending=False)
                for cat_name, row_data in og.iterrows(): st.write(f"- {cat_name}({int(row_data['Date'])}회): {row_data['KRW_val']:,.0f} 원")
            
            st.divider(); daily_set = exp_df.groupby('Date').agg({'KRW_val': 'sum', 'VND_val': 'sum'}).reset_index()
            surv_only = exp_df[exp_df['IsSurvival'] == 1].groupby('Date').agg({'KRW_val': 'sum', 'VND_val': 'sum'}).reset_index().rename(columns={'KRW_val': 'S_KRW', 'VND_val': 'S_VND'})
            daily_table = pd.merge(daily_set, surv_only, on='Date', how='left').fillna(0)
            st.table(daily_table.rename(columns={'Date':'날짜','KRW_val':'총(원)','VND_val':'총(동)','S_KRW':'일상(원)','S_VND':'일상(동)'}).style.format({c: '{:,.0f}' for c in['총(원)','총(동)','일상(원)','일상(동)']}))
            
            c_mode = st.radio("표시 통화 선택",["원화(KRW)", "동화(VND)"], horizontal=True, key="st_curr")
            y_col = 'KRW_val' if "원화" in c_mode else 'VND_val'
            color_map = {"식사": "#2E7D32", "간식": "#4CAF50", "Grab": "#00897B", "VinBus": "#00ACC1", "마사지": "#0288D1", "팁": "#03A9F4", "마트": "#E91E63", "선물": "#9C27B0", "투어": "#673AB7", "입장료": "#3F51B5", "통신": "#FF9800", "수수료": "#795548", "항공권": "#D32F2F", "호텔": "#1976D2", "보험": "#FBC02D"}
            
            if not dom_df.empty:
                dom_df['Date_Clean'] = dom_df['Date'].str.split('(').str[0]
                fig1 = px.bar(dom_df, x='Date_Clean', y=y_col, color='Category', title=f"🛫 사전 결제 및 고정 지출", color_discrete_map=color_map)
                fig1.update_layout(barmode='stack', margin=dict(l=5, r=5, t=40, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                st.plotly_chart(fig1, use_container_width=True)
            
            if not ovr_df.empty:
                ovr_df['Date_Clean'] = ovr_df['Date'].str.split('(').str[0]
                fig2 = px.bar(ovr_df, x='Date_Clean', y=y_col, color='Category', title=f"🚶‍♂️ 현지 체류 일일 지출 흐름 ({len(ovr_df['Date'].unique())}일차)", color_discrete_map=color_map)
                fig2.update_layout(barmode='stack', margin=dict(l=5, r=5, t=40, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                st.plotly_chart(fig2, use_container_width=True)

with tab_final:
    if not ledger_df.empty and 'exp_df' in locals() and not exp_df.empty:
        total_trip_krw = exp_df['KRW_val'].sum(); total_trip_vnd = exp_df['VND_val'].sum()
        dom_total_krw = exp_df[exp_df['Category'].isin(DOMESTIC_CATS)]['KRW_val'].sum()
        ovr_total_krw = total_trip_krw - dom_total_krw; ovr_total_vnd = exp_df[~exp_df['Category'].isin(DOMESTIC_CATS)]['VND_val'].sum()
        local_v = exp_df[(exp_df['IsSurvival'] == 1) & (exp_df['Currency'] == 'VND')].copy()
        avg_local_krw = local_v['KRW_val'].sum() / 7 if not local_v.empty else 0
        avg_local_vnd = local_v['VND_val'].sum() / 7 if not local_v.empty else 0
        def kpi_box(title, krw, vnd=None):
            vnd_str = f"<div class='kpi-value-vnd'>({vnd:,.0f} ₫)</div>" if vnd is not None else ""
            return f"<div class='kpi-box'><div class='kpi-title'>{title}</div><div class='kpi-value-krw'>{krw:,.0f} 원</div>{vnd_str}</div>"
        st.header("🏁 글로벌 여행 최종 전략 리포트")
        k1, k2, k3, k4 = st.columns(4)
        with k1: st.markdown(kpi_box("여행 최종 총 지출", total_trip_krw, total_trip_vnd), unsafe_allow_html=True)
        with k2: st.markdown(kpi_box("국내 지출 총액", dom_total_krw), unsafe_allow_html=True)
        with k3: st.markdown(kpi_box("현지 지출 총액", ovr_total_krw, ovr_total_vnd), unsafe_allow_html=True)
        with k4: st.markdown(kpi_box(f"현지 일상/생존 1일 평균 (7일)", avg_local_krw, avg_local_vnd), unsafe_allow_html=True)
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

st.caption(f"GTL Platform v26.05.02.004 | Volume Guard: 51.2 KB | Sync: {datetime.now(st.session_state.current_tz).strftime('%Y-%m-%d %H:%M:%S')} | Strategic Partner Gem")
