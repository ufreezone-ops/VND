# [Project: Global Travel Ledger (GTL) / Version: v26.04.29.001]
# [Strategic Partner: Gem / Core: Full-Stack FIFO Platform with Running Audit]
# [Status: Total System Restoration - NO COMPRESSION]

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date as dt_date
from streamlit_gsheets import GSheetsConnection
import time

# --- SECTION 1: Configuration & Global Setup ---
st.set_page_config(page_title="여행 가계부 (GTL Platform)", layout="wide")

# AttributeError 방지를 위한 전역 변수 강제 초기화
if 'rate_names' not in st.session_state:
    st.session_state.rate_names = ['부산 1차', '머니박스', '트래블 2차', 'Slot 4', 'Slot 5']
if 'rates' not in st.session_state:
    st.session_state.rates = [0.0561, 0.0610, 0.0564, 0.0561, 0.0561]
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

# --- SECTION 2: [Module A] Data Engine (Robust Sync & Running Audit) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # 캐시 없이 직접 읽기로 데이터 무결성 확보
        df = conn.read(worksheet="ledger", ttl="0s")
        if df is None or df.empty: 
            return pd.DataFrame(columns=COLUMNS + AUDIT_COLUMNS)
        
        # 데이터 정규화 (유실 방지)
        df = df.reindex(columns=COLUMNS + AUDIT_COLUMNS)
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
        df['AppliedRate'] = pd.to_numeric(df['AppliedRate'], errors='coerce').fillna(1.0)
        df['IsExpense'] = pd.to_numeric(df['IsExpense'], errors='coerce').fillna(0).astype(int)
        return df
    except Exception as e:
        if "429" in str(e):
            st.error("🚨 구글 API 한도 초과. 1분 뒤에 다시 시도하세요.")
        else:
            st.error(f"데이터 로드 실패: {e}")
        return pd.DataFrame(columns=COLUMNS + AUDIT_COLUMNS)

def calculate_running_totals(df):
    """[Restored] 구글 시트의 I, J, K열 누계를 명시적인 루프로 계산합니다."""
    temp_df = df.copy()
    c_budget = 0.0
    c_card = 0.0
    c_cash = 0.0
    
    for i, row in temp_df.iterrows():
        qty = row['Amount']
        rate = row['AppliedRate']
        desc = str(row['Description'])
        cat = row['Category']
        method = row['PaymentMethod']
        curr = row['Currency']
        is_exp = row['IsExpense']

        # 1. 예산(원화계좌 지출) 누계
        if method == '원화계좌':
            if curr == 'KRW':
                c_budget += qty
            else:
                c_budget += qty * rate
        
        # 2. 자산 흐름 추적 (Inflow/Outflow)
        # 입금류
        if cat in ['충전', '환전', '입금', '직접환전']:
            if "카드VND" in desc:
                c_card += qty
            elif "지폐VND" in desc:
                c_cash += qty
        # ATM 출금 (카드 -> 현금 이동)
        elif cat == 'ATM출금':
            c_card -= qty
            c_cash += qty
        # 순수 지출 (IsExpense == 1)
        elif is_exp == 1 and curr == TRAVEL_CURRENCY:
            if "트래블로그" in method:
                c_card -= qty
            elif "현금" in method:
                c_cash -= qty
        # 보증금 (현금에서만 차감)
        elif cat == '보증금':
            c_cash -= qty

        # 행 단위 누계 기입
        temp_df.at[i, 'Cum_Budget_KRW'] = round(c_budget, 0)
        temp_df.at[i, 'Cum_Card_VND'] = round(c_card, 0)
        temp_df.at[i, 'Cum_Cash_VND'] = round(c_cash, 0)
        
    return temp_df

