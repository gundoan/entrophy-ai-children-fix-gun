import requests
import os
import json
from azure.cognitiveservices.vision.customvision.prediction import CustomVisionPredictionClient
from msrest.authentication import ApiKeyCredentials

VISION_ENDPOINT = os.getenv("VISION_ENDPOINT")
VISION_KEY = os.getenv("VISION_KEY")
FACE_ENDPOINT = os.getenv("FACE_ENDPOINT")
FACE_KEY = os.getenv("FACE_KEY")

def detect_hand_side(image_path: str):
    url = f"{VISION_ENDPOINT}/computervision/imageanalysis:analyze"
    params = {
        "api-version": "2024-02-01",
        "features": "people"
    }
    headers = {
        "Ocp-Apim-Subscription-Key": VISION_KEY,
        "Content-Type": "application/octet-stream"
    }

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    res = requests.post(url, params=params, headers=headers, data=image_bytes)
    res.raise_for_status()
    data = res.json()

    if not data.get("peopleResult", {}).get("values"):
        return None

    person = data["peopleResult"]["values"][0]
    person_box = person["boundingBox"]
    person_center_x = person_box["x"] + person_box["w"] / 2

    for part in person.get("bodyParts", []):
        if part["name"].lower() == "hand":
            hand_box = part["boundingBox"]
            hand_center_x = hand_box["x"] + hand_box["w"] / 2
            return hand_center_x > person_center_x  # True = right hand

    return None

def detect_expression(image_path: str, expected="happy"):
    url = f"{FACE_ENDPOINT}/face/v1.0/detect"
    params = {
        "returnFaceAttributes": "emotion",
        "detectionModel": "detection_01"
    }
    headers = {
        "Ocp-Apim-Subscription-Key": FACE_KEY,
        "Content-Type": "application/octet-stream"
    }

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    res = requests.post(url, params=params, headers=headers, data=image_bytes)
    res.raise_for_status()
    faces = res.json()

    if not faces:
        return False

    emotion_scores = faces[0]["faceAttributes"]["emotion"]
    dominant_emotion = max(emotion_scores, key=emotion_scores.get)

    return dominant_emotion == expected

ENDPOINT = os.getenv("CUSTOM_VISION_ENDPOINT")
PREDICTION_KEY = os.getenv("CUSTOM_VISION_KEY")
PROJECT_ID = os.getenv("CUSTOM_VISION_PROJECT_ID")
PUBLISH_ITERATION_NAME = "face-expression-1"

def test_custom_vision():
    # 1. 이미지 경로 설정 (현재 스크립트 위치 기준으로 상위 폴더의 test.jpg 찾기)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(current_dir, "..", "test.jpg")

    print(f"📂 이미지 경로: {image_path}")

    if not os.path.exists(image_path):
        print("❌ 루트 경로에 'test.jpg' 파일이 없습니다! 파일을 확인해주세요.")
        return

    # 2. 클라이언트 초기화
    try:
        credentials = ApiKeyCredentials(in_headers={"Prediction-key": PREDICTION_KEY})
        predictor = CustomVisionPredictionClient(ENDPOINT, credentials)
    except Exception as e:
        print(f"❌ 클라이언트 초기화 실패: {e}")
        return

    print("🚀 Custom Vision에 이미지 전송 중...")

    # 3. 예측 요청 및 결과 출력
    try:
        with open(image_path, "rb") as image_contents:
            results = predictor.classify_image(
                PROJECT_ID, 
                PUBLISH_ITERATION_NAME, 
                image_contents
            )

        print("\n✅ 분석 결과:")
        print("-" * 30)
        
        # 확률순 정렬
        sorted_predictions = sorted(results.predictions, key=lambda x: x.probability, reverse=True)

        for prediction in sorted_predictions:
            # 확률을 백분율로 표시
            probability = prediction.probability * 100
            print(f"🏷️  {prediction.tag_name:<15}: {probability:.2f}%")

        print("-" * 30)
        
        # 가장 높은 확률의 태그
        best_tag = sorted_predictions[0].tag_name
        best_prob = sorted_predictions[0].probability * 100
        print(f"🏆 최종 판단: [{best_tag}] ({best_prob:.2f}%)")

    except Exception as e:
        print(f"❌ 예측 중 오류 발생: {e}")
        print("팁: Project ID, Key, Endpoint, Iteration Name이 정확한지 확인해보세요.")

if __name__ == "__main__":
    
    # image = "test.jpg"

    # is_right_hand = detect_hand_side(image)
    # # expression_match = detect_expression(image, expected="happy")

    # print(json.dumps({
    #     "is_right_hand": is_right_hand,
    #     # "expression_match": expression_match
    # }, indent=2))

    test_custom_vision()