from typing import Dict, Optional
from dataclasses import dataclass
from threading import Lock

from poker_domain import (
    PokerTable, Chips, GamePhase, GameState, ActionResult, PlayerState,
)
from ..models import PokerTable as PokerTableModel, TablePlayer, GameHand, ActionLog


SUIT_TO_SHORT = {
    'hearts': 'h',
    'diamonds': 'd',
    'clubs': 'c',
    'spades': 's',
}

RANK_TO_SHORT = {
    2: '2', 3: '3', 4: '4', 5: '5', 6: '6', 7: '7', 8: '8', 9: '9',
    10: 'T', 11: 'J', 12: 'Q', 13: 'K', 14: 'A',
}


PHASE_MAP = {
    'showdown': 'finished',
    'pre_flop': 'preflop',
}


def _map_phase(phase_value: str) -> str:
    return PHASE_MAP.get(phase_value, phase_value)


def card_to_dict(card) -> dict:
    rank_str = RANK_TO_SHORT[card.rank.value]
    suit_str = SUIT_TO_SHORT[card.suit.value]
    return {'rank': rank_str, 'suit': suit_str, 'display': f'{rank_str}{suit_str}'}


@dataclass
class PlayerInfo:
    """DBプレイヤーとドメインプレイヤーの対応情報"""
    username: str
    seat_number: int
    token: str
    db_id: int


