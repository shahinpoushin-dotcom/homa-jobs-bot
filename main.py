"""
هما — ربات هوشمند جستجوی شغل
Claude AI + Web Search + Telegram
"""

import os
import time
import json
import requests

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
TELEGRAM_TOKEN    = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID  = os.environ["TELEGRAM_CHAT_ID"]

SEARCHES = [
    "Romania Bucharest jobs hiring foreigners welder electrician construction cook 2025",
    "Romania jobs work permit non-EU workers 2025 driver painter warehouse",
    "Azerbaijan Baku job vacancies 2025 engineer IT welder driver cook hospitality",
    "Azerbaijan Baku jobs hiring foreigners 2025 work permit",
    "Oman Muscat job vacancies 2025 engineer technician driver cook hospitality",
    "Oman jobs hiring expats 2025 welder electrician construction driver",
]

def call_claude(messages, system="", use_search=False, max_tokens=2000):
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
        "anthropic-beta": "web-search-2025-03-05",
    }
    payload = {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system:
        payload["system"] = system
    if use_search:
        payload["tools"] = [{"type": "web_search_20250305", "name": "web_search"}]

    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers=headers,
        json=payload,
        timeout=60,
    )
    data = r.json()
    text = ""
    for block in data.get("content", []):
        if block.get("type") == "text":
            text += block.get("text", "")
    return text


def search_jobs(query: str) -> str:
    """مرحله ۱: جستجوی شغل"""
    return call_claude(
        messages=[{"role": "user", "content": f"Search for real job openings: {query}. List job title, company name, location, salary, and requirements for each job found."}],
        use_search=True,
        max_tokens=2000,
    )


def format_jobs(search_result: str, country: str) -> str:
    """مرحله ۲: فرمت‌کردن نتایج"""
    system = """You extract job listings from text and format them strictly.
For each job found, output EXACTLY:

---JOB---
CATEGORY: simple
TITLE: [job title in Persian]
LOCATION: [city, country in Persian]
COUNTRY: """ + country + """
EMPLOYER: [company name]
CONTRACT: تمام‌وقت
START: فوری
SALARY: [salary or توافقی]
BENEFITS: بیمه درمان|اسکان|وعده غذا
REQUIREMENTS: [main requirement 1|requirement 2|requirement 3]
DOCUMENTS: پاسپورت معتبر|گواهی سلامت|مدارک تحصیلی
DEADLINE:
NOTE: برای اطلاعات بیشتر با هما تماس بگیرید
---END---

Set CATEGORY based on job type:
- simple: driver, laborer, cleaner, warehouse worker
- semi: welder, cook, electrician, painter, hotel staff
- expert: engineer, IT, doctor, teacher, manager

Output ONLY the formatted jobs. If no jobs in the text, output: NO_JOBS_FOUND"""

    return call_claude(
        messages=[{"role": "user", "content": f"Extract and format all jobs from this text:\n\n{search_result}"}],
        system=system,
        use_search=False,
        max_tokens=2000,
    )


def parse_jobs(text: str) -> list:
    jobs = []
    if not text or "NO_JOBS_FOUND" in text:
        return jobs
    for section in text.split("---JOB---")[1:]:
        if "---END---" not in section:
            continue
        job = {}
        for line in section.split("---END---")[0].strip().split("\n"):
            if ":" in line:
                k, _, v = line.partition(":")
                job[k.strip()] = v.strip()
        if job.get("TITLE"):
            jobs.append(job)
    return jobs


def format_telegram(job: dict) -> str:
    cat_map = {
        "simple": ("🔵", "ساده"),
        "semi":   ("🟡", "نیمه‌تخصصی"),
        "expert": ("🟢", "تخصصی"),
    }
    emoji, label = cat_map.get(job.get("CATEGORY", "semi"), ("⚪", "سایر"))
    flags = {"azerbaijan": "🇦🇿", "romania": "🇷🇴", "oman": "🇴🇲"}
    flag = flags.get(job.get("COUNTRY", "").lower(), "🌍")

    def bullets(f):
        return "\n".join(f"▫️ {x.strip()}" for x in job.get(f,"").split("|") if x.strip())

    docs = " | ".join(x.strip() for x in job.get("DOCUMENTS","").split("|") if x.strip())

    return f"""{emoji} <b>فرصت شغلی | {label}</b>
{flag} {job.get("TITLE","")}

━━━━━━━━━━━━━━━━
<b>💼 موقعیت</b>
📍 {job.get("LOCATION","")}
🏢 {job.get("EMPLOYER","")}
📄 {job.get("CONTRACT","")}
🗓 شروع: {job.get("START","")}

<b>💰 حقوق و مزایا</b>
💵 حقوق: {job.get("SALARY","")}
{bullets("BENEFITS")}

<b>📋 شرایط</b>
{bullets("REQUIREMENTS")}

<b>📁 مدارک لازم</b>
{docs}
━━━━━━━━━━━━━━━━
📩 برای ارسال رزومه با <b>مشاورین هما</b> تماس بگیرید

#هما #فرصت_شغلی #{job.get("COUNTRY","").replace(" ","_")} #{label.replace("‌","")}"""


def send_telegram(text: str) -> bool:
    r = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": TELEGRAM_CHAT_ID, "text": text,
              "parse_mode": "HTML", "disable_web_page_preview": True},
        timeout=10,
    )
    return r.json().get("ok", False)


COUNTRY_MAP = {
    "Romania": "romania",
    "Azerbaijan": "azerbaijan",
    "Oman": "oman",
}


def main():
    print("🚀 هما — شروع جستجوی روزانه\n")
    all_jobs = []

    for query in SEARCHES:
        country = next((v for k, v in COUNTRY_MAP.items() if k in query), "azerbaijan")
        print(f"🔍 جستجو: {query[:50]}...")
        try:
            raw = search_jobs(query)
            print(f"   📝 {len(raw)} کاراکتر پیدا شد")
            formatted = format_jobs(raw, country)
            jobs = parse_jobs(formatted)
            all_jobs.extend(jobs)
            print(f"   ✅ {len(jobs)} شغل استخراج شد")
        except Exception as e:
            print(f"   ❌ خطا: {e}")
        time.sleep(5)

    seen, unique = set(), []
    for j in all_jobs:
        key = j.get("TITLE","") + j.get("EMPLOYER","")
        if key not in seen:
            seen.add(key)
            unique.append(j)

    print(f"\n📋 مجموع: {len(unique)} شغل\n")

    sent = 0
    for job in unique:
        if send_telegram(format_telegram(job)):
            print(f"📤 {job.get('TITLE','')}")
            sent += 1
            time.sleep(1.5)

    send_telegram(f"""📊 <b>گزارش روزانه هما</b>

✅ {sent} فرصت شغلی معتبر امروز
🌍 آذربایجان 🇦🇿 | رومانی 🇷🇴 | عمان 🇴🇲

#هما #گزارش_روزانه""")

    print(f"\n✅ پایان — {sent} شغل ارسال شد")


if __name__ == "__main__":
    main()
