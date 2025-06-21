# YouTube Clone - Render デプロイメントガイド

このプロジェクトをRenderにデプロイするための手順とファイルの説明です。

## デプロイメントファイルの説明

### 必須ファイル
- `requirements.txt` - Pythonパッケージの依存関係
- `build.sh` - ビルドスクリプト（実行可能にする必要があります）
- `render.yaml` - Render設定ファイル
- `youtube_clone/production_settings.py` - 本番環境用Django設定
- `runtime.txt` - Pythonバージョン指定
- `Procfile` - プロセス定義（オプション、render.yamlがある場合）

### 設定ファイル
- `.env.example` - 環境変数のサンプル

## デプロイ手順

### 1. Renderアカウント準備
- [Render](https://render.com/)でアカウントを作成
- GitHubリポジトリとの連携を設定

### 2. リポジトリのプッシュ
```bash
git init
git add .
git commit -m "Initial commit for YouTube Clone"
git remote add origin YOUR_GITHUB_REPO_URL
git push -u origin main
```

### 3. Renderでの設定
1. Renderダッシュボードで「New +」をクリック
2. 「Blueprint」を選択
3. GitHub リポジトリを選択
4. `render.yaml`ファイルが自動検出される

### 4. 環境変数の設定
Render上で以下の環境変数が自動設定されます：
- `SECRET_KEY` - 自動生成
- `DATABASE_URL` - PostgreSQLデータベースURL（自動設定）
- `DEBUG` - `False`に設定済み
- `DJANGO_SETTINGS_MODULE` - `youtube_clone.production_settings`

### 5. デプロイメントの確認
- ビルドログを確認
- データベースマイグレーションの実行確認
- 静的ファイルの収集確認

## 本番環境の特徴

### データベース
- SQLiteから PostgreSQLに変更
- 無料のPostgreSQLインスタンスを使用

### 静的ファイル
- WhiteNoiseを使用して静的ファイルを配信
- `collectstatic`でファイルを収集

### セキュリティ
- `DEBUG=False`で実行
- HTTPS設定に対応
- セキュアなクッキー設定

### ログ
- コンソール出力でログを管理
- Renderのログビューアで確認可能

## トラブルシューティング

### よくある問題
1. **ビルドエラー**: `requirements.txt`の依存関係を確認
2. **データベースエラー**: マイグレーションファイルの確認
3. **静的ファイルエラー**: `STATIC_ROOT`設定の確認
4. **メディアファイル**: Renderでは永続ストレージが制限されるため、画像・動画ファイルには外部ストレージ（AWS S3等）を推奨

### デバッグ
- Renderのログで詳細なエラー情報を確認
- 本番環境で`DEBUG=True`に一時的に設定してデバッグ（セキュリティ上、デバッグ後は必ず`False`に戻す）

## 注意事項

### ファイルアップロード
- Renderの無料プランでは永続ストレージが制限されます
- 動画ファイルや画像ファイルのアップロードには外部ストレージサービスの使用を推奨

### データベース
- PostgreSQL無料プランには容量制限があります
- 大量のデータを扱う場合は有料プランへのアップグレードを検討

### パフォーマンス
- 無料プランでは一定時間アクセスがないとスリープモードになります
- 初回アクセス時に数秒の起動時間が必要な場合があります