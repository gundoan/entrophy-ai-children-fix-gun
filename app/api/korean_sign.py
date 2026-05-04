from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.concurrency import run_in_threadpool
from typing import List
from app.services.mediapipe_service import process_image_to_landmarks
from app.services.feature_extractor import extract_feature_json
from app.services.evaluation_service import evaluate_dynamic_sign
from app.services.korean_answer_service import (
    get_word_list,
    get_answer_for_word,
    save_answer_for_word,
    word_has_answer,
    WORDS,
)

router = APIRouter()


@router.get("/words")
async def get_words():
    return get_word_list()


@router.post("/record/{word_id}")
async def record_answer(word_id: int, files: List[UploadFile] = File(...)):
    """여러 프레임을 받아 동적 수화 정답으로 저장"""
    if not any(w["id"] == word_id for w in WORDS):
        raise HTTPException(status_code=404, detail=f"단어 ID {word_id} 가 없습니다.")
    if not files:
        raise HTTPException(status_code=400, detail="프레임이 없습니다.")

    try:
        features = []
        for file in files:
            image_bytes = await file.read()
            results = await run_in_threadpool(process_image_to_landmarks, image_bytes)
            feature = extract_feature_json(results)
            features.append(feature)

        hand_detected = any(
            f.get("left", {}).get("present") or f.get("right", {}).get("present")
            for f in features
        )
        if not hand_detected:
            raise HTTPException(
                status_code=422,
                detail="손이 감지되지 않았습니다. 손을 카메라에 잘 보이게 해주세요."
            )

        save_answer_for_word(word_id, features)
        word = next(w for w in WORDS if w["id"] == word_id)
        return {"success": True, "word": word["korean"], "frames": len(features)}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"처리 중 오류 발생: {str(e)}")


@router.post("/evaluate/{word_id}")
async def evaluate_sign(word_id: int, files: List[UploadFile] = File(...)):
    """사용자 수화 프레임 시퀀스를 정답과 비교"""
    if not any(w["id"] == word_id for w in WORDS):
        raise HTTPException(status_code=404, detail=f"단어 ID {word_id} 가 없습니다.")
    if not word_has_answer(word_id):
        raise HTTPException(status_code=404, detail="정답이 없습니다. 먼저 녹화해주세요.")
    if not files:
        raise HTTPException(status_code=400, detail="프레임이 없습니다.")

    try:
        user_features = []
        for file in files:
            image_bytes = await file.read()
            results = await run_in_threadpool(process_image_to_landmarks, image_bytes)
            feature = extract_feature_json(results)
            user_features.append(feature)

        answer_frames = get_answer_for_word(word_id)
        result = evaluate_dynamic_sign(user_features, answer_frames)

        word = next(w for w in WORDS if w["id"] == word_id)
        return {
            "isCorrect": result["score"] >= 0.90,
            "score": round(result["score"], 3),
            "word": word["korean"],
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"처리 중 오류 발생: {str(e)}")
