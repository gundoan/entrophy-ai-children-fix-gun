# 🤟 어린이날 수어 챌린지

어린이들이 한국 수화(KSL)를 웹캠으로 따라 하고 맞는지 확인하는 프로젝트예요.  
선생님(관리자)이 먼저 정답 수화를 녹화해두면, 아이들이 `/check` 페이지에서 수화를 따라 하며 채점받을 수 있어요.

---

## 필요한 것

| 항목 | 버전 |
|------|------|
| Python | **3.11** (3.8, 3.10 안 됩니다!) |
| 웹캠 | 필수 |
| Gemini API 키 | [여기서 발급](https://aistudio.google.com/app/apikey) |

---

## 설치 방법

### 1. 저장소 받기

```bash
git clone <저장소 주소>
cd entrophy-ai-children-fix-gun
```

### 2. Python 3.11 가상환경 만들기

> ⚠️ 반드시 Python **3.11**로 만들어야 해요. mediapipe가 3.8이나 3.12에서 안 돌아가요.

**Windows:**
```bash
py -3.11 -m venv venv311
venv311\Scripts\activate
```

**Mac / Linux:**
```bash
python3.11 -m venv venv311
source venv311/bin/activate
```

가상환경이 활성화되면 터미널 앞에 `(venv311)` 이 붙어요.

### 3. 패키지 설치

```bash
pip install -r requirements.txt
```

> 설치 시간이 2~5분 정도 걸릴 수 있어요 (mediapipe가 좀 커요).

### 4. 환경변수 파일 만들기

프로젝트 루트에 `.env` 파일을 새로 만들고 아래 내용을 붙여넣으세요.

```
GEMINI_API_KEY=여기에_발급받은_키_붙여넣기
```

> `.env` 파일은 보안 때문에 git에 올라가 있지 않아요. 직접 만들어야 해요.

---

## 서버 실행

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

실행 후 브라우저에서 아래 주소로 접속하세요:

| 페이지 | 주소 | 설명 |
|--------|------|------|
| 정답 녹화 | http://127.0.0.1:8000/record | 선생님/관리자용. 정답 수화 영상 녹화 |
| 수화 확인 | http://127.0.0.1:8000/check  | 아이들용. 수화 따라하고 채점 |

---

## 처음 사용 순서

### Step 1. 정답 녹화 먼저 하기 (`/record`)

아이들이 확인하기 전에 **선생님이 먼저 정답 수화를 녹화**해야 해요.

1. http://127.0.0.1:8000/record 접속
2. 단어 카드 클릭 (엄마, 아빠, 사랑해, 나, 아들, 딸)
3. 웹캠 앞에서 해당 수화를 하면 3초 카운트다운 후 3초간 녹화
4. 저장 완료 메시지 확인
5. 6개 단어 모두 녹화

> 정답 데이터는 `app/answers/korean/` 폴더에 JSON 파일로 저장돼요.  
> 녹화 후 아래 명령어로 git에 올리면 친구가 pull 받았을 때 다시 녹화할 필요 없어요.
> ```bash
> git add app/answers/korean/
> git commit -m "정답 수화 데이터 추가"
> git push
> ```

### Step 2. 아이들이 수화 확인하기 (`/check`)

1. http://127.0.0.1:8000/check 접속
2. 단어 카드 클릭
3. 3초 카운트다운 후 해당 수화를 3초간 따라 하기
4. 90점 이상이면 성공! 🎉

---

## 대상 단어 (6개)

| 한국어 | 영어 |
|--------|------|
| 엄마 | Mom |
| 아빠 | Dad |
| 사랑해 | I Love You |
| 나 | Me / I |
| 아들 | Son |
| 딸 | Daughter |

---

## 자주 겪는 문제

### ❌ `mediapipe` 설치 오류가 나요
Python 버전을 확인해보세요. `python --version` 입력 시 **3.11.x** 여야 해요.  
3.8이나 3.12면 안 돼요.

### ❌ 웹캠을 열 수 없다고 나와요
브라우저 주소창 왼쪽 자물쇠 아이콘 → 카메라 권한을 **허용**으로 바꿔주세요.

### ❌ `손이 감지되지 않습니다` 오류가 나요
- 조명이 충분한 곳에서 시도해보세요
- 손이 웹캠 화면 안에 잘 보이게 해주세요

### ❌ 서버가 안 켜지고 `No module named ...` 오류가 나요
가상환경이 활성화돼 있는지 확인해요. 터미널에 `(venv311)` 이 없으면:
```bash
# Windows
venv311\Scripts\activate

# Mac / Linux
source venv311/bin/activate
```

### ❌ `GEMINI_API_KEY` 관련 오류가 나요
`.env` 파일이 프로젝트 루트(README.md 있는 폴더)에 있는지, 키가 올바른지 확인해주세요.

---

## 프로젝트 구조

```
entrophy-ai-children-fix-gun/
├── app/
│   ├── main.py                   # FastAPI 서버 진입점
│   ├── api/
│   │   └── korean_sign.py        # 녹화/채점 API
│   └── services/
│       ├── mediapipe_service.py  # 웹캠 이미지 → 랜드마크 추출
│       ├── feature_extractor.py  # 특징 벡터 추출
│       └── evaluation_service.py # 정답 비교/채점
├── static/
│   ├── record.html               # 정답 녹화 페이지
│   └── check.html                # 수화 확인 페이지 (아이들용)
├── answers/
│   └── korean/                   # 녹화된 정답 JSON 파일들
├── .env                          # API 키 (직접 만들어야 함, git 미포함)
└── requirements.txt
```
