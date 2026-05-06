"""
هما — ربات هوشمند جستجوی شغل
Claude AI + Web Search + Telegram
"""

import os
import time
import json
import requests

# ─── تنظیمات ──────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
TELEGRAM_TOKEN    = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID  = os.environ["TELEGRAM_CHAT_ID"]
# ──────────────────────────────────────────────────────

SEARCHES = [
    "jobs Azerbaijan Baku visa sponsorship welder electrician engineer driver cook 2025",
    "jobs Azerbaijan Baku hiring foreigners work permit IT programmer teacher 2025",
    "Romania jobs foreigners work permit welder construction electrician painter cook 2025",
    "Romania ejobs bestjobs foreign workers visa sponsorship 2025",
    "Oman Muscat jobs visa sponsorship engineer driver welder hospitality cook 2025",
    "Oman bayt naukrigulf jobs iranians visa work permit 2025",
]

SYSTEM_PROMPT = """
تو دستیار هما هستی — شرکت مشاوره مهاجرت و کاریابی برای ایرانیان.

وظیفه‌ات: جستجو کن و آگهی‌های شغلی واقعی را که:
۱. ویزا یا کار پرمیت می‌دهند (visa sponsorship / work permit)
۲. برای ایرانیان امکان‌پذیر است
۳. اطلاعات کافی دارند
شناسایی و استخراج کن.

برای هر شغل دقیقاً با این فرمت بنویس:

---JOB---
CATEGORY: [simple یا semi یا expert]
TITLE: [عنوان فارسی]
LOCATION: [شهر، کشور]
COUNTRY: [azerbaijan یا romania یا oman]
EMPLOYER: [نام شرکت]
CONTRACT: [نوع قرارداد]
START: [زمان شروع]
SALARY: [حقوق یا توافقی]
BENEFITS: [مزیت۱|مزیت۲|مزیت۳]
REQUIREMENTS: [شرط۱|شرط۲|شرط۳]
DOCUMENTS: [پاسپورت معتبر|گواهی سلامت|مدارک تحصیلی]
DEADLINE: []
NOTE: [نکته مهم یا خالی]
---END---

دسته‌بندی:
- simple = راننده، کارگر، نظافت، بارانداز
- semi = جوشکار، برق‌کار، آشپز، هتل‌داری، نقاش
- expert = مهندس، IT، معلم، پزشک

فقط آگهی‌های واقعی با ویزا اسپانسرشیپ صریح بنویس.
اگر هیچ آگهی معتبری نبود فقط بنویس: NO_JOBS_FOUND
"""


def search_jobs_with_claude(query: str) -> str:
    """جستجو با Claude API + Web Search"""
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
        "anthropic-beta": "web-search-2025-03-05",
    }

    payload = {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 2000,
        "system": SYSTEM_PROMPT,
        "tools": [{"type": "web_search_20250305", "name": "web_search"}],
        "messages": [
            {
                "role": "user",
                "content": f"جستجو کن و آگهی‌های شغلی معتبر با ویزا اسپانسرشیپ پیدا کن:\n{query}"
            }
        ],
    }

    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers=headers,
        json=payload,
        timeout=60,
    )

    data = r.json()
    full_text = ""
    for block in data.get("content", []):
        if block.get("type") == "text":
            full_text += block.get("text", "")

    return full_text


def parse_jobs(text: str) -> list:
    """استخراج آگهی‌ها از متن"""
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


def format_message(job: dict) -> str:
    """فرمت پیام تلگرام"""
    cat_map = {
        "simple": ("🔵", "ساده"),
        "semi":   ("🟡", "نیمه‌تخصصی"),
        "expert": ("🟢", "تخصصی"),
    }
    emoji, label = cat_map.get(job.get("CATEGORY", "semi"), ("⚪", "سایر"))

    flags = {
        "azerbaijan": "🇦🇿", "romania": "🇷🇴", "oman": "🇴🇲",
        "qatar": "🇶🇦", "turkey": "🇹🇷", "germany": "🇩🇪", "uk": "🇬🇧",
    }
    flag = flags.get(job.get("COUNTRY", "").lower(), "🌍")

    def bullet_list(field):
        return "\n".join(
            f"▫️ {x.strip()}"
            for x in job.get(field, "").split("|") if x.strip()
        )

    docs = " | ".join(
        x.strip() for x in job.get("DOCUMENTS", "").split("|") if x.strip()
    )
    deadline = (
        f"\n⏰ <b>این فرصت فقط {job['DEADLINE']} ساعت معتبر است</b>"
        if job.get("DEADLINE") else ""
    )
    note = f"\n\n📌 {job['NOTE']}" if job.get("NOTE") else ""
    country_tag = job.get("COUNTRY", "").replace(" ", "_")

    return f"""{emoji} <b>فرصت شغلی | {label}</b>
{flag} {job.get("TITLE", "")}

━━━━━━━━━━━━━━━━
<b>💼 موقعیت</b>
📍 {job.get("LOCATION", "")}
🏢 {job.get("EMPLOYER", "")}
📄 {job.get("CONTRACT", "")}
🗓 شروع: {job.get("START", "")}

<b>💰 حقوق و مزایا</b>
💵 حقوق: {job.get("SALARY", "")}
{bullet_list("BENEFITS")}

<b>📋 شرایط</b>
{bullet_list("REQUIREMENTS")}

<b>📁 مدارک لازم</b>
{docs}
━━━━━━━━━━━━━━━━{deadline}
📩 برای ارسال رزومه با <b>مشاورین هما</b> تماس بگیرید{note}

#هما #فرصت_شغلی #{country_tag} #{label.replace("‌", "")}"""


def send_telegram(text: str) -> bool:
    """ارسال به تلگرام"""
    r = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
        timeout=10,
    )
    return r.json().get("ok", False)


def main():
    print("🚀 هما — شروع جستجوی روزانه\n")
    all_jobs = []

    for query in SEARCHES:
        print(f"🔍 {query[:60]}...")
        try:
            result = search_jobs_with_claude(query)
            jobs = parse_jobs(result)
            all_jobs.extend(jobs)
            print(f"   ✅ {len(jobs)} شغل پیدا شد")
        except Exception as e:
            print(f"   ❌ خطا: {e}")
        time.sleep(3)

    # حذف تکراری
    seen, unique = set(), []
    for j in all_jobs:
        key = j.get("TITLE", "") + j.get("LOCATION", "")
        if key not in seen:
            seen.add(key)
            unique.append(j)

    print(f"\n📋 مجموع: {len(unique)} شغل منحصربه‌فرد\n")

    sent = 0
    for job in unique:
        msg = format_message(job)
        if send_telegram(msg):
            print(f"📤 ارسال: {job.get('TITLE', '')}")
            sent += 1
            time.sleep(1.5)

    send_telegram(f"""📊 <b>گزارش روزانه هما</b>

✅ {sent} فرصت شغلی معتبر امروز
🌍 آذربایجان 🇦🇿 | رومانی 🇷🇴 | عمان 🇴🇲

#هما #گزارش_روزانه""")

    print(f"\n✅ پایان — {sent} شغل ارسال شد")


if __name__ == "__main__":
    main()
