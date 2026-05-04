#!/usr/bin/env python3
"""
🎬 Movie Auto-Poster
TMDB → DeepSeek AI (বাংলা ক্যাপশন) → Facebook Page
"""

import os
import sys
import json
import random
import requests
import tempfile
from datetime import datetime
from pathlib import Path

# ─── API Keys (GitHub Secrets থেকে আসবে) ───────────────────────────────────
TMDB_API_KEY        = os.environ["TMDB_API_KEY"]
DEEPSEEK_API_KEY    = os.environ["DEEPSEEK_API_KEY"]
FB_PAGE_ID          = os.environ["FACEBOOK_PAGE_ID"]
FB_ACCESS_TOKEN     = os.environ["FACEBOOK_ACCESS_TOKEN"]

TMDB_BASE    = "https://api.themoviedb.org/3"
TMDB_IMG     = "https://image.tmdb.org/t/p/w780"
DS_BASE      = "https://api.deepseek.com/v1/chat/completions"
FB_BASE      = "https://graph.facebook.com/v19.0"

# ─── পূর্বে পোস্ট করা মুভি track রাখার ফাইল ──────────────────────────────
POSTED_FILE = Path("posted_movies.json")


def load_posted() -> set:
    if POSTED_FILE.exists():
        try:
            return set(json.loads(POSTED_FILE.read_text()))
        except Exception:
            return set()
    return set()


def save_posted(posted: set):
    POSTED_FILE.write_text(json.dumps(list(posted)))


# ─── TMDB: Popular Hollywood মুভি আনো ────────────────────────────────────
def fetch_popular_movies(page: int = 1) -> list:
    url = f"{TMDB_BASE}/movie/popular"
    params = {
        "api_key": TMDB_API_KEY,
        "language": "en-US",
        "region": "US",
        "page": page,
    }
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    return r.json().get("results", [])


def get_movie_details(movie_id: int) -> dict:
    url = f"{TMDB_BASE}/movie/{movie_id}"
    params = {"api_key": TMDB_API_KEY, "language": "en-US", "append_to_response": "credits"}
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def pick_unposted_movie(posted: set) -> dict | None:
    """৩ পেজ ঘেঁটে একটি unposted মুভি বের করো"""
    for page in range(1, 4):
        movies = fetch_popular_movies(page)
        unposted = [m for m in movies if str(m["id"]) not in posted]
        if unposted:
            return random.choice(unposted)
    return None


def download_poster(poster_path: str) -> str | None:
    """TMDB থেকে পোস্টার ডাউনলোড → temp file path ফেরত দাও"""
    if not poster_path:
        return None
    url = f"{TMDB_IMG}{poster_path}"
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        suffix = ".jpg"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp.write(r.content)
        tmp.close()
        print(f"✅ পোস্টার ডাউনলোড হয়েছে: {tmp.name} ({len(r.content)//1024} KB)")
        return tmp.name
    except Exception as e:
        print(f"⚠️ পোস্টার ডাউনলোড ব্যর্থ: {e}")
        return None


# ─── DeepSeek: বাংলা ক্যাপশন তৈরি ────────────────────────────────────────
def generate_caption(movie: dict) -> str:
    title      = movie.get("title", "")
    overview   = movie.get("overview", "")[:600]
    release    = movie.get("release_date", "")[:4]
    rating     = round(movie.get("vote_average", 0), 1)
    genres     = ", ".join(g["name"] for g in movie.get("genres", [])[:3])
    cast       = ", ".join(
        c["name"] for c in movie.get("credits", {}).get("cast", [])[:4]
    )
    director   = next(
        (c["name"] for c in movie.get("credits", {}).get("crew", []) if c["job"] == "Director"),
        "অজানা"
    )

    prompt = f"""তুমি একটি বাংলা মুভি রিভিউ পেজের কন্টেন্ট রাইটার।
নিচের হলিউড মুভিটির জন্য একটি আকর্ষণীয় বাংলা Facebook পোস্ট লেখো।

মুভির তথ্য:
- নাম: {title} ({release})
- ঘরানা: {genres}
- IMDb রেটিং: {rating}/10
- পরিচালক: {director}
- অভিনেতা: {cast}
- কাহিনী সংক্ষেপ: {overview}

নির্দেশনা:
✅ পোস্ট শুরু করো একটি আকর্ষণীয় বাংলা হেডলাইন দিয়ে (ইমোজি সহ)
✅ ২-৩ প্যারায় মুভি সম্পর্কে উত্তেজনাপূর্ণ বাংলায় লেখো
✅ রেটিং, পরিচালক, কাস্ট উল্লেখ করো
✅ শেষে ৪-৫টি বাংলা ও ইংরেজি হ্যাশট্যাগ দাও
✅ পোস্ট ২০০-৩০০ শব্দের মধ্যে রাখো
❌ "অবশ্যই", "নিশ্চিতভাবে" এই ধরনের কথা দিয়ে শুরু করো না"""

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 600,
        "temperature": 0.85,
    }
    r = requests.post(DS_BASE, headers=headers, json=payload, timeout=30)
    r.raise_for_status()
    caption = r.json()["choices"][0]["message"]["content"].strip()
    print(f"✅ DeepSeek ক্যাপশন তৈরি হয়েছে ({len(caption)} অক্ষর)")
    return caption


