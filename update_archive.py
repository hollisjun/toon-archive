import os, json, datetime, urllib.request, urllib.error, sys

api_key = os.environ.get("GEMINI_API_KEY")

if not api_key or api_key.strip() == "":
    print("❌ 에러: GEMINI_API_KEY가 비어있습니다.")
    sys.exit(1)

api_key = api_key.strip()

# 1. 내 API 키로 쓸 수 있는 모델 리스트 확인하기 (404 원천 차단)
list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
try:
    req = urllib.request.Request(list_url)
    res = urllib.request.urlopen(req)
    models_data = json.loads(res.read().decode('utf-8'))
    available_models = [m['name'] for m in models_data.get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
except Exception as e:
    print(f"❌ 모델 목록 조회 실패: {e}")
    sys.exit(1)

# 2. 접근 가능한 가장 좋은 모델 자동 선택
target_model = None
for preferred in ["models/gemini-1.5-flash", "models/gemini-2.0-flash", "models/gemini-1.5-pro", "models/gemini-pro", "models/gemini-1.0-pro"]:
    if preferred in available_models:
        target_model = preferred
        break

if not target_model:
    if available_models:
        target_model = available_models[0]
    else:
        print("❌ 사용 가능한 모델이 없습니다.")
        sys.exit(1)

print(f"🚀 자동 선택된 AI 모델: {target_model}")

# 3. 데이터 수집 실행
url = f"https://generativelanguage.googleapis.com/v1beta/{target_model}:generateContent?key={api_key}"

prompt = """오늘 온라인 커뮤니티와 SNS에서 직장 일상 및 연애 분야로 추천수/반응이 가장 폭발한 소재 정확히 10개를 뽑아줘.
각 항목마다 추천수가 가장 높았던 '실제 베스트 댓글 2~3개'와 댓글 추천수(따봉수)를 함께 구성해줘.
반드시 마크다운 백틱 없이 순수 JSON 배열([...])로만 시작하고 끝나게 출력해.
형식: [{"rank": 1, "category": "직장", "keyword": "점심값", "title": "선배가 밥 사준다더니", "best_comments": [{"text": "그럴거면 편의점 가자", "likes": 1420}], "reaction_summary": "댓글 600+개", "s": [5, 4, 5, 3, 4]}]"""

data = {
    "contents": [{"parts": [{"text": prompt}]}]
}

try:
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
    res = urllib.request.urlopen(req)
    result = json.loads(res.read().decode('utf-8'))
    raw_text = result['candidates'][0]['content']['parts'][0]['text']
    
    # AI가 마크다운을 붙이더라도 안전하게 JSON만 추출
    clean_text = raw_text.replace('```json', '').replace('```', '').strip()
    new_items = json.loads(clean_text)
except urllib.error.HTTPError as e:
    error_msg = e.read().decode('utf-8')
    print(f"❌ 데이터 수집 중 에러 ({e.code}):\n{error_msg}")
    sys.exit(1)
except Exception as e:
    print(f"❌ 데이터 파싱 에러 발생: {e}\n(원문: {raw_text[:100]}...)")
    sys.exit(1)

# 4. 파일에 누적 저장
today = datetime.datetime.now().strftime("%Y-%m-%d")

if os.path.exists('data.json'):
    with open('data.json', 'r', encoding='utf-8') as f:
        try:
            archive = json.load(f)
        except:
            archive = []
else:
    archive = []

archive.insert(0, {"date": today, "items": new_items})

with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(archive, f, ensure_ascii=False, indent=2)

print("✅ 데이터 수집 및 저장 완료!")
