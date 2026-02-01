#!/usr/bin/env python3
"""
ポーカーボットスクリプト

使い方:
  python3 poker_bot.py [URL] [--auto-join TABLE_ID] [--name NAME] [--seat SEAT]

例:
  python3 poker_bot.py http://localhost
  python3 poker_bot.py http://localhost --auto-join 1 --name Bot1 --seat 1
"""

import argparse
import json
import random
import sys
import time
import urllib.request
import urllib.error


class PokerBot:
    def __init__(self, base_url: str, name: str = None, min_players: int = 2):
        self.base_url = base_url.rstrip('/')
        self.api_url = f"{self.base_url}/api/poker"
        self.name = name or f"Bot_{random.randint(1000, 9999)}"
        self.token = None
        self.table_id = None
        self.seat = None
        self.running = True
        self.min_players = min_players

    def _request(self, method: str, endpoint: str, data: dict = None, token: str = None) -> dict:
        """HTTPリクエストを送信"""
        url = f"{self.api_url}{endpoint}"
        headers = {"Content-Type": "application/json"}
        if token:
            headers["X-Player-Token"] = token

        req_data = json.dumps(data).encode() if data else None
        req = urllib.request.Request(url, data=req_data, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            try:
                return json.loads(error_body)
            except:
                return {"error": error_body}
        except urllib.error.URLError as e:
            return {"error": str(e)}

    def get_tables(self) -> list:
        """テーブル一覧を取得"""
        return self._request("GET", "/tables/")

    def join_table(self, table_id: int, seat: int) -> dict:
        """テーブルに参加"""
        result = self._request(
            "POST",
            f"/tables/{table_id}/join/",
            {"username": self.name, "seat_number": seat}
        )
        if "token" in result:
            self.token = result["token"]
            self.table_id = table_id
            self.seat = seat
        return result

    def leave_table(self) -> dict:
        """テーブルから退出"""
        if not self.token:
            return {"error": "Not joined"}
        return self._request("POST", f"/tables/{self.table_id}/leave/", token=self.token)

    def get_state(self) -> dict:
        """ゲーム状態を取得"""
        return self._request("GET", f"/tables/{self.table_id}/state/", token=self.token)

    def start_game(self) -> dict:
        """ゲーム開始"""
        return self._request("POST", f"/tables/{self.table_id}/start/", token=self.token)

    def do_action(self, action: str, amount: int = 0) -> dict:
        """アクションを実行"""
        data = {"action": action}
        if amount > 0:
            data["amount"] = amount
        return self._request("POST", f"/tables/{self.table_id}/action/", data, token=self.token)

    def decide_action(self, state: dict) -> tuple:
        """
        AIロジック: アクションを決定
        シンプルな戦略:
        - 70% コール/チェック
        - 20% レイズ/ベット
        - 10% フォールド（ベットがある場合のみ）
        """
        valid_actions = state.get("valid_actions", {})
        if not valid_actions:
            return None, 0

        # 自分のカード情報
        my_player = None
        for p in state.get("players", []):
            if p.get("seat") == self.seat:
                my_player = p
                break

        # ランダムに決定
        roll = random.random()

        # チェック可能ならチェック優先
        if "check" in valid_actions:
            if roll < 0.7:
                return "check", 0
            elif "bet" in valid_actions and roll < 0.9:
                bet_info = valid_actions["bet"]
                min_bet = bet_info.get("min", 20)
                max_bet = bet_info.get("max", 100)
                # 小さめのベット
                bet_amount = min(min_bet * 2, max_bet)
                return "bet", bet_amount
            else:
                return "check", 0

        # コール必要な場合
        if "call" in valid_actions:
            call_amount = valid_actions["call"].get("amount", 0)

            # 10%でフォールド（大きなベットの場合は確率上昇）
            if roll < 0.1 or (call_amount > 100 and roll < 0.3):
                return "fold", 0

            # 20%でレイズ
            if "raise" in valid_actions and roll < 0.3:
                raise_info = valid_actions["raise"]
                min_raise = raise_info.get("min", call_amount * 2)
                max_raise = raise_info.get("max", call_amount * 3)
                raise_amount = min(min_raise, max_raise)
                return "raise", raise_amount

            return "call", 0

        # オールインしか選択肢がない場合
        if "all_in" in valid_actions:
            if roll < 0.5:
                return "all_in", 0
            return "fold", 0

        # フォールバック
        if "fold" in valid_actions:
            return "fold", 0

        return None, 0

    def play_loop(self):
        """メインループ: 自動プレイ"""
        print(f"\n[{self.name}] 自動プレイ開始 (テーブル {self.table_id}, シート {self.seat})")
        print(f"[{self.name}] Ctrl+C で終了\n")

        last_hand = 0
        tried_start = False

        while self.running:
            try:
                state = self.get_state()

                if "error" in state:
                    print(f"[{self.name}] エラー: {state['error']}")
                    time.sleep(2)
                    continue

                phase = state.get("phase", "unknown")
                hand_number = state.get("hand_number", 0)
                current_seat = state.get("current_player_seat")

                # 新しいハンド開始時
                if hand_number != last_hand:
                    last_hand = hand_number
                    tried_start = False
                    if hand_number > 0:
                        print(f"\n[{self.name}] === ハンド #{hand_number} ===")
                        # 自分のカードを表示
                        for p in state.get("players", []):
                            if p.get("seat") == self.seat:
                                cards = p.get("hole_cards", [])
                                if cards and not cards[0].get("hidden"):
                                    card_str = " ".join(c.get("display", "??") for c in cards)
                                    print(f"[{self.name}] 手札: {card_str}")
                                break

                # 待機中: ゲーム開始を試みる
                if phase == "waiting":
                    if not tried_start:
                        player_count = len([p for p in state.get("players", []) if p.get("is_active")])
                        if player_count >= self.min_players:
                            print(f"[{self.name}] ゲーム開始を試みます... ({player_count}人)")
                            result = self.start_game()
                            if "error" not in result:
                                print(f"[{self.name}] ゲーム開始!")
                            tried_start = True
                        else:
                            print(f"[{self.name}] 待機中... ({player_count}/{self.min_players}人)")
                            tried_start = True  # 1回だけ表示
                    time.sleep(1)
                    continue

                # ゲーム終了
                if phase == "finished":
                    # 結果表示
                    for p in state.get("players", []):
                        if p.get("seat") == self.seat:
                            print(f"[{self.name}] チップ: {p.get('chips', 0)}")
                            break
                    print(f"[{self.name}] ハンド終了、次のハンドを待機...")
                    tried_start = False
                    time.sleep(2)
                    continue

                # 自分の番かチェック
                if current_seat == self.seat:
                    action, amount = self.decide_action(state)
                    if action:
                        print(f"[{self.name}] アクション: {action}" + (f" {amount}" if amount else ""))
                        result = self.do_action(action, amount)
                        if "error" in result:
                            print(f"[{self.name}] アクションエラー: {result['error']}")
                else:
                    # 他のプレイヤーの番
                    pass

                time.sleep(0.5)

            except KeyboardInterrupt:
                print(f"\n[{self.name}] 終了します...")
                self.running = False
                break
            except Exception as e:
                print(f"[{self.name}] 例外: {e}")
                time.sleep(2)


def select_table(bot: PokerBot) -> int:
    """テーブル選択UI"""
    tables = bot.get_tables()

    if isinstance(tables, dict) and "error" in tables:
        print(f"エラー: {tables['error']}")
        return None

    if not tables:
        print("テーブルがありません。新規作成しますか？ (y/n): ", end="")
        if input().lower() == 'y':
            name = input("テーブル名: ") or "Bot Table"
            result = bot._request("POST", "/tables/", {"name": name})
            if "id" in result:
                print(f"テーブル作成: ID={result['id']}")
                return result["id"]
            else:
                print(f"作成失敗: {result}")
                return None
        return None

    print("\n=== テーブル一覧 ===")
    for t in tables:
        print(f"  [{t['id']}] {t['name']} - プレイヤー: {t['player_count']}/{t['max_players']} - 状態: {t['status']}")

    print("\nテーブルIDを入力 (0で新規作成): ", end="")
    try:
        table_id = int(input())
        if table_id == 0:
            name = input("テーブル名: ") or "Bot Table"
            result = bot._request("POST", "/tables/", {"name": name})
            if "id" in result:
                print(f"テーブル作成: ID={result['id']}")
                return result["id"]
            else:
                print(f"作成失敗: {result}")
                return None
        return table_id
    except ValueError:
        print("無効な入力")
        return None


def select_seat(bot: PokerBot, table_id: int) -> int:
    """席選択UI"""
    state = bot._request("GET", f"/tables/{table_id}/state/")
    if "error" in state:
        # テーブルがまだ開始されていない場合、詳細を取得
        detail = bot._request("GET", f"/tables/{table_id}/")
        max_players = detail.get("max_players", 6)
        occupied = []
    else:
        max_players = state.get("settings", {}).get("max_players", 6)
        occupied = [p["seat"] for p in state.get("players", [])]

    available = [s for s in range(1, max_players + 1) if s not in occupied]

    if not available:
        print("空席がありません")
        return None

    print(f"\n空席: {available}")
    print("席番号を入力 (0でランダム): ", end="")

    try:
        seat = int(input())
        if seat == 0:
            seat = random.choice(available)
            print(f"席 {seat} を選択")
        elif seat not in available:
            print("その席は使用できません")
            return None
        return seat
    except ValueError:
        print("無効な入力")
        return None


def main():
    parser = argparse.ArgumentParser(description="ポーカーボット")
    parser.add_argument("url", nargs="?", default="http://localhost", help="サーバーURL")
    parser.add_argument("--auto-join", "-a", type=int, help="自動参加するテーブルID")
    parser.add_argument("--name", "-n", help="ボット名")
    parser.add_argument("--seat", "-s", type=int, help="席番号")
    parser.add_argument("--min-players", "-m", type=int, default=2, help="ゲーム開始に必要な最低人数 (デフォルト: 2)")
    args = parser.parse_args()

    print("=" * 50)
    print("  ポーカーボット")
    print("=" * 50)

    bot = PokerBot(args.url, args.name, args.min_players)
    print(f"サーバー: {bot.api_url}")
    print(f"ボット名: {bot.name}")
    print(f"最低人数: {bot.min_players}人")

    # 自動参加モード
    if args.auto_join:
        table_id = args.auto_join
        seat = args.seat or random.randint(1, 6)
    else:
        # インタラクティブモード
        table_id = select_table(bot)
        if not table_id:
            return

        seat = select_seat(bot, table_id)
        if not seat:
            return

    # テーブルに参加
    print(f"\nテーブル {table_id} 席 {seat} に参加中...")
    result = bot.join_table(table_id, seat)

    if "error" in result:
        print(f"参加失敗: {result['error']}")
        return

    print(f"参加成功! トークン: {bot.token[:16]}...")

    # 自動プレイ開始
    try:
        bot.play_loop()
    finally:
        print(f"[{bot.name}] テーブルから退出...")
        bot.leave_table()


if __name__ == "__main__":
    main()
