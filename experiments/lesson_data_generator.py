import sys
import os
import cv2
import mediapipe as mp
import json
import time
import numpy as np
import requests
import tempfile
from datetime import datetime

# 현재 파일(answer_generator.py)의 부모의 부모 디렉토리(프로젝트 루트)를 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from app.services.feature_extractor import extract_feature_json
from app.services.expression_analyzation_service import analyze_expression_with_llm

API_BASE_URL = os.getenv("BACKEND_ENDPOINT")
X_ADMIN_KEY = os.getenv("X_ADMIN_KEY")

# === 설정 및 초기화 ===
mp_holistic = mp.solutions.holistic
mp_drawing = mp.solutions.drawing_utils

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NumpyEncoder, self).default(obj)

def generate_static_lesson():
    cap = cv2.VideoCapture(0)
    
    with mp_holistic.Holistic(
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5) as holistic:
        
        print(">>> 3초 카운트다운 시작!")
        start_time = time.time()
        
        captured_data = None
        final_image = None
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # 분석용 원본 프레임 (정방향)
            analysis_frame = frame.copy()
            # 화면 출력용 프레임 (거울모드)
            display_frame = cv2.flip(frame, 1)

            elapsed = time.time() - start_time
            remaining = 3 - elapsed

            if remaining > 0:
                text = str(int(remaining) + 1)
                cv2.putText(display_frame, text, (300, 250),
                            cv2.FONT_HERSHEY_SIMPLEX, 7, (0, 255, 255), 10)
                cv2.imshow('Hand Capture', display_frame)
                cv2.waitKey(1)
                continue
            else:
                print(">>> 캡처 및 분석 중...")

                # 1. MediaPipe 분석은 '정방향(analysis_frame)'으로 수행
                image = cv2.cvtColor(analysis_frame, cv2.COLOR_BGR2RGB)
                image.flags.writeable = False
                results = holistic.process(image)

                # LLM 분석용 바이트 변환 (정방향 사용)
                _, buffer = cv2.imencode('.jpg', analysis_frame)
                image_bytes = buffer.tobytes()

                expression = analyze_expression_with_llm(image_bytes)
                captured_data = extract_feature_json(results, expression)
                
                # 2. [수정됨] 업로드용 이미지는 '거울모드'로 저장
                final_image = cv2.flip(analysis_frame, 1) 

                cv2.putText(display_frame, "Captured!", (50, 250),
                            cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 0), 3)
                cv2.imshow('Hand Capture', display_frame)
                cv2.waitKey(1000)
                break

    cap.release()
    cv2.destroyAllWindows()
    return captured_data, final_image

# ... (앞부분 import 생략) ...

