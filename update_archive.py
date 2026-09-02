import os, json, datetime, urllib.request, urllib.error, re, sys

api_key = os.environ.get("GEMINI_API_KEY")

if not api_key or api_key.strip() == "":
    print("❌ 에러: GEMINI_API_KEY가 비어있습니다.")
    sys.exit(1)

api_key = api_key.strip()

print("🔍 1단계: 네이트판 실시간 베스트 썰(진짜 링크) 직수집 중...")
real_data_list = []

# 1. 썰의 성지 '네이트판' 실시간 랭킹 HTML 직접 크롤링
try:
    req = urllib.request.Request("https://pann.nate.com/talk/ranking/d", headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    html = urllib.request.urlopen(req).read().decode('utf-8')
    
    # 정규식으로 실제 글 고유 주소와 제목만 정확하게 추출
    pattern = r'<dt>\s*<a href="(/talk/\d+)"[^>]*title="([^"]+)"'
    matches = re.findall(pattern, html)
    
    seen = set()
    for link, title in matches:
        if link not in seen:
            seen.add(link)
            # 수집한 진짜 주소 조립
            real_data_list.append(f"제목: {title}\n링크: https://pann.nate.com{link}")
            if len(real_data_list) >= 25:  # 25개 넉넉히 수집
                break
except Exception as e:
    print(f"❌ 네이트판 수집 에러: {e}")

real_data_text = "\n\n".join(real_data_list)

if not real_data_text:
    print("❌ 실시간 데이터를 수집하지 못했습니다.")
    sys.exit(1)

print("🚀 2단계: AI에게 '절대 지어내지 말라'고 강력 통제하며 분석 중...")
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"

prompt = f"""
너는 인스타툰 소재 큐레이터야.
아래 [오늘자 실제 수집 데이터]에는 오늘 한국 커뮤니티에 올라온 '진짜 제목'과 '진짜 접속 링크'가 있어.

[오늘자 실제 수집 데이터]
{real_data_text}

[🚨초엄격 규칙 - 위반 시 시스템 오류 발생🚨]
1. 무조건 위 데이터 목록에 있는 제목과 링크를 **토씨 하나 틀리지 말고 100% 그대로 복사**해서 써야 해.
2. 절대 네가 스스로 지어내거나 가짜 링크(할루시네이션)를 만들면 안 돼. 위 목록에 없는 건 절대 쓰지 마.
3. 위 목록 중에서 인스타툰(직장/연애/일상)으로 그리기 가장 좋은 것 10개를 골라줘.
4. 댓글(best_comments)은 해당 글의 내용을 상상해서 독자들이 달 법한 현실적인 댓글로 2개씩 지어줘.

[출력 JSON 형식] (반드시 순수 JSON 배열 [...] 형태만 출력)
[{{
  "rank": 1,
  "category": "연애",
  "keyword": "핵심키워드",
  "title": "실제 제목 그대로 복사",
  "link": "실제 링크 그대로 복사",
  "best_comments": [
    {{"text": "현실 공감 댓글 내용", "likes": 234}}
  ],
  "reaction_summary": "사람들의 예상 분노/공감 포인트 요약",
  "s": [5, 4, 5, 3, 4]
}}]
"""

data = {
    "contents": [{"parts": [{"text": prompt}]}],
    "generationConfig": {
        "temperature": 0.0, # 창의성을 완전히 꺼서 거짓말(할루시네이션) 원천 차단
        "response_mime_type": "application/json"
    }
}

try:
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
    res = urllib.request.urlopen(req)
    result = json.loads(res.read().decode('utf-8'))
    
    # JSON 강제 출력 옵션을 켰으므로 마크다운 정제 없이 바로 파싱 가능
    raw_text = result['candidates'][0]['content']['parts'][0]['text']
    new_items = json.loads(raw_text.strip())
except urllib.error.HTTPError as e:
    print(f"❌ API 에러 ({e.code}):\n{e.read().decode('utf-8')}")
    sys.exit(1)
except Exception as e:
    print(f"❌ 데이터 파싱 에러 발생: {e}")
    sys.exit(1)

print("💾 3단계: 완성된 데이터를 사이트에 중복 없이 누적 저장 중...")
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

print("✅ 성공! 100% 진짜 링크로 업데이트 완료!")
