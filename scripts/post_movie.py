#!/usr/bin/env python3
"""
🎬 Movie Auto-Poster
TMDB → NVIDIA DeepSeek AI (বাংলা ক্যাপশন) → Facebook Page
"""

import os
import sys
import json
import random
import requests
import tempfile
from datetime import datetime
from pathlib import Path
from openai import OpenAI

# ─── API Keys (GitHub Secrets থেকে আসবে) ───────────────────────────────────
TMDB_API_KEY        = os.environ["TMDB_API_KEY"]
NVIDIA_API_KEY      = os.environ["NVIDIA_API_KEY"]
FB_PAGE_ID          = os.environ["FACEBOOK_PAGE_ID"]
FB_ACCESS_TOKEN     = os.environ["FACEBOOK_ACCESS_TOKEN"]

TMDB_BASE    = "https://api.themoviedb.org/3"
TMDB_IMG     = "https://image.tmdb.org/t/p/w780"
FB_BASE      = "https://graph.facebook.com/v19.0"

# ─── NVIDIA OpenAI-compatible client ────────────────────────────────────────
nvidia_client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=NVIDIA_API_KEY,
    max_retries=0,   # retry আমরা নিজে handle করবো
)

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


# ─── NVIDIA DeepSeek V4 Flash: বাংলা ক্যাপশন তৈরি ──────────────────────
def generate_caption(movie: dict) -> str:
    title      = movie.get("title", "")
    overview   = movie.get("overview", "")[:800]
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

    # Website line — Python থেকে inject, AI পরিবর্তন করতে পারবে না
    WEBSITE_LINE = "ফ্রিতে মুভি ও সিরিজ দেখতে ভিজিট করুন অথবা গুগোলে সার্চ করুন - 𝐌𝐲𝐜𝐢𝐧𝐞𝐛𝐝.𝐜𝐨𝐦"

    # First hashtag always: MovieTitle (Year)
    title_tag = title.replace(" ", "")

    prompt = f"""তুমি একটি বাংলা মুভি রিভিউ পেজের অভিজ্ঞ কন্টেন্ট রাইটার।
নিচের হলিউড মুভিটির জন্য একটি সম্পূর্ণ বাংলা Facebook পোস্ট লেখো।
পোস্টটি পড়লে মানুষ মুভিটা দেখতে আগ্রহী হয়ে উঠবে।

মুভির তথ্য:
- নাম: {title} ({release})
- ঘরানা: {genres}
- রেটিং: {rating}/10
- পরিচালক: {director}
- অভিনেতা: {cast}
- কাহিনী: {overview}

পোস্টের exact format (এই ক্রমে, কিছু বাদ দেবে না):

[LINE 1] 🎥 {title} ({release})
[LINE 2] Genre: {genres}
[LINE 3] (খালি লাইন)
[LINE 4-শেষ] মূল বাংলা রিভিউ — নিচের নির্দেশনা মেনে লেখো:

রিভিউ লেখার নির্দেশনা:
- প্রথম লাইনে একটি চমকপ্রদ hook দাও (ইমোজি সহ) যা মানুষকে থামিয়ে দেবে
- কাহিনীর মূল conflict/mystery তুলে ধরো — spoiler দেবে না, কিন্তু curiosity জাগাও
- অভিনেতাদের performance নিয়ে genuine উত্তেজনাপূর্ণ মন্তব্য করো
- পরিচালনা ও ভিজ্যুয়াল নিয়ে বলো (যদি notable হয়)
- রেটিং উল্লেখ করো
- শেষে এমন একটা লাইন দাও যা পড়লে মানুষ এখনই দেখতে চাইবে
- লেখা হবে সহজ, প্রাণবন্ত, conversational বাংলায় — formal না
- ৩০০-৪০০ শব্দের মধ্যে রাখো — সম্পূর্ণ লিখবে, মাঝপথে থামবে না

রিভিউ শেষ হলে একটি খালি লাইন দিয়ে লিখবে:
{WEBSITE_LINE}

তারপর খালি লাইন দিয়ে হ্যাশট্যাগ (মাত্র ৩-৪টি):
#{title_tag} #{title_tag}{release} #Movies{release}
(genre অনুযায়ী আরও ১টি হ্যাশট্যাগ যোগ করতে পারো)

কঠোর নিষেধ:
❌ "অবশ্যই" বা "নিশ্চিতভাবে" দিয়ে শুরু করবে না
❌ website লাইনটি এক অক্ষরও পরিবর্তন করবে না
❌ হ্যাশট্যাগ ৪টির বেশি দেবে না
❌ রিভিউ অসম্পূর্ণ রাখবে না — শেষ পর্যন্ত লিখবে"""

    # ─── Helper: একটি model দিয়ে caption তৈরির চেষ্টা ───────────────────
    def _try_model(model_name: str, timeout_sec: int) -> str:
        completion = nvidia_client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.85,
            top_p=0.95,
            max_tokens=2048,
            stream=True,
            timeout=timeout_sec,
        )
        parts = []
        for chunk in completion:
            if not getattr(chunk, "choices", None):
                continue
            delta = chunk.choices[0].delta
            # reasoning/thinking content — শুধু log করো, caption-এ নেবো না
            reasoning = (
                getattr(delta, "reasoning", None)
                or getattr(delta, "reasoning_content", None)
            )
            if reasoning:
                print(reasoning, end="", flush=True)
            if getattr(delta, "content", None):
                parts.append(delta.content)
        result = "".join(parts).strip()
        if not result:
            raise ValueError(f"{model_name} থেকে খালি response এসেছে!")
        return result

    # ─── Template fallback (AI ছাড়া, সর্বশেষ উপায়) ─────────────────────
    def _template_caption() -> str:
        genre_tags = "".join(f"#{g.replace(' ', '')}" for g in genres.split(", ")[:2])
        return (
            f"🎥 {title} ({release})\n"
            f"Genre: {genres}\n\n"
            f"⭐ রেটিং {rating}/10 পাওয়া এই মুভিটি এই বছরের অন্যতম আলোচিত একটি ছবি।\n\n"
            f"🎬 পরিচালক {director}-এর হাত ধরে {cast} অভিনীত এই মুভিতে রয়েছে "
            f"এক অসাধারণ গল্প যা আপনাকে শেষ মুহূর্ত পর্যন্ত স্ক্রিনে আটকে রাখবে।\n\n"
            f"মিস করলে কিন্তু পস্তাবেন! 🔥\n\n"
            f"{WEBSITE_LINE}\n\n"
            f"#{title_tag} #{title_tag}{release} #Movies{release} {genre_tags}"
        )

    # ══════════════════════════════════════════════════════════════════════
    # STEP 1 — Primary: NVIDIA DeepSeek V4 Flash
    # ══════════════════════════════════════════════════════════════════════
    print("⏳ [1/3] NVIDIA DeepSeek V4 Flash API-তে request পাঠানো হচ্ছে...")
    try:
        caption = _try_model("deepseek-ai/deepseek-v4-flash", timeout_sec=90)
        print(f"\n✅ DeepSeek V4 Flash ক্যাপশন তৈরি হয়েছে ({len(caption)} অক্ষর)")
        return caption
    except Exception as e:
        print(f"\n⚠️ DeepSeek V4 Flash ব্যর্থ: {e}")

    # ══════════════════════════════════════════════════════════════════════
    # STEP 2 — Fallback: NVIDIA Llama 3.3 70B (একই prompt)
    # ══════════════════════════════════════════════════════════════════════
    print("⏳ [2/3] Fallback — NVIDIA Llama 3.3 70B দিয়ে চেষ্টা করা হচ্ছে...")
    try:
        caption = _try_model("meta/llama-3.3-70b-instruct", timeout_sec=60)
        print(f"\n✅ Llama 3.3 70B ক্যাপশন তৈরি হয়েছে ({len(caption)} অক্ষর)")
        return caption
    except Exception as e:
        print(f"\n⚠️ Llama 3.3 70B ব্যর্থ: {e}")

    # ══════════════════════════════════════════════════════════════════════
    # STEP 3 — Last resort: Template caption
    # ══════════════════════════════════════════════════════════════════════
    print("⏳ [3/3] সব AI ব্যর্থ — Template caption ব্যবহার করা হচ্ছে...")
    caption = _template_caption()
    print(f"✅ Template ক্যাপশন তৈরি হয়েছে ({len(caption)} অক্ষর)")
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
    print("\n✍️  NVIDIA DeepSeek V4 Flash দিয়ে বাংলা ক্যাপশন তৈরি হচ্ছে...")
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
