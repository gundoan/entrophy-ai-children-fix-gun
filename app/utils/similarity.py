from typing import Tuple, Dict, Any

def compare_feature(user: dict, answer: dict) -> Tuple[float, Dict[str, Any]]:
    total = 0
    matched = 0
    diff_log = {}  # 틀린 항목의 정답 데이터만 모을 딕셔너리

    def compare_dict(u, a, diff_accum):
        nonlocal total, matched
        for k in a:
            if isinstance(a[k], dict):
                # 다음 계층을 위한 빈 딕셔너리 생성
                sub_diff = {}
                # 재귀 호출 시 sub_diff를 넘겨줌
                compare_dict(u.get(k, {}), a[k], sub_diff)
                
                # 하위 항목에서 틀린 내용이 잡혔을 때만 현재 계층에 추가 (깔끔한 결과 보장)
                if sub_diff:
                    diff_accum[k] = sub_diff
            else:
                total += 1
                user_val = u.get(k)
                ans_val = a[k]
                
                # 문자열 "true"/"false" 와 불리언 True/False를 유연하게 비교
                str_user = str(user_val).lower() if user_val is not None else "none"
                str_ans = str(ans_val).lower()

                if str_user == str_ans:
                    matched += 1
                else:
                    # [변경] 틀렸을 경우: diff_accum에 '정답 값'을 기록
                    # LLM이 "사용자는 A를 했지만 정답은 B입니다"라고 말하려면 B(정답)가 필요함
                    diff_accum[k] = ans_val

    # 최상위 호출 시 diff_log를 넘겨줌
    compare_dict(user, answer, diff_log)
    
    score = round(matched / total, 3) if total else 0.0
    
    # 점수와 틀린 부분(정답 기준) 딕셔너리를 함께 반환
    return score, diff_log

# def compare_feature(user: dict, answer: dict) -> float:
#     total = 0
#     matched = 0

#     def compare_dict(u, a):
#         nonlocal total, matched
#         for k in a:
#             if isinstance(a[k], dict):
#                 compare_dict(u.get(k, {}), a[k])
#             # (위 코드의 else 부분 수정)
#             else:
#                 total += 1
#                 user_val = u.get(k)
#                 ans_val = a[k]
                
#                 # 문자열 "true"/"false" 와 불리언 True/False를 유연하게 비교
#                 str_user = str(user_val).lower() if user_val is not None else "none"
#                 str_ans = str(ans_val).lower()

#                 if str_user == str_ans:
#                     matched += 1

#     compare_dict(user, answer)
#     return round(matched / total, 3) if total else 0.0

# def compare_feature(user: dict, answer: dict) -> float:
#     total = 0
#     matched = 0

#     print(f"--- 비교 시작 ---")

#     def compare_dict(u, a, path=""):
#         nonlocal total, matched
        
#         # u가 딕셔너리가 아닌 경우(None 등) 방어 로직
#         if not isinstance(u, dict):
#             print(f"[구조 불일치] '{path}' 경로에서 user 데이터가 딕셔너리가 아닙니다. (값: {u})")
#             u = {} 

#         for k in a:
#             current_path = f"{path}.{k}" if path else k
            
#             # 1. answer의 값이 딕셔너리인 경우 (재귀 진입)
#             if isinstance(a[k], dict):
#                 # user 쪽에도 해당 키가 있는지 확인하면서 재귀
#                 compare_dict(u.get(k, {}), a[k], current_path)
            
#             # 2. answer의 값이 실제 값(True/False)인 경우 (비교 수행)
#             else:
#                 total += 1
#                 user_val = u.get(k)
#                 ans_val = a[k]
                
#                 # 디버깅 출력: 값이 다를 때만 출력하거나, 모두 출력해서 확인
#                 if user_val != ans_val:
#                     print(f"[불일치] Key: {current_path} | User: {user_val} ({type(user_val)}) != Answer: {ans_val} ({type(ans_val)})")
#                 else:
#                     matched += 1

#     compare_dict(user, answer)
    
#     score = matched / total if total else 0.0
#     print(f"--- 결과: {matched}/{total} -> {score} ---")
#     return score