import json
from pathlib import Path
import os 
import requests

API_BASE_URL = os.getenv("BACKEND_ENDPOINT")
def get_answer_frame(lessonId: int) -> dict:
    """
    GET /api/lessons/{lessonId}/answer-frames
    API 응답의 'hand' 필드 안에 있는 데이터를 추출하여 반환
    """
    url = f"{API_BASE_URL}/api/lessons/{lessonId}/answer-frames"
    
    # 반환할 기본 구조 초기화
    result_data = {
        "left": {},
        "right": {},
        "inter_hand_relation": {},
        "finger_relation": {}
    }

    try:
        response = requests.get(url)
        response.raise_for_status()
        
        frames_list = response.json()
        
        # 데이터가 비어있으면 빈 딕셔너리 반환
        if not frames_list:
            print("⚠️ API 응답 리스트가 비어있습니다.")
            return result_data

        # 리스트의 첫 번째 아이템(혹은 필요한 아이템)을 가져옵니다.
        # 보통 정답 프레임은 하나라고 가정합니다.
        item = frames_list[0]
        
        # 'hand' 딕셔너리를 가져옴 (여기에 진짜 데이터가 있음)
        hand_data = item.get('hand', {})
        
        if not isinstance(hand_data, dict):
            print(f"⚠️ 'hand' 필드가 딕셔너리가 아닙니다: {type(hand_data)}")
            return result_data

        # API 구조 그대로 매핑
        # hand_data 안에 이미 'left', 'right' 키가 존재함
        if 'left' in hand_data:
            result_data['left'] = hand_data['left']
        
        if 'right' in hand_data:
            result_data['right'] = hand_data['right']
            
        if 'inter_hand_relation' in hand_data:
            result_data['inter_hand_relation'] = hand_data['inter_hand_relation']
            
        if 'finger_relation' in hand_data:
            result_data['finger_relation'] = hand_data['finger_relation']

        if 'non_manual_signal' in hand_data:
            result_data['non_manual_signal'] = hand_data['non_manual_signal']

        print("✅ 정답 데이터 로딩 성공!")
        return result_data

    except requests.exceptions.RequestException as e:
        print(f"❌ API 호출 중 오류 발생: {e}")
        return result_data
    
def get_answer_frames(lessonId: int) -> list:
    """
    [NEW] DB에 저장된 정답 프레임 '전체 리스트'를 가져와서 반환
    """
    url = f"{API_BASE_URL}/api/lessons/{lessonId}/answer-frames"
    
    clean_frames = []

    try:
        response = requests.get(url)
        response.raise_for_status()
        
        frames_list = response.json()
        
        if not frames_list:
            print("⚠️ API 응답 리스트가 비어있습니다.")
            return []

        # 리스트를 순회하며 필요한 데이터만 정제
        for item in frames_list:
            hand_data = item.get('hand', {})
            
            # 데이터 구조 매핑 (null safe)
            frame_data = {
                "left": hand_data.get('left', {}),
                "right": hand_data.get('right', {}),
                "inter_hand_relation": hand_data.get('inter_hand_relation', {}),
                "finger_relation": hand_data.get('finger_relation', {})
            }
            clean_frames.append(frame_data)

        print(f"✅ 총 {len(clean_frames)}개의 정답 프레임 로딩 성공!")
        return clean_frames

    except requests.exceptions.RequestException as e:
        print(f"❌ API 호출 중 오류 발생: {e}")
        return []

def get_test_answer_frame():
    """
    임시 테스트용 정답 로더
    answers/hand.json 파일을 정답으로 간주한다.
    """

    # 현재 파일 기준 경로
    base_dir = Path(__file__).resolve().parent.parent
    answer_path = base_dir / "answers" / "hand.json"

    if not answer_path.exists():
        raise FileNotFoundError(f"정답 파일을 찾을 수 없습니다: {answer_path}")

    with open(answer_path, "r", encoding="utf-8") as f:
        answer_data = json.load(f)

    return answer_data

# def get_lesson_word(lessonId: int) -> str:
#     """
#     [NEW] GET /api/lessons/{lessonId}
#     레슨 ID로 단어 이름(wordName)을 조회하여 반환
#     """
#     url = f"{API_BASE_URL}/api/lessons/{lessonId}"
    
#     try:
#         response = requests.get(url)
#         response.raise_for_status()
        
#         data = response.json()
        
#         word_name = data.get("title") 
        
#         if not word_name:
#             print(f"⚠️ 레슨 {lessonId}의 단어 이름이 없습니다. 응답: {data}")
#             return None

#         print(f"✅ 단어 조회 성공: ID {lessonId} -> {word_name}")
#         return word_name

#     except requests.exceptions.RequestException as e:
#         print(f"❌ 단어 조회 API 실패 (ID: {lessonId}): {e}")
#         return None