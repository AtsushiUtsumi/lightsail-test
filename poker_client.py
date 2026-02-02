#!/usr/bin/env python3
"""
ポーカークライアントCLI

使い方:
  python3 poker_client.py [URL]

例:
  python3 poker_client.py http://localhost
"""

import argparse
import json
import random
import sys
import time
import urllib.request
import urllib.error


class PokerClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.api_url = f"{self.base_url}/api/poker"
        self.token = None
        self.table_id = None
        self.seat = None
        self.username = None

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

    def create_table(self, name: str, **kwargs) -> dict:
        """テーブル作成"""
        data = {"name": name}
        data.update(kwargs)
        return self._request("POST", "/tables/", data)

    def get_table_detail(self, table_id: int) -> dict:
        """テーブル詳細を取得"""
        return self._request("GET", f"/tables/{table_id}/")

    def join_table(self, table_id: int, username: str, seat: int) -> dict:
        """テーブルに参加"""
        result = self._request(
            "POST",
            f"/tables/{table_id}/join/",
            {"username": username, "seat_number": seat}
        )
        if "token" in result:
            self.token = result["token"]
            self.table_id = table_id
            self.seat = seat
            self.username = username
        return result

    def leave_table(self) -> dict:
        """テーブルから退出"""
        if not self.token:
            return {"error": "Not joined"}
        result = self._request("POST", f"/tables/{self.table_id}/leave/", token=self.token)
        self.token = None
        self.table_id = None
        self.seat = None
        return result

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

    def get_logs(self) -> dict:
        """アクションログを取得"""
        return self._request("GET", f"/tables/{self.table_id}/logs/")


def clear_screen():
    """画面クリア"""
    print("\033[2J\033[H", end="")


def format_cards(cards: list) -> str:
    """カードを表示用にフォーマット"""
    if not cards:
        return "なし"
    result = []
    for c in cards:
        if c.get("hidden"):
            result.append("??")
        else:
            result.append(c.get("display", "??"))
    return " ".join(result)


def display_state(state: dict, my_seat: int):
    """ゲーム状態を表示"""
    print("\n" + "=" * 60)
    print(f"テーブル: {state.get('name', 'Unknown')} (ID: {state.get('table_id')})")
    print(f"フェーズ: {state.get('phase', 'unknown')} | ハンド: #{state.get('hand_number', 0)}")
    print(f"ポット: {state.get('pot', 0)} | 現在のベット: {state.get('current_bet', 0)}")
    print("-" * 60)

    # コミュニティカード
    community = state.get("community_cards", [])
    print(f"コミュニティカード: {format_cards(community)}")
    print("-" * 60)

    # プレイヤー情報
    current_seat = state.get("current_player_seat")
    button_seat = state.get("button_seat")
    sb_seat = state.get("sb_seat")
    bb_seat = state.get("bb_seat")

    print("プレイヤー:")
    for p in state.get("players", []):
        seat = p.get("seat")
        markers = []
        if seat == button_seat:
            markers.append("BTN")
        if seat == sb_seat:
            markers.append("SB")
        if seat == bb_seat:
            markers.append("BB")
        marker_str = f" [{'/'.join(markers)}]" if markers else ""

        status = ""
        if p.get("is_folded"):
            status = " (フォールド)"
        elif p.get("is_all_in"):
            status = " (オールイン)"

        turn_marker = " <<< あなたの番" if seat == current_seat and seat == my_seat else ""
        if seat == current_seat and seat != my_seat:
            turn_marker = " <<< 待機中"

        is_me = " *" if seat == my_seat else ""

        cards_str = ""
        if seat == my_seat:
            cards = p.get("hole_cards", [])
            cards_str = f" | 手札: {format_cards(cards)}"

        print(f"  席{seat}{is_me}: {p.get('username', 'Unknown')}{marker_str} - "
              f"チップ: {p.get('chips', 0)} | ベット: {p.get('current_bet', 0)}{status}{cards_str}{turn_marker}")

    print("=" * 60)


