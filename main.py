"""
هما — ربات هوشمند جستجوی شغل
Claude AI + Web Search + Telegram
"""
 
import os
import time
import requests
 
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
TELEGRAM_TOKEN    = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID  = os.environ["TELEGRAM_CHAT_ID"]
 
QUERIES = [
    ("Romania Bucharest welder electrician cook driver jobs foreigners 2025", "romania"),
    ("Azerbaijan Baku engineer IT driver cook jobs foreigners 2025", "azerbaijan"),
    ("Oman Muscat engineer driver cook technician jobs expats 2025", "oman"),
]
 
SYSTEM = """You are a job search assistant. Search the web and find REAL current job openings.
 
For each real job found, output it in EXACTLY this format with no deviation:
 
---JOB---
CATEGORY: semi
TITLE: [job title translated to Persian]
LOCATION: [city in Persian], [country in Persian]
COUNTRY: [azerbaijan or romania or oman]
EMPLOYER: [company name in English]
CONTRACT: تمام‌وقت
START: فوری
SALARY: [salary with currency, or توافقی]
BENEFITS: بیمه درمان|اسکان یا کمک اجاره|وعده غذا
REQUIREMENTS: [requirement 1 in Persian]|[requirement 2]|[requirement 3]
DOCUMENTS: پاسپورت معتبر|گواهی سلامت|مدارک تحصیلی
DEADLINE:
NOTE: امکان اخذ ویزای کاری
---END---
 
Set CATEGORY:
- simple: driver, laborer, cleaner, security, warehouse
- semi: welder, cook, electrician, painter, hotel staff, mechanic
- expert: engineer, IT, doctor, teacher, manager, accountant
 
IMPORTANT: Output ONLY the job blocks. No other text. Find at least 3-5 real jobs."""
 
 
def find_jobs(query: str, country: str) -> list:
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
        "anthropic-beta": "web-search-2025-03-05",
    }
    payload = {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 3000,
        "tools": [{"type": "web_search_20250305", "name": "web_search"}],
        "messages": [{
            "role": "user",
            "content": f"""Search the web for real current job openings: {query}
 
After searching, output ONLY job listings using EXACTLY this format for each job:
 
---JOB---
CATEGORY: [simple or semi or expert]
TITLE: [job title in Persian]
LOCATION: [city in Persian], [country in Persian]
COUNTRY: {country}
EMPLOYER: [company name]
CONTRACT: تمام‌وقت
START: فوری
SALARY: [salary or توافقی]
BENEFITS: بیمه درمان|اسکان|وعده غذا
REQUIREMENTS: [req1 in Persian]|[req2]|[req3]
DOCUMENTS: پاسپورت معتبر|گواهی سلامت|مدارک تحصیلی
DEADLINE:
NOTE: امکان اخذ ویزای کاری
---END---
 
Categories: simple=driver/laborer/cleaner, semi=welder/cook/electrician/painter, expert=engineer/IT/doctor/teacher
 
Output MINIMUM 3 jobs. Use ONLY the ---JOB--- format above. No other text."""
        }]
    }
 
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers=headers,
        json=payload,
        timeout=90,
    )
    data = r.json()
    text = "".join(b.get("text","") for b in data.get("content",[]) if b.get("type")=="text")
    print(f"   📝 پاسخ: {text[:300]}")
    return parse(text)
 
 
def parse(text: str) -> list:
    jobs = []
    if not text:
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
 
 
def telegram_msg(job: dict) -> str:
    cats = {"simple":("🔵","ساده"),"semi":("🟡","نیمه‌تخصصی"),"expert":("🟢","تخصصی")}
    emoji, label = cats.get(job.get("CATEGORY","semi"), ("⚪","سایر"))
    flags = {"azerbaijan":"🇦🇿","romania":"🇷🇴","oman":"🇴🇲"}
    flag = flags.get(job.get("COUNTRY","").lower(),"🌍")
 
    def b(f):
        return "\n".join(f"▫️ {x.strip()}" for x in job.get(f,"").split("|") if x.strip())
 
    docs = " | ".join(x.strip() for x in job.get("DOCUMENTS","").split("|") if x.strip())
    ct = job.get("COUNTRY","").replace(" ","_")
 
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
{b("BENEFITS")}
 
<b>📋 شرایط</b>
{b("REQUIREMENTS")}
 
<b>📁 مدارک لازم</b>
{docs}
━━━━━━━━━━━━━━━━
📩 برای ارسال رزومه با <b>مشاورین هما</b> تماس بگیرید
 
#هما #فرصت_شغلی #{ct} #{label.replace("‌","")}"""
 
 
def send(text: str) -> bool:
    r = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id":TELEGRAM_CHAT_ID,"text":text,"parse_mode":"HTML","disable_web_page_preview":True},
        timeout=10,
    )
    return r.json().get("ok", False)
 
 
def main():
    print("🚀 هما — شروع جستجوی روزانه\n")
    all_jobs = []
 
    for query, country in QUERIES:
        print(f"🔍 {country}: {query[:50]}...")
        try:
            jobs = find_jobs(query, country)
            all_jobs.extend(jobs)
            print(f"   ✅ {len(jobs)} شغل")
        except Exception as e:
            print(f"   ❌ {e}")
        time.sleep(5)
 
    seen, unique = set(), []
    for j in all_jobs:
        k = j.get("TITLE","") + j.get("EMPLOYER","")
        if k not in seen:
            seen.add(k)
            unique.append(j)
 
    print(f"\n📋 مجموع: {len(unique)} شغل\n")
 
    sent = 0
    for job in unique:
        if send(telegram_msg(job)):
            print(f"📤 {job.get('TITLE','')}")
            sent += 1
            time.sleep(1.5)
 
    send(f"""📊 <b>گزارش روزانه هما</b>
 
✅ {sent} فرصت شغلی معتبر امروز
🌍 آذربایجان 🇦🇿 | رومانی 🇷🇴 | عمان 🇴🇲
 
#هما #گزارش_روزانه""")
 
    print(f"\n✅ پایان — {sent} شغل ارسال شد")
 
 
if __name__ == "__main__":
    main()
