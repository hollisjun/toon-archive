import os, json, datetime, urllib.request

api_key = os.environ.get("GEMINI_API_KEY")
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"

prompt = """오늘 온라인 커뮤니티(블라인드, 네이트판, 더쿠, 에브리타임)와 SNS에서 직장 일상 및 연애 분야로 추천수/반응이 가장 폭발한 소재 정확히 10개를 뽑아줘.
각 항목마다 추천수가 가장 높았던 '실제 베스트 댓글 2~3개'와 댓글 추천수(따봉수)를 함께 구성해줘.

반드시 마크다운 없이 순수 JSON 배열([...])로만 출력해.
형식:
[
  {
    "rank": 1,
    "category": "직장",
    "keyword": "점심값 눈치",
    "title": "선배가 밥 사준다더니 만원 이하로 고르라 함",
    "best_comments": [
      {"text": "그럴 거면 그냥 편의점에서 삼김이나 사주지 굳이 데려가서 생색냄", "likes": 1420},
      {"text": "사주고 욕먹는 전형적인 꼰대 스타일", "likes": 980}
    ],
    "reaction_summary": "댓글 600+개 / 치사함과 생색내기에 대한 극대노",
    "s": [5, 4, 5, 3, 4]
  }
]"""

data = {
    "contents": [{"parts": [{"text": prompt}]}],
    "generationConfig": {
        "response_mime_type": "application/json"
    }
}

req = urllib.request.Request(
    url, 
    data=json.dumps(data).encode('utf-8'), 
    headers={'Content-Type': 'application/json'}
)

res = urllib.request.urlopen(req)
result = json.loads(res.read().decode('utf-8'))
raw_text = result['candidates'][0]['content']['parts'][0]['text']
new_items = json.loads(raw_text.strip())

# 날짜별 누적 저장
today = datetime.datetime.now().strftime("%Y-%m-%d")

if os.path.exists('data.json'):
    with open('data.json', 'r', encoding='utf-8') as f:
        try:
            archive = json.load(f)
        except Exception:
            archive = []
else:
    archive = []

# 최신 날짜가 항상 맨 위에 오도록 추가
archive.insert(0, {"date": today, "items": new_items})

with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(archive, f, ensure_ascii=False, indent=2)