def display_valid_actions(state: dict):
    """有効なアクションを表示"""
    valid = state.get("valid_actions", {})
    if not valid:
        print("現在アクションできません")
        return

    print("\n有効なアクション:")
    options = []
    if "fold" in valid:
        options.append("1. フォールド (fold)")
    if "check" in valid:
        options.append("2. チェック (check)")
    if "call" in valid:
        amount = valid["call"].get("amount", 0)
        options.append(f"3. コール (call) - {amount}チップ")
    if "bet" in valid:
        info = valid["bet"]
        options.append(f"4. ベット (bet) - {info.get('min', 0)}～{info.get('max', 0)}チップ")
    if "raise" in valid:
        info = valid["raise"]
        options.append(f"5. レイズ (raise) - {info.get('min', 0)}～{info.get('max', 0)}チップ")
    if "all_in" in valid:
        amount = valid["all_in"].get("amount", 0)
        options.append(f"6. オールイン (all_in) - {amount}チップ")

    for opt in options:
        print(f"  {opt}")


def get_user_action(state: dict) -> tuple:
    """ユーザーからアクションを取得"""
    valid = state.get("valid_actions", {})

    display_valid_actions(state)

    print("\nアクションを入力 (fold/check/call/bet/raise/all_in): ", end="")
    action_input = input().strip().lower()

    # 数字入力の場合
    action_map = {
        "1": "fold", "f": "fold", "fold": "fold",
        "2": "check", "k": "check", "check": "check",
        "3": "call", "c": "call", "call": "call",
        "4": "bet", "b": "bet", "bet": "bet",
        "5": "raise", "r": "raise", "raise": "raise",
        "6": "all_in", "a": "all_in", "all_in": "all_in", "allin": "all_in"
    }

    action = action_map.get(action_input)
    if not action:
        print("無効なアクションです")
        return None, 0

    if action not in valid:
        print(f"'{action}' は現在実行できません")
        return None, 0

    amount = 0
    if action in ["bet", "raise"]:
        info = valid[action]
        min_amt = info.get("min", 0)
        max_amt = info.get("max", 0)
        print(f"金額を入力 ({min_amt}～{max_amt}): ", end="")
        try:
            amount = int(input().strip())
            if amount < min_amt or amount > max_amt:
                print(f"金額は{min_amt}～{max_amt}の範囲で入力してください")
                return None, 0
        except ValueError:
            print("無効な金額です")
            return None, 0

    return action, amount


def select_table(client: PokerClient) -> int:
    """テーブル選択"""
    tables = client.get_tables()

    if isinstance(tables, dict) and "error" in tables:
        print(f"エラー: {tables['error']}")
        return None

    if not tables:
        print("テーブルがありません。")
        print("新規作成しますか？ (y/n): ", end="")
        if input().strip().lower() == 'y':
            name = input("テーブル名: ").strip() or "My Table"
            result = client.create_table(name)
            if "id" in result:
                print(f"テーブル作成完了: ID={result['id']}")
                return result["id"]
            else:
                print(f"作成失敗: {result}")
                return None
        return None

    print("\n" + "=" * 50)
    print("  テーブル一覧")
    print("=" * 50)
    for t in tables:
        print(f"  [{t['id']}] {t['name']}")
        print(f"      プレイヤー: {t['player_count']}/{t['max_players']} | 状態: {t['status']}")

    print("\nテーブルIDを入力 (0で新規作成, qで終了): ", end="")
    try:
        choice = input().strip()
        if choice.lower() == 'q':
            return None
        table_id = int(choice)
        if table_id == 0:
            name = input("テーブル名: ").strip() or "My Table"
            result = client.create_table(name)
            if "id" in result:
                print(f"テーブル作成完了: ID={result['id']}")
                return result["id"]
            else:
                print(f"作成失敗: {result}")
                return None
        return table_id
    except ValueError:
        print("無効な入力")
        return None


def select_seat(client: PokerClient, table_id: int) -> int:
    """席選択"""
    state = client._request("GET", f"/tables/{table_id}/state/")
    if "error" in state:
        detail = client.get_table_detail(table_id)
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
        seat = int(input().strip())
        if seat == 0:
            seat = random.choice(available)
            print(f"席 {seat} を選択しました")
        elif seat not in available:
            print("その席は使用できません")
            return None
        return seat
    except ValueError:
        print("無効な入力")
        return None