def save_data(df, metrics=None):
    if df is None or len(df) == 0:
        st.error("🚨 시스템 보호: 빈 데이터를 저장할 수 없습니다.")
        return False
    with st.status("Audit 데이터 생성 및 Cloud 동기화 중...", expanded=False):
        try:
            # 저장 전 누계 자동 계산
            df_with_audit = calculate_running_totals(df)
            conn.update(worksheet="ledger", data=df_with_audit)
            
            # Summary 탭 업데이트 (있는 경우)
            if metrics:
                summary_data = pd.DataFrame({
                    "항목": ["🏦 예산 (KRW)", "💳 카드 (VND)", "💵 현금 (VND)", "🕒 업데이트"],
                    "수치": [f"{metrics[0]:,.0f}", f"{metrics[1]:,.0f}", f"{metrics[2]:,.0f}", datetime.now().strftime("%H:%M")]
                })
                try:
                    conn.update(worksheet="summary", data=summary_data)
                except: pass
            
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

# --- SECTION 3: [Module B] FIFO Inventory Engine ---
def get_inventory_status(df):
    """[Restored] 지갑별 환율 배치를 FIFO로 정밀 추적합니다."""
    inv = { "트래블로그(VND)": {}, "현금(VND)": {} }
    if df.empty: return inv

    for _, row in df.iterrows():
        qty = row['Amount']
        rate = row['AppliedRate']
        desc = str(row['Description'])
        cat = row['Category']
        method = row['PaymentMethod']
        
        # 유입
        if cat in ['충전', '환전', '입금', '직접환전']:
            target = "트래블로그(VND)" if "카드VND" in desc else "현금(VND)"
            inv[target][rate] = inv[target].get(rate, 0) + qty
        # ATM출금 (배치 전이)
        elif cat == 'ATM출금':
            temp_qty = qty
            for r in sorted(inv["트래블로그(VND)"].keys()):
                if temp_qty <= 0: break
                take = min(temp_qty, inv["트래블로그(VND)"][r])
                inv["트래블로그(VND)"][r] -= take
                inv["현금(VND)"][r] = inv["현금(VND)"].get(r, 0) + take
                temp_qty -= take
        # 지출 (소진)
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
    """인벤토리 재고를 기반으로 가중평균 환율을 자동 도출합니다."""
    target = "트래블로그(VND)" if "트래블로그" in method else "현금(VND)"
    available = {r: q for r, q in current_inventory.get(target, {}).items() if q > 0}
    
    if not available:
        return 0.0561 # 데이터 없을 시 기본 환율
        
    total_cost_krw = 0
    remaining = amount
    
    for r in sorted(available.keys()):
        if remaining <= 0: break
        take = min(remaining, available[r])
        total_cost_krw += take * r
        remaining -= take
        
    # 재고 초과 지출 시 마지막 환율 적용
    if remaining > 0:
        total_cost_krw += remaining * max(available.keys())
        
    return total_cost_krw / amount if amount > 0 else 0

def calculate_summary_metrics(df):
    """[Restored] 사이드바와 요약용 지표 계산"""
    if df.empty: return 0.0, 0.0, 0.0
    # 예산: 누계 컬럼의 마지막 값 활용 (데이터가 있다면)
    b_total = df['Cum_Budget_KRW'].iloc[-1] if not df.empty else 0
    card_v = sum(current_inventory["트래블로그(VND)"].values())
    cash_v = sum(current_inventory["현금(VND)"].values())
    return b_total, card_v, cash_v

# --- SECTION 4: [Module C] Intelligent Input (📝 입력) ---
st.title("🌏 여행 가계부 (FIFO Platform)")
tab_in, tab_his, tab_rpt, tab_final = st.tabs(["📝 입력", "🔍 내역 조회", "📊 지출 분석", "🏁 종료 보고서"])

