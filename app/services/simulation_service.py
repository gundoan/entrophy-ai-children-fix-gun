# import json
# from app.ai.llm_client import call_gpt_json_async, call_dalle_image_async
# from app.models.schemas import SimulationResponse, DialogueLine

# async def generate_simulation_scenario(lesson_words: dict) -> SimulationResponse:
#     """
#     lesson_words: {lesson_id: "단어명", ...}
#     """
#     words_str = ", ".join(lesson_words.values())
    
#     # 1. GPT 프롬프트 작성
#     system_prompt = """
# You are a scenario writer for a sign language learning app.
# Your task is to generate a short first-person role-play conversation
# where the AI speaks directly to the user.

# THIS TASK IS STRICTLY STRUCTURAL.
# If the structure is broken, the output is INVALID.

# ==================================================
# ABSOLUTE CONVERSATION STRUCTURE (VERY IMPORTANT)
# ==================================================

# Let N = number of vocabulary words.

# The dialogue MUST follow this exact pattern:

# 1. AI Opening Turn (1 turn)
# 2. For EACH vocabulary word:
#    - User uses EXACTLY ONE vocabulary word
#    - AI responds naturally (NO vocabulary usage)
# 3. AI Closing Turn (1 turn, NO vocabulary usage)

# Therefore:
# - User turns = N
# - AI turns = N + 1
# - Total turns = (N × 2) + 1
# - The LAST turn MUST ALWAYS be spoken by AI

# ==================================================
# USER RESPONSE RULES
# ==================================================

# - The User is a learner who can ONLY respond with ONE WORD.
# - Each User response MUST be exactly one vocabulary word.
# - No punctuation, no explanation, no variation.
# - Each vocabulary word MUST be used EXACTLY ONCE.

# ==================================================
# AI RESPONSE RULES
# ==================================================

# - AI MUST start the conversation.
# - AI MUST end the conversation.
# - AI MUST NEVER use any vocabulary word.
# - The final AI turn MUST be a natural closing line
#   (e.g., encouragement, conclusion, or feedback).

# ==================================================
# IMAGE GENERATION RULE
# ==================================================

# - Write a vivid, descriptive situation suitable for image generation.
# - The image MUST be described from a FIRST-PERSON point of view.
# - The image_prompt MUST be written in English and optimized for DALL·E.

# ==================================================
# LANGUAGE RULE
# ==================================================

# - ALL text MUST be written in English.

# ==================================================
# OUTPUT FORMAT (JSON ONLY)
# ==================================================

# Return ONLY a valid JSON object.
# NO explanations. NO comments. NO extra text.

# {
#   "situation": "Situation (English)",
#   "image_prompt": "First-person view ... (English)",
#   "dialogue": [
#     { "speaker": "AI", "text": "..." },
#     { "speaker": "User", "text": "...", "target_word": "VOCAB" },
#     { "speaker": "AI", "text": "..." }
#   ]
# }

# ==================================================
# FINAL VALIDATION (MANDATORY)
# ==================================================

# Before outputting:
# - Check that the LAST dialogue item is spoken by AI
# - Check that AI turns = User turns + 1
# - Check that total turns = (N × 2) + 1
# - If ANY check fails, REGENERATE internally before outputting
# """

#     user_prompt = f"사용할 단어 목록: {json.dumps(lesson_words, ensure_ascii=False)}"

#     # 2. GPT 호출 (JSON 모드)
#     scenario_data = await call_gpt_json_async(system_prompt, user_prompt)
    
#     # 3. DALL-E 3 이미지 생성 호출
#     # 프롬프트에 '1인칭 시점' 등 스타일 추가
#     final_image_prompt = f"First-person view, photorealistic, {scenario_data['image_prompt']}, high quality"
#     image_url = await call_dalle_image_async(final_image_prompt)

#     # 4. 결과 매핑 (단어명 -> ID 변환)
#     word_to_id = {v: k for k, v in lesson_words.items()}
#     dialogue_list = []
    
#     for line in scenario_data["dialogue"]:
#         lid = None
#         # User 차례이고 target_word가 있으면 ID 찾기
#         if line["speaker"] == "User" and "target_word" in line:
#             target_w = line["target_word"]
#             # 정확히 일치하거나 포함되는 단어 찾기
#             for w, i in word_to_id.items():
#                 if w in target_w or target_w in w:
#                     lid = i
#                     break
        
#         dialogue_list.append(DialogueLine(
#             speaker=line["speaker"],
#             text=line["text"],
#             target_lesson_id=lid
#         ))

#     return SimulationResponse(
#         situation=scenario_data["situation"],
#         image_url=image_url,
#         dialogue=dialogue_list
#     )