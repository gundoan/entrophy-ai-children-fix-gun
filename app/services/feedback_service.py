from app.ai.llm_client import call_llm

def generate_feedback(evaluation):

    # 정답이면 LLM 호출 안 함
    if evaluation["is_correct"]:
        return "Congratulations!"

    prompt = f"""
            너는 미국 수어 학습 코치야.

            사용자가 수어 동작을 틀렸는데, 원래는 다음과 같이 동작해야 하는데 사용자가 그렇게 동작하지 않았어.

            [정답 수어 특징]
            {evaluation["wrong_parts"]}

            사용자가 왜 틀렸는지, 그래서 어떻게 고쳐야 하는지 사용자에게 아주 짧고 핵심적으로 1 문장의 영어로 피드백해 줘. 지어야 하는 표정이 특성에 있다면 그것도 같이 말해줘. 강조 기호는 사용하지마. e.g.) Stretch your pinky finger, turn your wrist forward, etc..
            """

    return call_llm(prompt)
