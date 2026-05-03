import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

import cv2
import mediapipe as mp
import json
import time
import numpy as np
from app.services.feature_extractor import extract_feature_json

WORDS = [
    {"id": 1, "korean": "엄마",  "english": "Mom"},
    {"id": 2, "korean": "아빠",  "english": "Dad"},
    {"id": 3, "korean": "사랑해", "english": "I Love You"},
    {"id": 4, "korean": "나",    "english": "Me / I"},
    {"id": 5, "korean": "아들",  "english": "Son"},
    {"id": 6, "korean": "딸",   "english": "Daughter"},
]

PROJECT_ROOT    = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
SAVE_DIR        = os.path.join(PROJECT_ROOT, "answers", "korean")
RECORD_DURATION = 3.0   # 녹화 시간 (초)
TARGET_FPS      = 5     # 초당 저장 프레임 수


class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):  return int(obj)
        if isinstance(obj, np.floating): return float(obj)
        if isinstance(obj, np.bool_):    return bool(obj)
        if isinstance(obj, np.ndarray):  return obj.tolist()
        return super().default(obj)


def capture_frames(holistic, cap, word_info):
    """3초 카운트다운 → RECORD_DURATION초 동안 연속 프레임 캡처"""
    print(f"\n[{word_info['id']}/6] '{word_info['korean']}' ({word_info['english']}) — 준비하세요!")

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
        cv2.rectangle(display_frame, (0, 0), (w, 75), (20, 20, 20), -1)
        cv2.putText(display_frame,
                    f"[{word_info['id']}/6] {word_info['english']}",
                    (15, 52), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 220, 50), 2)

        elapsed   = time.time() - start_time
        remaining = 3.0 - elapsed

        if remaining > 0:
            # 카운트다운
            cv2.putText(display_frame, str(int(remaining) + 1),
                        (w // 2 - 50, h // 2 + 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 8, (0, 230, 230), 12)

        else:
            if capture_start is None:
                capture_start = time.time()
                print(">>> 녹화 시작!")

            cap_elapsed = time.time() - capture_start

            if cap_elapsed < RECORD_DURATION:
                # 녹화 중 — 진행바
                progress = cap_elapsed / RECORD_DURATION
                bar_w    = int(w * progress)
                cv2.rectangle(display_frame, (0, h - 18), (bar_w, h), (0, 200, 0), -1)

                # TARGET_FPS 맞춰서 프레임 저장
                if cap_elapsed - last_capture_t >= 1.0 / TARGET_FPS:
                    image = cv2.cvtColor(analysis_frame, cv2.COLOR_BGR2RGB)
                    image.flags.writeable = False
                    results = holistic.process(image)
                    raw = extract_feature_json(results)
                    frame_clean = {k: v for k, v in raw.items() if k != "non_manual_signal"}
                    frames_data.append(frame_clean)
                    last_capture_t = cap_elapsed

                cv2.putText(display_frame,
                            f"REC  {len(frames_data)} frames",
                            (15, h // 2),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 80), 2)

            else:
                # 녹화 완료
                cv2.rectangle(display_frame, (0, h // 2 - 55), (w, h // 2 + 55), (0, 140, 0), -1)
                cv2.putText(display_frame,
                            f"Done!  {len(frames_data)} frames",
                            (w // 2 - 175, h // 2 + 18),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.4, (255, 255, 255), 3)
                cv2.imshow("Answer Generator", display_frame)
                cv2.waitKey(1500)
                return frames_data

        cv2.imshow("Answer Generator", display_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            return None

    return frames_data if frames_data else None


def main():
    os.makedirs(SAVE_DIR, exist_ok=True)

    print("=" * 52)
    print("    수어 정답 녹화 프로그램 (동적 수화)")
    print("=" * 52)
    print(f"대상 단어: {', '.join(w['korean'] for w in WORDS)}")
    print(f"저장 위치: {SAVE_DIR}")
    print(f"녹화 시간: {RECORD_DURATION}초 / {TARGET_FPS}fps\n")

    already = [w for w in WORDS if os.path.exists(os.path.join(SAVE_DIR, f"{w['korean']}.json"))]
    pending = [w for w in WORDS if w not in already]

    if already:
        print(f"이미 녹화됨: {', '.join(w['korean'] for w in already)}")
        ans = input("다시 전체 녹화하시겠습니까? (y / n, 기본 n): ").strip().lower()
        words_to_record = WORDS if ans == 'y' else pending
    else:
        words_to_record = WORDS

    if not words_to_record:
        print("\n모든 단어가 이미 녹화되어 있습니다. sign_checker.py 를 실행하세요!")
        return

    print(f"\n녹화할 단어: {', '.join(w['korean'] for w in words_to_record)}")
    input("준비되면 Enter 를 눌러 시작하세요...")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ 웹캠을 열 수 없습니다.")
        return

    mp_holistic = mp.solutions.holistic
    with mp_holistic.Holistic(
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    ) as holistic:

        for word_info in words_to_record:
            input(f"\n'{word_info['korean']}' 수화 준비 후 Enter 를 누르세요: ")

            frames = capture_frames(holistic, cap, word_info)

            if frames is None:
                print(f"⚠️  '{word_info['korean']}' 녹화 취소")
                break

            save_path = os.path.join(SAVE_DIR, f"{word_info['korean']}.json")
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(frames, f, indent=2, cls=NumpyEncoder, ensure_ascii=False)
            print(f"✅  저장 완료 ({len(frames)}프레임) → {save_path}")

    cap.release()
    cv2.destroyAllWindows()

    print("\n" + "=" * 52)
    print("  모든 녹화 완료! sign_checker.py 를 실행하세요.")
    print("=" * 52)


if __name__ == "__main__":
    main()
