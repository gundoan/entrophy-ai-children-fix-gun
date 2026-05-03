import json
import numpy as np
from pathlib import Path


class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):  return int(obj)
        if isinstance(obj, np.floating): return float(obj)
        if isinstance(obj, np.bool_):    return bool(obj)
        if isinstance(obj, np.ndarray):  return obj.tolist()
        return super().default(obj)

BASE_DIR    = Path(__file__).resolve().parent.parent
ANSWERS_DIR = BASE_DIR / "answers" / "korean"

WORDS = [
    {"id": 1, "korean": "엄마",  "english": "Mom"},
    {"id": 2, "korean": "아빠",  "english": "Dad"},
    {"id": 3, "korean": "사랑해", "english": "I Love You"},
    {"id": 4, "korean": "나",    "english": "Me / I"},
    {"id": 5, "korean": "아들",  "english": "Son"},
    {"id": 6, "korean": "딸",   "english": "Daughter"},
]


def _answer_path(word_id: int) -> Path:
    word = next((w for w in WORDS if w["id"] == word_id), None)
    if word is None:
        raise ValueError(f"단어 ID {word_id} 가 없습니다.")
    ANSWERS_DIR.mkdir(parents=True, exist_ok=True)
    return ANSWERS_DIR / f"{word['korean']}.json"


def word_has_answer(word_id: int) -> bool:
    try:
        return _answer_path(word_id).exists()
    except ValueError:
        return False


def get_word_list() -> list:
    return [{**w, "is_recorded": word_has_answer(w["id"])} for w in WORDS]


def get_answer_for_word(word_id: int) -> list:
    """항상 프레임 리스트로 반환 (구버전 단일 dict도 리스트로 래핑)"""
    path = _answer_path(word_id)
    if not path.exists():
        raise FileNotFoundError(f"단어 ID {word_id} 의 정답이 없습니다.")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else [data]


def save_answer_for_word(word_id: int, features: list):
    """features: list of feature dicts (동적 수화 = 여러 프레임)"""
    data = [{k: v for k, v in f.items() if k != "non_manual_signal"} for f in features]
    path = _answer_path(word_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, cls=NumpyEncoder)
