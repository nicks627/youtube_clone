# YouTube Clone

Django で作成されたYouTubeクローンアプリケーション

## 機能一覧

### 🎥 動画機能
- ✅ 動画アップロード（MP4形式、最大128GB）
- ✅ 動画再生（HTML5ビデオプレーヤー）
- ✅ 動画の長さ自動計算（FFprobe使用時）
- ✅ サムネイル表示
- ✅ 動画の説明・タイトル
- ✅ ジャンル別動画分類（音楽、ゲーム、ニュース、教育など）
- ✅ 動画の視聴回数カウント
- ✅ 有料コンテンツ対応

### 👤 ユーザー機能
- ✅ ユーザー登録・ログイン
- ✅ ユーザープロフィール編集
- ✅ チャンネル作成・編集
- ✅ チャンネルアバター・バナー
- ✅ チャンネル紹介文・外部リンク
- ✅ アカウント設定（再生速度設定、アカウント削除）

### 📺 チャンネル・登録機能
- ✅ チャンネル登録/登録解除
- ✅ 登録チャンネル一覧
- ✅ チャンネルフォルダー管理
- ✅ チャンネル詳細ページ
- ✅ 登録者数表示
- ✅ チャンネル統計情報

### 🔍 検索・発見機能
- ✅ 動画検索（タイトル、説明、投稿者）
- ✅ ジャンル別動画表示
- ✅ 急上昇動画
- ✅ 人気動画
- ✅ 探索ページ

### 💬 インタラクション機能
- ✅ 動画へのコメント投稿
- ✅ コメント削除
- ✅ 動画の高評価/低評価
- ✅ 動画の共有（SNS、リンクコピー）
- ✅ 後で見るリスト
- ✅ 高評価した動画一覧
- ✅ 視聴履歴

### 💰 収益化機能
- ✅ Link決済統合
- ✅ 投げ銭機能
- ✅ 有料コンテンツ販売
- ✅ 決済設定ページ
- ✅ 購入履歴
- ✅ 収益管理

### ⚡ パフォーマンス最適化
- ✅ データベースクエリ最適化（select_related、prefetch_related）
- ✅ キャッシュシステム（trending、popular videos）
- ✅ ページネーション（12件ずつ表示）
- ✅ 遅延読み込み（Lazy Loading）
- ✅ データベースインデックス
- ✅ 静的ファイル最適化

### 📱 UI/UX
- ✅ レスポンシブデザイン
- ✅ ダークテーマ
- ✅ YouTube風デザイン
- ✅ サイドバーナビゲーション
- ✅ モーダルダイアログ
- ✅ 通知システム
- ✅ アニメーション効果

## 技術スタック

- **バックエンド**: Django 5.0.2
- **データベース**: SQLite（開発環境）
- **フロントエンド**: HTML5, CSS3, JavaScript, Bootstrap 5
- **動画処理**: FFprobe（動画情報取得）
- **決済**: Link決済API
- **キャッシュ**: Django Cache Framework
- **静的ファイル**: Django Static Files

## セットアップ

1. 依存関係のインストール
```bash
pip install django pillow
```

2. データベースマイグレーション
```bash
python manage.py makemigrations
python manage.py migrate
```

3. スーパーユーザー作成
```bash
python manage.py createsuperuser
```

4. 開発サーバー起動
```bash
python manage.py runserver
```

## 設定

### 動画処理機能を有効にする場合
FFprobeをインストール:
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Windows
# https://ffmpeg.org/download.html からダウンロード
```

### Link決済設定
1. 管理画面または設定ページでAPIキーを設定
2. `settings.py`で`LINK_API_BASE_URL`を設定（本番環境）

### 本番環境設定
- `DEBUG = False`
- `ALLOWED_HOSTS`の設定
- PostgreSQLなどの本番データベース設定
- Redis/Memcachedなどのキャッシュバックエンド設定
- 静的ファイル配信の設定

## ディレクトリ構造

```
youtube_clone/
├── videos/               # メインアプリケーション
│   ├── models.py        # データベースモデル
│   ├── views.py         # ビューロジック
│   ├── urls.py          # URLルーティング
│   ├── forms.py         # フォーム定義
│   ├── utils.py         # ユーティリティ関数
│   ├── payment_service.py # 決済サービス
│   └── templates/       # HTMLテンプレート
├── static/              # 静的ファイル
│   └── js/
│       └── lazy-loading.js
├── media/               # アップロードファイル
│   ├── videos/
│   ├── thumbnails/
│   ├── avatars/
│   └── banners/
└── youtube_clone/       # プロジェクト設定
    └── settings.py
```

## API エンドポイント

- `POST /api/toggle-subscription/` - チャンネル登録切り替え
- `POST /api/comments/add/` - コメント追加
- `POST /api/comments/delete/` - コメント削除
- `POST /api/videos/like/` - 動画の評価
- `POST /api/watch-later/toggle/` - 後で見る切り替え
- `POST /api/payments/donation/` - 投げ銭処理
- `POST /api/payments/purchase/` - コンテンツ購入

## ライセンス

このプロジェクトは教育目的で作成されています。