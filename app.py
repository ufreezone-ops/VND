# --- [TAB 3: 일일 결산 및 환전 예측 (Module D: Modified)] ---
with tab_stats:
    if not ledger_df.empty:
        exp_df = ledger_df[ledger_df['IsExpense'] == 1].copy()
        if not exp_df.empty:
            # 앵커 환율 설정
            anchor_rate = st.session_state.rates[0] / 100.0 if st.session_state.rates[0] > 0 else 0.0561
            
            def to_krw_strict(r): return r['Amount'] if r['Currency'] == 'KRW' else r['Amount'] * r['AppliedRate']
            def to_vnd_strict(r): return r['Amount'] if r['Currency'] == 'VND' else r['Amount'] / anchor_rate
            
            exp_df['KRW_val'] = exp_df.apply(to_krw_strict, axis=1)
            exp_df['VND_val'] = exp_df.apply(to_vnd_strict, axis=1)

            # [Added] 일상 지출(Survival) vs 이벤트 지출(Event) 분류
            # Dan의 기준: 지하철(한국), 마트, 선물, 투어 등은 이벤트 지출로 제외
            SURVIVAL_CATS = ["식사", "간식", "택시", "VinBus", "마사지", "팁"]
            exp_df['IsSurvival'] = exp_df['Category'].apply(lambda x: 1 if x in SURVIVAL_CATS else 0)

            daily_set = exp_df.groupby('Date').agg({
                'KRW_val':'sum', 'VND_val':'sum',
                'IsSurvival': 'sum' # 단순히 그룹화를 위해 포함
            }).reset_index()

            # 일상 지출만 따로 집계
            survival_df = exp_df[exp_df['IsSurvival'] == 1].groupby('Date')['VND_val'].sum().reset_index()
            survival_df.rename(columns={'VND_val': 'Survival_VND'}, inplace=True)
            
            # 메인 테이블과 결합
            daily_set = pd.merge(daily_set, survival_df, on='Date', how='left').fillna(0)

            st.subheader("🗓️ 일자별 정산 및 생존 지출")
            st.table(daily_set.rename(columns={
                'Date':'날짜', 'KRW_val':'총 지출(원화)', 'VND_val':'총 지출(동화)', 'Survival_VND':'순수 일상지출(동)'
            }).style.format({'총 지출(원화)': '{:,.0f}', '총 지출(동화)': '{:,.0f}', '순수 일상지출(동)': '{:,.0f}'}))

            # [Added] 환전 예측 엔진
            st.divider()
            st.subheader("🔮 향후 VND 필요량 예측 (환전 전략)")
            
            # 남은 일수 계산 (4/27까지)
            last_date = datetime(2026, 4, 27)
            today = datetime.now()
            remaining_days = (last_date - today).days + 1
            if remaining_days < 0: remaining_days = 0

            # 일평균 일상 지출 (0인 날 제외)
            avg_survival = daily_set[daily_set['Survival_VND'] > 0]['Survival_VND'].mean() if not daily_set.empty else 0
            predicted_need = avg_survival * remaining_days
            
            # 현재 잔액 가져오기 (지폐 + 카드VND)
            _, current_v, current_cash, _ = calculate_quad_balances(ledger_df)
            total_vnd_on_hand = current_v + current_cash
            shortage = predicted_need - total_vnd_on_hand

            c_predict1, c_predict2, c_predict3 = st.columns(3)
            with c_predict1:
                st.metric("일상 일평균 지출", f"{avg_survival:,.0f} ₫")
            with c_predict2:
                st.metric(f"남은 {remaining_days}일 필요량", f"{predicted_need:,.0f} ₫")
            with c_predict3:
                color = "normal" if shortage <= 0 else "inverse"
                st.metric("추가 환전 필요액", f"{max(0, shortage):,.0f} ₫", delta=f"{shortage:,.0f}", delta_color=color)

            if shortage > 0:
                st.warning(f"⚠️ 현재 페이스라면 약 **{shortage:,.0f} ₫**가 부족합니다. 추가 환전을 고려하세요!")
            else:
                st.success(f"✅ 현재 잔액으로 남은 일정을 소화할 수 있을 것으로 보입니다. (여유: {abs(shortage):,.0f} ₫)")

            # [Modified] 차트: 전체 지출 vs 일상 지출 비교
            st.divider()
            st.subheader("📈 지출 추이 분석 (전체 vs 일상)")
            
            base_d = datetime(2026, 4, 20)
            fixed_dates = [(base_d + timedelta(days=x)).strftime("%m/%d(%a)") for x in range(8)]
            chart_base = pd.DataFrame({'Date': fixed_dates})
            chart_final = pd.merge(chart_base, daily_set, on='Date', how='left').fillna(0)
            
            # 시각화 (막대는 전체, 선은 일상지출)
            fig = px.bar(chart_final, x='Date', y='VND_val', text_auto=',.0f', title="전체 지출(Bar) vs 일상 생존지출(Line)",
                         labels={'VND_val': 'VND 지출액'})
            fig.add_scatter(x=chart_final['Date'], y=chart_final['Survival_VND'], name="일상 지출 (Survival)",
                            line=dict(color='yellow', width=4), marker=dict(size=10))
            
            st.plotly_chart(fig, use_container_width=True)
            
        else: st.info("지출 내역이 없습니다.")
    else: st.info("데이터가 없습니다.")
