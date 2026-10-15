import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
import zipfile
from io import BytesIO

st.set_page_config(page_title="동네별 인구 피라미드", page_icon="🏘️", layout="wide")

st.markdown("""
<style>
.stApp { background: linear-gradient(180deg, #fff5df 0%, #fffaf1 100%); }
h1, h2, h3 { color: #70452a; }
div[data-testid="stMetric"] {
    background-color: #fffdf8; border: 1px solid #ead8bc;
    padding: 16px; border-radius: 15px;
}
div[data-testid="stSelectbox"] label { color: #70452a; font-weight: bold; }
.intro { color: #795b43; font-size: 17px; line-height: 1.8; }
.warning-note {
    background: #fff0d8; border: 1px solid #e4a24c; color: #874b12;
    border-radius: 12px; padding: 10px 14px; margin: 4px 0 12px 0;
    font-weight: 600;
}
.insight-note {
    background: #fffdf8; border-left: 5px solid #d7a66a; color: #70452a;
    border-radius: 8px; padding: 12px 16px; margin-top: 8px; font-size: 16px;
}
</style>
""", unsafe_allow_html=True)

st.title("🏘️ 동네별 인구 피라미드")
st.markdown(
    '<p class="intro">우리 동네에는 연령대별로 몇 명이 살고 있을까요?<br>'
    '지역을 선택해 남녀 인구 분포와 인구 지표를 비교해 보세요.</p>',
    unsafe_allow_html=True,
)

DATA_URL = (
    "https://raw.githubusercontent.com/first2022-cyber/"
    "contents/main/population_ts_yearly_gender.zip"
)

@st.cache_data
def load_data():
    # GitHub에서 ZIP 파일을 내려받아요.
    response = requests.get(DATA_URL, timeout=60)
    response.raise_for_status()

    # ZIP 파일을 메모리에서 열어요.
    try:
        archive = zipfile.ZipFile(BytesIO(response.content))
    except zipfile.BadZipFile as e:
        raise ValueError(
            "다운로드한 파일이 정상적인 ZIP 파일이 아니에요. "
            "데이터 주소와 GitHub 접근 상태를 확인해 주세요."
        ) from e

    # ZIP 안에서 CSV 파일을 찾아요.
    csv_files = [
        name for name in archive.namelist()
        if name.lower().endswith(".csv") and not name.endswith("/")
    ]
    if not csv_files:
        raise ValueError(
            "ZIP 파일 안에서 CSV 파일을 찾지 못했어요. "
            f"ZIP 내부 파일 목록: {archive.namelist()}"
        )

    # ZIP 안에 CSV가 여러 개면 첫 번째 파일을 사용해요.
    csv_bytes = archive.read(csv_files[0])

    # 한글 인코딩을 차례로 시도해요.
    last_error = None
    for encoding in ["utf-8-sig", "cp949", "euc-kr"]:
        try:
            df = pd.read_csv(BytesIO(csv_bytes), encoding=encoding)
            break
        except UnicodeDecodeError as e:
            last_error = e
    else:
        raise ValueError(
            "UTF-8, CP949, EUC-KR 인코딩으로 CSV를 읽지 못했어요."
        ) from last_error

    df.columns = df.columns.astype(str).str.strip()
    if "연도" not in df.columns:
        raise ValueError(f"'연도' 열이 없어요. 읽힌 열: {df.columns.tolist()[:20]}")

    df["연도"] = pd.to_numeric(df["연도"], errors="coerce")
    df = df.dropna(subset=["연도"]).copy()
    if df.empty:
        raise ValueError("연도 데이터가 비어 있어요.")

    latest_year = int(df["연도"].max())
    df = df[df["연도"] == latest_year].copy()

    for col in ["시도", "시군구", "동"]:
        if col not in df.columns:
            raise ValueError(f"'{col}' 열이 없어요. 읽힌 열: {df.columns.tolist()[:20]}")
        df[col] = df[col].fillna("").astype(str).str.strip()

    age_cols = [
        f"{gender}_{age}세"
        for age in range(100)
        for gender in ["남", "여"]
    ] + ["남_100세 이상", "여_100세 이상"]

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
    st.error("인구 데이터를 불러오지 못했어요.")
    st.info("아래 오류 내용을 확인하면 원인을 찾는 데 도움이 돼요.")
    st.code(f"{type(e).__name__}: {e}")
    st.stop()

if df.empty:
    st.error("최신 연도의 인구 데이터가 없어요.")
    st.stop()

st.caption(f"📅 분석 기준 연도: {latest_year}년")
st.subheader("📍 지역 선택")

col1, col2, col3 = st.columns(3)
with col1:
    selected_sido = st.selectbox("① 시도", sorted(df["시도"].unique().tolist()), key="sido")

df_sido = df[df["시도"] == selected_sido].copy()
with col2:
    selected_sigungu = st.selectbox(
        "② 시군구", sorted(df_sido["시군구"].unique().tolist()), key="sigungu"
    )

df_sigungu = df_sido[df_sido["시군구"] == selected_sigungu].copy()
with col3:
    selected_dong = st.selectbox(
        "③ 읍·면·동", sorted(df_sigungu["동"].unique().tolist()), key="dong"
    )

selected_data = df_sigungu[df_sigungu["동"] == selected_dong].copy()
if selected_data.empty:
    st.warning("선택한 지역의 데이터가 없어요.")
    st.stop()

ages = [f"{age}세" for age in range(100)] + ["100세 이상"]
male_columns = [f"남_{age}세" for age in range(100)] + ["남_100세 이상"]
female_columns = [f"여_{age}세" for age in range(100)] + ["여_100세 이상"]

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
