import mediapipe as mp
import cv2
import numpy as np

# 1. 점(Point) 하나를 흉내 내는 클래스
class ProtoLandmark:
    def __init__(self, x, y, z, visibility=0.0):
        self.x = x
        self.y = y
        self.z = z
        self.visibility = visibility

# 2. 랜드마크 리스트를 흉내 내는 클래스 (.landmark 속성 보유 필수)
class LandmarkListWrapper:
    def __init__(self, landmarks_list):
        self.landmark = landmarks_list  # 여기가 핵심입니다. 리스트를 .landmark에 담습니다.

# 3. 전체 결과(Results)를 흉내 내는 클래스
class MediaPipeResultAdapter:
    def __init__(self, mp_results):
        # 각 부위별로 래핑 처리
        self.pose_landmarks = self._wrap(mp_results.pose_landmarks)
        self.left_hand_landmarks = self._wrap(mp_results.left_hand_landmarks)
        self.right_hand_landmarks = self._wrap(mp_results.right_hand_landmarks)
        self.face_landmarks = self._wrap(mp_results.face_landmarks)

    def _wrap(self, source):
        # 데이터가 없으면 None 반환
        if not source:
            return None
        
        # 소스가 NormalizedLandmarkList 객체라면 .landmark로 리스트를 꺼내고,
        # 이미 리스트라면(Mac M4 등 환경 차이) 그대로 사용
        raw_list = getattr(source, 'landmark', source)
        
        # 내부 데이터를 단순 객체(ProtoLandmark)로 변환
        converted_list = [
            ProtoLandmark(lm.x, lm.y, lm.z, getattr(lm, 'visibility', 0.0))
            for lm in raw_list
        ]
        
        # [중요] 리스트를 바로 반환하지 않고, .landmark 속성을 가진 객체에 담아서 반환
        return LandmarkListWrapper(converted_list)

    # 혹시 모를 딕셔너리 접근 방어 코드
    def get(self, key, default=None):
        return getattr(self, key, default)


def process_image_to_landmarks(image_bytes: bytes):
    # 1. 이미지 디코딩
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img is None:
        raise ValueError("이미지를 디코딩할 수 없습니다.")

    # 2. BGR -> RGB 변환
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # 3. MediaPipe Holistic 수행
    mp_holistic = mp.solutions.holistic
    with mp_holistic.Holistic(
        static_image_mode=True,
        model_complexity=2,
        enable_segmentation=False,
        refine_face_landmarks=True
    ) as holistic:
        raw_results = holistic.process(img_rgb)

    # 4. 결과 변환 (구조 흉내)
    return MediaPipeResultAdapter(raw_results)