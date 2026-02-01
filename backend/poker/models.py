from django.db import models
import secrets


class PokerTable(models.Model):
    """ポーカーテーブルモデル"""
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    max_players = models.IntegerField(default=6)
    small_blind = models.IntegerField(default=10)
    big_blind = models.IntegerField(default=20)
    ante = models.IntegerField(default=0)
    initial_chips = models.IntegerField(default=1000)
    time_limit_seconds = models.IntegerField(default=30)
    allow_mid_entry = models.BooleanField(default=True)
    allow_mid_exit = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    # ゲーム状態
    STATUS_CHOICES = [
        ('waiting', '待機中'),
        ('playing', 'プレイ中'),
        ('finished', '終了'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting')
    current_hand_number = models.IntegerField(default=0)

    def __str__(self):
        return self.name


class TablePlayer(models.Model):
    """テーブルに参加しているプレイヤー"""
    table = models.ForeignKey(PokerTable, on_delete=models.CASCADE, related_name='table_players')
    username = models.CharField(max_length=100)
    seat_number = models.IntegerField()
    chips = models.IntegerField(default=1000)
    token = models.CharField(max_length=64, unique=True)
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['table', 'seat_number'], ['table', 'username']]

    def __str__(self):
        return f"{self.username} at {self.table.name} (seat {self.seat_number})"

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_hex(32)
        if not self.chips:
            self.chips = self.table.initial_chips
        super().save(*args, **kwargs)


class GameHand(models.Model):
    """1ハンド（1ゲーム）の記録"""
    table = models.ForeignKey(PokerTable, on_delete=models.CASCADE, related_name='hands')
    hand_number = models.IntegerField()
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    # ボタン位置
    button_seat = models.IntegerField()

    # ポット情報
    total_pot = models.IntegerField(default=0)

    # コミュニティカード（JSON形式）
    community_cards = models.JSONField(default=list)

    # 勝者情報
    winner_seats = models.JSONField(default=list)
    winning_hand = models.CharField(max_length=100, blank=True)

    class Meta:
        unique_together = ['table', 'hand_number']

    def __str__(self):
        return f"Hand #{self.hand_number} at {self.table.name}"


class ActionLog(models.Model):
    """アクションログ"""
    ACTION_CHOICES = [
        ('join', '参加'),
        ('leave', '退出'),
        ('post_blind', 'ブラインド'),
        ('post_ante', 'アンティ'),
        ('fold', 'フォールド'),
        ('check', 'チェック'),
        ('call', 'コール'),
        ('bet', 'ベット'),
        ('raise', 'レイズ'),
        ('all_in', 'オールイン'),
        ('deal', '配布'),
        ('showdown', 'ショーダウン'),
        ('win', '勝利'),
    ]

    table = models.ForeignKey(PokerTable, on_delete=models.CASCADE, related_name='action_logs')
    hand = models.ForeignKey(GameHand, on_delete=models.CASCADE, related_name='actions', null=True, blank=True)
    player = models.ForeignKey(TablePlayer, on_delete=models.SET_NULL, null=True, blank=True, related_name='actions')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    amount = models.IntegerField(default=0)
    details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        player_name = self.player.username if self.player else 'System'
        return f"{player_name}: {self.action} ({self.amount})"
