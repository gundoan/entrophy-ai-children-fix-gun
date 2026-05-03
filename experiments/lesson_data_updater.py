import sys
import os
import mediapipe as mp
import json
import requests

# 현재 파일(answer_generator.py)의 부모의 부모 디렉토리(프로젝트 루트)를 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from app.services.feature_extractor import extract_feature_json
from app.services.expression_analyzation_service import analyze_expression_with_llm
from lesson_data_generator import NumpyEncoder, generate_static_lesson, generate_dynamic_lesson, post_images, post_videos

API_BASE_URL = os.getenv("BACKEND_ENDPOINT")
X_ADMIN_KEY = os.getenv("X_ADMIN_KEY")

# === 설정 및 초기화 ===
mp_holistic = mp.solutions.holistic
mp_drawing = mp.solutions.drawing_utils

# === Lesson CRUD 함수 ===
def get_lessons(lesson_id):
    """레슨 정보 조회"""
    url = f"{API_BASE_URL}/api/lessons/{lesson_id}"
    try:
        res = requests.get(url)
        res.raise_for_status()
        data = res.json()
        print(f"✅ Lesson Loaded: {data['title']} (Mode: {data.get('mode', 'Unknown')})")
        return data
    except Exception as e:
        print(f"❌ Get Lesson Failed: {e}")
        return None

def put_lessons(lesson_id, lesson_data, new_image_url=None, new_video_url=None):
    """레슨 정보 업데이트"""
    url = f"{API_BASE_URL}/api/lessons/{lesson_id}"
    
    # 기존 데이터에 새 URL 덮어쓰기
    payload = lesson_data.copy()
    
    # 불필요한 필드 제거 (응답에는 있지만 요청엔 필요 없는 것들)
    payload.pop('id', None)
    payload.pop('categoryName', None)
    
    # 새 미디어가 있으면 교체, 없으면 기존 것 유지
    if new_image_url:
        payload['imageUrl'] = new_image_url
    if new_video_url:
        payload['videoUrl'] = new_video_url

    headers = {"Content-Type": "application/json"}
    try:
        res = requests.put(url, json=payload, headers=headers)
        res.raise_for_status()
        print(f"✅ Lesson Updated: ID {lesson_id}")
        return lesson_id
    except Exception as e:
        print(f"❌ Put Lesson Failed: {e}")
        return None

def put_answer_frames(lesson_id, seq, answer_frame):
    """정답 프레임 업데이트"""
    url = f"{API_BASE_URL}/api/lessons/{lesson_id}/answer-frames/{seq}"
    
    payload = {
        "seq": seq,
        "hand": answer_frame,
        "frameMeta": f"frame_{seq}_updated"
    }
    
    headers = {"Content-Type": "application/json"}
    
    # NumpyEncoder를 사용하여 JSON 직렬화
    json_data = json.dumps(payload, cls=NumpyEncoder)

    try:
        res = requests.put(url, data=json_data, headers=headers)
        res.raise_for_status()
        print(f"✅ Answer Frame {seq} Updated")
    except Exception as e:
        print(f"❌ Put Answer Frame Failed: {e}")

# === Main Logic ===
def main():
    print("=== Sign Language Lesson Updater ===")
    
    # 1. Lesson ID 입력 및 조회
    try:
        lesson_id_input = input("Target Lesson ID to Update: ")
        lesson_id = int(lesson_id_input)
    except ValueError:
        print("Invalid ID.")
        return

    # 2. 기존 정보 가져오기
    current_data = get_lessons(lesson_id)
    if not current_data:
        print("Cannot find lesson.")
        return

    print(f"\n[Current Info] Title: {current_data['title']}, Mode: {current_data.get('mode')}")
    
    # 3. 재촬영 여부 확인
    confirm = input("Do you want to re-record this lesson? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Update cancelled.")
        return

    # 4. 모드에 따른 재촬영 및 업데이트
    # 기존 데이터의 mode를 기준으로 판단 (없으면 STATIC 가정)
    mode = current_data.get('mode', 'STATIC')
    
    new_image_url = None
    new_video_url = None

    if mode == 'STATIC':
        # 정적 이미지 재촬영
        hand_json, image = generate_static_lesson()
        
        if image is not None:
            print("Uploading Image...")
            new_image_url = post_images(image)
            
            if new_image_url:
                # 레슨 메타데이터 업데이트 (이미지 URL 교체)
                if put_lessons(lesson_id, current_data, new_image_url=new_image_url):
                    # 정답 프레임 업데이트 (seq=1)
                    put_answer_frames(lesson_id, 1, hand_json)

    elif mode == 'DYNAMIC':
        # 동적 비디오 재촬영
        # 기존 frameNumber(길이)를 가져오거나 기본값 사용
        duration = int(input("Frame Number : "))
        print(f"Recording for {duration} seconds...")
        
        hand_jsons, video_path = generate_dynamic_lesson(duration)
        
        if video_path:
            print("Uploading Video...")
            new_video_url = post_videos(video_path)
            
            # (옵션) 썸네일용으로 첫 프레임을 이미지로 올릴 수도 있음
            # new_image_url = ... 
            
            if new_video_url:
                # 레슨 메타데이터 업데이트 (비디오 URL 교체)
                if put_lessons(lesson_id, current_data, new_video_url=new_video_url):
                    # 정답 프레임 리스트 업데이트
                    for i, hand_json in enumerate(hand_jsons):
                        put_answer_frames(lesson_id, i + 1, hand_json)
            
            # 임시 파일 삭제
            if os.path.exists(video_path):
                os.remove(video_path)

    else:
        print(f"Unknown mode: {mode}")

if __name__ == "__main__":
    main()