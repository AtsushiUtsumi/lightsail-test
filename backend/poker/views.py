from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404

from .models import PokerTable as PokerTableModel, TablePlayer, ActionLog as ActionLogModel
from .serializers import (
    PokerTableSerializer, TablePlayerSerializer, JoinTableSerializer,
    ActionSerializer, ActionLogSerializer
)
from .services.table_manager import table_manager
from .authentication import get_player_from_request


class PokerTableViewSet(viewsets.ModelViewSet):
    """ポーカーテーブルViewSet"""
    queryset = PokerTableModel.objects.none()  # DBアクセス無効化（デバッグ用）
    serializer_class = PokerTableSerializer
    permission_classes = [AllowAny]

    def list(self, request, *args, **kwargs):
        """一覧取得（DBアクセス無効化中）"""
        return Response({'message': 'DB access disabled for debugging', 'tables': []})

    def create(self, request, *args, **kwargs):
        """テーブル作成"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        """テーブルに参加"""
        db_table = self.get_object()
        serializer = JoinTableSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data['username']
        seat_number = serializer.validated_data['seat_number']

        # 席番号チェック
        if seat_number > db_table.max_players:
            return Response(
                {'error': f'Seat number must be between 1 and {db_table.max_players}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 席が空いているかチェック
        if TablePlayer.objects.filter(table=db_table, seat_number=seat_number, is_active=True).exists():
            return Response(
                {'error': 'Seat already taken'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ユーザー名重複チェック
        if TablePlayer.objects.filter(table=db_table, username=username, is_active=True).exists():
            return Response(
                {'error': 'Username already taken at this table'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # プレイヤー作成
        player = TablePlayer.objects.create(
            table=db_table,
            username=username,
            seat_number=seat_number,
            chips=db_table.initial_chips,
        )

        # インメモリテーブルに追加
        table = table_manager.get_or_create_table(db_table.id)
        if table:
            table.add_player(
                seat=seat_number,
                username=username,
                chips=player.chips,
                token=player.token,
                db_id=player.id,
            )

        return Response({
            'message': 'Joined successfully',
            'token': player.token,
            'player': TablePlayerSerializer(player).data,
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        """テーブルから退出"""
        db_table = self.get_object()
        player = get_player_from_request(request)

        if not player or player.table_id != db_table.id:
            return Response(
                {'error': 'Not a member of this table'},
                status=status.HTTP_403_FORBIDDEN
            )

        # インメモリテーブルから削除
        table = table_manager.get_table(db_table.id)
        if table:
            table.remove_player(player.seat_number)
            table_manager.sync_to_db(table)

        # DBから削除（非アクティブ化）
        player.is_active = False
        player.save()

        return Response({'message': 'Left the table'})

    @action(detail=True, methods=['get'])
    def state(self, request, pk=None):
        """テーブル状態取得"""
        db_table = self.get_object()
        table = table_manager.get_or_create_table(db_table.id)

        if not table:
            return Response(
                {'error': 'Table not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # トークンがあれば自分のカードも見える
        token = request.headers.get('X-Player-Token')
        state = table.get_state(viewer_token=token)

        return Response(state)

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """ゲーム開始"""
        db_table = self.get_object()
        player = get_player_from_request(request)

        if not player or player.table_id != db_table.id:
            return Response(
                {'error': 'Not a member of this table'},
                status=status.HTTP_403_FORBIDDEN
            )

        table = table_manager.get_or_create_table(db_table.id)
        if not table:
            return Response(
                {'error': 'Table not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        success, message = table.start_game()
        if not success:
            return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)

        # ゲームハンド作成
        hand = table_manager.create_game_hand(table)

        # DB同期
        table_manager.sync_to_db(table)

        return Response({
            'message': message,
            'hand_number': table.hand_number,
            'state': table.get_state(viewer_token=player.token),
        })

    @action(detail=True, methods=['post'], url_path='action')
    def do_action(self, request, pk=None):
        """アクション実行"""
        db_table = self.get_object()
        player = get_player_from_request(request)

        if not player or player.table_id != db_table.id:
            return Response(
                {'error': 'Not a member of this table'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = ActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        table = table_manager.get_or_create_table(db_table.id)
        if not table:
            return Response(
                {'error': 'Table not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # アクション処理
        success, message = table.process_action(
            seat=player.seat_number,
            action=serializer.validated_data['action'],
            amount=serializer.validated_data.get('amount', 0),
        )

        if not success:
            return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)

        # DB同期
        table_manager.sync_to_db(table)

        # ゲーム終了時
        if table.phase.value == 'finished':
            # アクションログを保存
            try:
                from .models import GameHand
                hand = GameHand.objects.filter(
                    table=db_table,
                    hand_number=table.hand_number
                ).first()
                if hand:
                    table_manager.save_action_logs(table, hand)
                    table_manager.update_game_hand(hand, table)
            except Exception:
                pass

        return Response({
            'message': message,
            'state': table.get_state(viewer_token=player.token),
        })

    @action(detail=True, methods=['get'])
    def logs(self, request, pk=None):
        """アクションログ取得"""
        db_table = self.get_object()

        # インメモリログを取得
        table = table_manager.get_table(db_table.id)
        if table:
            return Response({
                'current_hand_logs': table.get_action_logs(),
                'hand_number': table.hand_number,
            })

        # DBからログ取得
        logs = ActionLogModel.objects.filter(table=db_table).order_by('-created_at')[:100]
        return Response({
            'logs': ActionLogSerializer(logs, many=True).data,
        })
