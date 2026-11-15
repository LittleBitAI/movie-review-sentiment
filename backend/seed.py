"""제출용 예시 데이터(영화 3편, 영화마다 리뷰 11개)를 API로 등록한다. 리뷰는 직접 쓴 예시 문장이다.

사용법: python seed.py [백엔드 주소]   (기본값 http://127.0.0.1:8000)
"""
import sys

import requests

API = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
NAMU = "https://i.namu.wiki/i/"
DATA = [
    ({"title": "기생충", "release_date": "2019-05-30", "director": "봉준호", "genre": "드라마",
      "poster_url": NAMU + "NUAWoGqQ_V4elaH2mW5seiCMfNbzDjsbJdAsENYVWix5UJ0LFH5um3DFkucAtFDlVR41T7P7ygwbFi9L4mSpQhUgJDAnUHnkvUOrSR6fyJe9D289TygACZGnAOWC4fdM8l31JC8jyRL-raU81fA3hA.webp"},
     [("영화광", "계단 하나하나에 계층을 담은 연출이 대단했어요. 두 번 봐도 새로 보이는 장면이 있네요."),
      ("민지", "웃으면서 보다가 후반부에 소름이 쫙 돋았습니다. 왜 상을 휩쓸었는지 알겠어요."),
      ("주말관객", "배우들 연기가 하나같이 자연스러워서 몰입이 깨질 틈이 없었어요."),
      ("하늘", "냄새라는 소재 하나로 이렇게까지 긴장감을 만들 수 있다니 놀랍네요."),
      ("dh_kim", "기대가 너무 컸나. 중반까지는 좋았는데 결말은 좀 과하다고 느꼈습니다."),
      ("팝콘", "솔직히 왜 이렇게 극찬받는지 모르겠음. 불편하기만 했다."),
      ("시네필", "가족끼리 보러 갔다가 분위기 싸해짐. 영화는 잘 만들었는데 같이 볼 영화는 아님."),
      ("현우", "보고 나서 며칠 동안 생각이 나네요. 씁쓸하지만 꼭 볼 만한 영화입니다."),
      ("익명", "상 받은 영화라 봤는데 재미는 그냥 그랬어요."),
      ("수아", "음악, 미술, 촬영 다 완벽. 한국 영화 수준을 보여 준 작품이라고 생각해요."),
      ("ㅇㅇ", "아 진짜 대단하다~ 보는 내내 하품만 나오게 만드는 재주가.")]),
    ({"title": "서울의 봄", "release_date": "2023-11-22", "director": "김성수", "genre": "드라마",
      "poster_url": NAMU + "UPu8KgPnh6D_tiFPAH3a_fOqe44bdvLseg0AQrUw2kMr2ySuynb0xLxE61KxBRMT0s5Gst4sfqQQKcAoZOupvpeH3RR_VZ0hiHgJIwT4BKZxjTQ3I0StVhqVbOJHSGP-834qqfaStOGLNoqVTVdc9Q.webp"},
     [("역사덕후", "결말을 알고 봐도 손에 땀을 쥐게 만드네요. 두 시간 넘는 러닝타임이 짧게 느껴졌어요."),
      ("정민", "황정민 배우 연기 보고 진심으로 화가 났습니다. 그만큼 잘했다는 뜻이에요."),
      ("극장러", "보고 나오는데 심장이 계속 뛰었어요. 올해 본 한국 영화 중 최고."),
      ("유진", "정우성 배우가 연기한 인물이 너무 답답하고 안타까워서 눈물이 났어요."),
      ("서연", "실화라서 더 화나고 슬펐습니다. 젊은 사람들이 꼭 봤으면 좋겠어요."),
      ("무비", "연출은 좋은데 인물이 너무 많아서 중간에 누가 누군지 헷갈렸어요."),
      ("kmh", "너무 답답해서 보는 내내 스트레스 받았음. 다시는 못 볼 듯."),
      ("영화초보", "역사 공부하는 기분이라 저한테는 좀 지루했어요."),
      ("태호", "배우들 연기는 압도적인데 결말을 아니까 긴장감이 덜했습니다."),
      ("하루", "보고 나서 관련 다큐까지 찾아봤어요. 잘 만든 영화는 이런 거죠."),
      ("익명2", "평점 보고 기대했는데 생각보다 평범했어요. 그냥 볼 만한 정도.")]),
    ({"title": "파묘", "release_date": "2024-02-22", "director": "장재현", "genre": "오컬트",
      "poster_url": NAMU + "SwGXb6dziqs_UnSqvI0o2duG4uhU0w-5HeTk4IneY9XciZLfu9m7pGLMgg8Sk_QZTd7EnRvpN4UKnkK9vmtaKg5LdwKx6LL4i4ix7eOt72zH-eguQXNc6yAQX57tWxPr1lLegOjz67TfDJMUIEYhiw.webp"},
     [("공포매니아", "김고은 배우의 굿 장면은 극장에서 꼭 봐야 합니다. 소름 돋았어요."),
      ("지훈", "전반부 분위기가 정말 좋았어요. 한국적인 오컬트를 제대로 살렸네요."),
      ("영화보는곰", "후반부에 장르가 확 바뀌어서 당황했어요. 앞부분만 보면 최고였는데."),
      ("나연", "배우들 합이 너무 좋아서 시리즈로 더 보고 싶어요."),
      ("ghost", "무서운 거 못 보는데 생각보다 견딜 만했고 재밌었어요."),
      ("민수", "중반 이후로 너무 늘어지고 이야기가 산으로 갑니다. 실망했어요."),
      ("관객A", "사운드가 진짜 무섭게 잘 만들어져 있어요. 꼭 큰 화면으로 보세요."),
      ("소희", "기대 안 하고 봤는데 대박. 시간 가는 줄 몰랐어요."),
      ("익명3", "천만 영화라길래 봤는데 이게 왜 천만인지 이해가 안 감."),
      ("준", "최민식 배우 연기는 역시 믿고 봅니다. 다만 CG는 조금 아쉬웠어요."),
      ("ㅁㅁ", "와 정말 무섭다 무서워. 이렇게 안 무서운 공포 영화는 처음이네.")]),
]

for movie, reviews in DATA:
    r = requests.post(f"{API}/movies", json=movie)
    r.raise_for_status()
    for author, content in reviews:
        requests.post(f"{API}/reviews", json={"movie_id": r.json()["id"], "author": author, "content": content}).raise_for_status()
    print(f"{movie['title']}: 리뷰 {len(reviews)}개 등록")
