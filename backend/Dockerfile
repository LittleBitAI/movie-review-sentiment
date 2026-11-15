# 1단계: PyTorch로 모델을 ONNX로 바꾸고 INT8로 양자화한다. 이 단계의 패키지는 최종 이미지에 들어가지 않는다.
FROM python:3.13-slim AS export
WORKDIR /app
COPY requirements.txt requirements-experiment.txt ./
RUN pip install --no-cache-dir -r requirements-experiment.txt
COPY sentiment.py .
RUN python -c "import sentiment; sentiment.export('daekeun-ml/koelectra-small-v3-nsmc')"

# 2단계: 서버 이미지. 모델은 빌드 때 만들어 두어 컨테이너 실행 중에는 내려받지 않는다.
FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --from=export /app/model/int8.onnx /app/model/tokenizer.json model/
COPY main.py sentiment.py ./
# DB 파일은 /data에 둔다. 컨테이너를 지워도 남기려면 실행할 때 이 경로에 볼륨을 연결한다.
RUN mkdir /data
ENV DB_PATH=/data/movies.db
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