# ─── Facebook: ছবিসহ পোস্ট করো ───────────────────────────────────────────
def post_to_facebook(caption: str, image_path: str | None) -> str:
    if image_path:
        url = f"{FB_BASE}/{FB_PAGE_ID}/photos"
        with open(image_path, "rb") as img:
            files = {"source": ("poster.jpg", img, "image/jpeg")}
            data  = {"message": caption, "access_token": FB_ACCESS_TOKEN}
            r = requests.post(url, files=files, data=data, timeout=60)
    else:
        # ছবি না থাকলে শুধু টেক্সট পোস্ট
        url  = f"{FB_BASE}/{FB_PAGE_ID}/feed"
        data = {"message": caption, "access_token": FB_ACCESS_TOKEN}
        r = requests.post(url, json=data, timeout=30)

    r.raise_for_status()
    post_id = r.json().get("id") or r.json().get("post_id", "unknown")
    print(f"✅ Facebook পোস্ট সফল! Post ID: {post_id}")
    return post_id


# ─── মূল ফাংশন ────────────────────────────────────────────────────────────
def main():
    print(f"\n{'='*50}")
    print(f"🎬 Movie Auto-Poster চালু — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")

    posted     = load_posted()
    print(f"📋 এখন পর্যন্ত {len(posted)} টি মুভি পোস্ট হয়েছে")

    movie_basic = pick_unposted_movie(posted)
    if not movie_basic:
        print("⚠️ নতুন মুভি পাওয়া যায়নি! Posted list রিসেট করা হচ্ছে...")
        posted = set()
        movie_basic = pick_unposted_movie(posted)

    if not movie_basic:
        print("❌ TMDB থেকে মুভি আনতে সমস্যা হয়েছে।")
        sys.exit(1)

    print(f"\n🎥 নির্বাচিত মুভি: {movie_basic['title']} (ID: {movie_basic['id']})")

    # পূর্ণ বিবরণ আনো
    movie = get_movie_details(movie_basic["id"])
    print(f"   রেটিং: {movie.get('vote_average', 'N/A')} | রিলিজ: {movie.get('release_date', 'N/A')[:4]}")

    # পোস্টার ডাউনলোড
    image_path = download_poster(movie.get("poster_path"))

    # বাংলা ক্যাপশন তৈরি
    print("\n✍️  DeepSeek দিয়ে বাংলা ক্যাপশন তৈরি হচ্ছে...")
    caption = generate_caption(movie)
    print(f"\n--- ক্যাপশন প্রিভিউ ---\n{caption[:200]}...\n")

    # Facebook পোস্ট
    print("📤 Facebook-এ পোস্ট করা হচ্ছে...")
    post_id = post_to_facebook(caption, image_path)

    # track করো
    posted.add(str(movie["id"]))
    save_posted(posted)

    # temp ফাইল মুছো
    if image_path:
        try:
            os.unlink(image_path)
        except Exception:
            pass

    print(f"\n🎉 সম্পন্ন! মুভি: {movie['title']} | Post ID: {post_id}")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()
