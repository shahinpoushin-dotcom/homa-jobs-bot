"""
هما — ربات جستجوی شغل
Adzuna API (رایگان) + Telegram
"""

import os
import time
import requests

TELEGRAM_TOKEN   = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
ADZUNA_APP_ID    = os.environ["ADZUNA_APP_ID"]
ADZUNA_API_KEY   = os.environ["ADZUNA_API_KEY"]

# کشورها و دسته‌بندی‌ها
SEARCHES = [
    # رومانی
    ("ro", "welder",      "romania",     "semi"),
    ("ro", "electrician", "romania",     "semi"),
    ("ro", "cook",        "romania",     "semi"),
    ("ro", "driver",      "romania",     "simple"),
    ("ro", "engineer",    "romania",     "expert"),
    # عمان
    ("gb", "welder oman",      "oman",   "semi"),
    ("gb", "cook oman",        "oman",   "semi"),
    ("gb", "driver oman",      "oman",   "simple"),
    ("gb", "engineer oman",    "oman",   "expert"),
    # آذربایجان — از UK چون Adzuna AZ ندارد
    ("gb", "engineer azerbaijan",  "azerbaijan", "expert"),
    ("gb", "IT azerbaijan baku",   "azerbaijan", "expert"),
]

CAT_LABELS = {
    "simple": ("🔵", "ساده"),
    "semi":   ("🟡", "نیمه‌تخصصی"),
    "expert": ("🟢", "تخصصی"),
}

FLAGS = {
    "romania":    "🇷🇴",
    "oman":       "🇴🇲",
    "azerbaijan": "🇦🇿",
}

COUNTRY_FA = {
    "romania":    "رومانی",
    "oman":       "عمان",
    "azerbaijan": "آذربایجان",
}


def fetch_jobs(country_code: str, what: str, results: int = 5) -> list:
    """جستجو از Adzuna API"""
    url = f"https://api.adzuna.com/v1/api/jobs/{country_code}/search/1"
    params = {
        "app_id":       ADZUNA_APP_ID,
        "app_key":      ADZUNA_API_KEY,
        "results_per_page": results,
        "what":         what,
        "content-type": "application/json",
    }
    r = requests.get(url, params=params, timeout=15)
    if r.status_code != 200:
        print(f"   ❌ Adzuna error {r.status_code}")
        return []
    return r.json().get("results", [])


def format_message(job: dict, country: str, category: str) -> str:
    emoji, label = CAT_LABELS.get(category, ("⚪", "سایر"))
    flag = FLAGS.get(country, "🌍")
    country_fa = COUNTRY_FA.get(country, country)

    title    = job.get("title", "")
    company  = job.get("company", {}).get("display_name", "")
    location = job.get("location", {}).get("display_name", "")
    salary_min = job.get("salary_min")
    salary_max = job.get("salary_max")
    url      = job.get("redirect_url", "")
    desc     = job.get("description", "")[:200]

    if salary_min and salary_max:
        salary = f"{int(salary_min):,} - {int(salary_max):,}"
    elif salary_min:
        salary = f"از {int(salary_min):,}"
    else:
        salary = "توافقی"

    return f"""{emoji} <b>فرصت شغلی | {label}</b>
{flag} {title}

━━━━━━━━━━━━━━━━
<b>💼 موقعیت</b>
📍 {location}، {country_fa}
🏢 {company}
📄 تمام‌وقت
🗓 شروع: فوری

<b>💰 حقوق</b>
💵 {salary}

<b>📋 توضیحات</b>
{desc}...

<b>📁 مدارک لازم</b>
پاسپورت معتبر | گواهی سلامت | مدارک تحصیلی
━━━━━━━━━━━━━━━━
📩 برای ارسال رزومه با <b>مشاورین هما</b> تماس بگیرید
🔗 <a href="{url}">مشاهده آگهی کامل</a>

#هما #فرصت_شغلی #{country} #{label.replace("‌","")}"""


def send(text: str) -> bool:
    r = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        },
        timeout=15,
    )
    return r.json().get("ok", False)


def main():
    print("🚀 هما — شروع جستجوی روزانه\n")
    seen_urls = set()
    sent = 0

    for country_code, what, country, category in SEARCHES:
        print(f"🔍 {country} — {what}...")
        try:
            jobs = fetch_jobs(country_code, what)
            print(f"   ✅ {len(jobs)} آگهی پیدا شد")
            for job in jobs:
                url = job.get("redirect_url", "")
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                msg = format_message(job, country, category)
                if send(msg):
                    print(f"   📤 {job.get('title','')}")
                    sent += 1
                    time.sleep(1.5)
        except Exception as e:
            print(f"   ❌ {e}")
        time.sleep(3)

    send(f"""📊 <b>گزارش روزانه هما</b>

✅ {sent} فرصت شغلی معتبر امروز
🌍 آذربایجان 🇦🇿 | رومانی 🇷🇴 | عمان 🇴🇲

#هما #گزارش_روزانه""")

    print(f"\n✅ پایان — {sent} شغل ارسال شد")


if __name__ == "__main__":
    main()
