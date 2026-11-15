"""영화·리뷰 API 서버. 데이터는 SQLite 파일 하나에 저장한다."""
import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from pydantic import AnyHttpUrl, BaseModel, Field, computed_field

import sentiment

DB_PATH = os.environ.get("DB_PATH", "movies.db")
KST = timezone(timedelta(hours=9))  # 한국은 서머타임이 없어 고정 오프셋으로 충분하고, slim 이미지에 시간대 DB가 없어도 된다


@asynccontextmanager
async def lifespan(app):
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            release_date TEXT NOT NULL,
            director TEXT NOT NULL,
            genre TEXT NOT NULL,
            poster_url TEXT NOT NULL)""")
        con.execute("""CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY,
            movie_id INTEGER NOT NULL REFERENCES movies(id) ON DELETE CASCADE,
            author TEXT NOT NULL,
            content TEXT NOT NULL,
            score REAL NOT NULL,
            created_at TEXT NOT NULL)""")
    app.state.model = sentiment.load()  # 요청마다 불러오지 않도록 서버 시작 때 한 번만 연다
    yield


app = FastAPI(title="영화 리뷰 API", description="영화와 리뷰를 관리하고 리뷰 감성을 분석합니다.", lifespan=lifespan)


def db():
    # 의존성과 엔드포인트가 서로 다른 스레드에서 돌 수 있어 check_same_thread를 끈다. 연결은 요청마다 새로 연다.
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
        con.commit()
    finally:
        con.close()


class MovieIn(BaseModel):
    title: str = Field(min_length=1, description="영화 제목", examples=["기생충"])
    release_date: date = Field(description="개봉일", examples=["2019-05-30"])
    director: str = Field(min_length=1, description="감독", examples=["봉준호"])
    genre: str = Field(min_length=1, description="장르", examples=["드라마"])
    poster_url: AnyHttpUrl = Field(description="포스터 이미지 URL")


class Movie(MovieIn):
    id: int = Field(description="영화 ID")


def find_movie(con, movie_id):
    row = con.execute("SELECT * FROM movies WHERE id = ?", (movie_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "영화를 찾을 수 없습니다.")
    return dict(row)


@app.post("/movies", status_code=201, response_model=Movie, tags=["영화"], summary="영화 등록")
def create_movie(movie: MovieIn, con=Depends(db)):
    data = movie.model_dump(mode="json")  # 날짜와 URL을 문자열로 바꿔 SQLite에 넣는다
    cur = con.execute("INSERT INTO movies (title, release_date, director, genre, poster_url) "
                      "VALUES (:title, :release_date, :director, :genre, :poster_url)", data)
    return {"id": cur.lastrowid, **data}


@app.get("/movies", response_model=list[Movie], tags=["영화"], summary="전체 영화 조회")
def list_movies(con=Depends(db)):
    return [dict(r) for r in con.execute("SELECT * FROM movies ORDER BY id")]


@app.get("/movies/{movie_id}", response_model=Movie, tags=["영화"], summary="특정 영화 조회",
         responses={404: {"description": "영화를 찾을 수 없음"}})
def get_movie(movie_id: int, con=Depends(db)):
    return find_movie(con, movie_id)


@app.delete("/movies/{movie_id}", status_code=204, tags=["영화"], summary="특정 영화 삭제",
            responses={404: {"description": "영화를 찾을 수 없음"}})
def delete_movie(movie_id: int, con=Depends(db)):
    """영화를 지우면 그 영화의 리뷰도 함께 지워집니다."""
    if con.execute("DELETE FROM movies WHERE id = ?", (movie_id,)).rowcount == 0:
        raise HTTPException(404, "영화를 찾을 수 없습니다.")


class Rating(BaseModel):
    movie_id: int = Field(description="영화 ID")
    review_count: int = Field(description="리뷰 수")
    average_score: float | None = Field(description="리뷰 감성 점수(긍정 확률)의 평균. 리뷰가 없으면 null")


@app.get("/movies/{movie_id}/rating", response_model=Rating, tags=["영화"], summary="평점 조회",
         responses={404: {"description": "영화를 찾을 수 없음"}})
def get_rating(movie_id: int, con=Depends(db)):
    find_movie(con, movie_id)
    count, avg = con.execute("SELECT COUNT(*), AVG(score) FROM reviews WHERE movie_id = ?", (movie_id,)).fetchone()
    return {"movie_id": movie_id, "review_count": count, "average_score": avg}


class ReviewIn(BaseModel):
    movie_id: int = Field(description="리뷰할 영화 ID")
    author: str = Field(min_length=1, max_length=50, description="작성자 이름", examples=["김민기"])
    content: str = Field(min_length=1, max_length=2000, description="리뷰 내용", examples=["배우들 연기가 정말 좋았어요."])


class Review(ReviewIn):
    id: int = Field(description="리뷰 ID")
    score: float = Field(description="감성 점수. 모델이 판단한 긍정 확률(0~1)")
    created_at: datetime = Field(description="등록 시각(한국 시간)")

    @computed_field(description="감성 분석 결과. 점수가 0.5보다 크면 긍정")
    @property
    def sentiment(self) -> str:
        return "긍정" if self.score > 0.5 else "부정"


@app.post("/reviews", status_code=201, response_model=Review, tags=["리뷰"], summary="리뷰 등록",
          responses={404: {"description": "영화를 찾을 수 없음"}})
def create_review(review: ReviewIn, request: Request, con=Depends(db)):
    """리뷰를 저장하기 전에 감성 분석을 실행하고, 결과를 함께 저장합니다."""
    find_movie(con, review.movie_id)
    data = {**review.model_dump(), "score": sentiment.predict(request.app.state.model, review.content),
            "created_at": datetime.now(KST).isoformat(timespec="seconds")}
    cur = con.execute("INSERT INTO reviews (movie_id, author, content, score, created_at) "
                      "VALUES (:movie_id, :author, :content, :score, :created_at)", data)
    return {"id": cur.lastrowid, **data}


@app.get("/reviews", response_model=list[Review], tags=["리뷰"], summary="리뷰 조회",
         responses={404: {"description": "영화를 찾을 수 없음"}})
def list_reviews(movie_id: int | None = Query(None, description="이 영화의 리뷰만 조회. 비우면 전체"),
                 limit: int | None = Query(None, ge=1, le=100, description="최근 리뷰 몇 개까지 받을지. 비우면 전부"),
                 con=Depends(db)):
    """최근에 등록한 리뷰부터 돌려줍니다."""
    if movie_id is not None:
        find_movie(con, movie_id)
    rows = con.execute("SELECT * FROM reviews WHERE ? IS NULL OR movie_id = ? ORDER BY id DESC LIMIT ?",
                       (movie_id, movie_id, limit or -1))  # SQLite에서 LIMIT -1은 제한 없음
    return [dict(r) for r in rows]


@app.delete("/reviews/{review_id}", status_code=204, tags=["리뷰"], summary="리뷰 삭제",
            responses={404: {"description": "리뷰를 찾을 수 없음"}})
def delete_review(review_id: int, con=Depends(db)):
    if con.execute("DELETE FROM reviews WHERE id = ?", (review_id,)).rowcount == 0:
        raise HTTPException(404, "리뷰를 찾을 수 없습니다.")
