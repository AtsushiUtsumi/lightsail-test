from dataclasses import dataclass, field
from typing import List, Optional
from .deck import Card


@dataclass
class Player:
    """ポーカープレイヤー"""
    seat: int
    username: str
    chips: int
    token: str
    db_id: int

    # ゲーム中の状態
    hole_cards: List[Card] = field(default_factory=list)
    current_bet: int = 0
    total_bet_in_hand: int = 0
    is_folded: bool = False
    is_all_in: bool = False
    is_active: bool = True

    def reset_for_new_hand(self):
        """新しいハンドのためにリセット"""
        self.hole_cards = []
        self.current_bet = 0
        self.total_bet_in_hand = 0
        self.is_folded = False
        self.is_all_in = False

    def bet(self, amount: int) -> int:
        """ベットする（チップから引く）"""
        actual_bet = min(amount, self.chips)
        self.chips -= actual_bet
        self.current_bet += actual_bet
        self.total_bet_in_hand += actual_bet
        if self.chips == 0:
            self.is_all_in = True
        return actual_bet

    def fold(self):
        """フォールドする"""
        self.is_folded = True

    def receive_cards(self, cards: List[Card]):
        """カードを受け取る"""
        self.hole_cards = cards

    def win(self, amount: int):
        """ポットを獲得"""
        self.chips += amount

    def can_act(self) -> bool:
        """アクション可能かどうか"""
        return self.is_active and not self.is_folded and not self.is_all_in

    def to_dict(self, show_cards: bool = False) -> dict:
        """辞書形式に変換"""
        data = {
            'seat': self.seat,
            'username': self.username,
            'chips': self.chips,
            'current_bet': self.current_bet,
            'is_folded': self.is_folded,
            'is_all_in': self.is_all_in,
            'is_active': self.is_active,
        }
        if show_cards and self.hole_cards:
            data['hole_cards'] = [c.to_dict() for c in self.hole_cards]
        elif self.hole_cards:
            data['hole_cards'] = [{'hidden': True}] * len(self.hole_cards)
        else:
            data['hole_cards'] = []
        return data
