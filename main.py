import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.express as px

st.set_page_config(page_title="전국 고령화 단계구분도", layout="wide")

st.title("👵 2026년 전국 시군구별 고령화 단계구분도")
st.markdown("2026년 6월 기준 65세 이상 인구 비율(%)을 나타낸 지도입니다.")

@st.cache_data
def load_data():
    # 1. 인구 데이터 로드 (zip 파일 압축 해제 후 판다스로 바로 읽기)
    pop_url = "https://raw.githubusercontent.com/first2022-cyber/contents//main/population_ts_yearly_gender.zip"
    df = pd.read_csv(pop_url, compression='zip')
    
    # 2026년 데이터만 필터링
    df_2026 = df[df['연도'] == 2026].copy()
    
    # 코드를 5자리 문자열(시군구 코드)로 변환
    df_2026['시군구코드'] = df_2026['코드'].astype(str).str.zfill(8).str[:5]
    
    # 열 이름 추출
    total_pop_cols = [col for col in df_2026.columns if col.startswith('계_')]
    
    # 65세 이상 열 추출 (계_65세 ~ 계_100세 이상)
    elderly_cols = []
    for col in total_pop_cols:
        age_str = col.replace('계_', '').replace('세', '').replace(' 이상', '')
        if age_str.isdigit() and int(age_str) >= 65:
            elderly_cols.append(col)
    
    # 시군구별 전체 인구 및 65세 이상 인구 합계 계산
    df_2026['전체인구'] = df_2026[total_pop_cols].sum(axis=1)
    df_2026['65세이상인구'] = df_2026[elderly_cols].sum(axis=1)
    
    # 시군구 단위 집계
    grouped = df_2026.groupby('시군구코드')[['전체인구', '65세이상인구']].sum().reset_index()
    
    # 고령화율(%) 계산
    grouped['고령화율'] = np.where(
        grouped['전체인구'] > 0,
        (grouped['65세이상인구'] / grouped['전체인구']) * 100,
        0
    ).round(2)
    
    # 2. GeoJSON 데이터 로드
    geojson_url = "https://raw.githubusercontent.com/first2022-cyber/contents//main/sigungu_kr.geojson"
    geojson_data = requests.get(geojson_url).json()
    
    # GeoJSON에 존재하는 시군구 이름 매핑 생성 (툴팁/호버용)
    sigungu_map = {}
    for feature in geojson_data['features']:
        code = str(feature['properties']['코드'])
        name = feature['properties']['시군구']
        sido = feature['properties']['시도']
        sigungu_map[code] = f"{sido} {name}"
        
    grouped['지역명'] = grouped['시군구코드'].map(sigungu_map)
    
    return grouped, geojson_data

with st.spinner("데이터를 불러오는 중입니다..."):
    df_sigungu, geojson_kr = load_data()

# Plotly Choropleth (단계구분도) 생성
fig = px.choropleth(
    df_sigungu,
    geojson=geojson_kr,
    locations='시군구코드',
    featureidkey='properties.코드',
    color='고령화율',
    color_continuous_scale='Reds', # 고령화율이 높을수록 진한 빨간색
    hover_name='지역명',
    hover_data={
        '시군구코드': True,
        '고령화율': ':.2f',
        '전체인구': ':,',
        '65세이상인구': ':,'
    },
    labels={
        '고령화율': '고령화율(%)',
        '시군구코드': '시군구 코드',
        '전체인구': '전체 인구(명)',
        '65세이상인구': '65세 이상 인구(명)'
    }
)

# 배경지도 타일 제거 및 대한민국 영역 맞춤 설정
fig.update_geos(
    fitbounds="locations",
    visible=False
)

fig.update_layout(
    margin={"r": 0, "t": 30, "l": 0, "b": 0},
    height=700
)

# 스트림릿 화면 출력
st.plotly_chart(fig, use_container_width=True)

# 요약 데이터표 제공
with st.expander("📊 시군구별 상세 데이터 보기"):
    st.dataframe(
        df_sigungu.sort_values(by='고령화율', ascending=False),
        use_container_width=True
    )
