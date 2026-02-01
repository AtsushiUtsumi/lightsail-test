from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import TablePlayer


class PlayerTokenAuthentication(BaseAuthentication):
    """プレイヤートークン認証"""

    def authenticate(self, request):
        token = request.headers.get('X-Player-Token')
        if not token:
            return None  # 認証なし（匿名アクセス）

        try:
            player = TablePlayer.objects.get(token=token, is_active=True)
        except TablePlayer.DoesNotExist:
            raise AuthenticationFailed('Invalid token')

        # request.playerとしてアクセス可能にする
        request.player = player
        return (player, token)


def get_player_from_request(request):
    """リクエストからプレイヤーを取得"""
    token = request.headers.get('X-Player-Token')
    if not token:
        return None

    try:
        return TablePlayer.objects.get(token=token, is_active=True)
    except TablePlayer.DoesNotExist:
        return None
