from django.db import models
from django.contrib.auth.models import User


class PokerTable(models.Model):
    """ポーカーテーブルモデル"""
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    players = models.ManyToManyField(User, related_name='poker_tables')
    max_players = models.IntegerField(default=6)
    
    def __str__(self):
        return self.name
    
    def add_player(self, user):
        """プレイヤーをテーブルに追加"""
        if self.players.count() < self.max_players:
            self.players.add(user)
            return True
        return False
    
    def remove_player(self, user):
        """プレイヤーをテーブルから削除"""
        self.players.remove(user)
