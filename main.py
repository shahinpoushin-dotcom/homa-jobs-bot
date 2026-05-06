import os
import time
import requests

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
TELEGRAM_TOKEN    = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID  = os.environ["TELEGRAM_CHAT_ID"]

QUERIES = [
    # Romania (local sources)
    ("site:ejobs.ro (welder OR sudor OR electrician OR cook OR driver) Bucuresti", "romania"),
    ("site:bestjobs.eu (welder OR electrician OR cook OR driver) Romania", "romania"),
    ("site:olx.ro (sofer OR driver OR electrician OR bucatar OR sudor) Bucuresti", "romania"),

    # Azerbaijan (local sources)
    ("site:boss.az (surucu OR sürücü OR driver OR electrician OR cook OR welder)", "azerbaijan"),
    ("site:jobsearch.az (surucu OR driver OR electrician OR cook OR welder)", "azerbaijan"),

    # Oman (local sources)
    ("site:bayt.com Oman (driver OR electrician OR cook OR welder OR technician)", "oman"),
    ("site:naukrigulf.com Oman (driver OR electrician OR cook OR welder OR technician)", "oman"),
    ("site:gulftalent.com Oman (driver OR electrician OR cook OR welder OR technician)", "oman"),
]

SYSTEM = """You are a job openings collector.
Search the web and find REAL current job openings from credible sources.
Use local job boards for the target country.

CRITICAL RULES:
1) Output ONLY job blocks in EXACTLY this format. No other text.
2) Do NOT invent details. If a field is missing from the source, leave it EMPTY (nothing after the colon).
3) Every job MUST include a valid SOURCE_URL (non-empty). If you don't have a URL, skip the job.
4) SALARY and DEADLINE are optional; leave empty if not stated.
5) VISA_SPONSORSHIP and FOREIGNERS_ACCEPTED must be:
   - yes only if explicitly stated in the posting
   - no only if explicitly stated in the posting
   - otherwise unknown
6) Minimum 3 jobs per query if possible.

OUTPUT FORMAT (no deviation):
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
CONTACT:
NOTE:
---END---

CATEGORY guide:
simple: driver, laborer, cleaner, security, warehouse
semi: welder, cook, electrician, painter, hotel staff, mechanic
expert: engineer, IT, doctor, teacher, manager, accountant

Language rules:
- TITLE and LOCATION must be in Persian.
- EMPLOYER can be English (as in source).
- Plain text only.
"""

def find_jobs(query: str, country: str) -> list[dict]:
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
        "anthropic-beta": "web-search-2025-03-05",
    }

    payload = {
        "model": "claude-3-5-haiku-latest",
        "max_tokens": 2500,
        "system": SYSTEM,
        "tools": [{"type": "web_search_20250305", "name": "web_search"}],
        "messages": [{
            "role": "user",
            "content": f"Search the web for real job postings. Query: {query}. Country: {country}. Remember: output ONLY the ---JOB--- blocks."
        }]
    }

    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers=headers,
        json=payload,
        timeout=120,
    )

    if r.status_code != 200:
        raise RuntimeError(f"Anthropic error {r.status_code}: {r.text[:800]}")

    data = r.json()
    text = "".join(
        b.get("text", "")
        for b in data.get("content", [])
        if b.get("type") == "text"
    )

    # Optional debug: if model didn't follow format, keep raw for inspection
    if "---JOB---" not in (text or ""):
        open(f"raw_{country}_{int(time.time())}.txt", "w", encoding="utf-8").write(text or "")

    return parse(text or "")

def parse(text: str) -> list[dict]:
    jobs = []
    if not text:
        return jobs

    for section in text.split("---JOB---")[1:]:
        if "---END---" not in section:
            continue

        block = section.split("---END---")[0].strip()
        job = {}

        for line in block.splitlines():
            line = line.strip()
            if not line:
                continue
            if ":" in line:
                k, _, v = line.partition(":")
                job[k.strip()] = v.strip()

        # Keep only real postings with a URL
        src = job.get("SOURCE_URL", "")
        if src.startswith("http://") or src.startswith("https://"):
            jobs.append(job)

    return jobs

def telegram_msg(job: dict) -> str:
    flags = {"azerbaijan":"🇦🇿","romania":"🇷🇴","oman":"🇴🇲"}
    flag = flags.get((job.get("COUNTRY","") or "").lower(), "🌍")

    def safe(s: str) -> str:
        return (s or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

    title = safe(job.get("TITLE",""))
    loc   = safe(job.get("LOCATION",""))
    emp   = safe(job.get("EMPLOYER",""))
    src   = safe(job.get("SOURCE_URL",""))
    sal   = safe(job.get("SALARY",""))
    ddl   = safe(job.get("DEADLINE",""))
    visa  = safe(job.get("VISA_SPONSORSHIP","unknown"))
    frn   = safe(job.get("FOREIGNERS_ACCEPTED","unknown"))

    parts = [
        f"<b>{flag} فرصت شغلی</b>",
        f"💼 <b>{title}</b>" if title else "",
        f"📍 {loc}" if loc else "",
        f"🏢 {emp}" if emp else "",
        f"💰 حقوق: {sal}" if sal else "",
        f"⏳ ددلاین: {ddl}" if ddl else "",
        f"🛂 ویزا/اسپانسر: {visa}",
        f"🌐 پذیرش خارجی‌ها: {frn}",
        f"🔗 منبع: {src}",
    ]
    return "\n".join([p for p in parts if p])

def send(text: str) -> bool:
    r = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        },
        timeout=20,
    )
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram error: {data}")
    return True

def main():
    print("Homa - starting daily job search\n")
    all_jobs = []

    for query, country in QUERIES:
        print(f"Searching {country}: {query[:60]}...")
        try:
            jobs = find_jobs(query, country)
            all_jobs.extend(jobs)
            print(f"  found {len(jobs)} jobs")
        except Exception as e:
            print(f"  error: {e}")
        time.sleep(2)

    # Deduplicate
    seen = set()
    unique = []
    for j in all_jobs:
        key = (j.get("TITLE","") + "|" + j.get("EMPLOYER","") + "|" + j.get("SOURCE_URL","")).lower()
        if key not in seen:
            seen.add(key)
            unique.append(j)

    sent = 0
    for job in unique:
        if send(telegram_msg(job)):
            sent += 1
            time.sleep(1.2)

    send(f"Daily report: {sent} jobs sent. Countries: Azerbaijan | Romania | Oman")
    print(f"\nDone. Sent {sent} jobs.")

if __name__ == "__main__":
    main()
