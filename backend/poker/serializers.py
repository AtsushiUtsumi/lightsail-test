from rest_framework import serializers
from .models import PokerTable, TablePlayer, GameHand, ActionLog


class PokerTableSerializer(serializers.ModelSerializer):
    """ポーカーテーブルシリアライザ"""
    player_count = serializers.SerializerMethodField()

    class Meta:
        model = PokerTable
        fields = [
            'id', 'name', 'created_at', 'max_players', 'small_blind',
            'big_blind', 'ante', 'initial_chips', 'time_limit_seconds',
            'allow_mid_entry', 'allow_mid_exit', 'status', 'player_count'
        ]
        read_only_fields = ['id', 'created_at', 'status', 'player_count']

    def get_player_count(self, obj):
        return obj.table_players.filter(is_active=True).count()


class TablePlayerSerializer(serializers.ModelSerializer):
    """テーブルプレイヤーシリアライザ"""

    class Meta:
        model = TablePlayer
        fields = ['id', 'username', 'seat_number', 'chips', 'is_active', 'joined_at']
        read_only_fields = ['id', 'chips', 'is_active', 'joined_at']


class JoinTableSerializer(serializers.Serializer):
    """テーブル参加シリアライザ"""
    username = serializers.CharField(max_length=100)
    seat_number = serializers.IntegerField(min_value=1)


class ActionSerializer(serializers.Serializer):
    """アクションシリアライザ"""
    action = serializers.ChoiceField(choices=[
        'fold', 'check', 'call', 'bet', 'raise', 'all_in'
    ])
    amount = serializers.IntegerField(required=False, default=0)


class ActionLogSerializer(serializers.ModelSerializer):
    """アクションログシリアライザ"""
    player_name = serializers.SerializerMethodField()

    class Meta:
        model = ActionLog
        fields = ['id', 'action', 'player_name', 'amount', 'details', 'created_at']

    def get_player_name(self, obj):
        return obj.player.username if obj.player else 'System'


class GameHandSerializer(serializers.ModelSerializer):
    """ゲームハンドシリアライザ"""

    class Meta:
        model = GameHand
        fields = [
            'id', 'hand_number', 'started_at', 'finished_at',
            'button_seat', 'total_pot', 'community_cards',
            'winner_seats', 'winning_hand'
        ]
