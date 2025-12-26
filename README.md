# lightsail-test

Lightsailでdocker composeをするテスト用のサンプルアプリケーション

## 構成

- **Nginx**: リバースプロキシ (ポート80)
- **フロントエンド**: React 18 (内部ポート3000)
- **バックエンド**: Django 4.2 + Django REST Framework (内部ポート8000)
- **データベース**: PostgreSQL 15 (ポート5432)

## 機能

シンプルなTodoアプリケーション:
- Todoの追加
- Todoの完了/未完了の切り替え
- Todoの削除
- リアルタイムでのデータ同期

## セットアップと起動

### 必要な環境
- Docker
- Docker Compose

### 起動方法

```bash
docker-compose up -d
```

### アクセス方法

**ポート80でアクセス（推奨）**
- アプリケーション: http://localhost/
- バックエンドAPI: http://localhost/api/todos/
- Django Admin: http://localhost/admin/

**直接アクセス（開発用）**
- データベース: localhost:5432

Nginxがリバースプロキシとして動作し、フロントエンド（/）とバックエンド（/api/、/admin/）を1つのポート（80）で提供します。

### 停止方法

```bash
docker-compose down
```

### データベースを含めて完全に削除

```bash
docker-compose down -v
```

## API エンドポイント

| メソッド | エンドポイント | 説明 |
|---------|--------------|------|
| GET | /api/todos/ | Todo一覧を取得 |
| POST | /api/todos/ | 新しいTodoを作成 |
| GET | /api/todos/{id}/ | 特定のTodoを取得 |
| PATCH | /api/todos/{id}/ | Todoを更新 |
| DELETE | /api/todos/{id}/ | Todoを削除 |

## ディレクトリ構造

```
.
├── backend/              # Djangoバックエンド
│   ├── config/          # Django設定
│   ├── todos/           # Todoアプリ
│   ├── Dockerfile
│   ├── entrypoint.sh    # 起動スクリプト
│   └── requirements.txt
├── frontend/            # Reactフロントエンド
│   ├── public/
│   ├── src/
│   └── package.json
├── nginx/               # Nginxリバースプロキシ
│   └── nginx.conf       # Nginx設定
└── docker-compose.yml
```

## アーキテクチャ

```
ブラウザ (ポート80)
    ↓
Nginx (リバースプロキシ)
    ├─ / → React (ポート3000)
    └─ /api/, /admin/ → Django (ポート8000)
              ↓
        PostgreSQL (ポート5432)
```
