import traceback
import sys

# 콘솔 인코딩 강제 utf-8
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

steps = [
    "import app.services.mediapipe_service",
    "import app.services.feature_extractor",
    "import app.services.feedback_service",
    "import app.ai.llm_client",
    "import app.api.lesson_feedback",
    "import app.api.korean_sign",
    "import app.main",
]

for step in steps:
    try:
        exec(step)
        print(f"OK  : {step}")
    except Exception as e:
        print(f"FAIL: {step}")
        tb = traceback.format_exc()
        print(tb)
        break
