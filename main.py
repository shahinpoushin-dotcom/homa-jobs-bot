import os
import time
import requests

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
TELEGRAM_TOKEN    = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID  = os.environ["TELEGRAM_CHAT_ID"]
ANTHROPIC_MODEL   = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")

QUERIES = [
    ("site:ejobs.ro (welder OR sudor OR electrician OR cook OR driver) Bucuresti", "romania"),
    ("site:bestjobs.eu (welder OR electrician OR cook OR driver) Romania", "romania"),
    ("site:olx.ro (sofer OR driver OR electrician OR bucatar OR sudor) Bucuresti", "romania"),
    ("site:boss.az (surucu OR driver OR electrician OR cook OR welder)", "azerbaijan"),
    ("site:jobsearch.az (driver OR electrician OR cook OR welder)", "azerbaijan"),
    ("site:bayt.com Oman (driver OR electrician OR cook OR welder OR technician)", "oman"),
    ("site:naukrigulf.com Oman (driver OR electrician OR cook OR welder OR technician)", "oman"),
    ("site:gulftalent.com Oman (driver OR electrician OR cook OR welder OR technician)", "oman"),
]

SYSTEM = """You are a job openings collector.
Search the web and find REAL current job openings from credible sources.

CRITICAL RULES:
1) Output ONLY job blocks in EXACTLY this format. No other text.
2) Do NOT invent details. If a field is missing, leave it EMPTY.
3) Every job MUST include a valid SOURCE_URL starting with http. If no URL, skip the job.
4) Minimum 3 jobs per query if possible.

OUTPUT FORMAT:
---JOB---
COUNTRY: azerbaijan|romania|oman
CATEGORY: simple|semi|expert
TITLE:
LOCATION:
EMPLOYER:
SOURCE_URL:
SALARY:
DEADLINE:
VISA_SPONSORSHIP: yes|no|unknown
FOREIGNERS_ACCEPTED: yes|no|unknown
REQUIREMENTS:
NOTE:
---END---

CATEGORY: simple=driver/laborer/cleaner, semi=welder/cook/electrician/painter, expert=engineer/IT/doctor/teacher
TITLE and LOCATION in Persian. EMPLOYER in English."""

def post_with_retry(url, headers, payload, tries=5):
    for i in range(tries):
        r = requests.post(url, headers=headers, json=payload, timeout=120)
        if r.status_code == 429:
            wait = 30 * (i + 1)
            print(f"   ⏳ Rate limited. Waiting {wait}s...")
            time.sleep(wait)
            continue
        return r
    return r

def find_jobs(query: str, country: str) -> list:
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
        "anthropic-beta": "web-search-2025-03-05",
    }
    payload = {
        "model": ANTHROPIC_MODEL,
        "max_tokens": 900,
        "system": SYSTEM,
        "tools": [{"type": "web_search_20250305", "name": "web_search"}],
        "messages": [{
            "role": "user",
            "content": f"Search for real job postings. Query: {query}. Country: {country}. Output ONLY ---JOB--- blocks."
        }]
    }

    r = post_with_retry(
        "https://api.anthropic.com/v1/messages",
        headers=headers,
        payload=payload,
    )

    if r.status_code != 200:
        raise RuntimeError(f"API error {r.status_code}: {r.text[:400]}")

    data = r.json()
    text = "".join(b.get("text","") for b in data.get("content",[]) if b.get("type")=="text")
    print(f"   📝 {text[:200]}")
    return parse(text)

def parse(text: str) -> list:
    jobs = []
    if not text:
        return jobs
    for section in text.split("---JOB---")[1:]:
        if "---END---" not in section:
            continue
        job = {}
        for line in section.split("---END---")[0].strip().splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                job[k.strip()] = v.strip()
        src = job.get("SOURCE_URL","")
        if src.startswith("http"):
            jobs.append(job)
    return jobs

def telegram_msg(job: dict) -> str:
    flags = {"azerbaijan":"🇦🇿","romania":"🇷🇴","oman":"🇴🇲"}
    flag = flags.get(job.get("COUNTRY","").lower(),"🌍")
    cats = {"simple":"🔵 ساده","semi":"🟡 نیمه‌تخصصی","expert":"🟢 تخصصی"}
    cat = cats.get(job.get("CATEGORY","semi"),"⚪")

    def s(k): return (job.get(k,"") or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

    visa = "✅" if s("VISA_SPONSORSHIP")=="yes" else "❓" if s("VISA_SPONSORSHIP")=="unknown" else "❌"
    frn  = "✅" if s("FOREIGNERS_ACCEPTED")=="yes" else "❓" if s("FOREIGNERS_ACCEPTED")=="unknown" else "❌"

    lines = [
        f"{flag} <b>فرصت شغلی | {cat}</b>",
        f"💼 <b>{s('TITLE')}</b>",
        f"📍 {s('LOCATION')}" if s("LOCATION") else "",
        f"🏢 {s('EMPLOYER')}" if s("EMPLOYER") else "",
        f"💰 حقوق: {s('SALARY')}" if s("SALARY") else "",
        f"⏳ ددلاین: {s('DEADLINE')}" if s("DEADLINE") else "",
        f"🛂 ویزا/اسپانسر: {visa}  |  پذیرش خارجی: {frn}",
        f"📌 {s('NOTE')}" if s("NOTE") else "",
        "━━━━━━━━━━━━━━━━",
        f"📩 برای ارسال رزومه با <b>مشاورین هما</b> تماس بگیرید",
        f"🔗 <a href='{s('SOURCE_URL')}'>مشاهده آگهی</a>",
        f"\n#هما #فرصت_شغلی #{s('COUNTRY')}",
    ]
    return "\n".join(l for l in lines if l)

def send(text: str) -> bool:
    r = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id":TELEGRAM_CHAT_ID,"text":text,"parse_mode":"HTML","disable_web_page_preview":False},
        timeout=20,
    )
    return r.json().get("ok", False)

def main():
    print("🚀 هما — شروع جستجوی شغل\n")
    all_jobs = []

    for query, country in QUERIES:
        print(f"🔍 {country}: {query[:55]}...")
        try:
            jobs = find_jobs(query, country)
            all_jobs.extend(jobs)
            print(f"   ✅ {len(jobs)} شغل")
        except Exception as e:
            print(f"   ❌ {e}")
        time.sleep(20)

    seen, unique = set(), []
    for j in all_jobs:
        key = (j.get("TITLE","") + j.get("SOURCE_URL","")).lower()
        if key not in seen:
            seen.add(key)
            unique.append(j)

    print(f"\n📋 مجموع: {len(unique)} شغل\n")

    sent = 0
    for job in unique:
        try:
            if send(telegram_msg(job)):
                print(f"📤 {job.get('TITLE','')}")
                sent += 1
                time.sleep(1.5)
        except Exception as e:
            print(f"❌ {e}")

    send(f"📊 <b>گزارش هما</b>\n✅ {sent} فرصت شغلی\n🌍 آذربایجان 🇦🇿 | رومانی 🇷🇴 | عمان 🇴🇲\n#هما #گزارش_روزانه")
    print(f"\n✅ پایان — {sent} شغل ارسال شد")

if __name__ == "__main__":
    main()
