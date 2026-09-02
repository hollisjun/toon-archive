import os, json, datetime, urllib.request, urllib.error, sys

api_key = os.environ.get("GEMINI_API_KEY")

if not api_key or api_key.strip() == "":
    print("❌ 에러: GEMINI_API_KEY가 비어있습니다. GitHub Secrets 설정을 확인하세요.")
    sys.exit(1)

# 모델 주소를 latest 규격으로 정확히 지정
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={api_key.strip()}"

prompt = """오늘 온라인 커뮤니티와 SNS에서 직장 일상 및 연애 분야로 추천수/반응이 가장 폭발한 소재 정확히 10개를 뽑아줘.
각 항목마다 추천수가 가장 높았던 '실제 베스트 댓글 2~3개'와 댓글 추천수(따봉수)를 함께 구성해줘.
반드시 마크다운 없이 순수 JSON 배열([...])로만 출력해.
형식: [{"rank": 1, "category": "직장", "keyword": "점심값", "title": "선배가 밥 사준다더니", "best_comments": [{"text": "그럴거면 편의점 가자", "likes": 1420}], "reaction_summary": "댓글 600+개", "s": [5, 4, 5, 3, 4]}]"""

data = {
    "contents": [{"parts": [{"text": prompt}]}],
    "generationConfig": {"response_mime_type": "application/json"}
}

try:
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
    res = urllib.request.urlopen(req)
    result = json.loads(res.read().decode('utf-8'))
    raw_text = result['candidates'][0]['content']['parts'][0]['text']
    new_items = json.loads(raw_text.strip())
except urllib.error.HTTPError as e:
    # 404 등 에러 발생 시 구글 서버가 보낸 상세 원인 출력
    error_msg = e.read().decode('utf-8')
    print(f"❌ 구글 API 서버 상세 에러 ({e.code}):\n{error_msg}")
    sys.exit(1)
except Exception as e:
    print(f"❌ 알 수 없는 에러 발생: {e}")
    sys.exit(1)

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
