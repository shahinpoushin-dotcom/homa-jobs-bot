"""
هما — ربات هوشمند جستجوی شغل
Gemini AI + Google Search + Telegram
"""

import os
import time
import requests
import google.generativeai as genai

# ─── تنظیمات از Environment Variables ─────────────────
GEMINI_API_KEY   = os.environ["GEMINI_API_KEY"]
TELEGRAM_TOKEN   = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
# ──────────────────────────────────────────────────────

genai.configure(api_key=GEMINI_API_KEY)

SEARCHES = [
    "jobs Azerbaijan Baku visa sponsorship welder electrician engineer driver cook 2025",
    "Romania jobs foreigners work permit welder construction driver electrician painter 2025",
    "Oman Muscat jobs visa sponsorship engineer driver welder hospitality cook technician 2025",
    "Azerbaijan Baku hiring foreign workers permit IT programmer teacher 2025",
    "Romania ejobs bestjobs foreign workers visa sponsorship 2025",
    "Oman bayt naukrigulf jobs iranians visa work permit 2025",
]

SYSTEM_PROMPT = """
تو دستیار هما هستی — شرکت مشاوره مهاجرت و کاریابی برای ایرانیان.

وظیفه‌ات: از نتایج جستجو، آگهی‌های شغلی واقعی را که:
۱. ویزا یا کار پرمیت می‌دهند
۲. برای ایرانیان امکان‌پذیر است
۳. اطلاعات کافی دارند
شناسایی کن.

برای هر شغل دقیقاً با این فرمت بنویس:

---JOB---
CATEGORY: [simple یا semi یا expert]
TITLE: [عنوان فارسی]
LOCATION: [شهر، کشور]
COUNTRY: [azerbaijan یا romania یا oman]
EMPLOYER: [نام شرکت]
CONTRACT: [نوع قرارداد]
START: [زمان شروع]
SALARY: [حقوق]
BENEFITS: [مزیت۱|مزیت۲|مزیت۳]
REQUIREMENTS: [شرط۱|شرط۲|شرط۳]
DOCUMENTS: [مدرک۱|مدرک۲|مدرک۳]
DEADLINE: [ساعت یا خالی]
NOTE: [نکته مهم یا خالی]
---END---

دسته‌بندی:
- simple = راننده، کارگر، نظافت، بارانداز
- semi = جوشکار، برق‌کار، آشپز، هتل‌داری، نقاش
- expert = مهندس، IT، معلم، پزشک

اگر هیچ آگهی معتبری نبود بنویس: NO_JOBS_FOUND
فقط آگهی‌های واقعی با ویزا اسپانسرشیپ صریح را بنویس.
"""


def search_jobs(query: str) -> str:
    """جستجو با Gemini + Google Search"""
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        tools="google_search_retrieval",
        system_instruction=SYSTEM_PROMPT,
    )
    response = model.generate_content(
        f"جستجو کن و آگهی‌های معتبر پیدا کن:\n{query}"
    )
    return response.text


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
        return "\n".join(f"▫️ {x.strip()}" for x in job.get(field,"").split("|") if x.strip())

    docs = " | ".join(x.strip() for x in job.get("DOCUMENTS","").split("|") if x.strip())
    deadline = f"\n⏰ <b>این فرصت فقط {job['DEADLINE']} ساعت معتبر است</b>" if job.get("DEADLINE") else ""
    note = f"\n\n📌 {job['NOTE']}" if job.get("NOTE") else ""
    country_tag = job.get("COUNTRY","").replace(" ","_")

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
{bullet_list("BENEFITS")}

<b>📋 شرایط</b>
{bullet_list("REQUIREMENTS")}

<b>📁 مدارک لازم</b>
{docs}
━━━━━━━━━━━━━━━━{deadline}
📩 برای ارسال رزومه با <b>مشاورین هما</b> تماس بگیرید{note}

#هما #فرصت_شغلی #{country_tag} #{label.replace("‌","")}"""


def send_telegram(text: str) -> bool:
    """ارسال به تلگرام"""
    r = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": TELEGRAM_CHAT_ID, "text": text,
              "parse_mode": "HTML", "disable_web_page_preview": True},
        timeout=10
    )
    return r.json().get("ok", False)


def main():
    print("🚀 هما — شروع جستجوی روزانه\n")
    all_jobs = []

    for query in SEARCHES:
        print(f"🔍 {query[:55]}...")
        try:
            result = search_jobs(query)
            jobs = parse_jobs(result)
            all_jobs.extend(jobs)
            print(f"   ✅ {len(jobs)} شغل پیدا شد")
        except Exception as e:
            print(f"   ❌ خطا: {e}")
        time.sleep(3)

    # حذف تکراری
    seen, unique = set(), []
    for j in all_jobs:
        key = j.get("TITLE","") + j.get("LOCATION","")
        if key not in seen:
            seen.add(key)
            unique.append(j)

    print(f"\n📋 مجموع: {len(unique)} شغل منحصربه‌فرد\n")

    sent = 0
    for job in unique:
        msg = format_message(job)
        if send_telegram(msg):
            print(f"📤 ارسال: {job.get('TITLE','')}")
            sent += 1
            time.sleep(1.5)

    # گزارش نهایی
    send_telegram(f"""📊 <b>گزارش روزانه هما</b>

✅ {sent} فرصت شغلی معتبر امروز
🌍 آذربایجان 🇦🇿 | رومانی 🇷🇴 | عمان 🇴🇲

#هما #گزارش_روزانه""")

    print(f"\n✅ پایان — {sent} شغل ارسال شد")


if __name__ == "__main__":
    main()