class TableManager:
    """複数テーブルのインメモリ管理"""

    _instance = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._tables: Dict[int, PokerTable] = {}
        self._player_info: Dict[int, Dict[str, PlayerInfo]] = {}  # table_id -> {username -> PlayerInfo}
        self._hand_numbers: Dict[int, int] = {}  # table_id -> hand_number
        self._table_lock = Lock()
        self._initialized = True

    def get_or_create_table(self, table_id: int) -> Optional[PokerTable]:
        """テーブルを取得（なければDBから復元）"""
        with self._table_lock:
            if table_id in self._tables:
                return self._tables[table_id]

            # DBから復元
            try:
                db_table = PokerTableModel.objects.get(id=table_id)
            except PokerTableModel.DoesNotExist:
                return None

            table = PokerTable(
                table_id=str(db_table.id),
                max_players=db_table.max_players,
                small_blind=db_table.small_blind,
                big_blind=db_table.big_blind,
                timeout_seconds=db_table.time_limit_seconds,
            )

            self._player_info[table_id] = {}
            self._hand_numbers[table_id] = db_table.current_hand_number

            # プレイヤーを復元
            for db_player in db_table.table_players.filter(is_active=True):
                table.add_player(
                    player_id=db_player.username,
                    chips=Chips(db_player.chips),
                )
                self._player_info[table_id][db_player.username] = PlayerInfo(
                    username=db_player.username,
                    seat_number=db_player.seat_number,
                    token=db_player.token,
                    db_id=db_player.id,
                )

            self._tables[table_id] = table
            return table

    def get_table(self, table_id: int) -> Optional[PokerTable]:
        """テーブルを取得"""
        return self._tables.get(table_id)

    def add_player_info(self, table_id: int, info: PlayerInfo):
        """プレイヤー情報を登録"""
        if table_id not in self._player_info:
            self._player_info[table_id] = {}
        self._player_info[table_id][info.username] = info

    def get_player_info_by_username(self, table_id: int, username: str) -> Optional[PlayerInfo]:
        """usernameからプレイヤー情報を取得"""
        return self._player_info.get(table_id, {}).get(username)

    def get_player_info_by_token(self, table_id: int, token: str) -> Optional[PlayerInfo]:
        """トークンからプレイヤー情報を取得"""
        for info in self._player_info.get(table_id, {}).values():
            if info.token == token:
                return info
        return None

    def remove_table(self, table_id: int):
        """テーブルを削除"""
        with self._table_lock:
            self._tables.pop(table_id, None)
            self._player_info.pop(table_id, None)
            self._hand_numbers.pop(table_id, None)

    def increment_hand_number(self, table_id: int) -> int:
        """ハンド番号をインクリメントして返す"""
        self._hand_numbers[table_id] = self._hand_numbers.get(table_id, 0) + 1
        return self._hand_numbers[table_id]

    def get_hand_number(self, table_id: int) -> int:
        """現在のハンド番号を取得"""
        return self._hand_numbers.get(table_id, 0)

    def sync_to_db(self, table_id: int, state: GameState):
        """テーブル状態をDBに同期"""
        try:
            db_table = PokerTableModel.objects.get(id=table_id)
        except PokerTableModel.DoesNotExist:
            return

        # テーブル状態を更新
        db_table.current_hand_number = self._hand_numbers.get(table_id, 0)
        phase_value = state.phase.value
        if phase_value == 'waiting':
            db_table.status = 'waiting'
        elif phase_value == 'showdown':
            db_table.status = 'waiting'
        else:
            db_table.status = 'playing'
        db_table.save()

        # プレイヤーのチップを更新
        info_map = self._player_info.get(table_id, {})
        for player_state in state.players:
            info = info_map.get(player_state.player_id)
            if not info:
                continue
            try:
                db_player = TablePlayer.objects.get(id=info.db_id)
                db_player.chips = player_state.chips.amount
                db_player.save()
            except TablePlayer.DoesNotExist:
                pass

    def create_game_hand(self, table_id: int, state: GameState) -> Optional[GameHand]:
        """ゲームハンドをDBに作成"""
        try:
            db_table = PokerTableModel.objects.get(id=table_id)
        except PokerTableModel.DoesNotExist:
            return None

        hand_number = self._hand_numbers.get(table_id, 0)
        info_map = self._player_info.get(table_id, {})
        dealer_info = info_map.get(state.dealer_id)
        button_seat = dealer_info.seat_number if dealer_info else 0

        hand = GameHand.objects.create(
            table=db_table,
            hand_number=hand_number,
            button_seat=button_seat,
        )
        return hand

    def update_game_hand(self, hand: GameHand, state: GameState, winner_id: Optional[str] = None):
        """ゲームハンドを更新"""
        from django.utils import timezone

        hand.total_pot = state.pot.amount
        hand.community_cards = [card_to_dict(c)['display'] for c in state.community_cards]

        if winner_id:
            info_map = self._player_info.get(int(state.table_id), {})
            winner_info = info_map.get(winner_id)
            if winner_info:
                hand.winner_seats = [winner_info.seat_number]

        hand.finished_at = timezone.now()
        hand.save()

    def game_state_to_dict(self, table_id: int, state: GameState, db_table=None) -> dict:
        """GameStateをAPI応答用のdictに変換"""
        info_map = self._player_info.get(table_id, {})

        players_data = []
        for ps in state.players:
            info = info_map.get(ps.player_id)
            seat = info.seat_number if info else 0

            player_dict = {
                'seat': seat,
                'username': ps.player_id,
                'chips': ps.chips.amount,
                'current_bet': ps.current_bet.amount,
                'is_folded': ps.folded,
                'is_all_in': ps.is_all_in,
                'is_active': True,
            }

            if ps.hole_cards is not None:
                player_dict['hole_cards'] = [card_to_dict(c) for c in ps.hole_cards]
            else:
                player_dict['hole_cards'] = [{'hidden': True}, {'hidden': True}]

            players_data.append(player_dict)

        # ディーラーの席番号を取得
        dealer_info = info_map.get(state.dealer_id)
        button_seat = dealer_info.seat_number if dealer_info else None

        # 現在のプレイヤーの席番号
        current_player_seat = None
        if state.current_player_id:
            current_info = info_map.get(state.current_player_id)
            if current_info:
                current_player_seat = current_info.seat_number

        result = {
            'table_id': table_id,
            'name': db_table.name if db_table else '',
            'phase': _map_phase(state.phase.value),
            'hand_number': self._hand_numbers.get(table_id, 0),
            'pot': state.pot.amount,
            'current_bet': state.current_bet.amount,
            'community_cards': [card_to_dict(c) for c in state.community_cards],
            'players': players_data,
            'button_seat': button_seat,
            'current_player_seat': current_player_seat,
            'settings': {
                'max_players': 6,
                'small_blind': state.small_blind.amount,
                'big_blind': state.big_blind.amount,
                'ante': 0,
            },
        }

        if db_table:
            result['settings']['max_players'] = db_table.max_players

        return result


# シングルトンインスタンス
table_manager = TableManager()
