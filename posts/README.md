# SNS 投稿物（X 自動投稿）

Google ドライブ「ジリツ_SNS投稿物」のカルーセル画像を、X にスレッドで自動投稿する仕組み。

## しくみ

- `posts/<トピック>/` … 画像（`01.png`〜）、文字起こし（`transcript.md`）、投稿文（`post.json`）
- `posts/queue.txt` … 投稿する順番。上から 1 日 1 トピックずつ投稿する
- `posts/posted.json` … 投稿済みの記録（自動で更新される。手で消すと再投稿される）
- `.github/workflows/post-to-x.yml` … 毎日 19:00（日本時間）に次のトピックを投稿
- `scripts/post_to_x.py` … 投稿スクリプト

1 トピック（画像 8 枚）は、X の 1 投稿に画像が 4 枚までのため、2 投稿のスレッドになる。
`post.json` の `x_thread[0]` に画像 1〜4 枚目、`x_thread[1]` に 5〜8 枚目が付く。

## 最初の設定（1 回だけ）

1. **X Developer Portal で API キーを作る**（https://developer.x.com/）
   - 投稿するアカウントでログインし、プロジェクトとアプリを作る
   - アプリの「User authentication settings」で App permissions を **Read and write** にする
   - 「Keys and tokens」で次の 4 つを発行する（権限を変えた後に Access Token を発行し直すこと）
     - API Key / API Key Secret
     - Access Token / Access Token Secret
   - 投稿 API は有料プランが必要な場合がある。料金は Developer Portal で確認する
2. **GitHub に登録する**
   - リポジトリの Settings → Secrets and variables → Actions → New repository secret
   - `X_API_KEY` / `X_API_SECRET` / `X_ACCESS_TOKEN` / `X_ACCESS_TOKEN_SECRET`
3. **動作確認**
   - Actions → 「X 自動投稿」→ Run workflow（dry_run にチェック）で、投稿内容がログに出ることを確認
   - dry_run のチェックを外して実行すると、実際に 1 トピック投稿される

キーが未設定の間は、毎日の自動実行は投稿をスキップする（エラーにはならない）。

## よくある変更

- **投稿時間を変える**：`post-to-x.yml` の `cron`（UTC で書く。日本時間 − 9 時間）
  - 例：毎日 12:00 → `0 3 * * *`、月水金 19:00 → `0 10 * * 1,3,5`
- **順番を変える・止める**：`queue.txt` の行を並べ替える／`#` を付けてコメントアウトする
- **文面を直す**：`post.json` の `x_thread` を編集する（1 投稿 全角 140 文字まで）
- **新しいトピックを足す**：`posts/<名前>/` に画像と `post.json` を置き、`queue.txt` に追記する
- **確認だけしたい**：`python scripts/post_to_x.py --check-all`（全トピックの文字数・画像を検証）

## TikTok について

TikTok の写真投稿 API（Content Posting API）は使えるが、次が必要なので後回しにしている。

- TikTok for Developers でアプリを作り、審査を通す（通るまでは「自分のみ」公開でしか投稿できない）
- 画像を自社ドメインのサーバーに置き、そのドメインを TikTok で所有確認する（Google ドライブの URL は不可）
