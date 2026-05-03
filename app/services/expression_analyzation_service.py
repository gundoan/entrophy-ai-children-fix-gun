# from azure.cognitiveservices.vision.customvision.prediction import CustomVisionPredictionClient
from msrest.authentication import ApiKeyCredentials
import os
import base64
import requests

# 환경 변수에서 가져오기 (Azure Portal -> Configuration에 꼭 등록해야 함!)
# ENDPOINT = os.environ.get("CUSTOM_VISION_ENDPOINT")
# PREDICTION_KEY = os.environ.get("CUSTOM_VISION_KEY")
# PROJECT_ID = os.environ.get("CUSTOM_VISION_PROJECT_ID")
# PUBLISH_ITERATION_NAME = "face-expression-1" # Publish 할 때 지은 이름

# # 클라이언트 초기화
# credentials = ApiKeyCredentials(in_headers={"Prediction-key": PREDICTION_KEY})
# predictor = CustomVisionPredictionClient(ENDPOINT, credentials)

# def analyze_expression(image_bytes: bytes) -> str:
#     """
#     이미지를 Custom Vision에 보내서 가장 확률 높은 표정 태그(문자열)를 반환
#     """
#     try:
#         results = predictor.classify_image(
#             PROJECT_ID, 
#             PUBLISH_ITERATION_NAME, 
#             image_bytes
#         )
        
#         # 확률(Probability)이 가장 높은 예측 결과 가져오기
#         if not results.predictions:
#             return "Unknown"

#         best_prediction = max(results.predictions, key=lambda x: x.probability)
        
#         # 확률이 너무 낮으면(예: 50% 미만) 신뢰할 수 없음 처리
#         if best_prediction.probability < 0.5:
#             return "Uncertain"
            
#         return best_prediction.tag_name

#     except Exception as e:
#         print(f"❌ Custom Vision Error: {e}")
#         return "Error"
import os
import base64
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

_model = None

def _get_model():
    global _model
    if _model is None:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        _model = genai.GenerativeModel('gemini-2.0-flash')
    return _model

def analyze_expression_with_llm(image_bytes: bytes) -> str:
    """
    Gemini 1.5 Flash (Vision)를 사용하여
    표정을 Question / Positive / Negative / Neutral 중 하나로 분류
    """
    try:
        # 1. 이미지 데이터 준비 (Gemini SDK는 딕셔너리 형태로 데이터를 받습니다)
        image_part = {
            "mime_type": "image/jpeg",  # 혹은 이미지 형식에 맞게 조정
            "data": image_bytes
        }

        # 2. 시스템 프롬프트와 유저 프롬프트 구성
        system_instruction = (
            "You are an AI assistant that analyzes a user's facial expression from an image.\n"
            "You MUST choose exactly one of the following labels:\n"
            "- Question (questioning, interested, wondering)\n"
            "- Positive (happy, pleased, friendly)\n"
            "- Negative (angry, sad, frustrated)\n"
            "- Neutral (no clear emotion)\n\n"
            "Respond with ONLY the label name."
        )
        
        user_prompt = "Classify the facial expression in this image."

        # 3. Gemini 호출
        import google.generativeai as genai
        response = _get_model().generate_content(
            [system_instruction, image_part, user_prompt],
            generation_config=genai.types.GenerationConfig(
                temperature=0,  # 정확도를 위해 0 설정
                max_output_tokens=10
            )
        )

        label = response.text.strip()

        # 4. 허용된 라벨인지 검증
        allowed = {"Question", "Positive", "Negative", "Neutral"}
        
        # 가끔 Gemini가 마침표(.)를 찍는 경우가 있어 제거 후 비교
        clean_label = label.replace(".", "")
        return clean_label if clean_label in allowed else "Uncertain"

    except Exception as e:
        print(f"❌ Gemini Expression Error: {e}")
        return "Error"