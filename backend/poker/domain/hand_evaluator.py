from typing import List, Tuple
from itertools import combinations
from .deck import Card


class HandEvaluator:
    """ポーカーハンドの評価"""

    # ハンドランク（高い方が強い）
    HIGH_CARD = 1
    ONE_PAIR = 2
    TWO_PAIR = 3
    THREE_OF_A_KIND = 4
    STRAIGHT = 5
    FLUSH = 6
    FULL_HOUSE = 7
    FOUR_OF_A_KIND = 8
    STRAIGHT_FLUSH = 9
    ROYAL_FLUSH = 10

    HAND_NAMES = {
        HIGH_CARD: 'High Card',
        ONE_PAIR: 'One Pair',
        TWO_PAIR: 'Two Pair',
        THREE_OF_A_KIND: 'Three of a Kind',
        STRAIGHT: 'Straight',
        FLUSH: 'Flush',
        FULL_HOUSE: 'Full House',
        FOUR_OF_A_KIND: 'Four of a Kind',
        STRAIGHT_FLUSH: 'Straight Flush',
        ROYAL_FLUSH: 'Royal Flush',
    }

    @classmethod
    def evaluate(cls, hole_cards: List[Card], community_cards: List[Card]) -> Tuple[int, List[int], str]:
        """
        ホールカードとコミュニティカードから最強のハンドを評価
        Returns: (ハンドランク, キッカー値リスト, ハンド名)
        """
        all_cards = hole_cards + community_cards
        if len(all_cards) < 5:
            return (0, [], 'Not enough cards')

        best_rank = 0
        best_kickers = []
        best_name = ''

        # 全ての5枚の組み合わせを評価
        for five_cards in combinations(all_cards, 5):
            rank, kickers = cls._evaluate_five(list(five_cards))
            if rank > best_rank or (rank == best_rank and kickers > best_kickers):
                best_rank = rank
                best_kickers = kickers
                best_name = cls.HAND_NAMES[rank]

        return (best_rank, best_kickers, best_name)

    @classmethod
    def _evaluate_five(cls, cards: List[Card]) -> Tuple[int, List[int]]:
        """5枚のカードを評価"""
        values = sorted([c.value for c in cards], reverse=True)
        suits = [c.suit for c in cards]

        is_flush = len(set(suits)) == 1
        is_straight, straight_high = cls._is_straight(values)

        # ランク別の枚数をカウント
        value_counts = {}
        for v in values:
            value_counts[v] = value_counts.get(v, 0) + 1

        counts = sorted(value_counts.values(), reverse=True)
        unique_values = sorted(value_counts.keys(), key=lambda x: (value_counts[x], x), reverse=True)

        # ハンド判定
        if is_straight and is_flush:
            if straight_high == 14:
                return (cls.ROYAL_FLUSH, [14])
            return (cls.STRAIGHT_FLUSH, [straight_high])

        if counts == [4, 1]:
            return (cls.FOUR_OF_A_KIND, unique_values)

        if counts == [3, 2]:
            return (cls.FULL_HOUSE, unique_values)

        if is_flush:
            return (cls.FLUSH, values)

        if is_straight:
            return (cls.STRAIGHT, [straight_high])

        if counts == [3, 1, 1]:
            return (cls.THREE_OF_A_KIND, unique_values)

        if counts == [2, 2, 1]:
            return (cls.TWO_PAIR, unique_values)

        if counts == [2, 1, 1, 1]:
            return (cls.ONE_PAIR, unique_values)

        return (cls.HIGH_CARD, values)

    @classmethod
    def _is_straight(cls, values: List[int]) -> Tuple[bool, int]:
        """ストレートかどうか判定"""
        unique_values = sorted(set(values), reverse=True)
        if len(unique_values) != 5:
            return (False, 0)

        # 通常のストレート
        if unique_values[0] - unique_values[4] == 4:
            return (True, unique_values[0])

        # A-2-3-4-5（ホイール）
        if unique_values == [14, 5, 4, 3, 2]:
            return (True, 5)

        return (False, 0)

    @classmethod
    def compare_hands(cls, hand1: Tuple[int, List[int], str],
                      hand2: Tuple[int, List[int], str]) -> int:
        """
        2つのハンドを比較
        Returns: 1 if hand1 wins, -1 if hand2 wins, 0 if tie
        """
        rank1, kickers1, _ = hand1
        rank2, kickers2, _ = hand2

        if rank1 > rank2:
            return 1
        if rank1 < rank2:
            return -1

        # 同じランクならキッカーで比較
        for k1, k2 in zip(kickers1, kickers2):
            if k1 > k2:
                return 1
            if k1 < k2:
                return -1

        return 0

    @classmethod
    def find_winners(cls, players_hands: List[Tuple[int, Tuple[int, List[int], str]]]) -> List[int]:
        """
        複数プレイヤーから勝者を決定
        Args: [(seat, (rank, kickers, name)), ...]
        Returns: 勝者のシート番号リスト（タイの場合は複数）
        """
        if not players_hands:
            return []

        best_hand = None
        winners = []

        for seat, hand in players_hands:
            if best_hand is None:
                best_hand = hand
                winners = [seat]
            else:
                comparison = cls.compare_hands(hand, best_hand)
                if comparison > 0:
                    best_hand = hand
                    winners = [seat]
                elif comparison == 0:
                    winners.append(seat)

        return winners
