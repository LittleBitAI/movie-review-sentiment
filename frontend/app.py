"""영화 리뷰 Streamlit 화면. 데이터는 저장하지 않고 매번 백엔드 API에서 받아 온다."""
import os
from datetime import date

import requests
import streamlit as st

# Windows에서 localhost는 IPv6(::1)부터 시도해 요청마다 2초씩 늦어지므로 IPv4 주소를 직접 쓴다
API = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")
FIELD_NAMES = {"title": "제목", "release_date": "개봉일", "director": "감독", "genre": "장르",
               "poster_url": "포스터 URL", "movie_id": "영화", "author": "작성자", "content": "리뷰 내용"}


def show_error(r):
    """영화 추가와 리뷰 등록 폼이 함께 쓰는 API 오류 표시."""
    if r.status_code == 422:
        st.error("입력값을 확인해 주세요: " + ", ".join(FIELD_NAMES[e["loc"][-1]] for e in r.json()["detail"]))
    else:
        st.error(r.json()["detail"])


st.set_page_config(page_title="영화 리뷰", layout="wide")
st.title("영화 리뷰")
# 등록 결과가 같은 실행 안에서 목록과 평점에 바로 보이도록, 등록 탭을 먼저 처리하고 목록을 나중에 그린다
list_tab, add_tab, review_tab = st.tabs(["영화 목록", "영화 추가", "리뷰"])

with add_tab, st.form("add_movie"):
    movie = {
        "title": st.text_input("제목"),
        "release_date": st.date_input("개봉일", value=None, min_value=date(1900, 1, 1)),
        "director": st.text_input("감독"),
        "genre": st.text_input("장르"),
        "poster_url": st.text_input("포스터 URL", placeholder="https://i.namu.wiki/..."),
    }
    if st.form_submit_button("등록"):
        movie["release_date"] = movie["release_date"] and movie["release_date"].isoformat()
        r = requests.post(f"{API}/movies", json=movie)
        if r.ok:
            st.success(f"'{movie['title']}'을(를) 등록했습니다.")
        else:
            show_error(r)

movies = requests.get(f"{API}/movies").json()

with review_tab:
    if not movies:
        st.info("리뷰를 쓸 영화가 없습니다. '영화 추가' 탭에서 먼저 등록해 주세요.")
    else:
        with st.form("add_review"):
            picked = st.selectbox("영화", movies, format_func=lambda m: f"{m['id']}. {m['title']}")
            author = st.text_input("작성자")
            content = st.text_area("리뷰 내용")
            if st.form_submit_button("등록"):
                r = requests.post(f"{API}/reviews", json={"movie_id": picked["id"], "author": author, "content": content})
                if not r.ok:
                    show_error(r)
                else:
                    review = r.json()
                    alert = st.success if review["sentiment"] == "긍정" else st.warning
                    alert(f"감성 분석 결과: {review['sentiment']} (긍정 확률 {review['score']:.1%})")

    st.subheader("최근 리뷰 10개")
    reviews = requests.get(f"{API}/reviews", params={"limit": 10}).json()
    for rv in reviews:
        rv["created_at"] = rv["created_at"][:16].replace("T", " ")
    st.dataframe(reviews, hide_index=True, column_order=["movie_id", "created_at", "author", "content", "sentiment", "score"],
                 column_config={"movie_id": "영화 ID", "created_at": "등록일", "author": "작성자", "content": "리뷰 내용",
                                "sentiment": "감성", "score": st.column_config.ProgressColumn("긍정 확률", format="percent", min_value=0, max_value=1)})

with list_tab:
    if not movies:
        st.info("등록된 영화가 없습니다. '영화 추가' 탭에서 등록해 주세요.")
    for i, m in enumerate(movies):
        if i % 4 == 0:  # 포스터 높이가 달라도 줄이 맞도록 4개마다 새 줄을 만든다
            cols = st.columns(4)
        rating = requests.get(f"{API}/movies/{m['id']}/rating").json()
        with cols[i % 4]:
            st.image(m["poster_url"], width="stretch")
            st.markdown(f"**{m['title']}**")
            st.caption(f"{m['release_date']} · {m['director']} · {m['genre']}")
            if rating["review_count"]:
                # 평점은 감성 점수(긍정 확률) 평균을 익숙한 5점 척도로 바꿔 보여 준다
                st.caption(f"평점 {rating['average_score'] * 5:.1f} / 5 (리뷰 {rating['review_count']}개)")
            else:
                st.caption("아직 리뷰가 없습니다.")
