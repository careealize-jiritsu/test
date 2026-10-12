# 引き継ぎメモ：ジリツ SNS 投稿物の X 自動投稿

最終更新：2026-10-12

## 目的

Google ドライブの就活 Tips のカルーセル画像（1500×1500、1 トピック 8 枚）を、X に毎日自動投稿する。
TikTok は審査と自社ドメインでの画像配信が必要なので後回し。

## できていること

- リポジトリ `careealize-jiritsu/test` のブランチ `claude/festive-babbage-qgq9zt` にすべてプッシュ済み（main には未取り込み）
- `scripts/post_to_x.py`：投稿スクリプト。X API v2 を OAuth 1.0a で使う
  - 画像アップロードは `POST https://api.x.com/2/media/upload`、投稿は `POST https://api.x.com/2/tweets`
  - 1 トピックを 2 投稿のスレッドにする（`x_thread[i]` に画像 `slides[4i:4i+4]` を付ける）
  - `posts/posted.json` に記録して二重投稿を防ぐ。途中で失敗しても、投稿できた分は記録する
  - `--dry-run`（表示だけ）、`--check-all`（全トピック検証）、`--slug <名前>`（指定投稿）
- `.github/workflows/post-to-x.yml`：毎日 19:00 JST（cron `0 10 * * *`）に実行
  - 手動実行（Run workflow）は既定で dry_run。API キー（Secrets）が未設定なら投稿をスキップする
  - 実行後に `posts/posted.json` をコミットして戻す（`contents: write`）
- `posts/<トピック>/`：画像、`transcript.md`（文字起こし）、`post.json`（投稿文）
- `posts/queue.txt`：投稿順（完全な 6 トピック → 欠けのある 4 トピックはコメントアウト）

## 素材の場所

- 元のフォルダ（持ち主 wadaryou8421@gmail.com、pr@careealize.jp からは中身が一覧できない）：
  https://drive.google.com/drive/folders/1Pnt6X0gc42xO_diThpLQ7pOOepG9Ig-X
- 取り込みに使ったフォルダ（ZIP を展開したもの。1 つ目の ZIP だけ）：
  https://drive.google.com/drive/folders/1LdJZN2J7kxe8jR7BJpbwMLHGync3DtU_

## 残っている作業（この順で）

1. **X Developer Portal でキーを作る**（投稿する X アカウントでログイン）
   - アプリの User authentication settings：App permissions を **Read and write**、Type は Web App, Automated App or Bot
     （Callback URI / Website URL は使わないので会社サイトの URL でよい）
   - 権限を変えた**あとで** Keys and tokens から API Key / API Key Secret / Access Token / Access Token Secret を発行
     （Access Token の表示が「Read and Write」になっていること）
   - プランで「投稿」と「画像アップロード」が使えるか確認する
2. **GitHub Secrets に登録**（リポジトリ Settings → Secrets and variables → Actions）
   - `X_API_KEY` / `X_API_SECRET` / `X_ACCESS_TOKEN` / `X_ACCESS_TOKEN_SECRET`
   - キーはチャットや Git に書かない
3. **main に取り込む**：`claude/festive-babbage-qgq9zt` → main のプルリクエストを作ってマージ
   （スケジュール実行は main 上のワークフローでしか動かない）
4. **テスト**：Actions →「X 自動投稿」→ Run workflow
   - まず dry_run のまま実行 → ログに投稿内容が出るか確認
   - dry_run を外して実行 → 1 トピック（早期内定ロードマップ）が実際に投稿されるか確認
   - 失敗したらログのエラー（HTTP ステータスと本文）を見る。403 は権限かプラン、401 はキー間違いが多い
5. **欠けている画像を足す**：ドライブのダウンロードが ZIP 2 つに分かれていて、2 つ目が未アップロードと思われる
   - ES：4 枚目／企業研究：3・5 枚目／面接：3・6 枚目／夏インターン：2・3 枚目
   - 画像を `posts/<トピック>/NN.png` に足し、`post.json` の `slides` に入れ、`x_thread` を 4 枚ずつの区切りに合わせて書き直す
   - `python scripts/post_to_x.py --check-all` が通ったら `queue.txt` の `#` を外す

## 注意

- 志望動機の 8 枚目に「GDの前に見返して…」とある（GD 投稿からの写し間違いと思われる）。投稿文には入れていない
- 投稿文は画像に書いてある内容だけで作った。数字や事実を足さない
- 投稿時間を変えるときは cron を UTC で書く（日本時間 − 9 時間）