with tab_in:
    mode = st.radio("기록 모드 선택", ["일반 지출", "자산 이동"], horizontal=True, key="in_mode")
    
    if mode == "일반 지출":
        # [Modified] Dan의 순서: 항목 -> 통화 -> 환율 -> 결제수단 -> 금액 -> 내용
        cat = st.radio("항목 선택", EXPENSE_CATS, index=st.session_state.last_cat_idx, horizontal=True, key="exp_cat")
        st.session_state.last_cat_idx = EXPENSE_CATS.index(cat)
        
        col1, col2 = st.columns(2)
        with col1:
            curr = st.selectbox("통화", ["VND", "KRW", "USD"], key="exp_curr")
            
            # 환율 프리셋
            r_opts = [f"{st.session_state.rate_names[i]} ({st.session_state.rates[i]:.4f})" for i in range(5)]
            sel_r_str = st.selectbox("참조 환율 선택", r_opts, index=st.session_state.last_rate_idx, key="exp_rate_sel")
            st.session_state.last_rate_idx = r_opts.index(sel_r_str)
            rv = st.session_state.rates[st.session_state.last_rate_idx]
            
            met = st.selectbox("결제수단", ["현금(VND)", "트래블로그(VND)", "원화계좌"], key="exp_method")
            
        with col2:
            # [Added] 동적 포맷팅: VND/KRW는 정수, USD는 소수점 지원
            if curr in ["VND", "KRW"]:
                amt = st.number_input("금액 (Amount)", min_value=0, step=1000, format="%d", key="exp_amt_int")
            else:
                amt = st.number_input("금액 (Amount)", min_value=0.0, step=1.0, format="%.2f", key="exp_amt_float")
            
            # [Logic] FIFO 자동 환율 제시
            if curr == TRAVEL_CURRENCY and amt > 0:
                calc_rate = auto_calc_fifo_rate(amt, met)
                st.caption(f"💡 인벤토리 기반 권장 환율: **{calc_rate:.5f}**")
                final_rate = st.number_input("확정 환율", value=calc_rate, format="%.5f", key="exp_rate_final")
            else:
                default_r = 1.0 if curr == BASE_CURRENCY else rv
                final_rate = st.number_input("확정 환율", value=default_r, format="%.5f", key="exp_rate_man")

        desc = st.text_input("내용 (메모)", key="exp_desc")
        s_date = st.date_input("날짜", datetime.now(), key="exp_date")

        if st.button("🚀 지출 기록하기", use_container_width=True):
            if amt < 0: st.warning("음수는 입력할 수 없습니다.")
            else:
                new_row = pd.DataFrame([{'Date': s_date.strftime("%m/%d(%a)"), 'Category': cat, 'Description': desc, 'Currency': curr, 'Amount': amt, 'PaymentMethod': met, 'IsExpense': 1, 'AppliedRate': final_rate}])
                # 지표와 함께 저장
                b_now, card_now, cash_now = calculate_summary_metrics(ledger_df)
                if save_data(pd.concat([ledger_df[COLUMNS], new_row], ignore_index=True), metrics=[b_now, card_now, cash_now]):
                    st.toast("기록 완료! ✅"); time.sleep(0.5); st.rerun()

    else:
        # [Module C - 자산 이동]
        st.subheader("🔁 자산 이동 및 환전 (ATM 수수료 포함)")
        ty = st.selectbox("이동 유형", ["직접환전 (원화계좌 -> 지폐VND)", "충전 (원화계좌 -> 카드VND)", "ATM출금 (카드VND -> 지폐VND)"], key="tr_type")
        
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            t_amt = st.number_input("받은 금액 (VND)", min_value=0, step=1000, format="%d", key="tr_target")
            source_label = "소요 비용 (VND)" if "ATM" in ty else "지불 비용 (KRW)"
            s_cost = st.number_input(source_label, min_value=0, step=1000, format="%d", key="tr_source")
        with col_t2:
            tr_date = st.date_input("이동 날짜", datetime.now(), key="tr_date")
            fee_amt = st.number_input("ATM 수수료 (VND)", min_value=0, step=1000, format="%d", key="tr_fee") if "ATM" in ty else 0
            
        if st.button("🔄 이동 실행", use_container_width=True):
            rate = s_cost / t_amt if t_amt > 0 else 0
            dest = "카드VND" if "카드" in ty else "지폐VND"
            new_desc = f"{ty.split(' ')[0]} (-> {dest})"
            
            # [Added] ATM 수수료 자동 행 분리 로직
            main_row = pd.DataFrame([{'Date': tr_date.strftime("%m/%d(%a)"), 'Category': ty.split(" ")[0], 'Description': new_desc, 'Currency': "VND", 'Amount': t_amt, 'PaymentMethod': "원화계좌" if "원화계좌" in ty else "트래블로그(VND)", 'IsExpense': 0, 'AppliedRate': rate}])
            
            if fee_amt > 0:
                fee_rate = auto_calc_fifo_rate(fee_amt, "트래블로그(VND)")
                fee_row = pd.DataFrame([{'Date': tr_date.strftime("%m/%d(%a)"), 'Category': "수수료", 'Description': "ATM 출금 수수료", 'Currency': "VND", 'Amount': fee_amt, 'PaymentMethod': "트래블로그(VND)", 'IsExpense': 1, 'AppliedRate': fee_rate}])
                final_entry = pd.concat([ledger_df[COLUMNS], main_row, fee_row], ignore_index=True)
            else:
                final_entry = pd.concat([ledger_df[COLUMNS], main_row], ignore_index=True)
            
            b_now, card_now, cash_now = calculate_summary_metrics(ledger_df)
            if save_data(final_entry, metrics=[b_now, card_now, cash_now]):
                st.toast("이동 완료! 🔁"); time.sleep(0.5); st.rerun()

