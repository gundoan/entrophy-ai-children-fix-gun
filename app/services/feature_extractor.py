import numpy as np
import math

def calculate_distance(p1, p2):
    return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2 + (p1.z - p2.z)**2)

def get_vector(p1, p2):
    return np.array([p2.x - p1.x, p2.y - p1.y, p2.z - p1.z])

def normalize_vector(v):
    norm = np.linalg.norm(v)
    if norm == 0: return v
    return v / norm

def is_folded(landmarks, indices):
    # 간단한 굽힘 판별: 손가락 끝(TIP)이 관절(PIP)보다 손목(WRIST)에 더 가까우면 접힌 것
    wrist = landmarks[0]
    pip = landmarks[indices[1]]
    tip = landmarks[indices[3]]
    
    dist_tip_wrist = calculate_distance(tip, wrist)
    dist_pip_wrist = calculate_distance(pip, wrist)
    
    return dist_tip_wrist < dist_pip_wrist

def analyze_inter_hand_relation(left_lm, right_lm):
    if not left_lm or not right_lm:
        return {
            "both_present": False,
            "forming_single_shape": False,
            "mirrored_shape": False,
            "hand_distance_close": False,
            "finger_tips_facing": False
        }

    l_wrist = left_lm.landmark[0]
    r_wrist = right_lm.landmark[0]

    wrist_dist = calculate_distance(l_wrist, r_wrist)

    # fingertip 평균 위치
    l_tip = left_lm.landmark[8]   # index tip
    r_tip = right_lm.landmark[8]

    tip_dist = calculate_distance(l_tip, r_tip)

    return {
        "both_present": True,
        "forming_single_shape": wrist_dist < 0.25,
        "mirrored_shape": True,              # 좌우 hand label 기준 대칭은 MediaPipe가 이미 보장
        "hand_distance_close": wrist_dist < 0.15,
        "finger_tips_facing": tip_dist < 0.08
    }

def analyze_finger_relation(hand_lm):
    if not hand_lm:
        return {
            "index_middle_crossed": False,
            "index_over_middle": False,
            "middle_over_index": False
        }

    lm = hand_lm.landmark

    index_tip = lm[8]
    middle_tip = lm[12]

    crossed = abs(index_tip.x - middle_tip.x) < 0.02 and \
              abs(index_tip.y - middle_tip.y) < 0.02

    return {
        "index_middle_crossed": crossed,
        "index_over_middle": crossed and (index_tip.z < middle_tip.z),
        "middle_over_index": crossed and (middle_tip.z < index_tip.z)
    }

