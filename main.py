missing_columns = [
    col for col in male_columns + female_columns if col not in selected_data.columns
]
if missing_columns:
    st.error("필요한 연령별 인구 열이 없어요: " + ", ".join(missing_columns[:10]))
    st.stop()

male_population = selected_data[male_columns].sum(axis=0).to_numpy(dtype=float)
female_population = selected_data[female_columns].sum(axis=0).to_numpy(dtype=float)
total_by_age = male_population + female_population

total_male = int(male_population.sum())
total_female = int(female_population.sum())
total_population = total_male + total_female
elderly_population = int(total_by_age[65:].sum())
child_population = int(total_by_age[:15].sum())

# 연령별 인구로 평균연령을 근사 계산해요. 100세 이상은 100세로 간주해요.
age_numbers = np.array(list(range(100)) + [100], dtype=float)
if total_population > 0:
    average_age = float(np.dot(total_by_age, age_numbers) / total_population)
    aging_rate = elderly_population / total_population * 100
else:
    average_age = 0.0
    aging_rate = 0.0

st.subheader("📊 한눈에 보는 인구 지표")
m1, m2, m3 = st.columns(3)
with m1:
    st.metric("👥 총인구", f"{total_population:,}명")
with m2:
    st.metric("🎂 평균연령", f"{average_age:.1f}세")
with m3:
    st.metric("🧓 고령화율 (65세 이상)", f"{aging_rate:.1f}%")

if aging_rate > 20:
    st.markdown(
        '<div class="warning-note">⚠️ 주의: 고령화율이 20%를 넘어요. '
        '65세 이상 인구 비율이 높은 지역이에요.</div>',
        unsafe_allow_html=True,
    )

fig = go.Figure()
fig.add_trace(go.Bar(
    y=ages, x=-male_population, name="남성", orientation="h",
    marker_color="#6B9AC4", customdata=male_population,
    hovertemplate="나이: %{y}<br>남성 인구: %{customdata:,.0f}명<extra></extra>",
))
fig.add_trace(go.Bar(
    y=ages, x=female_population, name="여성", orientation="h",
    marker_color="#E99A9A",
    hovertemplate="나이: %{y}<br>여성 인구: %{x:,.0f}명<extra></extra>",
))

max_population = max(float(male_population.max()), float(female_population.max()), 1.0)
axis_limit = max_population * 1.15
tick_step = max(1, int(np.ceil(axis_limit / 5)))
tick_values_positive = list(range(0, int(axis_limit) + tick_step, tick_step))
tick_values = sorted(set([-v for v in tick_values_positive] + tick_values_positive))

fig.update_layout(
    title={
        "text": f"{selected_sido} {selected_sigungu} {selected_dong} 인구 피라미드 ({latest_year}년)",
        "x": 0.5, "xanchor": "center",
    },
    barmode="overlay", bargap=0.12, height=1500,
    paper_bgcolor="#fffaf1", plot_bgcolor="#fffaf1",
    font=dict(family="Arial, sans-serif", size=12, color="#624632"),
    legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="center", x=0.5),
    xaxis=dict(
        title="인구수 (명)", tickmode="array", tickvals=tick_values,
        ticktext=[f"{abs(v):,}" for v in tick_values],
        range=[-axis_limit, axis_limit], zeroline=True,
        zerolinecolor="#8D735E", zerolinewidth=2, gridcolor="#EADCCB",
    ),
    yaxis=dict(
        title="나이",
        # 0세부터 100세 이상까지 직접 지정해 0세가 아래쪽에 오게 해요.
        categoryorder="array", categoryarray=ages,
        tickmode="array", tickvals=ages, ticktext=ages,
        autorange=True, gridcolor="#F1E5D7",
    ),
    margin=dict(l=90, r=40, t=100, b=70),
)
st.plotly_chart(fig, use_container_width=True)

st.subheader("💡 우리 동네 인구 특징")
if total_population == 0:
    insight = "인구 데이터가 없어 아이와 어르신의 비율을 비교하기 어려워요."
else:
    child_rate = child_population / total_population * 100
    elderly_rate = elderly_population / total_population * 100
    if child_rate > elderly_rate:
        insight = (
            f"이 동네는 0~14세 비율({child_rate:.1f}%)이 65세 이상 비율"
            f"({elderly_rate:.1f}%)보다 높아, 상대적으로 아이의 비중이 큰 편이에요."
        )
    elif elderly_rate > child_rate:
        insight = (
            f"이 동네는 65세 이상 비율({elderly_rate:.1f}%)이 0~14세 비율"
            f"({child_rate:.1f}%)보다 높아, 상대적으로 어르신의 비중이 큰 편이에요."
        )
    else:
        insight = f"이 동네는 0~14세와 65세 이상 비율이 모두 {child_rate:.1f}%로 같아요."

st.markdown(f'<div class="insight-note">{insight}</div>', unsafe_allow_html=True)
st.caption(
    "참고: 평균연령은 연령별 인구로 계산한 근사치이며, "
    "'100세 이상' 인구는 계산상 100세로 간주했어요."
)

with st.expander("📋 연령별 인구 표 보기"):
    result_table = pd.DataFrame({
        "나이": ages,
        "남성 인구": male_population.astype(int),
        "여성 인구": female_population.astype(int),
    })
    result_table["전체 인구"] = result_table["남성 인구"] + result_table["여성 인구"]
    st.dataframe(result_table, use_container_width=True, hide_index=True)

st.caption("자료 출처: first2022-cyber/contents 인구 데이터")
