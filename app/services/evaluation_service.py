from app.utils.similarity import compare_feature
import json

def evaluate_static_sign(user: dict, answer: dict) -> dict:
    score, wrong_parts = compare_feature(user, answer)
    return {
        "score": score,
        "is_correct": score == 1.0,
        "wrong_parts": wrong_parts
    }

def evaluate_dynamic_sign(user_frames: list, answer_frames: list) -> dict:
    total_score = 0.0
    frame_count = len(user_frames)
    
    # 길이가 다르면 최소 길이 기준으로 맞춤 (혹은 에러 처리)
    min_len = min(len(user_frames), len(answer_frames))
    
    if min_len == 0:
        return {"score": 0.0, "is_correct": False, "wrong_parts": None, "worst_frame_idx": 0}

    lowest_score = 1.1 # 1.0보다 큰 값으로 초기화
    worst_frame_idx = 0
    worst_frame_wrong_parts = {}

    # 1:1 매칭 채점
    for i in range(min_len):
        # 기존 compare_feature 함수 재사용 (static 채점 로직과 동일)
        score, wrong_parts = compare_feature(user_frames[i], answer_frames[i])
        total_score += score

        # 피드백을 위해 가장 점수가 낮은(가장 많이 틀린) 순간을 포착
        if score < lowest_score:
            lowest_score = score
            worst_frame_idx = i
            worst_frame_wrong_parts = wrong_parts

    avg_score = total_score / min_len if min_len > 0 else 0.0

    return {
        "score": avg_score,
        "is_correct": avg_score == 1.0, # 평균 점수가 1.0이어야 정답 (필요시 0.9 등으로 완화 가능)
        "wrong_parts": worst_frame_wrong_parts,
        "worst_frame_idx": worst_frame_idx, # LLM에게 "이 부분을 틀렸어"라고 말해주기 위함
    }