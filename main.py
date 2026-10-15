
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --------------------------------------------------
# 1. 페이지 기본 설정
# --------------------------------------------------
st.set_page_config(
    page_title="동네별 인구 피라미드",
    page_icon="🏘️",
    layout="wide",
)

# --------------------------------------------------
# 2. 따뜻한 크림색 테마 설정
# --------------------------------------------------
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(180deg, #fff5df 0%, #fffaf1 100%);
    }

    h1, h2, h3 {
        color: #70452a;
    }

    div[data-testid="stMetric"] {
        background-color: #fffdf8;
        border: 1px solid #ead8bc;
        padding: 16px;
        border-radius: 15px;
    }

    div[data-testid="stSelectbox"] label {
        color: #70452a;
        font-weight: bold;
    }

    .intro {
        color: #795b43;
        font-size: 17px;
        line-height: 1.8;
    }
</style>
""", unsafe_allow_html=True)

st.title("🏘️ 동네별 인구 피라미드")
st.markdown(
    '<p class="intro">'
    '우리 동네에는 연령대별로 몇 명이 살고 있을까요?<br>'
    '지역을 선택해 남녀 인구 분포를 비교해 보세요.'
    '</p>',
    unsafe_allow_html=True,
)

# --------------------------------------------------
# 3. 인구 데이터 불러오기
# --------------------------------------------------
DATA_URL = (
    "https://raw.githubusercontent.com/first2022-cyber/"
    "contents/main/population_ts_yearly_gender.zip"
)

@st.cache_data
def load_data():
    # pandas는 ZIP 주소를 직접 읽을 수 있어요.
    df = pd.read_csv(DATA_URL, compression="zip")

    # 열 이름 앞뒤에 불필요한 공백이 있으면 제거해요.
    df.columns = df.columns.astype(str).str.strip()

    # 연도 열을 숫자로 바꿔요.
    df["연도"] = pd.to_numeric(df["연도"], errors="coerce")

    # 가장 최신 연도만 남겨요.
    latest_year = int(df["연도"].max())
    df = df[df["연도"] == latest_year].copy()

    # 지역 이름이 비어 있는 행을 정리해요.
    for col in ["시도", "시군구", "동"]:
        df[col] = df[col].fillna("").astype(str).str.strip()

    # 연령별 인구 열을 숫자로 바꾸고, 빈 값은 0으로 처리해요.
    age_cols = [
        f"{gender}_{age}세"
        for age in range(100)
        for gender in ["남", "여"]
    ]
    age_cols += ["남_100세 이상", "여_100세 이상"]

    for col in age_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(",", "", regex=False),
                errors="coerce",
            ).fillna(0)

    return df, latest_year


try:
    with st.spinner("인구 데이터를 불러오는 중이에요..."):
        df, latest_year = load_data()

except Exception as e:
    st.error("데이터를 불러오지 못했어요.")
    st.info(
        "인터넷 연결과 CSV 주소를 확인해 주세요. "
        "잠시 후 다시 실행해 볼 수도 있어요."
    )
    st.exception(e)
    st.stop()

if df.empty:
    st.error("최신 연도의 인구 데이터가 없어요.")
    st.stop()

st.caption(f"📅 분석 기준 연도: {latest_year}년")

# --------------------------------------------------
# 4. 시도 → 시군구 → 동 순서로 선택하기
# --------------------------------------------------
st.subheader("📍 지역 선택")

col1, col2, col3 = st.columns(3)

# 첫 번째: 시도 선택
sido_list = sorted(df["시도"].unique().tolist())

with col1:
    selected_sido = st.selectbox(
        "① 시도",
        sido_list,
        key="sido",
    )

# 선택한 시도에 해당하는 데이터만 골라요.
df_sido = df[df["시도"] == selected_sido].copy()

# 두 번째: 시군구 선택
sigungu_list = sorted(df_sido["시군구"].unique().tolist())

with col2:
    selected_sigungu = st.selectbox(
        "② 시군구",
        sigungu_list,
        key="sigungu",
    )

# 선택한 시군구에 해당하는 데이터만 골라요.
df_sigungu = df_sido[
    df_sido["시군구"] == selected_sigungu
].copy()

# 세 번째: 동 선택
dong_list = sorted(df_sigungu["동"].unique().tolist())

with col3:
    selected_dong = st.selectbox(
        "③ 읍·면·동",
        dong_list,
        key="dong",
    )

# 세 가지 조건을 모두 만족하는 지역의 데이터예요.
selected_data = df_sigungu[
    df_sigungu["동"] == selected_dong
]

# --------------------------------------------------
# 5. 연령별 남녀 인구 계산하기
# --------------------------------------------------

# 0세부터 99세까지, 마지막은 100세 이상이에요.
ages = [f"{age}세" for age in range(100)] + ["100세 이상"]

male_columns = [
    f"남_{age}세" for age in range(100)
] + ["남_100세 이상"]

female_columns = [
    f"여_{age}세" for age in range(100)
] + ["여_100세 이상"]

# 일부 연령 열이 없는 경우에도 오류가 나지 않게 처리해요.
missing_columns = [
    col for col in male_columns + female_columns
    if col not in selected_data.columns
]

if missing_columns:
    st.error(
        "데이터에서 다음 열을 찾을 수 없어요: "
        + ", ".join(missing_columns[:10])
    )
    st.stop()

if selected_data.empty:
    st.warning("선택한 지역의 데이터가 없어요.")
    st.stop()

# 같은 지역에 여러 행이 있으면 연령별 인구를 합산해요.
male_population = (
    selected_data[male_columns]
    .sum(axis=0)
    .to_numpy(dtype=float)
)

female_population = (
    selected_data[female_columns]
    .sum(axis=0)
    .to_numpy(dtype=float)
)

# 남성은 왼쪽으로 표시하기 위해 음수로 바꿔요.
male_left = -male_population

# --------------------------------------------------
# 6. 주요 인구 지표 표시하기
# --------------------------------------------------
total_male = int(male_population.sum())
total_female = int(female_population.sum())
total_population = total_male + total_female

m1, m2, m3 = st.columns(3)

m1.metric("전체 인구", f"{total_population:,}명")
m2.metric("남성 인구", f"{total_male:,}명")
m3.metric("여성 인구", f"{total_female:,}명")

# --------------------------------------------------
# 7. 인구 피라미드 그리기
# --------------------------------------------------
fig = go.Figure()

# 남성 막대: 음수이므로 왼쪽으로 뻗어요.
fig.add_trace(
    go.Bar(
        y=ages,
        x=male_left,
        name="남성",
        orientation="h",
        marker_color="#6B9AC4",
        hovertemplate=(
            "나이: %{y}<br>"
            "남성 인구: %{customdata:,}명"
            "<extra></extra>"
        ),
        customdata=male_population,
    )
)

# 여성 막대: 양수이므로 오른쪽으로 뻗어요.
fig.add_trace(
    go.Bar(
        y=ages,
        x=female_population,
        name="여성",
        orientation="h",
        marker_color="#E99A9A",
        hovertemplate=(
            "나이: %{y}<br>"
            "여성 인구: %{x:,}명"
            "<extra></extra>"
        ),
    )
)

# 남성의 음수 축 눈금도 양수 인구처럼 보이게 만들어요.
max_population = max(
    float(male_population.max()),
    float(female_population.max()),
    1.0,
)
axis_limit = max_population * 1.15

tick_step = max(1, int(np.ceil(axis_limit / 5)))
tick_values_positive = list(
    range(0, int(axis_limit) + tick_step, tick_step)
)

# 양쪽에 대칭인 눈금을 만들어요.
tick_values = sorted(
    set([-v for v in tick_values_positive] + tick_values_positive)
)
tick_text = [f"{abs(v):,}" for v in tick_values]

fig.update_layout(
    title={
        "text": (
            f"{selected_sido} {selected_sigungu} "
            f"{selected_dong} 인구 피라미드 ({latest_year}년)"
        ),
        "x": 0.5,
        "xanchor": "center",
    },
    barmode="overlay",
    bargap=0.12,
    height=1500,
    paper_bgcolor="#fffaf1",
    plot_bgcolor="#fffaf1",
    font=dict(
        family="Arial, sans-serif",
        size=12,
        color="#624632",
    ),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.01,
        xanchor="center",
        x=0.5,
    ),
    xaxis=dict(
        title="인구수 (명)",
        tickmode="array",
        tickvals=tick_values,
        ticktext=tick_text,
        range=[-axis_limit, axis_limit],
        zeroline=True,
        zerolinecolor="#8D735E",
        zerolinewidth=2,
        gridcolor="#EADCCB",
    ),
    yaxis=dict(
        title="나이",
        # 나이 라벨을 0세부터 100세 이상까지 직접 고정해요.
        categoryorder="array",
        categoryarray=ages,
        # 자동으로 값이나 이름을 정렬하지 않아요.
        tickmode="array",
        tickvals=ages,
        ticktext=ages,
        # 축 전체를 뒤집지 않고 순서를 그대로 사용해요.
        autorange=True,
        gridcolor="#F1E5D7",
    ),
    margin=dict(l=90, r=40, t=100, b=70),
)

st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------
# 8. 결과 해석 안내
# --------------------------------------------------
st.subheader("🔎 그래프 읽는 방법")

st.markdown("""
- **왼쪽 파란색:** 남성 인구
- **오른쪽 분홍색:** 여성 인구
- **가운데 세로선:** 인구가 0명인 기준선
- **아래쪽:** 0세
- **위쪽:** 100세 이상

막대에 마우스를 올리면 해당 나이의 인구수를 확인할 수 있어요.
""")

# --------------------------------------------------
# 9. 선택한 지역의 연령별 자료 표
# --------------------------------------------------
with st.expander("📋 연령별 인구 표 보기"):
    result_table = pd.DataFrame({
        "나이": ages,
        "남성 인구": male_population.astype(int),
        "여성 인구": female_population.astype(int),
    })
    result_table["전체 인구"] = (
        result_table["남성 인구"] + result_table["여성 인구"]
    )

    st.dataframe(
        result_table,
        use_container_width=True,
        hide_index=True,
    )

st.caption("자료 출처: first2022-cyber/contents 인구 데이터")
