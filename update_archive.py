import os
import json
import time
import datetime
import urllib.request
import urllib.error
import sys


# =========================================================
# 1. GitHub Secrets
# =========================================================

SERPER_API_KEY = os.environ.get("SERPER_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.environ.get("SUPABASE_SECRET_KEY")


# =========================================================
# 2. 기본 설정
# =========================================================

GEMINI_MODEL = os.environ.get(
    "GEMINI_MODEL",
    "gemini-3.7-flash"
)

# 하루 자동 수집에서 Gemini를 최대 몇 번 호출할지
MAX_GEMINI_REQUESTS = int(
    os.environ.get(
        "MAX_GEMINI_REQUESTS",
        "10"
    )
)

# 이 점수 이상만 DB에 저장
MIN_TOON_FIT_SCORE = int(
    os.environ.get(
        "MIN_TOON_FIT_SCORE",
        "65"
    )
)


# =========================================================
# 3. 필수 Secret 확인
# =========================================================

required_values = {
    "SERPER_API_KEY": SERPER_API_KEY,
    "GEMINI_API_KEY": GEMINI_API_KEY,
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
# 4. 검색 키워드
# =========================================================

QUERIES = [

    # 직장
    "직장인 퇴사 썰 공감",
    "회사 상사 썰 직장인 공감",
    "회사에서 황당했던 일 썰",
    "신입사원 직장생활 공감",
    "직장인 월요일 공감",

    # 연애
    "연애 서운했던 순간 썰",
    "소개팅 현실 공감 썰",
    "장기연애 공감 썰",
    "이별 후 공감 썰",
    "썸 연애 현실 공감",

    # 일상 / 인간관계
    "친구 인간관계 공감 썰",
    "자취 현실 공감 썰",
    "혼자 살면서 생긴 일 썰",
    "요즘 사람들 일상 공감",
    "SNS 인간관계 공감 썰",
]


# =========================================================
# 5. Gemini 무료 할당량 초과용 예외
# =========================================================

class GeminiQuotaError(Exception):
    pass


# =========================================================
# 6. Serper 검색
# =========================================================

def serper_search(query):

    url = "https://google.serper.dev/search"

    body = {
        "q": query,
        "gl": "kr",
        "hl": "ko",
        "num": 10,
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(
            body
        ).encode("utf-8"),
        headers={
            "X-API-KEY":
                SERPER_API_KEY,

            "Content-Type":
                "application/json",
        },
        method="POST",
    )

    try:

        with urllib.request.urlopen(
            req,
            timeout=30
        ) as response:

            result = json.loads(
                response
                .read()
                .decode("utf-8")
            )

        items = []

        for item in result.get(
            "organic",
            []
        ):

            title = (
                item
                .get(
                    "title",
                    ""
                )
                .strip()
            )

            link = (
                item
                .get(
                    "link",
                    ""
                )
                .strip()
            )

            snippet = (
                item
                .get(
                    "snippet",
                    ""
                )
                .strip()
            )

            if not title or not link:
                continue

            items.append({
                "source_title":
                    title,

                "source_url":
                    link,

                "source_snippet":
                    snippet,

                "search_query":
                    query,
            })

        return items

    except urllib.error.HTTPError as e:

        error_body = (
            e.read()
            .decode(
                "utf-8",
                errors="ignore"
            )
        )

        print(
            f"❌ Serper 검색 실패 "
            f"[{query}] HTTP {e.code}"
        )

        print(error_body)

        return []

    except Exception as e:

        print(
            f"❌ Serper 검색 실패 "
            f"[{query}] : {e}"
        )

        return []


# =========================================================
# 7. Supabase에 이미 존재하는 URL 가져오기
# =========================================================

def get_existing_urls():

    endpoint = (
        f"{SUPABASE_URL}"
        "/rest/v1/toon_archive"
        "?select=source_url"
        "&limit=1000"
    )

    req = urllib.request.Request(
        endpoint,
        headers={
            "apikey":
                SUPABASE_SECRET_KEY,

            "Authorization":
                f"Bearer "
                f"{SUPABASE_SECRET_KEY}",
        },
        method="GET",
    )

    try:

        with urllib.request.urlopen(
            req,
            timeout=30
        ) as response:

            rows = json.loads(
                response
                .read()
                .decode("utf-8")
            )

        return {
            row.get(
                "source_url"
            )
            for row in rows
            if row.get(
                "source_url"
            )
        }

    except Exception as e:

        print(
            f"⚠️ 기존 URL 조회 실패: {e}"
        )

        print(
            "중복 확인 없이 계속 진행합니다."
        )

        return set()


# =========================================================
# 8. Gemini 분석
# =========================================================

def analyze_with_gemini(item):

    url = (
        "https://generativelanguage.googleapis.com/"
        "v1beta/"
        f"models/{GEMINI_MODEL}:generateContent"
    )

    prompt = f"""
아래는 검색 API를 통해 실제로 수집한 데이터다.

[실제 원본 데이터]

제목:
{item["source_title"]}

URL:
{item["source_url"]}

검색 결과 설명:
{item["source_snippet"]}

검색 키워드:
{item["search_query"]}


이 자료가 인스타툰 소재로 활용하기 좋은지 분석해라.

반드시 아래 규칙을 지켜라.

1. 실제 데이터에 없는 좋아요 수를 만들지 마라.
2. 실제 데이터에 없는 댓글 수를 만들지 마라.
3. 실제 댓글을 본 것처럼 댓글을 만들지 마라.
4. 조회수를 상상해서 만들지 마라.
5. 사실처럼 보이는 숫자를 임의로 만들지 마라.
6. 제목과 URL은 수정하거나 새로 만들지 마라.
7. 모든 평가는 AI 분석이라는 전제로 작성한다.
8. toon_fit_score는 1~100 사이 정수다.

아래 JSON 형식으로만 응답해라.

{{
  "category": "직장 또는 연애 또는 일상 또는 기타",
  "keyword": "핵심 키워드 하나",
  "ai_summary": "왜 사람들이 공감할 수 있는 인스타툰 소재인지 2~3문장",
  "toon_fit_score": 85,
  "hook": "인스타툰 첫 장에 사용할 수 있는 후킹 문장",
  "story_angle": "이 소재를 어떤 이야기 흐름으로 만들면 좋을지 설명"
}}
"""

    body = {

        "contents": [
            {
                "parts": [
                    {
                        "text":
                            prompt
                    }
                ]
            }
        ],

        "generationConfig": {

            "responseMimeType":
                "application/json"

        }
    }


    # 503일 때 최대 3번 재시도
    for attempt in range(
        1,
        4
    ):

        req = urllib.request.Request(

            url,

            data=json.dumps(
                body
            ).encode(
                "utf-8"
            ),

            headers={
                "Content-Type":
                    "application/json",

                "x-goog-api-key":
                    GEMINI_API_KEY,
            },

            method="POST",
        )

        try:

            with urllib.request.urlopen(
                req,
                timeout=60
            ) as response:

                result = json.loads(
                    response
                    .read()
                    .decode(
                        "utf-8"
                    )
                )

            raw_text = (
                result
                ["candidates"]
                [0]
                ["content"]
                ["parts"]
                [0]
                ["text"]
            )

            analysis = json.loads(
                raw_text
            )

            try:

                score = int(
                    analysis.get(
                        "toon_fit_score",
                        50
                    )
                )

            except (
                TypeError,
                ValueError
            ):

                score = 50

            score = max(
                1,
                min(
                    100,
                    score
                )
            )

            return {

                "category":
                    analysis.get(
                        "category",
                        "기타"
                    ),

                "keyword":
                    analysis.get(
                        "keyword",
                        ""
                    ),

                "ai_summary":
                    analysis.get(
                        "ai_summary",
                        ""
                    ),

                "toon_fit_score":
                    score,

                "hook":
                    analysis.get(
                        "hook",
                        ""
                    ),

                "story_angle":
                    analysis.get(
                        "story_angle",
                        ""
                    ),
            }


        except urllib.error.HTTPError as e:

            error_body = (
                e.read()
                .decode(
                    "utf-8",
                    errors="ignore"
                )
            )


            # 무료 할당량 초과
            if e.code == 429:

                raise GeminiQuotaError(
                    error_body
                )


            # 일시적 과부하
            if (
                e.code == 503
                and attempt < 3
            ):

                wait_seconds = (
                    attempt * 2
                )

                print(
                    "⚠️ Gemini 503 과부하. "
                    f"{wait_seconds}초 후 "
                    f"재시도 ({attempt}/3)"
                )

                time.sleep(
                    wait_seconds
                )

                continue


            print(
                f"❌ Gemini 분석 실패 "
                f"HTTP {e.code}"
            )

            print(
                error_body
            )

            return None


        except Exception as e:

            print(
                f"❌ Gemini 분석 실패: {e}"
            )

            return None


    return None


# =========================================================
# 9. Supabase 저장
# =========================================================

def save_to_supabase(row):

    endpoint = (
        f"{SUPABASE_URL}"
        "/rest/v1/toon_archive"
        "?on_conflict=source_url"
    )

    req = urllib.request.Request(

        endpoint,

        data=json.dumps(
            row,
            ensure_ascii=False
        ).encode(
            "utf-8"
        ),

        headers={

            "apikey":
                SUPABASE_SECRET_KEY,

            "Authorization":
                f"Bearer "
                f"{SUPABASE_SECRET_KEY}",

            "Content-Type":
                "application/json",

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
            f"❌ Supabase 저장 실패 "
            f"HTTP {e.code}"
        )

        print(
            error_body
        )

        return False

    except Exception as e:

        print(
            f"❌ Supabase 저장 실패: {e}"
        )

        return False


# =========================================================
# 10. 검색 결과를 골고루 섞기
# =========================================================

def collect_candidates():

    results_by_query = []

    for query in QUERIES:

        print(
            f"검색 중: {query}"
        )

        results = serper_search(
            query
        )

        print(
            f"→ {len(results)}개 발견"
        )

        results_by_query.append(
            results
        )


    # 검색어 하나가 후보를 독점하지 않도록
    # 첫 번째 결과 → 다음 검색어 첫 번째 결과 → ...
    candidates = []

    seen_urls = set()

    max_len = max(
        (
            len(items)
            for items
            in results_by_query
        ),
        default=0
    )


    for index in range(
        max_len
    ):

        for items in results_by_query:

            if index >= len(items):
                continue

            item = items[
                index
            ]

            url = item[
                "source_url"
            ]

            if url in seen_urls:
                continue

            seen_urls.add(
                url
            )

            candidates.append(
                item
            )


    return candidates


# =========================================================
# 11. 전체 실행
# =========================================================

def main():

    print("")

    print(
        "=============================="
    )

    print(
        "🚀 TOON ARCHIVE 자동 수집 시작"
    )

    print(
        "=============================="
    )

    print("")


    # -----------------------------------------------------
    # 1단계
    # -----------------------------------------------------

    print(
        "🔍 1단계: "
        "Serper 검색 데이터 수집"
    )

    candidates = (
        collect_candidates()
    )

    print(
        f"✅ 중복 제거 후 후보: "
        f"{len(candidates)}개"
    )


    if not candidates:

        print(
            "❌ 검색 결과가 없습니다."
        )

        sys.exit(1)


    # -----------------------------------------------------
    # 2단계
    # -----------------------------------------------------

    print("")

    print(
        "🧹 2단계: "
        "이미 DB에 있는 URL 제외"
    )

    existing_urls = (
        get_existing_urls()
    )


    new_candidates = [

        item

        for item in candidates

        if item[
            "source_url"
        ] not in existing_urls

    ]


    print(
        f"기존 DB URL: "
        f"{len(existing_urls)}개"
    )

    print(
        f"새 후보: "
        f"{len(new_candidates)}개"
    )


    if not new_candidates:

        print(
            "✅ 오늘 새로 분석할 "
            "URL이 없습니다."
        )

        return


    # -----------------------------------------------------
    # Gemini 분석 개수 제한
    # -----------------------------------------------------

    selected = (
        new_candidates[
            :MAX_GEMINI_REQUESTS
        ]
    )


    # -----------------------------------------------------
    # 3단계
    # -----------------------------------------------------

    print("")

    print(
        "🤖 3단계: Gemini 분석"
    )

    print(
        f"오늘 Gemini 최대 호출 수: "
        f"{MAX_GEMINI_REQUESTS}회"
    )

    print(
        f"실제 분석 대상: "
        f"{len(selected)}개"
    )

    print(
        f"저장 기준 점수: "
        f"{MIN_TOON_FIT_SCORE}점 이상"
    )


    success_count = 0

    low_score_count = 0

    fail_count = 0

    gemini_call_count = 0


    for number, item in enumerate(
        selected,
        start=1
    ):

        print("")

        print(
            f"[{number}/{len(selected)}] "
            f"{item['source_title'][:80]}"
        )


        try:

            gemini_call_count += 1

            analysis = (
                analyze_with_gemini(
                    item
                )
            )


        except GeminiQuotaError as e:

            print(
                "🛑 Gemini 무료 할당량을 "
                "모두 사용했습니다."
            )

            print(
                "오늘 수집은 여기서 "
                "중단합니다."
            )

            print(
                str(e)[:500]
            )

            break


        if not analysis:

            fail_count += 1

            continue


        # -------------------------------------------------
        # 낮은 점수 제거
        # -------------------------------------------------

        if (
            analysis[
                "toon_fit_score"
            ]
            < MIN_TOON_FIT_SCORE
        ):

            low_score_count += 1

            print(
                "⏭️ 적합도 낮아서 제외: "
                f"{analysis['toon_fit_score']}점"
            )

            continue


        # -------------------------------------------------
        # DB 저장
        # -------------------------------------------------

        now = (
            datetime
            .datetime
            .now(
                datetime.timezone.utc
            )
            .isoformat()
        )


        row = {

            # 실제 검색 데이터
            "source_url":
                item["source_url"],

            "source_title":
                item["source_title"],

            "source_type":
                "serper_google_search",

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
                analysis[
                    "toon_fit_score"
                ],

            "hook":
                analysis["hook"],

            "story_angle":
                analysis[
                    "story_angle"
                ],

            "ai_model":
                GEMINI_MODEL,

            "analyzed_at":
                now,
        }


        if save_to_supabase(
            row
        ):

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

    print(
        "=============================="
    )

    print(
        "🎉 자동 수집 종료"
    )

    print(
        "=============================="
    )

    print(
        f"Gemini 호출: "
        f"{gemini_call_count}회"
    )

    print(
        f"DB 저장 성공: "
        f"{success_count}개"
    )

    print(
        f"{MIN_TOON_FIT_SCORE}점 미만 제외: "
        f"{low_score_count}개"
    )

    print(
        f"실패: "
        f"{fail_count}개"
    )

    print("")


if __name__ == "__main__":

    main()