# --- SECTION 5: [Sidebar & Module F: Cash Tool] ---
with st.sidebar:
    st.title("💰 Wallet Status")
    b_val, card_val, cash_val = calculate_summary_metrics(ledger_df)
    
    st.metric("🏦 인출한 총 원화 (예산)", f"{b_val:,.0f} 원")
    st.caption(f"기준 환율: 100₫ = {(b_val / (card_val + cash_val + 1)*100):.2f}원 (실효추정)")
    st.divider()
    st.metric("💳 카드 VND 잔액", f"{card_val:,.0f} ₫")
    st.metric("💵 현금 VND 잔액", f"{cash_val:,.0f} ₫")
    
    with st.expander("💵 실물 지폐 정산기", expanded=False):
        curr_p_counts = {}
        total_ph = 0
        for b in BILLS:
            n = st.number_input(f"{b:,.0f} ₫", min_value=0, step=1, value=int(cloud_cash_counts.get(b,0)), key=f"p_{b}")
            curr_p_counts[b] = n
            total_ph += b * n
        if st.button("💾 현금 수량 저장", use_container_width=True):
            save_cash_count(curr_p_counts); time.sleep(0.5); st.rerun()
        st.write(f"실물 합계: {total_ph:,.0f} ₫")
        st.caption(f"장부 차액: {total_ph - cash_val:,.0f} ₫")

    with st.expander("💱 환율 매니저 (Presets)", expanded=False):
        for i in range(5):
            st.session_state.rate_names[i] = st.text_input(f"이름 {i+1}", value=st.session_state.rate_names[i], key=f"rn_{i}")
            st.session_state.rates[i] = st.number_input(f"환율 {i+1}", value=st.session_state.rates[i], format="%.4f", key=f"rv_{i}")
            
    if st.button("🔄 Cloud Refresh", use_container_width=True): st.cache_data.clear(); st.rerun()

# --- SECTION 6: [Module D, E, G: History & Analytics] ---
with tab_his:
    st.subheader("🔍 내역 조회 및 수정")
    if not ledger_df.empty:
        # [Module E] 데이터 에디터 통합
        edited_df = st.data_editor(ledger_df, use_container_width=True, num_rows="dynamic", key="editor_gtl_final")
        if not ledger_df.equals(edited_df) and st.button("💾 수정사항 저장", type="primary", key="bulk_save"):
            b_n, card_n, cash_n = calculate_summary_metrics(edited_df)
            if save_data(edited_df[COLUMNS], metrics=[b_n, card_n, cash_n]): st.rerun()
        if st.button("🗑️ 마지막 행 삭제", key="del_btn"):
            if save_data(ledger_df[COLUMNS][:-1]): st.rerun()
    else: st.info("기록된 데이터가 없습니다.")

