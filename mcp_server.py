import asyncio
import json
from mcp.server.fastmcp import FastMCP

# 기존 서비스 함수들 임포트 (경로에 맞게 수정하세요)
from app.services.lesson_service import get_lesson_word, get_answer_frame
from app.services.simulation_service import generate_simulation_scenario
from app.services.feedback_service import generate_feedback
from app.services.evaluation_service import evaluate_static_sign

# 1. MCP 서버 초기화 (이름: SignLanguageTutor)
mcp = FastMCP("Equal Sign - Sign Language Tutor")

# ==========================================
# 🛠️ 도구 1: 레슨 조회 (Resource/Tool)
# ==========================================
@mcp.tool()
def search_lesson_id(word_name: str) -> str:
    """
    사용자가 배우고 싶어하는 단어(예: 'I LOVE YOU')를 입력받아
    해당 단어의 Lesson ID와 정보를 반환합니다.
    """
    # 실제로는 DB에서 조회해야 함. 테스트용 목업 데이터 사용
    # 백엔드 DB 조회 함수가 있다면 그걸 연결하면 됨
    mock_db = {
        "I LOVE YOU": 1,
        "GOOD": 2,
        "HELLO": 3,
        "THANK YOU": 4
    }
    
    lesson_id = mock_db.get(word_name)
    if lesson_id:
        return json.dumps({"word": word_name, "lesson_id": lesson_id}, ensure_ascii=False)
    else:
        return f"'{word_name}'에 해당하는 레슨을 찾을 수 없습니다."

# ==========================================
# 🛠️ 도구 2: 시뮬레이션 생성
# ==========================================
@mcp.tool()
def create_roleplay_scenario(lesson_ids: list[int]) -> str:
    """
    오늘 배울 레슨 ID 리스트를 받아서,
    몰입형 1인칭 상황극(시나리오 + 이미지 URL)을 생성합니다.
    """
    try:
        # 기존 로직 재활용 (Mocking word lookup for demo)
        lesson_words = {lid: get_lesson_word(lid) for lid in lesson_ids} # 실제로는 get_lesson_word 사용
        
        # 시뮬레이션 서비스 호출
        result = generate_simulation_scenario(lesson_words)
        
        return json.dumps({
            "situation": result.situation,
            "image_url": result.image_url,
            "dialogue": [dict(d) for d in result.dialogue]
        }, ensure_ascii=False)
    except Exception as e:
        return f"시뮬레이션 생성 중 오류 발생: {str(e)}"

# ==========================================
# 🛠️ 도구 3: 수어 피드백 (핵심)
# ==========================================
@mcp.tool()
def evaluate_sign_language(lesson_id: int, user_landmarks_json: str) -> str:
    """
    사용자의 수어 동작(MediaPipe 랜드마크 JSON)을 입력받아,
    정답과 비교하고 교정 피드백을 반환합니다.
    """
    try:
        # 1. 사용자 데이터 파싱
        user_feature = json.loads(user_landmarks_json)
        
        # 2. 정답 데이터 가져오기 (기존 서비스 활용)
        # get_answer_frame 함수가 dict를 반환한다고 가정
        answer_feature = get_answer_frame(lesson_id)
        
        if not answer_feature:
            return "정답 데이터를 찾을 수 없습니다."

        # 3. 채점 (기존 서비스 활용)
        score, diff_log = evaluate_static_sign(user_feature, answer_feature) # 아까 수정한 버전 가정
        
        evaluation = {
            "is_correct": score == 1.0,
            "score": score
        }

        # 4. 피드백 생성 (LLM 호출)
        # 정답이면 칭찬, 틀렸으면 피드백
        if evaluation["is_correct"]:
            return "완벽합니다! 정확한 동작이에요. 🎉"
        else:
            # 틀린 부분만 넘겨서 피드백 생성
            feedback = generate_feedback(
                lesson_id=lesson_id,
                user_feature=user_feature,
                answer_feature=diff_log, # 틀린 부분만 전달
                evaluation=evaluation
            )
            return feedback

    except Exception as e:
        return f"피드백 생성 실패: {str(e)}"

if __name__ == "__main__":
    # MCP 서버 실행 (stdio 방식 - 로컬 에이전트 연결용)
    mcp.run()