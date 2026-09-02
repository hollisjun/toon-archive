import os, json, datetime, urllib.request, urllib.parse, sys

gemini_key = os.environ.get("GEMINI_API_KEY")
google_search_key = os.environ.get("GOOGLE_SERCH_API") or os.environ.get("GOOGLE_SEARCH_API_KEY")
search_engine_id = os.environ.get("SEARCH_ENGINE_ID")

if not all([gemini_key, google_search_key, search_engine_id]):
    print("❌ 에러: 필요한 API 키가 GitHub Secrets에 누락되었습니다.")
    sys.exit(1)

print("🔍 1단계: 검색 엔진을 통해 실시간 트렌드 수집 중...")
# 검색엔진에 이미 instagram.com이 등록되어 있으므로, 쿼리에는 사이트명을 빼고 키워드만 깔끔하게 던집니다.
queries = [
    "직장 퇴사 썰",
    "연애 이별 공감",
    "일상툰 레퍼런스"
]
real_data_list = []

for q in queries:
    search_url = f"https://customsearch.googleapis.com/customsearch/v1?q={urllib.parse.quote(q)}&cx={search_engine_id}&key={google_search_key}&dateRestrict=d[1]"
    try:
        req = urllib.request.Request(search_url)
        res = urllib.request.urlopen(req)
        search_data = json.loads(res.read().decode('utf-8'))
        
        for item in search_data.get('items', []):
            title = item.get('title', '')
            link = item.get('link', '')
            real_data_list.append(f"제목: {title}\n링크: {link}")
    except Exception as e:
        print(f"⚠️ 검색 API 수집 에러: {e}")

real_data_text = "\n\n".join(real_data_list)

if not real_data_text:
    print("❌ 실시간 데이터를 수집하지 못했습니다.")
    sys.exit(1)

print("🚀 2단계: AI가 인스타툰 소재용 데이터 분석 중...")
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key.strip()}"

prompt = f"""
아래는 구글 검색 API로 방금 긁어온 실제 데이터야.

[오늘자 실제 수집 데이터]
{real_data_text}

[🚨초엄격 규칙🚨]
1. 무조건 위 데이터 목록에 있는 제목과 링크를 토씨 하나 틀리지 말고 그대로 복사해서 써. 절대 링크를 지어내지 마.
2. 위 목록 중에서 인스타툰 소재로 그리기 좋은 알맹이 10개를 골라줘.
3. 댓글(best_comments)은 독자들의 반응을 상상해서 현실적인 댓글로 2개씩 지어줘.

[출력 JSON 형식] (반드시 순수 JSON 배열 [...] 형태만 출력)
[{{
  "rank": 1,
  "category": "직장",
  "keyword": "핵심키워드",
  "title": "실제 제목 그대로 복사",
  "link": "실제 링크 그대로 복사",
  "best_comments": [
    {{"text": "현실 공감 댓글 내용", "likes": 234}}
  ],
  "reaction_summary": "예상 공감 포인트 요약",
  "s": [5, 4, 5, 3, 4]
}}]
"""

data = {
    "contents": [{"parts": [{"text": prompt}]}],
    "generationConfig": {
        "temperature": 0.0,
        "response_mime_type": "application/json"
    }
}

try:
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
    res = urllib.request.urlopen(req)
    result = json.loads(res.read().decode('utf-8'))
    raw_text = result['candidates'][0]['content']['parts'][0]['text']
    new_items = json.loads(raw_text.strip())
except Exception as e:
    print(f"❌ 데이터 파싱 에러 발생: {e}")
    sys.exit(1)

print("💾 3단계: 완성된 데이터를 사이트에 누적 저장 중...")
today = datetime.datetime.now().strftime("%Y-%m-%d")

if os.path.exists('data.json'):
    with open('data.json', 'r', encoding='utf-8') as f:
        try:
            archive = json.load(f)
        except:
            archive = []
else:
    archive = []

updated = False
for day_data in archive:
    if day_data.get("date") == today:
        day_data["items"] = new_items
        updated = True
        break

if not updated:
    archive.insert(0, {"date": today, "items": new_items})

with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(archive, f, ensure_ascii=False, indent=2)

print("✅ 실시간 업데이트 완료!")
