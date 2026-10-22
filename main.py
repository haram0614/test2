import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.express as px

st.set_page_config(page_title="전국 연도별 인구 지표 단계구분도", layout="wide")

st.title("🗺️ 전국 시군구별 인구 지표 단계구분도 (2015~2026)")

@st.cache_data
def load_and_preprocess_data():
    # 1. 인구 데이터 로드 및 전처리
    pop_url = "https://raw.githubusercontent.com/first2022-cyber/contents//main/population_ts_yearly_gender.zip"
    df = pd.read_csv(pop_url, compression='zip')
    
    # 8자리 동 코드를 5자리 시군구 코드(문자열)로 변환
    df['시군구코드'] = df['코드'].astype(str).str.zfill(8).str[:5]
    
    # 행정구역 개편 코드 보정 (42->51 강원, 45->52 전북, 47720->27720 대구 군위군)
    sido_prefix = df['시군구코드'].str[:2]
    df.loc[sido_prefix == '42', '시군구코드'] = '51' + df['시군구코드'].str[2:]
    df.loc[sido_prefix == '45', '시군구코드'] = '52' + df['시군구코드'].str[2:]
    df.loc[df['시군구코드'] == '47720', '시군구코드'] = '27720'
    
    # 인구 관련 열 분류 ('계_'로 시작)
    total_pop_cols = [col for col in df.columns if col.startswith('계_')]
    
    elderly_cols = []
    child_cols = []
    
    for col in total_pop_cols:
        age_str = col.replace('계_', '').replace('세', '').replace(' 이상', '')
        if age_str.isdigit():
            age = int(age_str)
            if age >= 65:
                elderly_cols.append(col)
            elif age <= 14:
                child_cols.append(col)
                
    # 행 단위 합계 계산
    df['전체인구'] = df[total_pop_cols].sum(axis=1)
    df['65세이상인구'] = df[elderly_cols].sum(axis=1)
    df['유소년인구'] = df[child_cols].sum(axis=1)
    
    # 시군구 & 연도별 집계
    grouped = df.groupby(['연도', '시군구코드'])[['전체인구', '65세이상인구', '유소년인구']].sum().reset_index()
    
    # 비율 계산 (%)
    grouped['고령화율'] = np.where(
        grouped['전체인구'] > 0,
        (grouped['65세이상인구'] / grouped['전체인구']) * 100,
        0
    ).round(2)
    
    grouped['유소년비율'] = np.where(
        grouped['전체인구'] > 0,
        (grouped['유소년인구'] / grouped['전체인구']) * 100,
        0
    ).round(2)
    
    # 2. GeoJSON 데이터 로드
    geojson_url = "https://raw.githubusercontent.com/first2022-cyber/contents//main/sigungu_kr.geojson"
    geojson_data = requests.get(geojson_url).json()
    
    # GeoJSON 내 속성 매핑 정보 구축
    sigungu_info = {}
    geojson_codes = set()
    
    for feature in geojson_data['features']:
        code = str(feature['properties']['코드'])
        name = feature['properties']['시군구']
        sido = feature['properties']['시도']
        sigungu_info[code] = {'지역명': f"{sido} {name}", '시도': sido}
        geojson_codes.add(code)
        
    grouped['지역명'] = grouped['시군구코드'].apply(lambda x: sigungu_info[x]['지역명'] if x in sigungu_info else "미매칭 지역")
    grouped['시도'] = grouped['시군구코드'].apply(lambda x: sigungu_info[x]['시도'] if x in sigungu_info else "기타")
    
    return grouped, geojson_data, geojson_codes

# 데이터 로드
with st.spinner("데이터를 분석하고 준비 중입니다..."):
    df_all, geojson_kr, geojson_codes = load_and_preprocess_data()

# Sidebar / Top Controls
col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([1, 1, 1])

with col_ctrl1:
    selected_metric = st.radio(
        "📊 조회할 지표 선택",
        options=["고령화율 (65세 이상 %)", "유소년 비율 (0~14세 %)"],
        horizontal=True
    )

with col_ctrl2:
    available_years = sorted(df_all['연도'].unique())
    selected_year = st.slider("📅 연도 선택", min_value=int(min(available_years)), max_value=int(max(available_years)), value=int(max(available_years)), step=1)

# 시도 목록 추출
all_sido = ["전국"] + sorted([info['시도'] for info in df_all[['시도']].drop_duplicates().to_dict('records') if info['시도'] != '기타'])

with col_ctrl3:
    selected_sido = st.selectbox("📍 지역(시도) 선택", options=all_sido)

