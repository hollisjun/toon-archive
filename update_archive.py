import os
import json
import datetime
import urllib.request
import urllib.parse
import urllib.error
import sys


# =========================================================
# 1. GitHub Secrets에서 비밀값 가져오기
# =========================================================

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

GOOGLE_SEARCH_API_KEY = (
    os.environ.get("GOOGLE_SEARCH_API_KEY")
    or os.environ.get("GOOGLE_SERCH_API")
)

SEARCH_ENGINE_ID = os.environ.get("SEARCH_ENGINE_ID")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.environ.get("SUPABASE_SECRET_KEY")


# =========================================================
# 2. 필요한 키가 다 있는지 확인
# =========================================================

required_values = {
    "GEMINI_API_KEY": GEMINI_API_KEY,
    "GOOGLE_SEARCH_API_KEY": GOOGLE_SEARCH_API_KEY,
    "SEARCH_ENGINE_ID": SEARCH_ENGINE_ID,
    "SUPABASE_URL": SUPABASE_URL,
    "SUPABASE_SECRET_KEY": SUPABASE_SECRET_KEY,
}

missing = [
    name
    for name, value in required_values.items()
    if not value
]

if missing:
    print("❌ 필요한 GitHub Secret이 없습니다.")
    print("누락:", ", ".join(missing))
    sys.exit(1)


# =========================================================
# 3. 검색할 키워드
# =========================================================

QUERIES = [
    "직장 퇴사 썰",
    "연애 이별 공감",
    "일상 공감 썰",
    "직장인 공감",
    "연애 공감",
]


# =========================================================
# 4. Google 검색
# =========================================================

def google_search(query):

    params = urllib.parse.urlencode({
        "q": query,
        "cx": SEARCH_ENGINE_ID,
        "key": GOOGLE_SEARCH_API_KEY,
        "dateRestrict": "d7",
        "num": 10,
    })

    search_url = (
        "https://customsearch.googleapis.com/customsearch/v1?"
        + params
    )

    try:

        req = urllib.request.Request(search_url)

        with urllib.request.urlopen(
            req,
            timeout=30
        ) as response:

            result = json.loads(
                response.read().decode("utf-8")
            )

        items = []

        for item in result.get("items", []):

            title = item.get("title", "").strip()
            link = item.get("link", "").strip()

            if not title or not link:
                continue

            items.append({
                "source_title": title,
                "source_url": link,
                "search_query": query,
            })

        return items

    except Exception as e:

        print(
            f"⚠️ Google 검색 실패 [{query}] : {e}"
        )

        return []


# =========================================================
# 5. Gemini에게 '분석만' 시키기
# =========================================================

def analyze_with_gemini(item):

    model = "gemini-3.7-flash"

    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"models/{model}:generateContent"
    )

    prompt = f"""
아래 데이터는 Google 검색 API를 통해 실제로 수집한 데이터다.

[실제 원본 데이터]

제목:
{item["source_title"]}

URL:
{item["source_url"]}

검색 키워드:
{item["search_query"]}


이 자료가 인스타툰 소재로 활용하기 좋은지 분석해줘.

반드시 다음 규칙을 지켜라.

1. 실제 데이터에 없는 좋아요 수를 만들지 마라.
2. 실제 데이터에 없는 댓글 수를 만들지 마라.
3. 실제 댓글을 본 것처럼 댓글을 만들지 마라.
4. 조회수를 상상해서 만들지 마라.
5. 모든 평가는 반드시 "AI 분석"일 뿐이다.
6. 제목이나 URL을 새로 만들어내지 마라.
7. toon_fit_score는 1~100 사이의 정수다.

아래 JSON 형식으로만 응답해라.

{{
  "category": "직장 또는 연애 또는 일상 또는 기타",
  "keyword": "핵심 키워드 하나",
  "ai_summary": "왜 사람들이 공감할 수 있는 인스타툰 소재인지 2~3문장으로 설명",
  "toon_fit_score": 85,
  "hook": "인스타툰 첫 장에서 사용할 수 있는 후킹 문장",
  "story_angle": "이 소재를 어떤 이야기 흐름으로 만들면 좋을지 간단하게 설명"
}}
"""

    body = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
        }
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": GEMINI_API_KEY,
        },
        method="POST",
    )

    try:

        with urllib.request.urlopen(
            req,
            timeout=60
        ) as response:

            result = json.loads(
                response.read().decode("utf-8")
            )

        raw_text = (
            result["candidates"][0]
            ["content"]
            ["parts"][0]
            ["text"]
        )

        analysis = json.loads(raw_text)

        return {
            "category": analysis.get(
                "category",
                "기타"
            ),

            "keyword": analysis.get(
                "keyword",
                ""
            ),

            "ai_summary": analysis.get(
                "ai_summary",
                ""
            ),

            "toon_fit_score": analysis.get(
                "toon_fit_score",
                50
            ),

            "hook": analysis.get(
                "hook",
                ""
            ),

            "story_angle": analysis.get(
                "story_angle",
                ""
            ),
        }

    except Exception as e:

        print(
            f"⚠️ Gemini 분석 실패: {e}"
        )

        return None


