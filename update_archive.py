import os, json, datetime, urllib.request

api_key = os.environ.get("GEMINI_API_KEY")
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"

prompt = """오늘 직장 일상 및 연애 분야에서 실시간 반응이 터진 인기 키워드, 제목, 반응, 지표 점수(급상승,검색수요,적합도,수익화,신선도)를 JSON 배열로만 줘. 
형식: [{"category": "직장", "keyword": "키워드", "title": "제목", "reaction": "반응요약", "s": [5,4,5,3,4]}]"""

data = {"contents": [{"parts": [{"text": prompt}]}]}
req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
res = urllib.request.urlopen(req)
result = json.loads(res.read().decode('utf-8'))
raw_text = result['candidates'][0]['content']['parts'][0]['text']
clean_text = raw_text.replace('```json', '').replace('```', '').strip()
new_items = json.loads(clean_text)

today = datetime.datetime.now().strftime("%Y-%m-%d")
with open('data.json', 'r', encoding='utf-8') as f:
    archive = json.load(f)

archive.insert(0, {"date": today, "items": new_items})

with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(archive, f, ensure_ascii=False, indent=2)