with tab_rpt:
    if not ledger_df.empty:
        # [Module D] 분석 엔진 복구
        exp_df = ledger_df[ledger_df['IsExpense'] == 1].copy()
        if not exp_df.empty:
            # 1:1 대칭 정산 계산
            exp_df['KRW_val'] = exp_df.apply(lambda r: r['Amount'] if r['Currency'] == 'KRW' else r['Amount'] * r['AppliedRate'], axis=1)
            exp_df['VND_val'] = exp_df.apply(lambda r: r['Amount'] if r['Currency'] == 'VND' else r['Amount'] / r['AppliedRate'] if r['AppliedRate']>0 else 0, axis=1)
            exp_df['IsSurvival'] = exp_df['Category'].apply(lambda x: 1 if x in SURVIVAL_CATS else 0)

            # [Added] 인벤토리 현황 시각화
            st.subheader("📦 환율별 재고 현황 (FIFO)")
            for wallet, batches in current_inventory.items():
                active = {r: q for r, q in batches.items() if q > 0}
                if active:
                    st.write(f"**{wallet}**")
                    st.table([{"환율": f"{r:.4f}", "잔액": f"{q:,.0f} ₫", "원화가치": f"{r*q:,.0f} 원"} for r, q in active.items()])

            # 일자별 정산표
            st.divider(); st.subheader("🗓️ 일자별 정산")
            daily_set = exp_df.groupby('Date').agg({'KRW_val': 'sum', 'VND_val': 'sum'}).reset_index()
            surv_only = exp_df[exp_df['IsSurvival'] == 1].groupby('Date').agg({'KRW_val': 'sum', 'VND_val': 'sum'}).reset_index().rename(columns={'KRW_val': 'S_KRW', 'VND_val': 'S_VND'})
            daily_table = pd.merge(daily_set, surv_only, on='Date', how='left').fillna(0)
            
            st.table(daily_table.rename(columns={'Date':'날짜','KRW_val':'총(원)','VND_val':'총(동)','S_KRW':'일상(원)','S_VND':'일상(동)'}).style.format('{:,.0f}'))

            # 이중 막대 차트
            c_mode = st.radio("표시 통화", ["원화(KRW)", "동화(VND)"], horizontal=True, key="st_curr")
            y_s, y_t = ('S_KRW', 'KRW_val') if "원화" in c_mode else ('S_VND', 'VND_val')
            fig = go.Figure()
            fig.add_trace(go.Bar(x=daily_table['Date'], y=daily_table[y_s], name='일상경비', marker_color='#00FF00', text=daily_table[y_s], texttemplate='%{text:,.0f}'))
            fig.add_trace(go.Bar(x=daily_table['Date'], y=daily_table[y_t].apply(lambda x: x if x > 0 else None), name='전체지출', marker_color='#FF00FF'))
            fig.update_layout(barmode='group', margin=dict(l=0, r=0, t=30, b=0), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig, use_container_width=True)

with tab_final:
    if not ledger_df.empty and not exp_df.empty:
        # [Module G] 종료 보고서 복구
        st.header("🏁 최종 전략 리포트")
        # 1. 트리맵 (Greens)
        st.subheader("🌳 지출 구조 분석 (Treemap)")
        fig_tree = px.treemap(exp_df, path=['Category', 'Description'], values='KRW_val', color='KRW_val', color_continuous_scale='Greens')
        fig_tree.update_traces(texttemplate="<b>%{label}</b><br>%{value:,.0f}원")
        st.plotly_chart(fig_tree, use_container_width=True)
        
        st.divider()
        cf1, cf2, cf3 = st.columns(3)
        total_trip = exp_df['KRW_val'].sum()
        with cf1: st.metric("최종 총 지출", f"{total_trip:,.0f} 원")
        with cf2: st.metric("1일 평균 지출", f"{(total_trip/8):,.0f} 원")
        with cf3:
            cash_sum = exp_df[exp_df['PaymentMethod'].str.contains('현금')]['KRW_val'].sum()
            st.metric("현금 지출 비중", f"{(cash_sum/total_trip*100):.1f} %")
            
        # 2. 도넛 차트
        st.subheader("🍕 카테고리별 비중")
        cat_pie = exp_df.groupby('Category')['KRW_val'].sum().reset_index()
        fig_donut = px.pie(cat_pie, values='KRW_val', names='Category', hole=0.5, color_discrete_sequence=px.colors.qualitative.Set3)
        fig_donut.add_annotation(text=f"<b>총 지출</b><br>{total_trip:,.0f} 원", showarrow=False, font=dict(size=16))
        fig_donut.update_layout(height=500, margin=dict(l=10, r=10, t=50, b=50), legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5))
        st.plotly_chart(fig_donut, use_container_width=True)

st.caption(f"GTL Platform v1.13 | Sync: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Strategic Partner Gem")