def analyze_hand(hand_lm, face_lm, pose_lm, is_right_hand=False):
    """MediaPipe 랜드마크를 기반으로 hand.json 구조의 딕셔너리를 생성"""
    if not hand_lm:
        return None

    # 랜드마크 단축키
    lm = hand_lm.landmark
    
    # 1. Handshape Analysis
    # ---------------------
    # 손가락 인덱스: [MCP, PIP, DIP, TIP]
    fingers_idx = {
        'thumb': [1, 2, 3, 4],
        'index': [5, 6, 7, 8],
        'middle': [9, 10, 11, 12],
        'ring': [13, 14, 15, 16],
        'pinky': [17, 18, 19, 20]
    }

    # 굽힘 여부 (Folded)
    folded_status = {}
    for name, indices in fingers_idx.items():
        if name == 'thumb':
            dist = calculate_distance(lm[4], lm[17])
            folded_status[name] = dist < 0.15 
        else:
            folded_status[name] = is_folded(lm, indices)

    extended_status = {k: not v for k, v in folded_status.items()}

    # Finger Contact (접촉) - 임계값 0.04
    touch_thresh = 0.04
    contacts = {
        'thumb_index': calculate_distance(lm[4], lm[8]) < touch_thresh,
        'thumb_middle': calculate_distance(lm[4], lm[12]) < touch_thresh,
        'thumb_ring': calculate_distance(lm[4], lm[16]) < touch_thresh,
        'thumb_pinky': calculate_distance(lm[4], lm[20]) < touch_thresh,
        'index_middle': calculate_distance(lm[8], lm[12]) < touch_thresh,
        'middle_ring': calculate_distance(lm[12], lm[16]) < touch_thresh,
        'ring_pinky': calculate_distance(lm[16], lm[20]) < touch_thresh
    }

    # 2. Orientation Analysis
    # -----------------------
    wrist = lm[0]
    index_mcp = lm[5]
    pinky_mcp = lm[17]
    
    v1 = get_vector(wrist, index_mcp)
    v2 = get_vector(wrist, pinky_mcp)
    
    if is_right_hand:
        palm_normal = np.cross(v1, v2) # Right
    else:
        palm_normal = np.cross(v2, v1) # Left
        
    palm_normal = normalize_vector(palm_normal) # [x, y, z]
    finger_dir = normalize_vector(v1)

    orientation = {
        "palm_up": palm_normal[1] < -0.6,
        "palm_down": palm_normal[1] > 0.6,
        "palm_forward": palm_normal[2] < -0.6,
        "palm_backward": palm_normal[2] > 0.6, 
        "fingers_up": finger_dir[1] < -0.6,
        "fingers_down": finger_dir[1] > 0.6,
        "fingers_forward": finger_dir[2] < -0.6,
    }

    # 3. Location Analysis (Relative to Face/Body)
    # ------------------------------------------
    loc_data = {
        "face": False, "chin": False, "chest": False, "high": False, "mid": False, "low": False
    }
    
    if face_lm and pose_lm:
        chin_pt = face_lm.landmark[152]
        nose_pt = face_lm.landmark[1]
        
        left_shoulder = pose_lm.landmark[11]
        right_shoulder = pose_lm.landmark[12]
        chest_pt_y = (left_shoulder.y + right_shoulder.y) / 2
        
        hand_y = wrist.y

        if hand_y < nose_pt.y: 
            loc_data["high"] = True
        elif hand_y > chest_pt_y: 
            loc_data["low"] = True
        else:
            loc_data["mid"] = True

        if calculate_distance(wrist, chin_pt) < 0.15:
            loc_data["chin"] = True
            loc_data["face"] = True
        
        if abs(hand_y - chest_pt_y) < 0.15:
            loc_data["chest"] = True

    # === JSON 구조 매핑 ===
    return {
        "handshape": {
            "finger_selection": {
                "thumb": extended_status['thumb'],
                "index": extended_status['index'],
                "middle": extended_status['middle'],
                "ring": extended_status['ring'],
                "pinky": extended_status['pinky']
            },
            "finger_flexion": {
                "thumb_extended": extended_status['thumb'], "thumb_folded": folded_status['thumb'],
                "index_extended": extended_status['index'], "index_folded": folded_status['index'],
                "middle_extended": extended_status['middle'], "middle_folded": folded_status['middle'],
                "ring_extended": extended_status['ring'], "ring_folded": folded_status['ring'],
                "pinky_extended": extended_status['pinky'], "pinky_folded": folded_status['pinky']
            },
            "thumb_configuration": {
                "thumb_opposed": folded_status['thumb'], 
                "thumb_crossing": False, 
                "thumb_contact_index": contacts['thumb_index'],
                "thumb_contact_middle": contacts['thumb_middle'],
                "thumb_contact_ring": contacts['thumb_ring'],
                "thumb_contact_pinky": contacts['thumb_pinky']
            },
            "finger_contact": {
                "index_middle_contact": contacts['index_middle'],
                "middle_ring_contact": contacts['middle_ring'],
                "ring_pinky_contact": contacts['ring_pinky'],
                "all_fingers_spread": not (contacts['index_middle'] or contacts['middle_ring']),
                "all_fingers_closed": (contacts['index_middle'] and contacts['middle_ring'] and contacts['ring_pinky'])
            }
        },
        "orientation": {
            "palm_up": orientation['palm_up'],
            "palm_down": orientation['palm_down'],
            "palm_left": False, 
            "palm_right": False, 
            "palm_forward": orientation['palm_forward'],
            "palm_backward": orientation['palm_backward'],
            "fingers_up": orientation['fingers_up'],
            "fingers_down": orientation['fingers_down'],
            "fingers_left": False,
            "fingers_right": False,
            "fingers_forward": orientation['fingers_forward'],
            "fingers_backward": False,
            "wrist_pronated": False,
            "wrist_supinated": False,
            "wrist_neutral": True
        },
        "location": {
            "major": {
                "head": loc_data['high'],
                "face": loc_data['face'],
                "neck": False,
                "torso": loc_data['chest'],
                "arm": False,
                "handspace": False
            },
            "face": {
                "forehead": False, "eye": False, "nose": False, "mouth": False,
                "chin": loc_data['chin'], "cheek": False, "ear": False
            },
            "torso": {
                "chest": loc_data['chest'], "sternum": False, "stomach": False, "waist": False
            },
            "arm": {"upper_arm": False, "forearm": False, "wrist": False},
            "hand_relative": {"palm": False, "back_of_hand": False},
            "spatial_height": {
                "high": loc_data['high'], "mid": loc_data['mid'], "low": loc_data['low']
            },
            "spatial_distance": {"contact": False, "near": True, "far": False}
        }
    }

