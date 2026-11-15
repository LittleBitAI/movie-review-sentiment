"""리뷰 감성 분석 모델.

서버는 load와 predict만 쓰고 PyTorch 없이 onnxruntime으로 추론한다.
export는 Docker 빌드 단계와 모델실험.ipynb에서 ONNX 파일을 만들 때만 쓰므로 PyTorch를 함수 안에서 불러온다.
"""
from pathlib import Path

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

MODEL_DIR = Path(__file__).parent / "model"


def export(name, out_dir=MODEL_DIR):
    """Hugging Face 모델을 FP32 ONNX(fp32.onnx)로 바꾸고, 가중치를 INT8로 동적 양자화한 int8.onnx도 만든다."""
    import torch
    from onnxruntime.quantization import QuantType, quantize_dynamic
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    tok = AutoTokenizer.from_pretrained(name)
    tok.backend_tokenizer.save(str(out_dir / "tokenizer.json"))  # 서버는 transformers 대신 tokenizers만으로 이 파일을 읽는다
    model = AutoModelForSequenceClassification.from_pretrained(name).eval()
    enc = tok("예시 문장입니다", return_tensors="pt")
    names = ["input_ids", "attention_mask", "token_type_ids"]  # 모델 forward 인자 순서
    torch.onnx.export(model, tuple(enc[n] for n in names), out_dir / "fp32.onnx", input_names=names,
                      output_names=["logits"], dynamic_axes={n: {1: "length"} for n in names}, dynamo=False)
    quantize_dynamic(out_dir / "fp32.onnx", out_dir / "int8.onnx", weight_type=QuantType.QInt8)


def load(model_dir=MODEL_DIR, variant="int8", threads=0):
    """threads가 0이면 onnxruntime 기본값(물리 코어 수)을 쓴다."""
    tok = Tokenizer.from_file(str(Path(model_dir) / "tokenizer.json"))
    tok.enable_truncation(512)  # 후보 모델의 최대 입력 길이
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = threads
    return tok, ort.InferenceSession(str(Path(model_dir) / f"{variant}.onnx"), opts, providers=["CPUExecutionProvider"])


def predict(model, text):
    """리뷰 한 개의 긍정 확률(0~1)."""
    tok, session = model
    e = tok.encode(text)
    feeds = {"input_ids": [e.ids], "attention_mask": [e.attention_mask], "token_type_ids": [e.type_ids]}
    logits = session.run(None, {k: np.array(v, dtype=np.int64) for k, v in feeds.items()})[0][0]
    p = np.exp(logits - logits.max())
    return float(p[1] / p.sum())
