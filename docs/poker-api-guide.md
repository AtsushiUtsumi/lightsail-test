# ポーカーAPI プレイガイド

テキサスホールデムポーカーをプレイするためのガイドです。

## 目次

1. [基本情報](#基本情報)
2. [ゲームの流れ](#ゲームの流れ)
3. [クライアントCLI](#クライアントcli)
4. [ボット](#ボット)
5. [APIリファレンス](#apiリファレンス)
6. [プレイ例（curl）](#プレイ例)

---

## 基本情報

### ベースURL
```
http://localhost/api/poker
```

### 認証
- 参加時に発行されるトークンを `X-Player-Token` ヘッダーで送信
- トークンは64文字の16進数文字列

### ゲームルール
- テキサスホールデム（ノーリミット）
- デフォルト設定: SB 10 / BB 20 / 初期チップ 1000

---

## ゲームの流れ

```
1. テーブル作成 → 2. プレイヤー参加（トークン取得）→ 3. ゲーム開始
     ↓
4. プリフロップ → 5. フロップ → 6. ターン → 7. リバー → 8. ショーダウン
     ↓
9. 次のハンドを開始（3に戻る）
```

---

## クライアントCLI

対話形式でポーカーをプレイするためのコマンドラインツールです。

### 起動方法

```bash
python3 poker_client.py [URL]
```

### 使用例

```bash
# ローカルサーバーに接続
python3 poker_client.py http://localhost

# リモートサーバーに接続
python3 poker_client.py http://example.com
```

### 操作の流れ

1. **テーブル選択**
   - 起動するとテーブル一覧が表示されます
   - テーブルIDを入力して参加、または `0` で新規作成
   - `q` で終了

2. **ユーザー名入力**
   - 表示名を入力（空欄でランダム名が付与）

3. **席選択**
   - 空いている席番号を入力
   - `0` でランダムに選択

4. **ゲームプレイ**

### ゲーム中のコマンド

| 状況 | コマンド | 説明 |
|------|---------|------|
| 待機中 | `g` | ゲーム開始 |
| 待機中 | `s` | 状態更新 |
| 待機中 | `l` | ログ表示 |
| 待機中 | `q` | 退出 |
| 自分の番 | `1` or `fold` | フォールド |
| 自分の番 | `2` or `check` | チェック |
| 自分の番 | `3` or `call` | コール |
| 自分の番 | `4` or `bet` | ベット（金額入力が必要） |
| 自分の番 | `5` or `raise` | レイズ（金額入力が必要） |
| 自分の番 | `6` or `all_in` | オールイン |

### 画面表示例

```
============================================================
テーブル: Test Table (ID: 1)
フェーズ: flop | ハンド: #1
ポット: 60 | 現在のベット: 0
------------------------------------------------------------
コミュニティカード: Kh Qc 9s
------------------------------------------------------------
プレイヤー:
  席1 *: Player1 [BTN] - チップ: 980 | ベット: 0 | 手札: Ah Ks <<< あなたの番
  席2: Player2 [SB] - チップ: 980 | ベット: 0
  席3: Player3 [BB] - チップ: 960 | ベット: 0
============================================================

有効なアクション:
  1. フォールド (fold)
  2. チェック (check)
  4. ベット (bet) - 20～980チップ
  6. オールイン (all_in) - 980チップ

アクションを入力 (fold/check/call/bet/raise/all_in):
```

### マルチプレイヤーでの遊び方

複数のターミナルを開いて、それぞれでクライアントを起動します。

```bash
# ターミナル1
python3 poker_client.py http://localhost

# ターミナル2
python3 poker_client.py http://localhost

# ターミナル3
python3 poker_client.py http://localhost
```

同じテーブルに参加し、異なる席を選択してください。

---

## ボット

自動でポーカーをプレイするボットスクリプトです。

### 起動方法

```bash
python3 poker_bot.py [URL] [オプション]
```

### オプション

| オプション | 短縮 | 説明 |
|-----------|------|------|
| `--auto-join TABLE_ID` | `-a` | 指定テーブルに自動参加 |
| `--name NAME` | `-n` | ボット名を指定 |
| `--seat SEAT` | `-s` | 席番号を指定 |
| `--min-players N` | `-m` | ゲーム開始に必要な最低人数（デフォルト: 2） |

### 使用例

```bash
# インタラクティブモード（テーブル・席を対話で選択）
python3 poker_bot.py http://localhost

# 自動参加モード
python3 poker_bot.py http://localhost --auto-join 1 --name Bot1 --seat 1

# 3人必要なテーブルに参加
python3 poker_bot.py http://localhost -a 1 -n Bot1 -s 1 -m 3
```

### 複数ボットでのテスト

3つのボットを起動してゲームをテストする例：

```bash
# ターミナル1
python3 poker_bot.py http://localhost -a 1 -n Bot1 -s 1 -m 3

# ターミナル2
python3 poker_bot.py http://localhost -a 1 -n Bot2 -s 2 -m 3

# ターミナル3
python3 poker_bot.py http://localhost -a 1 -n Bot3 -s 3 -m 3
```

### ボットの戦略

ボットはシンプルな戦略でプレイします：
- 70%: チェック/コール
- 20%: ベット/レイズ
- 10%: フォールド（大きなベットがある場合は確率上昇）

---

## APIリファレンス

### テーブル一覧取得
```bash
curl http://localhost/api/poker/tables/
```

### テーブル作成
```bash
curl -X POST http://localhost/api/poker/tables/ \
  -H "Content-Type: application/json" \
  -d '{"name": "My Table"}'
```

オプションパラメータ:
| パラメータ | デフォルト | 説明 |
|-----------|-----------|------|
| name | 必須 | テーブル名 |
| max_players | 6 | 最大プレイヤー数 |
| small_blind | 10 | スモールブラインド |
| big_blind | 20 | ビッグブラインド |
| ante | 0 | アンティ |
| initial_chips | 1000 | 初期チップ |

### テーブル参加
```bash
curl -X POST http://localhost/api/poker/tables/{table_id}/join/ \
  -H "Content-Type: application/json" \
  -d '{"username": "Player1", "seat_number": 1}'
```

レスポンス例:
```json
{
  "message": "Joined successfully",
  "token": "f9174d373c0ef92a51e024bf036d0627438c57ee3230f7539c31e1e2d2248715",
  "player": {
    "id": 1,
    "username": "Player1",
    "seat_number": 1,
    "chips": 1000
  }
}
```

**重要**: `token` を保存してください。以降のアクションで必要です。

### テーブル退出
```bash
curl -X POST http://localhost/api/poker/tables/{table_id}/leave/ \
  -H "X-Player-Token: {your_token}"
```

### ゲーム状態取得
```bash
curl http://localhost/api/poker/tables/{table_id}/state/ \
  -H "X-Player-Token: {your_token}"
```

トークンなしでも取得可能（他プレイヤーのカードは非表示）:
```bash
curl http://localhost/api/poker/tables/{table_id}/state/
```

### ゲーム開始
```bash
curl -X POST http://localhost/api/poker/tables/{table_id}/start/ \
  -H "Content-Type: application/json" \
  -H "X-Player-Token: {your_token}"
```

### アクション実行
```bash
curl -X POST http://localhost/api/poker/tables/{table_id}/action/ \
  -H "Content-Type: application/json" \
  -H "X-Player-Token: {your_token}" \
  -d '{"action": "call"}'
```

#### 利用可能なアクション

| アクション | パラメータ | 説明 |
|-----------|-----------|------|
| fold | - | フォールド（降りる） |
| check | - | チェック（パス） |
| call | - | コール（現在のベットに合わせる） |
| bet | amount | ベット（最初の賭け） |
| raise | amount | レイズ（賭け金を上げる） |
| all_in | - | オールイン（全チップを賭ける） |

ベット/レイズの例:
```bash
# 40チップをベット
curl -X POST http://localhost/api/poker/tables/{table_id}/action/ \
  -H "Content-Type: application/json" \
  -H "X-Player-Token: {your_token}" \
  -d '{"action": "bet", "amount": 40}'

# 100にレイズ
curl -X POST http://localhost/api/poker/tables/{table_id}/action/ \
  -H "Content-Type: application/json" \
  -H "X-Player-Token: {your_token}" \
  -d '{"action": "raise", "amount": 100}'
```

### アクションログ取得
```bash
curl http://localhost/api/poker/tables/{table_id}/logs/
```

---

## プレイ例

### 3人でプレイする完全な例

```bash
#!/bin/bash

# === 1. テーブル作成 ===
echo "テーブル作成..."
TABLE=$(curl -s -X POST http://localhost/api/poker/tables/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Table"}')
TABLE_ID=$(echo $TABLE | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "テーブルID: $TABLE_ID"

# === 2. プレイヤー参加 ===
echo "Player1 参加..."
P1=$(curl -s -X POST http://localhost/api/poker/tables/$TABLE_ID/join/ \
  -H "Content-Type: application/json" \
  -d '{"username": "Player1", "seat_number": 1}')
TOKEN1=$(echo $P1 | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")
echo "Player1 トークン: $TOKEN1"

echo "Player2 参加..."
P2=$(curl -s -X POST http://localhost/api/poker/tables/$TABLE_ID/join/ \
  -H "Content-Type: application/json" \
  -d '{"username": "Player2", "seat_number": 2}')
TOKEN2=$(echo $P2 | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")
echo "Player2 トークン: $TOKEN2"

echo "Player3 参加..."
P3=$(curl -s -X POST http://localhost/api/poker/tables/$TABLE_ID/join/ \
  -H "Content-Type: application/json" \
  -d '{"username": "Player3", "seat_number": 3}')
TOKEN3=$(echo $P3 | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")
echo "Player3 トークン: $TOKEN3"

# === 3. ゲーム開始 ===
echo "ゲーム開始..."
curl -s -X POST http://localhost/api/poker/tables/$TABLE_ID/start/ \
  -H "Content-Type: application/json" \
  -H "X-Player-Token: $TOKEN1"

# === 4. 状態確認（Player1視点） ===
echo "Player1の手札を確認..."
curl -s http://localhost/api/poker/tables/$TABLE_ID/state/ \
  -H "X-Player-Token: $TOKEN1" | python3 -m json.tool

# === 5. プリフロップアクション ===
# ボタン=Seat1, SB=Seat2, BB=Seat3 の場合、Seat1(UTG)から

echo "Player1: コール"
curl -s -X POST http://localhost/api/poker/tables/$TABLE_ID/action/ \
  -H "Content-Type: application/json" \
  -H "X-Player-Token: $TOKEN1" \
  -d '{"action": "call"}'

echo "Player2: コール"
curl -s -X POST http://localhost/api/poker/tables/$TABLE_ID/action/ \
  -H "Content-Type: application/json" \
  -H "X-Player-Token: $TOKEN2" \
  -d '{"action": "call"}'

echo "Player3: チェック"
curl -s -X POST http://localhost/api/poker/tables/$TABLE_ID/action/ \
  -H "Content-Type: application/json" \
  -H "X-Player-Token: $TOKEN3" \
  -d '{"action": "check"}'

# === 6. フロップ以降 ===
# SB(Seat2)からアクション開始

echo "Player2: チェック"
curl -s -X POST http://localhost/api/poker/tables/$TABLE_ID/action/ \
  -H "Content-Type: application/json" \
  -H "X-Player-Token: $TOKEN2" \
  -d '{"action": "check"}'

echo "Player3: ベット 40"
curl -s -X POST http://localhost/api/poker/tables/$TABLE_ID/action/ \
  -H "Content-Type: application/json" \
  -H "X-Player-Token: $TOKEN3" \
  -d '{"action": "bet", "amount": 40}'

echo "Player1: フォールド"
curl -s -X POST http://localhost/api/poker/tables/$TABLE_ID/action/ \
  -H "Content-Type: application/json" \
  -H "X-Player-Token: $TOKEN1" \
  -d '{"action": "fold"}'

echo "Player2: コール"
curl -s -X POST http://localhost/api/poker/tables/$TABLE_ID/action/ \
  -H "Content-Type: application/json" \
  -H "X-Player-Token: $TOKEN2" \
  -d '{"action": "call"}'

# === 7. ターン・リバー（全員チェック）===
for round in "ターン" "リバー"; do
  echo "$round"
  curl -s -X POST http://localhost/api/poker/tables/$TABLE_ID/action/ \
    -H "Content-Type: application/json" \
    -H "X-Player-Token: $TOKEN2" \
    -d '{"action": "check"}'
  curl -s -X POST http://localhost/api/poker/tables/$TABLE_ID/action/ \
    -H "Content-Type: application/json" \
    -H "X-Player-Token: $TOKEN3" \
    -d '{"action": "check"}'
done

# === 8. 結果確認 ===
echo "最終状態..."
curl -s http://localhost/api/poker/tables/$TABLE_ID/state/ | python3 -m json.tool

echo "アクションログ..."
curl -s http://localhost/api/poker/tables/$TABLE_ID/logs/ | python3 -m json.tool
```

---

## ゲーム状態の読み方

### state レスポンス例
```json
{
  "table_id": 1,
  "name": "Test Table",
  "phase": "flop",
  "hand_number": 1,
  "pot": 60,
  "current_bet": 0,
  "community_cards": [
    {"rank": "K", "suit": "h", "display": "Kh"},
    {"rank": "Q", "suit": "c", "display": "Qc"},
    {"rank": "9", "suit": "s", "display": "9s"}
  ],
  "players": [
    {
      "seat": 1,
      "username": "Player1",
      "chips": 980,
      "current_bet": 0,
      "is_folded": false,
      "is_all_in": false,
      "hole_cards": [
        {"rank": "A", "suit": "h", "display": "Ah"},
        {"rank": "K", "suit": "s", "display": "Ks"}
      ]
    }
  ],
  "button_seat": 1,
  "sb_seat": 2,
  "bb_seat": 3,
  "current_player_seat": 2,
  "valid_actions": {
    "fold": {},
    "check": {},
    "bet": {"min": 20, "max": 980},
    "all_in": {"amount": 980}
  }
}
```

### フィールド説明

| フィールド | 説明 |
|-----------|------|
| phase | ゲームフェーズ (waiting/preflop/flop/turn/river/showdown/finished) |
| pot | 現在のポット額 |
| current_bet | 現在のベット額（コールに必要な額） |
| community_cards | コミュニティカード（ボード） |
| hole_cards | ホールカード（自分のみ表示、他者は hidden） |
| current_player_seat | 現在アクション中のプレイヤーのシート番号 |
| valid_actions | 実行可能なアクション一覧 |

### カード表記

- **ランク**: 2-9, T(10), J, Q, K, A
- **スート**: h(ハート), d(ダイヤ), c(クラブ), s(スペード)
- 例: `Ah` = ハートのエース, `Td` = ダイヤの10

---

## トラブルシューティング

### "Not your turn" エラー
現在のアクション権がありません。`state` を確認して `current_player_seat` を確認してください。

### "Invalid action" エラー
`valid_actions` に含まれるアクションのみ実行可能です。例えば、誰もベットしていない時は `call` ではなく `check` を使用します。

### "Need at least 2 players" エラー
ゲーム開始には最低2人のプレイヤーが必要です。

### "Seat already taken" エラー
指定した席は既に使用されています。別の席番号を指定してください。
