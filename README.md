# 🎬 Movie Auto-Poster — Setup Guide

TMDB থেকে Hollywood মুভি এনে DeepSeek AI দিয়ে বাংলা ক্যাপশন লিখে
প্রতিদিন স্বয়ংক্রিয়ভাবে Facebook পেজে পোস্ট করে।

---

## 📁 ফাইল স্ট্রাকচার

```
movie-autoposter/
├── .github/
│   └── workflows/
│       └── movie-poster.yml   ← GitHub Actions (Auto-run)
├── scripts/
│   └── post_movie.py          ← মূল স্ক্রিপ্ট
├── posted_movies.json         ← auto-তৈরি হবে (duplicate এড়াতে)
└── README.md
```

---

## 🔑 Step 1 — API Keys সংগ্রহ করুন

### TMDB API Key
1. https://www.themoviedb.org/signup — account করুন
2. Settings → API → "Request an API Key" (Developer)
3. Free — সাথে সাথে পাবেন

### DeepSeek API Key
1. https://platform.deepseek.com — login করুন
2. API Keys → Create new key
3. খুব সস্তা — $0.14 per million tokens

### Facebook Page Token (Permanent)
1. https://developers.facebook.com → My Apps → Create App
2. Add Product: Facebook Login + Pages API
3. Graph API Explorer → আপনার Page সিলেক্ট করুন
4. Permission দিন: `pages_manage_posts`, `pages_read_engagement`
5. Short token পেয়ে **আপনার BrandPoster টুল দিয়েই** Permanent Token বানান!

---

## 🔐 Step 2 — GitHub Secrets সেট করুন

GitHub Repository → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Secret Name              | Value                        |
|--------------------------|------------------------------|
| `TMDB_API_KEY`           | আপনার TMDB API key           |
| `DEEPSEEK_API_KEY`       | sk-xxxxxxxxxxxxxxxx           |
| `FACEBOOK_PAGE_ID`       | আপনার Page এর ID             |
| `FACEBOOK_ACCESS_TOKEN`  | Permanent Page Access Token  |

---

## 📤 Step 3 — GitHub-এ Upload করুন

```bash
# নতুন repo তৈরি করুন (GitHub.com এ)
# তারপর এই ফাইলগুলো upload করুন:

git init
git add .
git commit -m "🚀 Initial setup"
git branch -M main
git remote add origin https://github.com/আপনার-username/movie-autoposter.git
git push -u origin main
```

---

## ⏰ পোস্টের সময়সূচি

| সময় (বাংলাদেশ) | UTC    |
|-----------------|--------|
| সকাল ৯:০০       | 03:00  |
| দুপুর ২:০০      | 08:00  |
| রাত ৮:০০        | 14:00  |

> সময় পরিবর্তন করতে `.github/workflows/movie-poster.yml` এ `cron` line এডিট করুন।

---

## ▶️ ম্যানুয়ালি চালানো

GitHub → **Actions** → **Movie Auto-Poster** → **Run workflow** → **Run**

---

## 🔄 কীভাবে কাজ করে

```
1. TMDB Popular Movies API → Top 60 মুভির লিস্ট
2. posted_movies.json চেক → আগে পোস্ট হয়নি এমন মুভি বেছে নেয়
3. TMDB Movie Details API → পূর্ণ তথ্য + Cast + Director
4. TMDB Image → পোস্টার ডাউনলোড (780px)
5. DeepSeek AI → আকর্ষণীয় বাংলা ক্যাপশন তৈরি
6. Facebook Graph API → ছবিসহ পেজে পোস্ট
7. posted_movies.json আপডেট → পরের বার duplicate হবে না
```

---

## ❓ সমস্যা হলে

**Actions → Run → লাল X দেখলে** → লগ দেখুন কোন Step-এ ব্যর্থ হয়েছে

| সমস্যা | সমাধান |
|--------|--------|
| `TMDB_API_KEY` error | TMDB key সঠিক কিনা দেখুন |
| `401 Unauthorized` (DeepSeek) | DeepSeek key ও balance চেক করুন |
| `(#200) OAuthException` (FB) | Token expire হয়েছে — নতুন Permanent Token নিন |
