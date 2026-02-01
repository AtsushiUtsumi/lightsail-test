from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
from .deck import Deck, Card
from .player import Player
from .hand_evaluator import HandEvaluator


class GamePhase(Enum):
    WAITING = 'waiting'
    PREFLOP = 'preflop'
    FLOP = 'flop'
    TURN = 'turn'
    RIVER = 'river'
    SHOWDOWN = 'showdown'
    FINISHED = 'finished'


@dataclass
class ActionLog:
    """アクションログエントリ"""
    action: str
    player_seat: Optional[int]
    player_name: Optional[str]
    amount: int
    details: dict = field(default_factory=dict)


class PokerTable:
    """テキサスホールデムポーカーテーブル"""

    def __init__(
        self,
        table_id: int,
        name: str,
        max_players: int = 6,
        small_blind: int = 10,
        big_blind: int = 20,
        ante: int = 0,
        initial_chips: int = 1000,
        time_limit_seconds: int = 30,
    ):
        self.table_id = table_id
        self.name = name
        self.max_players = max_players
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.ante = ante
        self.initial_chips = initial_chips
        self.time_limit_seconds = time_limit_seconds

        # プレイヤー管理（seat -> Player）
        self.players: Dict[int, Player] = {}

        # ゲーム状態
        self.phase = GamePhase.WAITING
        self.deck = Deck()
        self.community_cards: List[Card] = []
        self.pot = 0
        self.side_pots: List[dict] = []

        # ベッティングラウンド状態
        self.current_bet = 0
        self.min_raise = big_blind
        self.current_player_seat: Optional[int] = None
        self.last_raiser_seat: Optional[int] = None
        self._first_actor_seat: Optional[int] = None
        self._acted_players: set = set()

        # ボタン・ブラインド位置
        self.button_seat: Optional[int] = None
        self.sb_seat: Optional[int] = None
        self.bb_seat: Optional[int] = None

        # ハンド番号
        self.hand_number = 0

        # アクションログ
        self.action_logs: List[ActionLog] = []

    def add_player(self, seat: int, username: str, chips: int, token: str, db_id: int) -> bool:
        """プレイヤーを追加"""
        if seat < 1 or seat > self.max_players:
            return False
        if seat in self.players:
            return False
        if len(self.players) >= self.max_players:
            return False

        player = Player(
            seat=seat,
            username=username,
            chips=chips,
            token=token,
            db_id=db_id,
        )
        self.players[seat] = player
        self._log_action('join', seat, username, chips, {})
        return True

    def remove_player(self, seat: int) -> bool:
        """プレイヤーを削除"""
        if seat not in self.players:
            return False

        player = self.players[seat]
        self._log_action('leave', seat, player.username, player.chips, {})
        del self.players[seat]
        return True

    def get_player_by_token(self, token: str) -> Optional[Player]:
        """トークンからプレイヤーを取得"""
        for player in self.players.values():
            if player.token == token:
                return player
        return None

    def _get_active_seats(self) -> List[int]:
        """アクティブなプレイヤーのシート番号リスト（ソート済み）"""
        return sorted([s for s, p in self.players.items() if p.is_active and not p.is_folded])

    def _get_next_seat(self, current_seat: int) -> Optional[int]:
        """次のアクティブなシートを取得"""
        active_seats = self._get_active_seats()
        if not active_seats:
            return None

        # 現在のシートより大きい最小のシートを探す
        for seat in active_seats:
            if seat > current_seat:
                return seat
        # なければ最小のシートに戻る
        return active_seats[0]

    def _get_next_acting_seat(self, current_seat: int) -> Optional[int]:
        """次にアクション可能なシートを取得"""
        seats = [s for s, p in self.players.items() if p.can_act()]
        if not seats:
            return None

        seats = sorted(seats)
        for seat in seats:
            if seat > current_seat:
                return seat
        return seats[0]

    def start_game(self) -> Tuple[bool, str]:
        """ゲーム開始"""
        if self.phase != GamePhase.WAITING and self.phase != GamePhase.FINISHED:
            return (False, "Game already in progress")

        active_players = [p for p in self.players.values() if p.is_active]
        if len(active_players) < 2:
            return (False, "Need at least 2 players")

        self._start_new_hand()
        return (True, "Game started")

    def _start_new_hand(self):
        """新しいハンドを開始"""
        self.hand_number += 1
        self.community_cards = []
        self.pot = 0
        self.side_pots = []
        self.current_bet = 0
        self.min_raise = self.big_blind
        self.action_logs = []

        # プレイヤーをリセット
        for player in self.players.values():
            player.reset_for_new_hand()

        # デッキをリセット・シャッフル
        self.deck.reset()
        self.deck.shuffle()

        # ボタン位置を決定（次のアクティブなプレイヤー）
        active_seats = self._get_active_seats()
        if self.button_seat is None:
            self.button_seat = active_seats[0]
        else:
            self.button_seat = self._get_next_seat(self.button_seat) or active_seats[0]

        # ブラインド位置を決定
        if len(active_seats) == 2:
            # ヘッズアップ
            self.sb_seat = self.button_seat
            self.bb_seat = self._get_next_seat(self.button_seat)
        else:
            self.sb_seat = self._get_next_seat(self.button_seat)
            self.bb_seat = self._get_next_seat(self.sb_seat)

        # アンティを徴収
        if self.ante > 0:
            for player in self.players.values():
                if player.is_active:
                    ante_amount = player.bet(self.ante)
                    self.pot += ante_amount
                    self._log_action('post_ante', player.seat, player.username, ante_amount, {})

        # ブラインドを徴収
        sb_player = self.players[self.sb_seat]
        sb_amount = sb_player.bet(self.small_blind)
        self.pot += sb_amount
        self._log_action('post_blind', self.sb_seat, sb_player.username, sb_amount, {'type': 'small_blind'})

        bb_player = self.players[self.bb_seat]
        bb_amount = bb_player.bet(self.big_blind)
        self.pot += bb_amount
        self.current_bet = bb_amount
        self._log_action('post_blind', self.bb_seat, bb_player.username, bb_amount, {'type': 'big_blind'})

        # カードを配る
        for _ in range(2):
            for seat in active_seats:
                card = self.deck.deal_one()
                self.players[seat].hole_cards.append(card)

        self._log_action('deal', None, None, 0, {'phase': 'preflop', 'cards_dealt': 2})

        # プリフロップ開始
        self.phase = GamePhase.PREFLOP
        self.last_raiser_seat = self.bb_seat

        # UTG（BB の次）からアクション開始
        self.current_player_seat = self._get_next_acting_seat(self.bb_seat)

        # プリフロップはBBがレイザーなので、_first_actor_seat は使わない
        self._first_actor_seat = None
        self._acted_players = set()

    def process_action(self, seat: int, action: str, amount: int = 0) -> Tuple[bool, str]:
        """アクションを処理"""
        if self.phase in [GamePhase.WAITING, GamePhase.SHOWDOWN, GamePhase.FINISHED]:
            return (False, "Cannot act in current phase")

        if seat != self.current_player_seat:
            return (False, "Not your turn")

        player = self.players.get(seat)
        if not player or not player.can_act():
            return (False, "Cannot act")

        valid_actions = self._get_valid_actions(seat)
        if action not in valid_actions:
            return (False, f"Invalid action. Valid actions: {list(valid_actions.keys())}")

        # アクション実行
        if action == 'fold':
            player.fold()
            self._log_action('fold', seat, player.username, 0, {})

        elif action == 'check':
            if player.current_bet < self.current_bet:
                return (False, "Cannot check, must call or fold")
            self._log_action('check', seat, player.username, 0, {})

        elif action == 'call':
            call_amount = min(self.current_bet - player.current_bet, player.chips)
            actual_bet = player.bet(call_amount)
            self.pot += actual_bet
            self._log_action('call', seat, player.username, actual_bet, {})

        elif action == 'bet':
            if self.current_bet > 0:
                return (False, "Cannot bet, use raise instead")
            if amount < self.big_blind:
                return (False, f"Minimum bet is {self.big_blind}")
            if amount > player.chips:
                return (False, "Not enough chips")
            actual_bet = player.bet(amount)
            self.pot += actual_bet
            self.current_bet = player.current_bet
            self.min_raise = amount
            self.last_raiser_seat = seat
            self._log_action('bet', seat, player.username, actual_bet, {})

        elif action == 'raise':
            if self.current_bet == 0:
                return (False, "Cannot raise, use bet instead")
            raise_to = amount
            raise_amount = raise_to - self.current_bet
            if raise_amount < self.min_raise and raise_to != player.chips + player.current_bet:
                return (False, f"Minimum raise is {self.min_raise}")
            call_amount = self.current_bet - player.current_bet
            total_amount = call_amount + raise_amount
            if total_amount > player.chips:
                return (False, "Not enough chips")
            actual_bet = player.bet(total_amount)
            self.pot += actual_bet
            self.min_raise = raise_amount
            self.current_bet = player.current_bet
            self.last_raiser_seat = seat
            self._log_action('raise', seat, player.username, actual_bet, {'raise_to': raise_to})

        elif action == 'all_in':
            all_in_amount = player.chips
            actual_bet = player.bet(all_in_amount)
            self.pot += actual_bet
            if player.current_bet > self.current_bet:
                raise_amount = player.current_bet - self.current_bet
                if raise_amount >= self.min_raise:
                    self.min_raise = raise_amount
                    self.last_raiser_seat = seat
                self.current_bet = player.current_bet
            self._log_action('all_in', seat, player.username, actual_bet, {})

        # 次のアクションを決定
        self._advance_action()
        return (True, "Action processed")

    def _get_valid_actions(self, seat: int) -> Dict[str, dict]:
        """有効なアクションを取得"""
        player = self.players.get(seat)
        if not player or not player.can_act():
            return {}

        actions = {}
        to_call = self.current_bet - player.current_bet

        # フォールドは常に可能
        actions['fold'] = {}

        if to_call == 0:
            # チェック可能
            actions['check'] = {}
            # ベット可能
            actions['bet'] = {'min': self.big_blind, 'max': player.chips}
        else:
            # コール可能
            actions['call'] = {'amount': min(to_call, player.chips)}
            # レイズ可能（十分なチップがあれば）
            min_raise_to = self.current_bet + self.min_raise
            if player.chips + player.current_bet > self.current_bet:
                actions['raise'] = {
                    'min': min(min_raise_to, player.chips + player.current_bet),
                    'max': player.chips + player.current_bet
                }

        # オールイン
        if player.chips > 0:
            actions['all_in'] = {'amount': player.chips}

        return actions

    def _advance_action(self):
        """次のアクションに進める"""
        # 現在のプレイヤーをアクション済みに追加
        if hasattr(self, '_acted_players'):
            self._acted_players.add(self.current_player_seat)

        # アクティブでフォールドしてないプレイヤー
        active_players = [p for p in self.players.values() if p.is_active and not p.is_folded]

        # 1人だけなら終了
        if len(active_players) == 1:
            self._end_hand_single_winner(active_players[0])
            return

        # 全員オールインまたは1人以外オールイン
        can_act_players = [p for p in active_players if p.can_act()]
        if len(can_act_players) <= 1:
            # 全員のベットが揃っているか、アクション可能なプレイヤーが1人以下
            all_bets_equal = all(
                p.current_bet == self.current_bet or p.is_all_in
                for p in active_players
            )
            if all_bets_equal or len(can_act_players) == 0:
                self._deal_remaining_and_showdown()
                return

        # 次のプレイヤーを探す
        next_seat = self._get_next_acting_seat(self.current_player_seat)

        # 全員がコール/チェック済みかチェック
        all_matched = all(
            p.current_bet == self.current_bet or p.is_folded or p.is_all_in
            for p in self.players.values() if p.is_active
        )

        # ベッティングラウンド終了判定
        if self.last_raiser_seat is not None:
            # 誰かがベット/レイズした場合
            if next_seat == self.last_raiser_seat and all_matched:
                # 一周した
                self._end_betting_round()
                return
        else:
            # 誰もベット/レイズしていない場合（全員チェック）
            # 全員がアクションしたかチェック
            if hasattr(self, '_acted_players') and hasattr(self, '_first_actor_seat'):
                acting_seats = {s for s, p in self.players.items() if p.can_act()}
                if acting_seats <= self._acted_players:
                    # 全員アクション済み
                    self._end_betting_round()
                    return

        self.current_player_seat = next_seat

    def _end_betting_round(self):
        """ベッティングラウンド終了"""
        # ベット額リセット
        for player in self.players.values():
            player.current_bet = 0
        self.current_bet = 0
        self.min_raise = self.big_blind

        # 次のフェーズへ
        if self.phase == GamePhase.PREFLOP:
            self._deal_flop()
        elif self.phase == GamePhase.FLOP:
            self._deal_turn()
        elif self.phase == GamePhase.TURN:
            self._deal_river()
        elif self.phase == GamePhase.RIVER:
            self._showdown()

    def _deal_flop(self):
        """フロップを配る"""
        self.phase = GamePhase.FLOP
        self.deck.burn()
        self.community_cards.extend(self.deck.deal(3))
        self._log_action('deal', None, None, 0, {
            'phase': 'flop',
            'cards': [str(c) for c in self.community_cards]
        })
        self._start_new_betting_round()

    def _deal_turn(self):
        """ターンを配る"""
        self.phase = GamePhase.TURN
        self.deck.burn()
        self.community_cards.append(self.deck.deal_one())
        self._log_action('deal', None, None, 0, {
            'phase': 'turn',
            'cards': [str(c) for c in self.community_cards]
        })
        self._start_new_betting_round()

    def _deal_river(self):
        """リバーを配る"""
        self.phase = GamePhase.RIVER
        self.deck.burn()
        self.community_cards.append(self.deck.deal_one())
        self._log_action('deal', None, None, 0, {
            'phase': 'river',
            'cards': [str(c) for c in self.community_cards]
        })
        self._start_new_betting_round()

    def _start_new_betting_round(self):
        """新しいベッティングラウンドを開始"""
        # ボタンの次からアクション開始
        active_seats = [s for s, p in self.players.items() if p.can_act()]
        if not active_seats:
            self._showdown()
            return

        # SBまたはその次のアクティブプレイヤーから開始
        self.current_player_seat = self._get_next_acting_seat(self.button_seat)
        # last_raiser_seatはNoneに設定（誰もベット/レイズしていない）
        self.last_raiser_seat = None
        # 最初のアクターを記録
        self._first_actor_seat = self.current_player_seat
        self._acted_players = set()

    def _deal_remaining_and_showdown(self):
        """残りのカードを配ってショーダウン"""
        while len(self.community_cards) < 5:
            self.deck.burn()
            if len(self.community_cards) == 0:
                self.community_cards.extend(self.deck.deal(3))
            else:
                self.community_cards.append(self.deck.deal_one())

        self._log_action('deal', None, None, 0, {
            'phase': 'showdown',
            'cards': [str(c) for c in self.community_cards]
        })
        self._showdown()

    def _showdown(self):
        """ショーダウン"""
        self.phase = GamePhase.SHOWDOWN
        active_players = [p for p in self.players.values() if p.is_active and not p.is_folded]

        # ハンドを評価
        players_hands = []
        for player in active_players:
            hand = HandEvaluator.evaluate(player.hole_cards, self.community_cards)
            players_hands.append((player.seat, hand))
            self._log_action('showdown', player.seat, player.username, 0, {
                'hole_cards': [str(c) for c in player.hole_cards],
                'hand': hand[2]
            })

        # 勝者を決定
        winner_seats = HandEvaluator.find_winners(players_hands)
        self._distribute_pot(winner_seats, players_hands)

        self.phase = GamePhase.FINISHED

    def _end_hand_single_winner(self, winner: Player):
        """1人残りで終了"""
        winner.win(self.pot)
        self._log_action('win', winner.seat, winner.username, self.pot, {'reason': 'last_player'})
        self.pot = 0
        self.phase = GamePhase.FINISHED

    def _distribute_pot(self, winner_seats: List[int], players_hands: List):
        """ポットを分配"""
        if not winner_seats:
            return

        # シンプルな分配（サイドポット未対応の簡易版）
        pot_per_winner = self.pot // len(winner_seats)
        remainder = self.pot % len(winner_seats)

        for i, seat in enumerate(winner_seats):
            win_amount = pot_per_winner + (1 if i < remainder else 0)
            self.players[seat].win(win_amount)

            # 勝利ハンドを取得
            winning_hand = ''
            for s, hand in players_hands:
                if s == seat:
                    winning_hand = hand[2]
                    break

            self._log_action('win', seat, self.players[seat].username, win_amount, {
                'hand': winning_hand
            })

        self.pot = 0

    def _log_action(self, action: str, seat: Optional[int], username: Optional[str],
                    amount: int, details: dict):
        """アクションをログに記録"""
        log = ActionLog(
            action=action,
            player_seat=seat,
            player_name=username,
            amount=amount,
            details=details
        )
        self.action_logs.append(log)

    def get_state(self, viewer_token: Optional[str] = None) -> dict:
        """テーブル状態を取得"""
        viewer_seat = None
        if viewer_token:
            viewer = self.get_player_by_token(viewer_token)
            if viewer:
                viewer_seat = viewer.seat

        players_data = []
        for seat, player in sorted(self.players.items()):
            show_cards = (
                self.phase == GamePhase.SHOWDOWN or
                self.phase == GamePhase.FINISHED or
                seat == viewer_seat
            )
            players_data.append(player.to_dict(show_cards=show_cards))

        state = {
            'table_id': self.table_id,
            'name': self.name,
            'phase': self.phase.value,
            'hand_number': self.hand_number,
            'pot': self.pot,
            'current_bet': self.current_bet,
            'community_cards': [c.to_dict() for c in self.community_cards],
            'players': players_data,
            'button_seat': self.button_seat,
            'sb_seat': self.sb_seat,
            'bb_seat': self.bb_seat,
            'current_player_seat': self.current_player_seat,
            'settings': {
                'max_players': self.max_players,
                'small_blind': self.small_blind,
                'big_blind': self.big_blind,
                'ante': self.ante,
            }
        }

        # 自分の番なら有効なアクションを追加
        if viewer_seat and viewer_seat == self.current_player_seat:
            state['valid_actions'] = self._get_valid_actions(viewer_seat)

        return state

    def get_action_logs(self) -> List[dict]:
        """アクションログを取得"""
        return [
            {
                'action': log.action,
                'player_seat': log.player_seat,
                'player_name': log.player_name,
                'amount': log.amount,
                'details': log.details,
            }
            for log in self.action_logs
        ]
