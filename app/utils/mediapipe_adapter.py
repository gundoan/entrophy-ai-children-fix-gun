from types import SimpleNamespace

HAND_LANDMARK_COUNT = 21
POSE_LANDMARK_COUNT = 33
FACE_LANDMARK_COUNT = 468


def build_mediapipe_results_from_request(raw_landmarks):
    """
    Front JSON → MediaPipe Holistic.process(img) 결과와 100% 동일한 구조
    landmark 개수 부족 시 자동 zero-padding
    """

    def pad_landmarks(landmarks, target_len):
        padded = list(landmarks) if landmarks else []

        while len(padded) < target_len:
            padded.append(
                SimpleNamespace(
                    x=0.0,
                    y=0.0,
                    z=0.0,
                    visibility=0.0
                )
            )
        return padded

    def to_landmark_list(landmarks, target_len):
        if not landmarks:
            return None

        padded = pad_landmarks(landmarks, target_len)

        return SimpleNamespace(
            landmark=[
                SimpleNamespace(
                    x=p.x,
                    y=p.y,
                    z=p.z,
                    visibility=getattr(p, "visibility", 1.0)
                )
                for p in padded
            ]
        )

    return SimpleNamespace(
        left_hand_landmarks=to_landmark_list(
            raw_landmarks.left_hand_landmarks,
            HAND_LANDMARK_COUNT
        ),
        right_hand_landmarks=to_landmark_list(
            raw_landmarks.right_hand_landmarks,
            HAND_LANDMARK_COUNT
        ),
        pose_landmarks=to_landmark_list(
            raw_landmarks.pose_landmarks,
            POSE_LANDMARK_COUNT
        ),
        face_landmarks=to_landmark_list(
            raw_landmarks.face_landmarks,
            FACE_LANDMARK_COUNT
        ),
    )