def get_empty_hand_data():
    """손이 감지되지 않았을 때의 기본값"""
    return {
        "present": False,
        "handshape": {
            "finger_selection": {k: False for k in ['thumb', 'index', 'middle', 'ring', 'pinky']},
            "finger_flexion": {
                "thumb_extended": False, "thumb_folded": False,
                "index_extended": False, "index_folded": False,
                "middle_extended": False, "middle_folded": False,
                "ring_extended": False, "ring_folded": False,
                "pinky_extended": False, "pinky_folded": False
            },
            "thumb_configuration": {
                "thumb_opposed": False, "thumb_crossing": False,
                "thumb_contact_index": False, "thumb_contact_middle": False,
                "thumb_contact_ring": False, "thumb_contact_pinky": False
            },
            "finger_contact": {
                "index_middle_contact": False, "middle_ring_contact": False,
                "ring_pinky_contact": False,
                "all_fingers_spread": False, "all_fingers_closed": False
            }
        },
        "orientation": {
            "palm_up": False, "palm_down": False, "palm_left": False, "palm_right": False,
            "palm_forward": False, "palm_backward": False,
            "fingers_up": False, "fingers_down": False, "fingers_left": False, "fingers_right": False,
            "fingers_forward": False, "fingers_backward": False,
            "wrist_pronated": False, "wrist_supinated": False, "wrist_neutral": False
        },
        "location": {
            "major": {"head": False, "face": False, "neck": False, "torso": False, "arm": False, "handspace": False},
            "face": {"forehead": False, "eye": False, "nose": False, "mouth": False, "chin": False, "cheek": False, "ear": False},
            "torso": {"chest": False, "sternum": False, "stomach": False, "waist": False},
            "arm": {"upper_arm": False, "forearm": False, "wrist": False},
            "hand_relative": {"palm": False, "back_of_hand": False},
            "spatial_height": {"high": False, "mid": False, "low": False},
            "spatial_distance": {"contact": False, "near": False, "far": False}
        }
    }

def extract_feature_json(results):

    final_json = {}
    
    if results.left_hand_landmarks:
        print("Left Hand Detected")
        data = analyze_hand(results.left_hand_landmarks, results.face_landmarks, results.pose_landmarks, is_right_hand=False)
        final_json['left'] = data
    else:
        final_json['left'] = get_empty_hand_data()

    if results.right_hand_landmarks:
        print("Right Hand Detected")
        data = analyze_hand(results.right_hand_landmarks, results.face_landmarks, results.pose_landmarks, is_right_hand=True)
        final_json['right'] = data
    else:
        final_json['right'] = get_empty_hand_data()

    final_json['left']['present'] = bool(results.left_hand_landmarks)
    final_json['right']['present'] = bool(results.right_hand_landmarks)
    final_json['inter_hand_relation'] = analyze_inter_hand_relation(
        results.left_hand_landmarks,
        results.right_hand_landmarks
    )

    final_json['finger_relation'] = analyze_finger_relation(
        results.right_hand_landmarks or results.left_hand_landmarks
    )

    return final_json

def extract_feature_json(results, expression: str = "Neutral"):

    final_json = {}
    
    # 1. 왼손 분석
    if results.left_hand_landmarks:
        # print("Left Hand Detected")
        data = analyze_hand(results.left_hand_landmarks, results.face_landmarks, results.pose_landmarks, is_right_hand=False)
        final_json['left'] = data
    else:
        final_json['left'] = get_empty_hand_data()

    # 2. 오른손 분석
    if results.right_hand_landmarks:
        # print("Right Hand Detected")
        data = analyze_hand(results.right_hand_landmarks, results.face_landmarks, results.pose_landmarks, is_right_hand=True)
        final_json['right'] = data
    else:
        final_json['right'] = get_empty_hand_data()

    # 3. 손 존재 여부 플래그
    final_json['left']['present'] = bool(results.left_hand_landmarks)
    final_json['right']['present'] = bool(results.right_hand_landmarks)
    
    # 4. 양손 관계 분석
    final_json['inter_hand_relation'] = analyze_inter_hand_relation(
        results.left_hand_landmarks,
        results.right_hand_landmarks
    )

    # 5. 손가락 관계 분석
    final_json['finger_relation'] = analyze_finger_relation(
        results.right_hand_landmarks or results.left_hand_landmarks
    )

    # 6. [NEW] 비수지기호(표정) 추가
    # Custom Vision에서 분석한 결과(예: "Question", "Happy")가 여기에 들어갑니다.
    final_json['non_manual_signal'] = {
        "expression": expression
    }

    return final_json

# def extract_feature_json2(raw_landmarks) -> dict:
#     """
#     프런트에서 받은 MediaPipe holistic 결과를
#     extract_phonogy_json()에 넣을 수 있는 형태로 변환
#     """

#     class DummyResults:
#         # dict인지 객체인지 확인 후 안전하게 접근
#         left_hand_landmarks = getattr(raw_landmarks, "leftHand", None) if not isinstance(raw_landmarks, dict) else raw_landmarks.get("leftHand")
#         right_hand_landmarks = getattr(raw_landmarks, "rightHand", None) if not isinstance(raw_landmarks, dict) else raw_landmarks.get("rightHand")
#         face_landmarks = getattr(raw_landmarks, "face", None) if not isinstance(raw_landmarks, dict) else raw_landmarks.get("face")
#         pose_landmarks = getattr(raw_landmarks, "pose", None) if not isinstance(raw_landmarks, dict) else raw_landmarks.get("pose")

#     results = DummyResults()
#     return extract_feature_json(results)
