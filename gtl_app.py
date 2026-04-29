# [Project: Global Travel Ledger (GTL) / Version: v26.04.29.008]
# [Strategic Partner: Gem / Core: Reactive FIFO Engine & Volume Guard]
# [Status: Total System Restoration - ZERO OMISSION - 28.8 KB]

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date as dt_date
from streamlit_gsheets import GSheetsConnection
import time

# --- SECTION 1: Configuration & Global Setup ---
# [Status: Maintained and Explicitly Expanded]
st.set_page_config(page_title="여행 가계부 (GTL Platform)", layout="wide")

# 모바일 가독성 및 고밀도 KPI 레이아웃 전용 CSS 스타일
st.markdown("""
    <style>
    .kpi-box {
        background-color: #1e2130;
        padding: 15px;
        border-radius: 12px;
        border-left: 6px solid #00FF00;
        margin-bottom: 15px;
        min-height: 115px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.3);
    }
    .kpi-title { font-size: 14px; color: #bbbbbb; margin-bottom: 8px; font-weight: 500; }
    .kpi-value-krw { font-size: 24px; font-weight: bold; color: #ffffff; line-height: 1.1; }
    .kpi-value-vnd { font-size: 16px; color: #00FF00; margin-top: 6px; font-family: 'Courier New', monospace; }
    /* 데이터 에디터 및 테이블 스타일 */
    div[data-testid="stTable"] { border: 1px solid #333; border-radius: 8px; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { 
        background-color: #161a24; 
        border-radius: 5px 5px 0 0; 
        padding: 10px 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# [Safeguard] AttributeError 방지를 위한 최상단 전역 변수 즉시 초기화
if 'rate_names' not in st.session_state:
    st.session_state.rate_names = ['부산 1차', '머니박스', '트래블 2차', '에어텔', '기타']
if 'rates' not in st.session_state:
    st.session_state.rates = [0.0561, 0.0610, 0.0564, 0.0560, 0.0561]
if 'last_cat_idx' not in st.session_state: 
    st.session_state.last_cat_idx = 0
if 'last_rate_idx' not in st.session_state: 
    st.session_state.last_rate_idx = 0

# 글로벌 통화 및 지폐 정의 (플랫폼 표준)
TRAVEL_CURRENCY = "VND"
BASE_CURRENCY = "KRW"
BILLS = [500000, 200000, 100000, 50000, 20000, 10000, 5000, 2000, 1000]

# 카테고리 헌법 및 필터 정의
EXPENSE_CATS = ["식사", "간식", "Grab", "VinBus", "마사지", "팁", "마트", "선물", "투어", "입장료", "통신", "수수료", "택시", "지하철", "항공권", "호텔", "보험", "입국", "출국"]
SURVIVAL_CATS = ["식사", "간식", "Grab", "VinBus", "마사지", "팁"]
FIXED_COST_CATS = ["항공권", "호텔", "보험"]
DOMESTIC_CATS = ["항공권", "호텔", "보험", "지하철", "택시"]
TRANSFER_CATS = ["충전", "ATM출금", "보증금", "환전", "직접환전"]

# 구글 시트 데이터 스키마 (H열까지 핵심, I~K열 Audit)
COLUMNS = ['Date', 'Category', 'Description', 'Currency', 'Amount', 'PaymentMethod', 'IsExpense', 'AppliedRate']
AUDIT_COLUMNS = ['Cum_Budget_KRW', 'Cum_Card_VND', 'Cum_Cash_VND']

# --- SECTION 2: [Module A] Data Engine (Multi-Sheet Sync & Running Audit) ---
# [Status: Restored Defensive Loading]
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    """구글 시트에서 데이터를 로드하고 정규화합니다."""
    try:
        # 캐시 없이 직접 읽기로 데이터 무결성 확보
        df = conn.read(worksheet="ledger", ttl="0s")
        
        if df is None or df.empty: 
            return pd.DataFrame(columns=COLUMNS + AUDIT_COLUMNS)
        
        # 유령 행 제거 및 컬럼 리인덱싱
        df = df.dropna(subset=['Date', 'Category'], how='any')
        df = df.reindex(columns=COLUMNS + AUDIT_COLUMNS)
        
        # 데이터 타입 강제 변환
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
        df['AppliedRate'] = pd.to_numeric(df['AppliedRate'], errors='coerce').fillna(1.0)
        df['IsExpense'] = pd.to_numeric(df['IsExpense'], errors='coerce').fillna(0).astype(int)
        
        return df
        
    except Exception as e:
        if "429" in str(e): 
            st.error("🚨 구글 서버 API 요청 한도 초과. 1분 뒤에 새로고침하세요.")
        else:
            st.error(f"데이터 로드 실패: {e}")
        return pd.DataFrame(columns=COLUMNS + AUDIT_COLUMNS)

def calculate_running_totals(df):
    """구글 시트 누계 컬럼 I, J, K를 명시적으로 계산합니다."""
    temp_df = df.copy()
    c_budget = 0.0
    c_card = 0.0
    c_cash = 0.0
    
    for i, row in temp_df.iterrows():
        qty, rate, desc, cat = row['Amount'], row['AppliedRate'], str(row['Description']), row['Category']
        method, curr, is_exp = row['PaymentMethod'], row['Currency'], row['IsExpense']
        
        # 1. 예산(원화계좌 지출) 누계 계산
        if method == '원화계좌':
            if curr == 'KRW': c_budget += qty
            else: c_budget += qty * rate
            
        # 2. 자산 흐름 (카드/현금 지갑) 계산
        if cat in ['충전', '환전', '입금', '직접환전']:
            if "카드VND" in desc: c_card += qty
            elif "지폐VND" in desc: c_cash += qty
        elif cat == 'ATM출금':
            c_card -= qty
            c_cash += qty
        elif is_exp == 1 and curr == TRAVEL_CURRENCY:
            if "트래블로그" in method: c_card -= qty
            elif "현금" in method: c_cash -= qty
        elif cat == '보증금':
            c_cash -= qty

        # 행 단위 결과 기입
        temp_df.at[i, 'Cum_Budget_KRW'] = round(c_budget, 0)
        temp_df.at[i, 'Cum_Card_VND'] = round(c_card, 0)
        temp_df.at[i, 'Cum_Cash_VND'] = round(c_cash, 0)
        
    return temp_df

def save_data(df, metrics=None):
    """Cloud 동기화 및 요약 탭 실시간 업데이트"""
    if df is None or len(df) == 0:
        st.error("🚨 시스템 보호막: 빈 데이터를 저장할 수 없습니다.")
        return False
        
    with st.status("전략적 데이터 안전 잠금 및 동기화 중...", expanded=False):
        try:
            # 저장 직전 누계 데이터 자동 생성
            df_audit = calculate_running_totals(df)
            conn.update(worksheet="ledger", data=df_audit)
            
            # Summary 탭 업데이트 (GSheets 직접 확인용)
            if metrics:
                summary_data = pd.DataFrame({
                    "항목": ["🏦 예산(KRW)", "💳 카드(VND)", "💵 현금(VND)", "🕒 업데이트 시각"],
                    "수치": [f"{metrics[0]:,.0f} 원", f"{metrics[1]:,.0f} ₫", f"{metrics[2]:,.0f} ₫", datetime.now().strftime("%H:%M")]
                })
                try: conn.update(worksheet="summary", data=summary_data)
                except: pass
            
            st.cache_data.clear() # 캐시 강제 무력화
            return True
        except Exception as e:
            st.error(f"Cloud 저장 실패: {e}")
            return False

@st.cache_data(ttl=0)
def load_cash_count():
    """현금 카운터 저장 상태 로드"""
    try:
        df = conn.read(worksheet="cash_count", ttl="0s")
        if df is not None and not df.empty:
            return dict(zip(df['Bill'].astype(int), df['Count'].astype(int)))
        return {b: 0 for b in BILLS}
    except:
        return {b: 0 for b in BILLS}

def save_cash_count(counts_dict):
    """현금 카운터 상태 저장"""
    try:
        df = pd.DataFrame(list(counts_dict.items()), columns=['Bill', 'Count'])
        conn.update(worksheet="cash_count", data=df)
        st.cache_data.clear()
        return True
    except:
        return False

# 초기 데이터 로딩
ledger_df = load_data()
cloud_cash_counts = load_cash_count()

# --- SECTION 3: [Module B] FIFO Inventory & Asset Engine ---
# [Status: Maintained - Core Logic]
def get_inventory_status(df):
    """지갑별 환율 배치를 FIFO로 정밀 추적하여 현재 잔액을 계산합니다."""
    inv = { "트래블로그(VND)": {}, "현금(VND)": {} }
    if df.empty: return inv

    for _, row in df.iterrows():
        qty, rate, cat, desc, method = row['Amount'], row['AppliedRate'], row['Category'], str(row['Description']), row['PaymentMethod']
        
        # 1. 유입
        if cat in ['충전', '환전', '입금', '직접환전']:
            target = "트래블로그(VND)" if "카드VND" in desc else "현금(VND)"
            inv[target][rate] = inv[target].get(rate, 0) + qty
        # 2. ATM출금 (배치 이동)
        elif cat == 'ATM출금':
            temp_qty = qty
            for r in sorted(inv["트래블로그(VND)"].keys()):
                if temp_qty <= 0: break
                take = min(temp_qty, inv["트래블로그(VND)"][r])
                inv["트래블로그(VND)"][r] -= take
                inv["현금(VND)"][r] = inv["현금(VND)"].get(r, 0) + take
                temp_qty -= take
        # 3. 지출 (소진)
        elif row['IsExpense'] == 1 and row['Currency'] == TRAVEL_CURRENCY:
            target = "트래블로그(VND)" if "트래블로그" in method else "현금(VND)"
            temp_qty = qty
            for r in sorted(inv.get(target, {}).keys()):
                if temp_qty <= 0: break
                take = min(temp_qty, inv[target][r]); inv[target][r] -= take; temp_qty -= take
    return inv

current_inventory = get_inventory_status(ledger_df)

# 가중평균환율 산출
swaps_df = ledger_df[(ledger_df['Category'].isin(['충전','환전','입금','직접환전'])) & (ledger_df['Currency'] == TRAVEL_CURRENCY)]
if not swaps_df.empty and swaps_df['Amount'].sum() > 0:
    WAR = (swaps_df['Amount'] * swaps_df['AppliedRate']).sum() / swaps_df['Amount'].sum()
else:
    WAR = 0.0561

def auto_calc_fifo_rate(amount, method):
    """현재 재고 바탕으로 가중평균 환율 자동 도출"""
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
    """지표 통합 계산"""
    if df.empty: return 0.0, 0.0, 0.0
    bank_actions = df[df['PaymentMethod'] == '원화계좌']
    b_total = (bank_actions[bank_actions['Currency'] == 'KRW']['Amount']).sum() + \
              (bank_actions[bank_actions['Currency'] != 'KRW']['Amount'] * bank_actions[bank_actions['Currency'] != 'KRW']['AppliedRate']).sum()
    card_v = sum(current_inventory["트래블로그(VND)"].values())
    cash_v = sum(current_inventory["현금(VND)"].values())
    return b_total, card_v, cash_v

# --- SECTION 4: [Module C] Intelligent Input (📝 입력) ---
# [Status: Modified - FIXED REACTIVE RATE INJECTION]
st.title("🌏 여행 가계부 (GTL v1.26)")
tab_in, tab_his, tab_stats, tab_final = st.tabs(["📝 입력", "🔍 내역 조회", "📊 일일 결산", "🏁 종료 보고서"])

with tab_in:
    mode = st.radio("기록 모드 선택", ["일반 지출", "자산 이동"], horizontal=True, key="mode_radio")
    
    if mode == "일반 지출":
        cat = st.radio("항목 선택", EXPENSE_CATS, index=st.session_state.last_cat_idx, horizontal=True, key="exp_cat")
        st.session_state.last_cat_idx = EXPENSE_CATS.index(cat)
        
        if cat in ["입국", "출국"]:
            st.info(f"✈️ {cat} 일정 메모를 기록합니다.")
            desc = st.text_input("내용", key="exp_desc_diary")
            sel_date = st.date_input("날짜", datetime.now(), key="exp_date_diary")
            if st.button("🚀 일정 기록 완료", use_container_width=True):
                new_row = pd.DataFrame([{'Date': sel_date.strftime("%m/%d(%a)"), 'Category': cat, 'Description': desc, 'Currency': 'KRW', 'Amount': 0, 'PaymentMethod': '원화계좌', 'IsExpense': 1, 'AppliedRate': 1.0}])
                if save_data(pd.concat([ledger_df[COLUMNS], new_row], ignore_index=True)): st.rerun()
        else:
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                curr = st.selectbox("통화", ["VND", "KRW", "USD"], key="exp_curr")
                r_opts = [f"{st.session_state.rate_names[i]} ({st.session_state.rates[i]:.4f})" for i in range(5)]
                sel_r_str = st.selectbox("참조 환율 선택", r_opts, index=st.session_state.last_rate_idx, key="exp_rate_sel")
                st.session_state.last_rate_idx = r_opts.index(sel_r_str); rv = st.session_state.rates[st.session_state.last_rate_idx]
                met = st.selectbox("결제수단", ["현금(VND)", "트래블로그(VND)", "원화계좌"], key="exp_met")
            with col_m2:
                # 동적 금액 포맷팅 (0원 대응)
                if curr in ["VND", "KRW"]: amt = st.number_input("금액", min_value=0, step=1000 if curr=="VND" else 1, format="%d", key="exp_amt_int")
                else: amt = st.number_input("금액", min_value=0.0, step=1.0, format="%.2f", key="exp_amt_float")
                
                # [CORE FIX: Reactive Key Injection]
                # 금액(amt)이나 결제수단(met)이 바뀔 때 위젯을 새로 그려 자동 주입 강제
                if curr == TRAVEL_CURRENCY and amt > 0:
                    calc_rate = auto_calc_fifo_rate(amt, met)
                    st.caption(f"💡 인벤토리 계산 환율: **{calc_rate:.5f}**")
                    # 동적 Key (met+amt)를 사용하여 값의 자동 갱신을 보장함
                    cr_final = st.number_input("확정 환율", value=calc_rate, format="%.5f", key=f"exp_cr_auto_{met}_{amt}")
                else:
                    cr_final = st.number_input("확정 환율", value=(1.0 if curr=="KRW" else rv), format="%.5f", key=f"exp_cr_man_{curr}")
                    
            desc = st.text_input("내용", key="exp_desc"); sel_date = st.date_input("날짜", datetime.now(), key="exp_date")
            if st.button("🚀 지출 기록하기", use_container_width=True):
                if amt < 0: st.warning("음수는 입력 불가합니다.")
                else:
                    new_row = pd.DataFrame([{'Date': sel_date.strftime("%m/%d(%a)"), 'Category': cat, 'Description': desc, 'Currency': curr, 'Amount': amt, 'PaymentMethod': met, 'IsExpense': 1, 'AppliedRate': cr_final}])
                    b_now, card_now, cash_now = calculate_summary_metrics(ledger_df)
                    if save_data(pd.concat([ledger_df[COLUMNS], new_row], ignore_index=True), metrics=[b_now, card_now, cash_now]): st.rerun()
    else:
        st.subheader("🔁 자산 이동")
        ty = st.selectbox("유형", ["직접환전 (원화계좌 -> 지폐VND)", "충전 (원화계좌 -> 카드VND)", "ATM출금 (카드VND -> 지폐VND)"], key="tr_type")
        c1, c2 = st.columns(2)
        with c1:
            t_amt = st.number_input("받은 금액 (VND)", min_value=0, step=1000, format="%d", key="tr_target")
            r_opts_tr = [f"{st.session_state.rate_names[i]} ({st.session_state.rates[i]:.4f})" for i in range(5)]
            sel_r_tr = st.selectbox("적용 환율 프리셋", r_opts_tr, key="tr_rate_preset"); rv_tr = st.session_state.rates[r_opts_tr.index(sel_r_tr)]
            s_cost = st.number_input("소요 원금", min_value=0, value=int(t_amt * rv_tr) if "ATM" not in ty else t_amt, step=1, format="%d", key="tr_source")
        with c2:
            tr_date = st.date_input("이동 날짜", datetime.now(), key="tr_date")
            fee_amt = st.number_input("ATM 수수료 (VND)", min_value=0, step=1000, format="%d", key="tr_fee")
        if st.button("🔄 이동 실행", use_container_width=True):
            rate = s_cost / t_amt if t_amt > 0 else 0
            dest = "카드VND" if "카드" in ty else "지폐VND"
            main_row = pd.DataFrame([{'Date': tr_date.strftime("%m/%d(%a)"), 'Category': ty.split(" ")[0], 'Description': f"{ty.split(' ')[0]} (-> {dest})", 'Currency': "VND", 'Amount': t_amt, 'PaymentMethod': "원화계좌" if "원화계좌" in ty else "트래블로그(VND)", 'IsExpense': 0, 'AppliedRate': rate}])
            final_entry = pd.concat([ledger_df[COLUMNS], main_row], ignore_index=True)
            if fee_amt > 0:
                fee_rate = auto_calc_fifo_rate(fee_amt, "트래블로그(VND)")
                fee_row = pd.DataFrame([{'Date': tr_date.strftime("%m/%d(%a)"), 'Category': "수수료", 'Description': f"{ty.split(' ')[0]} 수수료", 'Currency': "VND", 'Amount': fee_amt, 'PaymentMethod': "트래블로그(VND)", 'IsExpense': 1, 'AppliedRate': fee_rate}])
                final_entry = pd.concat([final_entry, fee_row], ignore_index=True)
            b_now, card_now, cash_now = calculate_summary_metrics(ledger_df); save_data(final_entry, metrics=[b_now, card_now, cash_now]); st.rerun()

# --- SECTION 5: [Sidebar] ---
with st.sidebar:
    st.title("💰 Wallet Status")
    b_val, card_val, cash_val = calculate_summary_metrics(ledger_df)
    st.metric("🏦 인출 총 원화 (예산)", f"{b_val:,.0f} 원")
    st.caption(f"평균 적용 환율: 100₫ = {WAR*100:.2f}원")
    st.divider(); st.metric("💳 카드 VND 잔액", f"{card_val:,.0f} ₫"); st.metric("💵 현금 VND 잔액", f"{cash_val:,.0f} ₫")
    with st.expander("💵 실물 지폐 정산기"):
        total_ph = sum([b * st.number_input(f"{b:,.0f} ₫", min_value=0, step=1, value=int(cloud_cash_counts.get(b,0)), key=f"p_{b}") for b in BILLS])
        if st.button("💾 현금 수량 저장"): save_cash_count({b: st.session_state[f"p_{b}"] for b in BILLS}); st.rerun()
        st.write(f"실물 합계: {total_ph:,.0f} ₫ / 차액: {total_ph - cash_val:,.0f} ₫")
    with st.expander("💱 환율 매니저"):
        for i in range(5):
            st.session_state.rate_names[i] = st.text_input(f"이름 {i+1}", value=st.session_state.rate_names[i], key=f"rn_{i}")
            st.session_state.rates[i] = st.number_input(f"환율 {i+1}", value=st.session_state.rates[i], format="%.4f", key=f"rv_{i}")
    if st.button("🔄 Cloud Refresh", use_container_width=True): st.cache_data.clear(); st.rerun()

# --- SECTION 6: [Module D, E: History & Settlement] ---
with tab_his:
    st.subheader("🔍 내역 조회 및 수정")
    if not ledger_df.empty:
        edited_df = st.data_editor(ledger_df, use_container_width=True, num_rows="dynamic", key="editor_gtl_final")
        col_ed1, col_ed2 = st.columns(2)
        with col_ed1:
            if not ledger_df.equals(edited_df) and st.button("💾 수정사항 저장", type="primary"):
                b_n, card_n, cash_n = calculate_summary_metrics(edited_df); save_data(edited_df[COLUMNS], metrics=[b_n, card_n, cash_n]); st.rerun()
        with col_ed2:
            if st.button("🗑️ 마지막 행 삭제", use_container_width=True):
                if save_data(ledger_df[COLUMNS][:-1]): st.rerun()

with tab_stats:
    if not ledger_df.empty:
        exp_df = ledger_df[ledger_df['IsExpense'] == 1].copy()
        if not exp_df.empty:
            exp_df['KRW_val'] = exp_df.apply(lambda r: r['Amount'] if r['Currency'] == 'KRW' else r['Amount'] * WAR, axis=1)
            exp_df['VND_val'] = exp_df.apply(lambda r: r['Amount'] if r['Currency'] == 'VND' else r['Amount'] / WAR if WAR>0 else 0, axis=1)
            exp_df['IsSurvival'] = exp_df['Category'].apply(lambda x: 1 if x in SURVIVAL_CATS else 0)

            # 1. FIFO 현황판 [Dan's Strategic View]
            st.subheader("📦 환율별 재고 현황 (FIFO)")
            for wallet, batches in current_inventory.items():
                active = {r: q for r, q in batches.items() if q > 0}
                if active:
                    st.write(f"**{wallet}**")
                    st.table([{"환율": f"{r:.4f}", "잔액": f"{q:,.0f} ₫", "원화가치": f"{r*q:,.0f} 원"} for r, q in active.items()])

            # 2. 요약 및 정산표
            st.subheader("🏁 여행 경제 요약")
            c1, c2 = st.columns(2)
            with c1:
                dom_df = exp_df[((exp_df['Currency'] == 'KRW') & (exp_df['PaymentMethod'] == '원화계좌')) & (~exp_df['Category'].isin(['입국','출국']))]
                st.info("🇰🇷 국내 지출"); st.metric("총액", f"{dom_df['KRW_val'].sum():,.0f} 원")
                with st.expander("세부 내역"):
                    dg = dom_df.groupby('Category').agg({'KRW_val':'sum', 'Date':'count'}).sort_values(by='KRW_val', ascending=False)
                    for cat, row in dg.iterrows(): st.write(f"- {cat}({int(row['Date'])}회): {row['KRW_val']:,.0f} 원")
            with c2:
                ovr_df = exp_df[~((exp_df['Currency'] == 'KRW') & (exp_df['PaymentMethod'] == '원화계좌'))]
                st.success("🇻🇳 해외 지출"); st.metric("총액", f"{ovr_df['KRW_val'].sum():,.0f} 원")
                with st.expander("해외 세부 내역 (내림차순)"):
                    og = ovr_df.groupby('Category').agg({'VND_val':'sum', 'Date':'count'}).sort_values(by='VND_val', ascending=False)
                    for cat, row in og.iterrows(): st.write(f"- {cat}({int(row['Date'])}회): {row['VND_val']:,.0f} ₫")

            st.divider(); daily_set = exp_df.groupby('Date').agg({'KRW_val': 'sum', 'VND_val': 'sum'}).reset_index()
            surv_only = exp_df[exp_df['IsSurvival'] == 1].groupby('Date').agg({'KRW_val': 'sum', 'VND_val': 'sum'}).reset_index().rename(columns={'KRW_val': 'S_KRW', 'VND_val': 'S_VND'})
            daily_table = pd.merge(daily_set, surv_only, on='Date', how='left').fillna(0)
            st.table(daily_table.rename(columns={'Date':'날짜','KRW_val':'총(원)','VND_val':'총(동)','S_KRW':'일상(원)','S_VND':'일상(동)'}).style.format({c: '{:,.0f}' for c in ['총(원)','총(동)','일상(원)','일상(동)']}))

# --- SECTION 7: [Module G: Final Strategic Report] ---
with tab_final:
    if not ledger_df.empty and not exp_df.empty:
        overseas_active = exp_df[~((exp_df['Currency'] == 'KRW') & (exp_df['PaymentMethod'] == '원화계좌'))]
        unique_days = len(overseas_active['Date'].unique())
        total_trip_krw = exp_df['KRW_val'].sum(); total_trip_vnd = exp_df['VND_val'].sum()
        dom_total_krw = exp_df[exp_df['Category'].isin(DOMESTIC_CATS)]['KRW_val'].sum()
        ovr_total_krw = total_trip_krw - dom_total_krw; ovr_total_vnd = exp_df[~exp_df['Category'].isin(DOMESTIC_CATS)]['VND_val'].sum()
        local_survival_krw = exp_df[(exp_df['IsSurvival'] == 1) & (~exp_df['Category'].isin(FIXED_COST_CATS))]['KRW_val'].sum()
        
        # [Added] KPI Box with Multi-Line HTML
        def kpi_box(title, krw, vnd=None):
            vnd_str = f"<div class='kpi-value-vnd'>({vnd:,.0f} ₫)</div>" if vnd is not None else ""
            return f"<div class='kpi-box'><div class='kpi-title'>{title}</div><div class='kpi-value-krw'>{krw:,.0f} 원</div>{vnd_str}</div>"

        st.header("🏁 푸꾸옥 여행 최종 전략 리포트")
        k1, k2, k3, k4 = st.columns(4)
        with k1: st.markdown(kpi_box("여행 최종 총 지출", total_trip_krw, total_trip_vnd), unsafe_allow_html=True)
        with k2: st.markdown(kpi_box("국내 지출 총액", dom_total_krw), unsafe_allow_html=True)
        with k3: st.markdown(kpi_box("현지 지출 총액", ovr_total_krw, ovr_total_vnd), unsafe_allow_html=True)
        avg_v = (local_survival_krw / WAR) / unique_days if unique_days > 0 and WAR > 0 else 0
        with k4: st.markdown(kpi_box(f"현지 1일 평균 ({unique_days}일)", local_survival_krw/unique_days if unique_days > 0 else 0, avg_v), unsafe_allow_html=True)

        st.subheader("🌳 지출 구조 상세 분석 (Treemap)")
        fig_tree = px.treemap(exp_df, path=['Category', 'Description'], values='KRW_val', color='KRW_val', color_continuous_scale='Greens')
        fig_tree.update_traces(texttemplate="<b>%{label}</b><br>%{value:,.0f}원<br>%{percentRoot:.1%}")
        fig_tree.update_layout(margin=dict(l=0, r=0, t=10, b=0), font=dict(size=14))
        st.plotly_chart(fig_tree, use_container_width=True)

        st.subheader("🍕 카테고리별 지출 비중")
        cat_pie = exp_df.groupby('Category')['KRW_val'].sum().reset_index().sort_values(by='KRW_val', ascending=False)
        fig_donut = px.pie(cat_pie, values='KRW_val', names='Category', hole=0.5, color_discrete_sequence=px.colors.qualitative.Set3)
        fig_donut.update_traces(textposition='inside', textinfo='label+value+percent', texttemplate='%{label}<br>%{value:,.0f}원<br>%{percent:.1%}')
        fig_donut.add_annotation(text=f"<b>총 지출</b><br>{total_trip_krw:,.0f} 원", showarrow=False, font=dict(size=16))
        fig_donut.update_layout(height=600, margin=dict(l=10, r=10, t=50, b=100), legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5), uniformtext_minsize=11, uniformtext_mode='hide')
        st.plotly_chart(fig_donut, use_container_width=True)

st.caption(f"GTL Platform v1.26 | Volume Guard: 28.8 KB | Sync: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Strategic Partner Gem")
