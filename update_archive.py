import os, json, datetime, urllib.request, urllib.parse, sys
import xml.etree.ElementTree as ET

api_key = os.environ.get("GEMINI_API_KEY")

if not api_key or api_key.strip() == "":
    print("❌ 에러: GEMINI_API_KEY가 비어있습니다.")
    sys.exit(1)

api_key = api_key.strip()

print("🔍 1단계: 최근 24시간 실시간 트렌드/커뮤니티 원본 수집 중...")
# 구글 뉴스의 최근 24시간(when:1d) 검색 기능을 활용해 진짜 커뮤니티 썰과 트렌드 기사 수집
queries = [
    "블라인드 OR 직장인 OR 퇴사 when:1d",
    "네이트판 OR 연애 OR 소개팅 when:1d",
    "인스타툰 OR 밈 OR 트렌드 when:1d"
]

real_data_text = ""
idx = 1
for q in queries:
    rss_url = f"https://news.google.com/rss/search?q={urllib.parse.quote(q)}&hl=ko&gl=KR&ceid=KR:ko"
    try:
        req = urllib.request.Request(rss_url, headers={'User-Agent': 'Mozilla/5.0'})
        xml_data = urllib.request.urlopen(req).read()
        root = ET.fromstring(xml_data)
        # 각 카테고리별로 최신 글 10개씩 총 30개의 진짜 데이터를 긁어옴
        for item in root.findall('./channel/item')[:10]:
            title = item.find('title').text
            link = item.find('link').text
            real_data_text += f"[{idx}] 제목: {title}\n링크: {link}\n\n"
            idx += 1
    except Exception as e:
        print(f"⚠️ RSS 수집 중 일부 에러 발생 (무시하고 진행): {e}")

if not real_data_text:
    print("❌ 실시간 데이터를 하나도 수집하지 못했습니다.")
    sys.exit(1)

print("🚀 2단계: AI가 수집된 진짜 데이터를 인스타툰 소재로 분석 중...")
# 안정적인 1.5-flash 모델로 고정
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"

prompt = f"""
아래는 내가 방금 직접 수집한 '오늘자(최근 24시간) 커뮤니티 썰 및 트렌드' 실제 데이터 30개야.
이 중에서 인스타툰 소재로 그렸을 때 가장 사람들의 공감과 댓글이 폭발할 만한 10개를 선별해서 JSON으로 만들어줘.

[수집된 오늘자 실제 데이터]
{real_data_text}

[엄격한 조건]
1. 반드시 위에 제공된 '수집된 데이터' 안에 있는 '제목'과 '링크'를 그대로 복사해서 사용해. 절대 링크를 지어내지 마.
2. 'best_comments'는 위 기사나 썰의 맥락을 보고, 실제 2030 독자들이 공감하며 달 법한 현실적인 예상 댓글 2개를 유추해서 적어.
3. category는 글의 성격에 따라 "직장", "연애", "인스타툰" 중 하나로 분류해.
4. 반드시 마크다운 백틱 없이 순수 JSON 배열([...])로만 시작하고 끝나게 출력해.

[형식]
[{{
  "rank": 1,
  "category": "직장",
  "keyword": "회식/퇴사",
  "title": "여기에 수집된 실제 제목 입력",
  "link": "여기에 수집된 실제 링크 입력",
  "best_comments": [{{"text": "유추한 현실 반응", "likes": 1420}}],
  "reaction_summary": "댓글 분위기 예상 요약",
  "s": [5, 4, 5, 3, 4]
}}]
"""

data = {
    "contents": [{"parts": [{"text": prompt}]}]
}

try:
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
    res = urllib.request.urlopen(req)
    result = json.loads(res.read().decode('utf-8'))
    raw_text = result['candidates'][0]['content']['parts'][0]['text']
    
    clean_text = raw_text.replace('```json', '').replace('```', '').strip()
    new_items = json.loads(clean_text)
except urllib.error.HTTPError as e:
    error_msg = e.read().decode('utf-8')
    print(f"❌ API 에러 ({e.code}):\n{error_msg}")
    sys.exit(1)
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

archive.insert(0, {"date": today, "items": new_items})

with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(archive, f, ensure_ascii=False, indent=2)

print("✅ 성공! 오늘자 실시간 트렌드 업데이트 완료!")
