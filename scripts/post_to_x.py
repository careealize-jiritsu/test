"""SNS 投稿物を X（旧 Twitter）にスレッドで自動投稿する。

posts/queue.txt の順に、まだ投稿していないトピックを 1 つ選び、
posts/<slug>/post.json の x_thread[i] に画像 slides[4i:4i+4] を付けてスレッド投稿する。
投稿結果は posts/posted.json に記録し、同じトピックを二重投稿しない。

使い方:
  python scripts/post_to_x.py --dry-run          # 次に投稿する内容を表示して検証だけ
  python scripts/post_to_x.py                    # 実際に投稿（環境変数に X の API キーが必要）
  python scripts/post_to_x.py --slug self-analysis  # トピックを指定して投稿

必要な環境変数（X Developer Portal の「Keys and tokens」）:
  X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET
"""

import argparse
import json
import math
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTS_DIR = ROOT / "posts"
QUEUE_FILE = POSTS_DIR / "queue.txt"
POSTED_FILE = POSTS_DIR / "posted.json"

API_BASE = "https://api.x.com/2"
MAX_WEIGHTED_LENGTH = 280
IMAGES_PER_POST = 4
JST = timezone(timedelta(hours=9))

# twitter-text v3 で 1 文字として数える範囲。それ以外（日本語・絵文字など）は 2 文字。
SINGLE_WEIGHT_RANGES = [(0, 4351), (8192, 8205), (8208, 8223), (8242, 8247)]


def weighted_length(text):
    total = 0
    for ch in text:
        cp = ord(ch)
        total += 1 if any(lo <= cp <= hi for lo, hi in SINGLE_WEIGHT_RANGES) else 2
    return total


def load_json(path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def load_queue():
    lines = QUEUE_FILE.read_text(encoding="utf-8").splitlines()
    return [ln.strip() for ln in lines if ln.strip() and not ln.strip().startswith("#")]


def load_post(slug):
    post_dir = POSTS_DIR / slug
    post = load_json(post_dir / "post.json", None)
    if post is None:
        raise SystemExit(f"posts/{slug}/post.json がありません")

    slides = post["slides"]
    thread = post["x_thread"]
    errors = []
    expected = math.ceil(len(slides) / IMAGES_PER_POST)
    if len(thread) != expected:
        errors.append(f"x_thread は {expected} 件必要（画像 {len(slides)} 枚）ですが {len(thread)} 件です")
    for i, text in enumerate(thread, 1):
        n = weighted_length(text)
        if n > MAX_WEIGHTED_LENGTH:
            errors.append(f"{i} 件目が長すぎます（{n}/{MAX_WEIGHTED_LENGTH}）")
    for name in slides:
        if not (post_dir / name).is_file():
            errors.append(f"画像がありません: posts/{slug}/{name}")
    if errors:
        raise SystemExit(f"posts/{slug} の検証エラー:\n  " + "\n  ".join(errors))

    chunks = [
        [post_dir / name for name in slides[i * IMAGES_PER_POST:(i + 1) * IMAGES_PER_POST]]
        for i in range(len(thread))
    ]
    return post, list(zip(thread, chunks))


def oauth_session():
    from requests_oauthlib import OAuth1Session

    keys = ["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET"]
    missing = [k for k in keys if not os.environ.get(k)]
    if missing:
        raise SystemExit("X の API キーが設定されていません: " + ", ".join(missing))
    return OAuth1Session(*(os.environ[k] for k in keys))


def upload_image(session, path):
    with path.open("rb") as f:
        resp = session.post(
            f"{API_BASE}/media/upload",
            files={"media": (path.name, f, "image/png")},
            data={"media_category": "tweet_image", "media_type": "image/png"},
        )
    if not resp.ok:
        raise SystemExit(f"画像アップロード失敗 {path.name}: {resp.status_code} {resp.text}")
    return resp.json()["data"]["id"]


def create_post(session, text, media_ids, reply_to=None):
    body = {"text": text}
    if media_ids:
        body["media"] = {"media_ids": media_ids}
    if reply_to:
        body["reply"] = {"in_reply_to_tweet_id": reply_to}
    resp = session.post(f"{API_BASE}/tweets", json=body)
    if not resp.ok:
        raise SystemExit(f"投稿失敗: {resp.status_code} {resp.text}")
    return resp.json()["data"]["id"]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="投稿せずに内容を表示する")
    parser.add_argument("--slug", help="投稿するトピック（省略時はキューの次のもの）")
    parser.add_argument("--check-all", action="store_true", help="キューの全トピックを検証する")
    args = parser.parse_args()

    queue = load_queue()
    posted = load_json(POSTED_FILE, {})

    if args.check_all:
        for slug in queue:
            post, items = load_post(slug)
            lengths = ", ".join(str(weighted_length(t)) for t, _ in items)
            print(f"OK {slug}: {post['title']}（{len(items)} 件 / 文字数 {lengths}）")
        return

    slug = args.slug or next((s for s in queue if s not in posted), None)
    if slug is None:
        print("キューのトピックはすべて投稿済みです。posts/queue.txt に追加してください。")
        return
    if slug in posted and not args.dry_run:
        raise SystemExit(f"{slug} は投稿済みです（{posted[slug]['posted_at']}）")

    post, items = load_post(slug)
    print(f"[{slug}] {post['title']}")
    for i, (text, images) in enumerate(items, 1):
        print(f"--- {i}/{len(items)}（{weighted_length(text)}/{MAX_WEIGHTED_LENGTH}）画像: {', '.join(p.name for p in images)}")
        print(text)
    if args.dry_run:
        return

    session = oauth_session()
    post_ids = []
    try:
        for text, images in items:
            media_ids = [upload_image(session, p) for p in images]
            post_ids.append(create_post(session, text, media_ids, reply_to=post_ids[-1] if post_ids else None))
            print(f"投稿しました: https://x.com/i/web/status/{post_ids[-1]}")
    finally:
        # 途中で失敗しても、投稿できた分は記録して二重投稿を防ぐ
        if post_ids:
            posted[slug] = {
                "posted_at": datetime.now(JST).isoformat(timespec="seconds"),
                "post_ids": post_ids,
                "complete": len(post_ids) == len(items),
            }
            POSTED_FILE.write_text(json.dumps(posted, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
