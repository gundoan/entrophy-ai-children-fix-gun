import os
import json
import asyncio
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# 모델을 처음 호출될 때 초기화 (서버 시작 시점 오류 방지)
_model = None
_model_json = None

def _get_model():
    global _model
    if _model is None:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        _model = genai.GenerativeModel('gemini-2.0-flash')
    return _model

def _get_model_json():
    global _model_json
    if _model_json is None:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        _model_json = genai.GenerativeModel(
            'gemini-2.0-flash',
            generation_config={"response_mime_type": "application/json"}
        )
    return _model_json

# [기존 함수 유지] 피드백 생성용 (동기 방식 유지)
def call_llm(prompt: str) -> str:
    import google.generativeai as genai
    system_instruction = (
        "너는 미국 수어(KSL) 학습자를 돕는 친절한 수어 코치야. "
        "틀렸으면 [정답 수어 특징]대로 사용자가 동작할 수 있도록 사용자에게 아주 짧지만 명확히 영어 1 문장으로 피드백해 줘. "
        "표정이 명시되어 있으면 그것도 포함해서 알려줘. 강조 기호는 사용하지마."
    )
    full_prompt = f"{system_instruction}\n\nUser: {prompt}"

    response = _get_model().generate_content(
        full_prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.4,
            max_output_tokens=300
        )
    )
    return response.text

# [NEW] 시나리오 생성용 (JSON 모드 지원 - 비동기)
# @retry(
#     stop=stop_after_attempt(3), 
#     wait=wait_exponential(multiplier=1, min=2, max=10)
# )
# async def call_gpt_json_async(system_prompt: str, user_prompt: str) -> dict:
#     full_prompt = f"{system_prompt}\n\nUser: {user_prompt}"
    
#     # 비동기 호출을 위해 loop.run_in_executor 사용 (SDK가 기본적으로 동기 위주임)
#     loop = asyncio.get_event_loop()
#     response = await loop.run_in_executor(
#         None, 
#         lambda: model_json.generate_content(
#             full_prompt,
#             generation_config=genai.types.GenerationConfig(temperature=0.7)
#         )
#     )
    
#     return json.loads(response.text)

# [NEW] 이미지 생성 호출 (DALL-E -> Gemini/Imagen 대체)
# 참고: Google AI Studio SDK에서 Imagen을 직접 호출하는 방식은 권한에 따라 다를 수 있습니다.
# 만약 Vertex AI가 아닌 일반 Gemini API를 쓰신다면 현재 텍스트 모델만 지원될 수 있습니다.
# 여기서는 기존 구조 유지를 위한 껍데기를 유지하거나, 필요 시 다른 이미지 API로 연결해야 합니다.
# @retry(
#     stop=stop_after_attempt(3), 
#     wait=wait_exponential(multiplier=1, min=2, max=10)
# )
# async def call_dalle_image_async(prompt: str) -> str:
#     """
#     현재 Google AI Studio Gemini API는 이미지 '생성' 결과물로 URL을 직접 반환하는 
#     DALL-E 스타일의 API와는 구조가 다릅니다(Vertex AI Imagen 사용 권장).
#     일단 로직 흐름을 위해 Imagen 모델 호출 구조로 작성해 두었습니다.
#     """
#     # 현재 무료 티어/일반 SDK에서는 이미지 생성이 제한적일 수 있으므로 
#     # 에러 발생 시를 대비한 예외 처리가 필요할 수 있습니다.
#     try:
#         imagen_model = genai.GenerativeModel('imagen-3') # 혹은 사용 가능한 이미지 모델
#         loop = asyncio.get_event_loop()
#         response = await loop.run_in_executor(
#             None,
#             lambda: imagen_model.generate_content(prompt)
#         )
#         # 이미지 URL 반환 로직 (SDK 버전에 따라 다름)
#         return response.candidates[0].content.parts[0].inline_data.data # 예시 구조
#     except Exception as e:
#         print(f"Image generation failed: {e}")
#         return "https://via.placeholder.com/1024" # 실패 시 대체 이미지