def generate_dynamic_lesson(duration_sec):
    cap = cv2.VideoCapture(0)
    
    # [핵심] 해상도를 640x480으로 강제 다운사이징 (용량 다이어트)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    filename = f"sign_video_{int(time.time())}.mov"
    save_path = os.path.join(current_dir, filename)
    
    fourcc = cv2.VideoWriter_fourcc(*'avc1') 
    
    # 실제 설정된 해상도 확인
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = 30.0 # 고정 30fps
    
    out = cv2.VideoWriter(save_path, fourcc, fps, (width, height))

    frames_to_analyze = [] 
    
    print(f">>> 녹화 해상도 설정: {width}x{height} (용량 최적화 모드)")

    # [Phase 0] 카운트다운
    start_time = time.time()
    while (time.time() - start_time) < 3:
        ret, frame = cap.read()
        if not ret: break
        display_frame = cv2.flip(frame, 1)
        remaining = 3 - (time.time() - start_time)
        cv2.putText(display_frame, str(int(remaining) + 1), (150, 200), # 텍스트 위치 조정
                        cv2.FONT_HERSHEY_SIMPLEX, 4, (0, 255, 255), 5)
        cv2.imshow('Video Capture', display_frame)
        cv2.waitKey(1)

    # [Phase 1] 고속 녹화
    print(">>> 🎥 녹화 시작!")
    record_start_time = time.time()
    last_capture_time = record_start_time - 1.0
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break
        
        current_time = time.time()
        elapsed = current_time - record_start_time

        if elapsed > duration_sec:
            break

        out.write(cv2.flip(frame, 1))

        if (current_time - last_capture_time) >= 1.0:
            frames_to_analyze.append(frame.copy())
            last_capture_time = current_time

        display_frame = cv2.flip(frame, 1)
        cv2.putText(display_frame, "REC", (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        cv2.imshow('Video Capture', display_frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    out.release()
    cv2.destroyAllWindows()
    
    # [용량 확인 로그 추가]
    file_size_mb = os.path.getsize(save_path) / (1024 * 1024)
    print(f">>> 📁 생성된 파일 크기: {file_size_mb:.2f} MB")

    if file_size_mb > 10.0:
        print(">>> ⚠️ 경고: 파일 크기가 10MB를 초과했습니다. 업로드 실패 가능성이 높습니다.")

    # [Phase 2] AI 분석 (생략 없이 진행)
    print(f"\n>>> 🧠 녹화 완료. AI 분석 시작 (총 {len(frames_to_analyze)}장)...")
    
    captured_jsons = []
    
    with mp_holistic.Holistic(
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5) as holistic:
        
        for idx, analysis_frame in enumerate(frames_to_analyze):
            # print(f"  ... Analyzing frame {idx + 1}")
            image_rgb = cv2.cvtColor(analysis_frame, cv2.COLOR_BGR2RGB)
            image_rgb.flags.writeable = False
            results = holistic.process(image_rgb)

            _, buffer = cv2.imencode('.jpg', analysis_frame)
            image_bytes = buffer.tobytes()

            expression = analyze_expression_with_llm(image_bytes)
            feature_json = extract_feature_json(results, expression)
            
            captured_jsons.append(feature_json)

    if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
        print(f">>> ✅ 영상 파일 준비 완료: {save_path}")
    else:
        return [], None
    
    return captured_jsons, save_path
def post_images(image):
    url = f"{API_BASE_URL}/api/storage/images"
    
    # OpenCV 이미지를 바이트로 변환
    _, img_encoded = cv2.imencode('.jpg', image)
    img_bytes = img_encoded.tobytes()
    
    # multipart/form-data 설정
    files = {
        'file': ('image.jpg', img_bytes, 'image/jpeg')
    }
    headers = {'X-ADMIN-KEY': X_ADMIN_KEY}

    try:
        response = requests.post(url, headers=headers, files=files)
        response.raise_for_status()
        result = response.json()
        print(f"✅ Image Upload Success: {result['uploadUrl']}")
        return result['uploadUrl']
    except Exception as e:
        print(f"❌ Image Upload Failed: {e}")
        return None
    
def post_videos(video_path):
    url = f"{API_BASE_URL}/api/storage/videos"
    
    # [수정 3] Swagger 요청과 동일한 헤더 구성
    headers = {
        'X-ADMIN-KEY': X_ADMIN_KEY
    }
    
    print(f">>> 업로드 시도: {video_path}")

    try:
        with open(video_path, 'rb') as f:
            # [수정 4] MIME 타입을 Swagger와 동일하게 'video/quicktime'으로 지정
            # 파일명도 .mov로 명시
            files = {
                'file': ('video.mov', f, 'video/quicktime')
            }
            
            # timeout을 넉넉하게 60초로 설정 (502 Timeout 방지)
            response = requests.post(url, headers=headers, files=files, timeout=60)
            
            if response.status_code != 200:
                print(f"❌ Server Error ({response.status_code}): {response.text}")
            
            response.raise_for_status()
            result = response.json()
            print(f"✅ Video Upload Success: {result['uploadUrl']}")
            return result['uploadUrl']
    except requests.exceptions.Timeout:
        print("❌ Upload Timeout: 서버 응답이 너무 늦습니다. 파일이 너무 크거나 백엔드 처리가 느립니다.")
        return None
    except Exception as e:
        print(f"❌ Video Upload Failed: {e}")
        return None
def post_lessons(category_id, title, sign_language, difficulty, type, mode, frame_number, image_url, video_url):
    url = f"{API_BASE_URL}/api/lessons"
    
    payload = {
        "categoryId": category_id,
        "title": title,
        "signLanguage": sign_language,
        "difficulty": difficulty,
        "type": type,
        "mode": mode,
        "imageUrl": image_url,
        "videoUrl": video_url,
        "frameNumber": frame_number
    }
    
    headers = {
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        print(f"✅ Lesson Created: ID {result['id']}")
        return result['id']
    except Exception as e:
        print(f"❌ Lesson Creation Failed: {e}")
        return None

def post_answer_frames(lesson_id, seq, answer_frame):
    url = f"{API_BASE_URL}/api/lessons/{lesson_id}/answer-frames"
    
    payload = {
        "seq": seq,
        "hand": answer_frame, 
        "frameMeta": "meta_data_placeholder"
    }
    
    json_data = json.dumps(payload, cls=NumpyEncoder)
    
    headers = {
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, data=json_data, headers=headers)
        response.raise_for_status()
        print(f"✅ Answer Frame {seq} Uploaded")
    except Exception as e:
        print(f"❌ Answer Frame Upload Failed: {e}")

def main():
    print("=== Sign Language Content Generator ===")
    try:
        category_id = int(input("Category ID : "))
        title = input("Title : ")
        sign_language = input("Sign Language (e.g. KSL, ASL) : ")
        difficulty = int(input("Difficulty (1-5) : "))
        is_word = input("Is Word? (y/n) : ").lower().startswith('y')
        type = "WORD" if is_word else "PHRASE"
        frame_number = int(input("Frame Number (Duration in sec) : "))
    except ValueError:
        print("Invalid Input.")
        return

    mode = None
    image_url = None
    video_url = None
    lesson_id = None

    if frame_number == 1:
        # 정적 이미지 로직 (생략 - 기존 유지)
        mode = "STATIC"
        hand_json, image = generate_static_lesson()
        if image is not None:
            image_url = post_images(image)
            if image_url:
                lesson_id = post_lessons(category_id, title, sign_language, difficulty, type, mode, frame_number, image_url, video_url)
                if lesson_id:
                    post_answer_frames(lesson_id, 1, hand_json)
    
    else:
        # 동적 비디오 로직
        mode = "DYNAMIC"
        hand_jsons, video_path = generate_dynamic_lesson(frame_number)
        
        if video_path and os.path.exists(video_path):
            video_url = post_videos(video_path)
            
            # [수정 3] 파일 삭제 코드 제거 (파일이 사라지는 원인)
            # os.remove(video_path) 
            # print(">>> 임시 파일 삭제 완료")
            
            if video_url:
                lesson_id = post_lessons(category_id, title, sign_language, difficulty, type, mode, frame_number, image_url, video_url)
                
                if lesson_id:
                    for i, hand_json in enumerate(hand_jsons):
                        post_answer_frames(lesson_id, i + 1, hand_json)
            else:
                print(">>> ⚠️ 비디오 업로드 실패로 레슨 생성을 중단합니다.")
        else:
            print(">>> ⚠️ 비디오 파일이 없어서 업로드를 건너뜁니다.")

if __name__ == "__main__":
    main()