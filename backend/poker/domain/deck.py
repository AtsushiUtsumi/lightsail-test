import random
from dataclasses import dataclass
from typing import List


@dataclass
class Card:
    """トランプカード"""
    SUITS = ['h', 'd', 'c', 's']  # hearts, diamonds, clubs, spades
    RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
    SUIT_NAMES = {'h': 'Hearts', 'd': 'Diamonds', 'c': 'Clubs', 's': 'Spades'}
    RANK_VALUES = {
        '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
        'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14
    }

    rank: str
    suit: str

    def __post_init__(self):
        if self.rank not in self.RANKS:
            raise ValueError(f"Invalid rank: {self.rank}")
        if self.suit not in self.SUITS:
            raise ValueError(f"Invalid suit: {self.suit}")

    @property
    def value(self) -> int:
        return self.RANK_VALUES[self.rank]

    def __str__(self) -> str:
        return f"{self.rank}{self.suit}"

    def __repr__(self) -> str:
        return f"Card('{self.rank}{self.suit}')"

    def __eq__(self, other) -> bool:
        if not isinstance(other, Card):
            return False
        return self.rank == other.rank and self.suit == other.suit

    def __hash__(self) -> int:
        return hash((self.rank, self.suit))

    def to_dict(self) -> dict:
        return {'rank': self.rank, 'suit': self.suit, 'display': str(self)}

    @classmethod
    def from_string(cls, s: str) -> 'Card':
        """文字列からカードを作成 (例: 'Ah' -> Card('A', 'h'))"""
        if len(s) != 2:
            raise ValueError(f"Invalid card string: {s}")
        return cls(rank=s[0], suit=s[1])


class Deck:
    """52枚のトランプデッキ"""

    def __init__(self):
        self.cards: List[Card] = []
        self.reset()

    def reset(self):
        """デッキをリセット"""
        self.cards = [Card(rank=r, suit=s) for s in Card.SUITS for r in Card.RANKS]

    def shuffle(self):
        """シャッフル"""
        random.shuffle(self.cards)

    def deal(self, count: int = 1) -> List[Card]:
        """指定枚数のカードを配る"""
        if count > len(self.cards):
            raise ValueError("Not enough cards in deck")
        dealt = self.cards[:count]
        self.cards = self.cards[count:]
        return dealt

    def deal_one(self) -> Card:
        """1枚配る"""
        return self.deal(1)[0]

    def burn(self):
        """バーンカード（1枚捨てる）"""
        if self.cards:
            self.cards.pop(0)

    def remaining(self) -> int:
        """残りのカード枚数"""
        return len(self.cards)

    def __len__(self) -> int:
        return len(self.cards)