def play_loop(client: PokerClient):
    """メインプレイループ"""
    print(f"\n参加完了！テーブル {client.table_id}, 席 {client.seat}")
    print("コマンド: s=状態表示, g=ゲーム開始, l=ログ表示, q=退出")
    print("-" * 50)

    last_hand = 0
    last_phase = None

    while True:
        try:
            state = client.get_state()

            if "error" in state:
                print(f"エラー: {state['error']}")
                time.sleep(1)
                continue

            phase = state.get("phase", "unknown")
            hand_number = state.get("hand_number", 0)
            current_seat = state.get("current_player_seat")

            # ハンドやフェーズが変わったら状態表示
            if hand_number != last_hand or phase != last_phase:
                last_hand = hand_number
                last_phase = phase
                display_state(state, client.seat)

            # 待機中
            if phase == "waiting":
                print("\n待機中... (g=ゲーム開始, s=状態更新, q=退出): ", end="")
                cmd = input().strip().lower()
                if cmd == 'g':
                    result = client.start_game()
                    if "error" in result:
                        print(f"開始失敗: {result['error']}")
                    else:
                        print("ゲーム開始！")
                elif cmd == 's':
                    continue
                elif cmd == 'q':
                    break
                elif cmd == 'l':
                    logs = client.get_logs()
                    print(json.dumps(logs, indent=2, ensure_ascii=False))
                continue

            # ゲーム終了
            if phase == "finished":
                display_state(state, client.seat)
                print("\nハンド終了！")
                print("続行する場合は g=ゲーム開始, s=状態更新, l=ログ, q=退出: ", end="")
                cmd = input().strip().lower()
                if cmd == 'g':
                    result = client.start_game()
                    if "error" in result:
                        print(f"開始失敗: {result['error']}")
                    else:
                        print("次のハンド開始！")
                        last_phase = None
                elif cmd == 'q':
                    break
                elif cmd == 'l':
                    logs = client.get_logs()
                    print(json.dumps(logs, indent=2, ensure_ascii=False))
                continue

            # 自分の番
            if current_seat == client.seat:
                display_state(state, client.seat)
                action, amount = get_user_action(state)
                if action:
                    result = client.do_action(action, amount)
                    if "error" in result:
                        print(f"アクション失敗: {result['error']}")
                    else:
                        print(f"アクション成功: {action}" + (f" {amount}" if amount else ""))
                        last_phase = None  # 状態更新のため
            else:
                # 他のプレイヤーの番
                print(f"\r待機中 (席{current_seat}のターン)... s=状態更新, q=退出: ", end="")
                # 非ブロッキング入力のシミュレーション
                import select
                import sys
                if sys.stdin in select.select([sys.stdin], [], [], 1)[0]:
                    cmd = input().strip().lower()
                    if cmd == 's':
                        display_state(state, client.seat)
                    elif cmd == 'q':
                        break
                    elif cmd == 'l':
                        logs = client.get_logs()
                        print(json.dumps(logs, indent=2, ensure_ascii=False))

        except KeyboardInterrupt:
            print("\n終了します...")
            break
        except Exception as e:
            print(f"例外: {e}")
            time.sleep(1)


def main():
    parser = argparse.ArgumentParser(description="ポーカークライアントCLI")
    parser.add_argument("url", nargs="?", default="http://localhost", help="サーバーURL")
    args = parser.parse_args()

    print("=" * 50)
    print("  ポーカークライアント")
    print("=" * 50)

    client = PokerClient(args.url)
    print(f"サーバー: {client.api_url}")

    # テーブル選択
    table_id = select_table(client)
    if not table_id:
        print("終了します")
        return

    # ユーザー名入力
    print("\nユーザー名を入力: ", end="")
    username = input().strip() or f"Player_{random.randint(1000, 9999)}"

    # 席選択
    seat = select_seat(client, table_id)
    if not seat:
        print("終了します")
        return

    # テーブルに参加
    print(f"\nテーブル {table_id} 席 {seat} に参加中...")
    result = client.join_table(table_id, username, seat)

    if "error" in result:
        print(f"参加失敗: {result['error']}")
        return

    print(f"参加成功！ユーザー: {username}")
    print(f"トークン: {client.token[:16]}...")

    # メインループ
    try:
        play_loop(client)
    finally:
        print(f"\n[{username}] テーブルから退出中...")
        client.leave_table()
        print("退出完了")


if __name__ == "__main__":
    main()
