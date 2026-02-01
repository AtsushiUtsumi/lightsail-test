from typing import Dict, Optional
from threading import Lock
from ..domain.poker_table import PokerTable
from ..models import PokerTable as PokerTableModel, TablePlayer, GameHand, ActionLog


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
                table_id=db_table.id,
                name=db_table.name,
                max_players=db_table.max_players,
                small_blind=db_table.small_blind,
                big_blind=db_table.big_blind,
                ante=db_table.ante,
                initial_chips=db_table.initial_chips,
                time_limit_seconds=db_table.time_limit_seconds,
            )

            # プレイヤーを復元
            for db_player in db_table.table_players.filter(is_active=True):
                table.add_player(
                    seat=db_player.seat_number,
                    username=db_player.username,
                    chips=db_player.chips,
                    token=db_player.token,
                    db_id=db_player.id,
                )

            self._tables[table_id] = table
            return table

    def get_table(self, table_id: int) -> Optional[PokerTable]:
        """テーブルを取得"""
        return self._tables.get(table_id)

    def remove_table(self, table_id: int):
        """テーブルを削除"""
        with self._table_lock:
            if table_id in self._tables:
                del self._tables[table_id]

    def sync_to_db(self, table: PokerTable):
        """テーブル状態をDBに同期"""
        try:
            db_table = PokerTableModel.objects.get(id=table.table_id)
        except PokerTableModel.DoesNotExist:
            return

        # テーブル状態を更新
        db_table.current_hand_number = table.hand_number
        if table.phase.value == 'waiting':
            db_table.status = 'waiting'
        elif table.phase.value == 'finished':
            db_table.status = 'waiting'  # 次のゲーム待ち
        else:
            db_table.status = 'playing'
        db_table.save()

        # プレイヤーのチップを更新
        for player in table.players.values():
            try:
                db_player = TablePlayer.objects.get(id=player.db_id)
                db_player.chips = player.chips
                db_player.is_active = player.is_active
                db_player.save()
            except TablePlayer.DoesNotExist:
                pass

    def save_action_logs(self, table: PokerTable, hand: Optional[GameHand] = None):
        """アクションログをDBに保存"""
        try:
            db_table = PokerTableModel.objects.get(id=table.table_id)
        except PokerTableModel.DoesNotExist:
            return

        for log in table.action_logs:
            db_player = None
            if log.player_seat:
                player = table.players.get(log.player_seat)
                if player:
                    try:
                        db_player = TablePlayer.objects.get(id=player.db_id)
                    except TablePlayer.DoesNotExist:
                        pass

            ActionLog.objects.create(
                table=db_table,
                hand=hand,
                player=db_player,
                action=log.action,
                amount=log.amount,
                details=log.details,
            )

    def create_game_hand(self, table: PokerTable) -> GameHand:
        """ゲームハンドをDBに作成"""
        try:
            db_table = PokerTableModel.objects.get(id=table.table_id)
        except PokerTableModel.DoesNotExist:
            return None

        hand = GameHand.objects.create(
            table=db_table,
            hand_number=table.hand_number,
            button_seat=table.button_seat,
        )
        return hand

    def update_game_hand(self, hand: GameHand, table: PokerTable):
        """ゲームハンドを更新"""
        from django.utils import timezone

        hand.total_pot = table.pot
        hand.community_cards = [str(c) for c in table.community_cards]

        # 勝者情報
        winners = []
        winning_hand = ''
        for log in table.action_logs:
            if log.action == 'win':
                winners.append(log.player_seat)
                if 'hand' in log.details:
                    winning_hand = log.details['hand']

        hand.winner_seats = winners
        hand.winning_hand = winning_hand
        hand.finished_at = timezone.now()
        hand.save()


# シングルトンインスタンス
table_manager = TableManager()