# =========================================================
# 6. Supabase에 저장
# =========================================================

def save_to_supabase(row):

    endpoint = (
        f"{SUPABASE_URL}/rest/v1/toon_archive"
        "?on_conflict=source_url"
    )

    payload = json.dumps(
        row,
        ensure_ascii=False
    ).encode("utf-8")

    req = urllib.request.Request(
        endpoint,
        data=payload,
        headers={
            "apikey": SUPABASE_SECRET_KEY,
            "Authorization":
                f"Bearer {SUPABASE_SECRET_KEY}",
            "Content-Type": "application/json",
            "Prefer":
                "resolution=merge-duplicates",
        },
        method="POST",
    )

    try:

        with urllib.request.urlopen(
            req,
            timeout=30
        ) as response:

            response.read()

        return True

    except urllib.error.HTTPError as e:

        error_body = (
            e.read()
            .decode(
                "utf-8",
                errors="ignore"
            )
        )

        print(
            f"❌ Supabase 저장 실패: "
            f"{e.code}"
        )

        print(error_body)

        return False

    except Exception as e:

        print(
            f"❌ Supabase 저장 실패: {e}"
        )

        return False


# =========================================================
# 7. 전체 실행
# =========================================================

def main():

    print("")
    print("==============================")
    print("🚀 TOON ARCHIVE 자동 수집 시작")
    print("==============================")
    print("")

    all_items = {}

    # -----------------------------------------------------
    # Google 검색
    # -----------------------------------------------------

    print("🔍 1단계: 실제 검색 데이터 수집")

    for query in QUERIES:

        print(
            f"검색 중: {query}"
        )

        results = google_search(query)

        print(
            f"→ {len(results)}개 발견"
        )

        for item in results:

            # URL을 기준으로 중복 제거
            all_items[
                item["source_url"]
            ] = item

    print("")
    print(
        f"✅ 중복 제거 후 "
        f"{len(all_items)}개"
    )
    print("")

    if not all_items:

        print(
            "❌ 검색 결과가 없습니다."
        )

        sys.exit(1)

    # -----------------------------------------------------
    # Gemini 분석 + Supabase 저장
    # -----------------------------------------------------

    print(
        "🤖 2단계: "
        "Gemini 소재 분석 시작"
    )

    success_count = 0
    fail_count = 0

    for number, item in enumerate(
        all_items.values(),
        start=1
    ):

        print("")
        print(
            f"[{number}/{len(all_items)}]"
        )

        print(
            item["source_title"][:80]
        )

        analysis = analyze_with_gemini(
            item
        )

        if not analysis:

            fail_count += 1
            continue

        now = (
            datetime.datetime.now(
                datetime.timezone.utc
            )
            .isoformat()
        )

        row = {

            # 실제 수집 데이터
            "source_url":
                item["source_url"],

            "source_title":
                item["source_title"],

            "source_type":
                "google_custom_search",

            "search_query":
                item["search_query"],


            # AI 분석 데이터
            "category":
                analysis["category"],

            "keyword":
                analysis["keyword"],

            "ai_summary":
                analysis["ai_summary"],

            "toon_fit_score":
                analysis["toon_fit_score"],

            "hook":
                analysis["hook"],

            "story_angle":
                analysis["story_angle"],

            "ai_model":
                "gemini-3.7-flash",

            "analyzed_at":
                now,
        }

        saved = save_to_supabase(
            row
        )

        if saved:

            success_count += 1

            print(
                "✅ Supabase 저장 완료"
            )

        else:

            fail_count += 1

    # -----------------------------------------------------
    # 결과
    # -----------------------------------------------------

    print("")
    print("==============================")
    print("🎉 자동 수집 완료")
    print("==============================")

    print(
        f"성공: {success_count}"
    )

    print(
        f"실패: {fail_count}"
    )

    print("")


if __name__ == "__main__":
    main()