# 지표 설정 분기
if selected_metric == "고령화율 (65세 이상 %)":
    metric_col = '고령화율'
    metric_label = '고령화율(%)'
    color_scale = 'Reds'
    # 고령사회/초고령사회/초고고령 기준을 고려한 색상 고정범위 설정
    color_range = [10, 40]
    thresholds = [19, 23, 28, 38]
else:
    metric_col = '유소년비율'
    metric_label = '유소년 비율(%)'
    color_scale = 'Blues'
    # 유소년 비율 분포에 맞춘 색상 고정범위 설정
    color_range = [5, 20]
    thresholds = [8, 11, 14, 17]

# 연도별 데이터 필터링
df_year = df_all[df_all['연도'] == selected_year].copy()

# 시도 필터링 및 지도 표시용 GeoJSON 조정
if selected_sido != "전국":
    df_filtered = df_year[df_year['시도'] == selected_sido].copy()
    filtered_codes = set(df_filtered['시군구코드'].unique())
    geojson_filtered = {
        "type": "FeatureCollection",
        "features": [f for f in geojson_kr['features'] if str(f['properties']['코드']) in filtered_codes]
    }
else:
    df_filtered = df_year.copy()
    geojson_filtered = geojson_kr

# -------------------------------------------------------------
# 1. 지표 카드 (Metric Cards)
# -------------------------------------------------------------
if not df_filtered.empty:
    total_pop_sum = df_filtered['전체인구'].sum()
    if selected_metric == "고령화율 (65세 이상 %)":
        target_pop_sum = df_filtered['65세이상인구'].sum()
    else:
        target_pop_sum = df_filtered['유소년인구'].sum()
        
    avg_rate = (target_pop_sum / total_pop_sum * 100) if total_pop_sum > 0 else 0
    
    # 미매칭 제외 최고/최저 계산
    valid_df = df_filtered[df_filtered['지역명'] != "미매칭 지역"]
    max_row = valid_df.loc[valid_df[metric_col].idxmax()]
    min_row = valid_df.loc[valid_df[metric_col].idxmin()]
    
    card_col1, card_col2, card_col3 = st.columns(3)
    card_col1.metric(
        label=f"{selected_sido} 평균 {metric_label}",
        value=f"{avg_rate:.2f}%"
    )
    card_col2.metric(
        label=f"최고 {metric_label} 지역",
        value=f"{max_row['지역명']}",
        delta=f"{max_row[metric_col]:.2f}%"
    )
    card_col3.metric(
        label=f"최저 {metric_label} 지역",
        value=f"{min_row['지역명']}",
        delta=f"{min_row[metric_col]:.2f}%"
    )

st.markdown("---")

# -------------------------------------------------------------
# 2. 단계구분도 (Choropleth Map)
# -------------------------------------------------------------
fig = px.choropleth(
    df_filtered,
    geojson=geojson_filtered,
    locations='시군구코드',
    featureidkey='properties.코드',
    color=metric_col,
    color_continuous_scale=color_scale,
    range_color=color_range, # 연도간 연속적 비교를 위한 색상 고정 범위
    hover_name='지역명',
    hover_data={
        '시군구코드': True,
        metric_col: ':.2f',
        '전체인구': ':,',
        '65세이상인구': ':,' if selected_metric == "고령화율 (65세 이상 %)" else False,
        '유소년인구': ':,' if selected_metric != "고령화율 (65세 이상 %)" else False
    },
    labels={
        metric_col: metric_label,
        '시군구코드': '코드',
        '전체인구': '전체 인구(명)',
        '65세이상인구': '65세 이상 인구(명)',
        '유소년인구': '0~14세 인구(명)'
    }
)

fig.update_geos(
    fitbounds="locations",
    visible=False
)

fig.update_layout(
    margin={"r": 0, "t": 10, "l": 0, "b": 0},
    height=650
)

st.plotly_chart(fig, use_container_width=True)

# -------------------------------------------------------------
# 3. 안내 문구 및 미매칭 처리 정보
# -------------------------------------------------------------
unmatched_in_geo = geojson_codes - set(df_year['시군구코드'].unique())
unmatched_in_df = set(df_year['시군구코드'].unique()) - geojson_codes

st.caption(
    f"💡 **안내**: 연도별 색상 비교를 위해 지도 색상 범위를 고정값({color_range[0]}% ~ {color_range[1]}%)으로 보정했습니다. "
    f"행정구역 개편(강원·전북 특별자치도, 대구 군위군 등) 반영 후에도 경계 데이터와 일치하지 않는 일부 지역은 **회색**으로 표기됩니다."
)

if unmatched_in_geo:
    with st.expander("ℹ️ 경계 데이터에는 있으나 인구 데이터와 매칭되지 않는 시군구 코드 (회색 표시)"):
        st.write(", ".join(sorted(list(unmatched_in_geo))))
