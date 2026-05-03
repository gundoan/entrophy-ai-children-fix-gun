import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

import cv2
import mediapipe as mp
import json
import time
import numpy as np
from app.services.feature_extractor import extract_feature_json
from app.services.evaluation_service import evaluate_dynamic_sign

WORDS = [
    {"id": 1, "korean": "엄마",  "english": "Mom"},
    {"id": 2, "korean": "아빠",  "english": "Dad"},
    {"id": 3, "korean": "사랑해", "english": "I Love You"},
    {"id": 4, "korean": "나",    "english": "Me / I"},
    {"id": 5, "korean": "아들",  "english": "Son"},
    {"id": 6, "korean": "딸",   "english": "Daughter"},
]

PROJECT_ROOT    = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
ANSWERS_DIR     = os.path.join(PROJECT_ROOT, "answers", "korean")
PASS_THRESHOLD  = 0.70
RECORD_DURATION = 3.0
TARGET_FPS      = 5


def load_answer(korean: str):
    path = os.path.join(ANSWERS_DIR, f"{korean}.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else [data]


def capture_user_frames(holistic, cap, word_info):
    """3초 카운트다운 → RECORD_DURATION초 동안 사용자 수화 캡처"""
    print(f"\n  '{word_info['korean']}' 수화를 해보세요!")

    start_time     = time.time()
    capture_start  = None
    frames_data    = []
    last_capture_t = -1.0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        analysis_frame = frame.copy()
        display_frame  = cv2.flip(frame, 1)
        h, w = display_frame.shape[:2]

        # 상단 배너
        cv2.rectangle(display_frame, (0, 0), (w, 75), (20, 20, 60), -1)
        cv2.putText(display_frame,
                    f"Check: {word_info['english']}  ({word_info['korean']})",
                    (15, 52), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (100, 200, 255), 2)

        elapsed   = time.time() - start_time
        remaining = 3.0 - elapsed

        if remaining > 0:
            cv2.putText(display_frame, str(int(remaining) + 1),
                        (w // 2 - 50, h // 2 + 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 8, (0, 230, 230), 12)

        else:
            if capture_start is None:
                capture_start = time.time()

            cap_elapsed = time.time() - capture_start

            if cap_elapsed < RECORD_DURATION:
                progress = cap_elapsed / RECORD_DURATION
                bar_w    = int(w * progress)
                cv2.rectangle(display_frame, (0, h - 18), (bar_w, h), (100, 180, 255), -1)

                if cap_elapsed - last_capture_t >= 1.0 / TARGET_FPS:
                    image = cv2.cvtColor(analysis_frame, cv2.COLOR_BGR2RGB)
                    image.flags.writeable = False
                    results = holistic.process(image)
                    frames_data.append(extract_feature_json(results))
                    last_capture_t = cap_elapsed

                cv2.putText(display_frame,
                            f"GO!  {len(frames_data)} frames",
                            (15, h // 2),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (100, 200, 255), 2)

            else:
                # 채점
                return frames_data

        cv2.imshow("Sign Checker", display_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            return None

    return frames_data if frames_data else None


def show_result(cap, word_info, is_correct, score, wait_ms=2500):
    """결과 화면 표시"""
    ret, frame = cap.read()
    if not ret:
        return
    display_frame = cv2.flip(frame, 1)
    h, w = display_frame.shape[:2]

    color       = (0, 180, 0)  if is_correct else (0, 0, 200)
    label       = "PASS!"      if is_correct else "TRY AGAIN"
    score_color = (200, 255, 200) if is_correct else (200, 200, 255)

    overlay = display_frame.copy()
    cv2.rectangle(overlay, (0, h // 2 - 70), (w, h // 2 + 80), color, -1)
    cv2.addWeighted(overlay, 0.75, display_frame, 0.25, 0, display_frame)

    cv2.putText(display_frame, label,
                (w // 2 - 155, h // 2 + 12),
                cv2.FONT_HERSHEY_SIMPLEX, 2.5, (255, 255, 255), 5)
    cv2.putText(display_frame, f"Score: {score:.0%}",
                (w // 2 - 90, h // 2 + 68),
                cv2.FONT_HERSHEY_SIMPLEX, 1.3, score_color, 3)

    cv2.imshow("Sign Checker", display_frame)
    cv2.waitKey(wait_ms)


def print_summary(results_log):
    print("\n" + "=" * 52)
    print("  최종 결과 요약")
    print("=" * 52)
    passed = 0
    for r in results_log:
        if r.get("skipped"):
            status = "⏭  건너뜀"
        elif r["passed"]:
            status = "✅ 통과"
            passed += 1
        else:
            status = "❌ 미통과"
        print(f"  {r['korean']:4s}  {status}  ({r['attempts']}번 시도, 최고 점수: {r['best_score']:.0%})")
    print("-" * 52)
    print(f"  통과: {passed} / {len(results_log)} 단어")
    print("=" * 52)


def main():
    print("=" * 52)
    print("    수어 확인 프로그램 (동적 수화)")
    print("=" * 52)

    available = [w for w in WORDS if load_answer(w["korean"]) is not None]
    missing   = [w for w in WORDS if w not in available]

    if missing:
        print(f"⚠️  정답 없는 단어: {', '.join(w['korean'] for w in missing)}")
        print("   answer_generator.py 를 먼저 실행해주세요!\n")

    if not available:
        print("❌ 확인 가능한 단어가 없습니다.")
        return

    print(f"확인 가능한 단어: {', '.join(w['korean'] for w in available)}\n")

    print("[모드 선택]")
    print("  1. 전체 단어 순서대로 확인")
    print("  2. 특정 단어만 선택해서 확인")
    mode = input("\n선택 (1 또는 2): ").strip()

    if mode == "2":
        print()
        for w in WORDS:
            tag = "✅" if w in available else "❌"
            print(f"  {w['id']}. {tag} {w['korean']} ({w['english']})")
        idx = input("번호 입력: ").strip()
        try:
            chosen = next(w for w in WORDS if str(w["id"]) == idx)
            words_to_check = [chosen] if chosen in available else []
        except StopIteration:
            words_to_check = []
        if not words_to_check:
            print("⚠️  선택한 단어의 정답이 없거나 번호가 잘못됐습니다.")
            return
    else:
        words_to_check = available

    input("\n준비되면 Enter 를 눌러 시작하세요...")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ 웹캠을 열 수 없습니다.")
        return

    results_log = []

    mp_holistic = mp.solutions.holistic
    with mp_holistic.Holistic(
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    ) as holistic:

        for word_info in words_to_check:
            answer_frames = load_answer(word_info["korean"])
            if answer_frames is None:
                continue

            attempts   = 0
            passed     = False
            best_score = 0.0

            while True:
                attempts += 1
                input(f"\n[{word_info['korean']}] 준비 후 Enter (시도 {attempts}회): ")

                user_frames = capture_user_frames(holistic, cap, word_info)

                if user_frames is None:
                    cap.release()
                    cv2.destroyAllWindows()
                    print_summary(results_log)
                    return

                # 동적 채점
                result     = evaluate_dynamic_sign(user_frames, answer_frames)
                score      = result["score"]
                is_correct = score >= PASS_THRESHOLD
                best_score = max(best_score, score)

                if is_correct:
                    print(f"  ✅ 정답!  (점수: {score:.1%})")
                else:
                    print(f"  ❌ 틀렸어요  (점수: {score:.1%})")

                show_result(cap, word_info, is_correct, score)

                if is_correct:
                    passed = True
                    results_log.append({
                        "korean": word_info["korean"],
                        "passed": True,
                        "attempts": attempts,
                        "best_score": best_score,
                    })
                    break
                else:
                    retry = input("다시 시도하시겠습니까? (y / n): ").strip().lower()
                    if retry != "y":
                        results_log.append({
                            "korean": word_info["korean"],
                            "passed": False,
                            "attempts": attempts,
                            "best_score": best_score,
                            "skipped": True,
                        })
                        break

    cap.release()
    cv2.destroyAllWindows()
    print_summary(results_log)


if __name__ == "__main__":
    main()
