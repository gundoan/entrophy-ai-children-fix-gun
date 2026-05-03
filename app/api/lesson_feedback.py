from fastapi import APIRouter, UploadFile, File, HTTPException
from app.models.schemas import LessonFeedbackRequest, LessonFeedbackResponse
from app.services.feature_extractor import extract_feature_json
from app.services.lesson_service import get_answer_frame, get_answer_frames,get_test_answer_frame
from app.services.evaluation_service import evaluate_static_sign, evaluate_dynamic_sign
from app.services.feedback_service import generate_feedback
from app.utils.mediapipe_adapter import build_mediapipe_results_from_request
from app.services.mediapipe_service import process_image_to_landmarks
from app.services.expression_analyzation_service import analyze_expression_with_llm
from typing import List
from fastapi.concurrency import run_in_threadpool

router = APIRouter()

@router.post("/{lessonId}/feedback", response_model=LessonFeedbackResponse)
async def lesson_feedback(lessonId: int, req: LessonFeedbackRequest):

    results = build_mediapipe_results_from_request(req.raw_landmarks)

    # 1. raw landmarks → feature json
    user_feature = extract_feature_json(results)

    # 2. 정답 frame 조회
    answer_feature = get_test_answer_frame()
    # answer_feature = get_answer_frame(lessonId)

    # 3. 정답 여부 판단
    result = evaluate_static_sign(user_feature, answer_feature)

    # 4. 자연어 피드백 생성
    feedback = await run_in_threadpool(
        generate_feedback,
        evaluation=result
    )

    return LessonFeedbackResponse(
        isCorrect=result["is_correct"],
        score=result["score"],
        feedback=feedback
    )


@router.post("/{lessonId}/feedback/image", response_model=LessonFeedbackResponse)
async def lesson_feedback_by_image(
    lessonId: int, 
    file: UploadFile = File(...)
):
    try:
        # 1. 이미지 읽기
        image_bytes = await file.read()
        
        # 2. 이미지 -> MediaPipe 추론 -> DummyResults 변환 (어댑터 사용)
        results = process_image_to_landmarks(image_bytes)

        # 3. raw landmarks → feature json (기존 로직 재사용)
        # user_feature = extract_feature_json(results)
        
        expression = await run_in_threadpool(analyze_expression_with_llm, image_bytes)
        user_feature = extract_feature_json(results, expression)

        # 4. 정답 frame 조회 (DB/API)
        answer_feature = get_answer_frame(lessonId)

        # 5. 정답 여부 판단
        result = evaluate_static_sign(user_feature, answer_feature)

        # 6. 자연어 피드백 생성
        feedback = await run_in_threadpool(
            generate_feedback,
            evaluation=result
        )

        return LessonFeedbackResponse(
            isCorrect=result["is_correct"],
            score=result["score"],
            feedback=feedback
        )

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        print(f"Error processing image feedback: {e}")
        raise HTTPException(status_code=500, detail="이미지 처리 중 오류가 발생했습니다.")
    
@router.post("/{lessonId}/feedback/images", response_model=LessonFeedbackResponse)
async def lesson_feedback_by_multiple_images(
    lessonId: int, 
    files: List[UploadFile] = File(...)
):
    try:
        if not files:
            raise HTTPException(status_code=400, detail="이미지가 없습니다.")

        # 1. 사용자 이미지 처리 (Loop)
        user_frames = []
        for file in files:
            image_bytes = await file.read()
            # MediaPipe 처리
            results = process_image_to_landmarks(image_bytes)
            # Feature JSON 추출
            # feature = extract_feature_json(results)

            expression = await run_in_threadpool(analyze_expression_with_llm, image_bytes)
            user_feature = extract_feature_json(results, expression)

            user_frames.append(user_feature)

        # 2. 정답 데이터 리스트 조회
        answer_frames = get_answer_frames(lessonId)

        if not answer_frames:
             raise HTTPException(status_code=404, detail="정답 데이터를 찾을 수 없습니다.")

        # 3. 채점 (Dynamic Evaluation)
        result = evaluate_dynamic_sign(user_frames, answer_frames)
        
        # 4. 피드백 생성 전략
        # 모든 프레임을 다 LLM에 넣으면 너무 길어지므로,
        # '가장 점수가 낮은(많이 틀린) 프레임'을 기준으로 피드백을 생성합니다.
        target_idx = result["worst_frame_idx"]
        
        # 인덱스 범위 안전 장치
        if target_idx >= len(user_frames) or target_idx >= len(answer_frames):
            target_idx = 0

        feedback = await run_in_threadpool( 
            generate_feedback,
            evaluation=result
        )

        return LessonFeedbackResponse(
            isCorrect=result["is_correct"],
            score=result["score"],
            feedback=feedback
        )

    except Exception as e:
        print(f"Error processing multiple images: {e}")
        raise HTTPException(status_code=500, detail=f"처리 중 오류 발생: {str(e)}")