from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from poker_domain import (
    Chips, Fold, Check, Call, Bet, Raise,
    GamePhase, EventType, PokerError,
)
from .models import PokerTable as PokerTableModel, TablePlayer, ActionLog as ActionLogModel
from .serializers import (
    PokerTableSerializer, TablePlayerSerializer, JoinTableSerializer,
    ActionSerializer, ActionLogSerializer
)
from .services.table_manager import table_manager, PlayerInfo
from .authentication import get_player_from_request


def _build_action(action_str: str, amount: int, state, username: str):
    """アクション文字列をドメインのActionオブジェクトに変換"""
    if action_str == 'fold':
        return Fold()
    elif action_str == 'check':
        return Check()
    elif action_str == 'call':
        return Call()
    elif action_str == 'bet':
        return Bet(amount=amount)
    elif action_str == 'raise':
        return Raise(amount=amount)
    elif action_str == 'all_in':
        # all_in は新ドメインに直接存在しないため、適切なアクションに変換
        player_state = next(
            (p for p in state.players if p.player_id == username), None
        )
        if not player_state:
            return Fold()
        player_chips = player_state.chips.amount
        player_current_bet = player_state.current_bet.amount
        table_current_bet = state.current_bet.amount

        if table_current_bet == 0:
            return Bet(amount=player_chips)
        else:
            total = player_chips + player_current_bet
            if total > table_current_bet:
                return Raise(amount=total)
            else:
                return Call()
    else:
        raise ValueError(f"Unknown action: {action_str}")


def _extract_winner_id(result):
    """ActionResultからSHOWDOWNイベントの勝者IDを取得"""
    for event in result.events:
        if event.event_type == EventType.SHOWDOWN:
            return event.payload.get('winner_id')
    return None


class PokerTableViewSet(viewsets.ModelViewSet):
    """ポーカーテーブルViewSet"""
    queryset = PokerTableModel.objects.all()
    serializer_class = PokerTableSerializer
    permission_classes = [AllowAny]

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

        # インメモリテーブルに先に追加（DBプレイヤー作成前に行い、復元時の重複を防ぐ）
        table = table_manager.get_or_create_table(db_table.id)
        if table:
            try:
                table.add_player(
                    player_id=username,
                    chips=Chips(db_table.initial_chips),
                )
            except PokerError as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # プレイヤー作成
        player = TablePlayer.objects.create(
            table=db_table,
            username=username,
            seat_number=seat_number,
            chips=db_table.initial_chips,
        )

        # プレイヤー情報を登録
        table_manager.add_player_info(db_table.id, PlayerInfo(
            username=username,
            seat_number=seat_number,
            token=player.token,
            db_id=player.id,
        ))

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
            try:
                table.remove_player(player_id=player.username)
            except PokerError:
                pass
            state = table.get_state()
            table_manager.sync_to_db(db_table.id, state)

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
        viewer_username = None
        if token:
            info = table_manager.get_player_info_by_token(db_table.id, token)
            if info:
                viewer_username = info.username

        state = table.get_state(viewer_player_id=viewer_username)
        state_dict = table_manager.game_state_to_dict(db_table.id, state, db_table)

        # 自分の番なら有効なアクションを追加
        if viewer_username and state.current_player_id == viewer_username:
            state_dict['valid_actions'] = _get_valid_actions_dict(state, viewer_username)

        return Response(state_dict)

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

        try:
            result = table.start_game()
        except PokerError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # ハンド番号をインクリメント
        hand_number = table_manager.increment_hand_number(db_table.id)

        # ゲームハンド作成
        hand = table_manager.create_game_hand(db_table.id, result.state)

        # DB同期
        table_manager.sync_to_db(db_table.id, result.state)

        # viewer用のstate取得
        viewer_state = table.get_state(viewer_player_id=player.username)
        state_dict = table_manager.game_state_to_dict(db_table.id, viewer_state, db_table)

        if viewer_state.current_player_id == player.username:
            state_dict['valid_actions'] = _get_valid_actions_dict(viewer_state, player.username)

        return Response({
            'message': 'Game started',
            'hand_number': hand_number,
            'state': state_dict,
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

        # 現在の状態を取得（all_inの変換に必要）
        current_state = table.get_state(viewer_player_id=player.username)

        # アクションオブジェクトを構築
        try:
            action_obj = _build_action(
                action_str=serializer.validated_data['action'],
                amount=serializer.validated_data.get('amount', 0),
                state=current_state,
                username=player.username,
            )
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # アクション処理
        try:
            result = table.action(player_id=player.username, action=action_obj)
        except PokerError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # DB同期
        table_manager.sync_to_db(db_table.id, result.state)

        # ゲーム終了時（SHOWDOWN）
        if result.state.phase == GamePhase.SHOWDOWN:
            try:
                hand = GameHand.objects.filter(
                    table=db_table,
                    hand_number=table_manager.get_hand_number(db_table.id),
                ).first()
                if hand:
                    winner_id = _extract_winner_id(result)
                    table_manager.update_game_hand(hand, result.state, winner_id)
            except Exception:
                pass

        # viewer用のstate取得
        viewer_state = table.get_state(viewer_player_id=player.username)
        state_dict = table_manager.game_state_to_dict(db_table.id, viewer_state, db_table)

        if viewer_state.current_player_id == player.username:
            state_dict['valid_actions'] = _get_valid_actions_dict(viewer_state, player.username)

        return Response({
            'message': 'Action processed',
            'state': state_dict,
        })

    @action(detail=True, methods=['get'])
    def logs(self, request, pk=None):
        """アクションログ取得"""
        db_table = self.get_object()

        # DBからログ取得
        logs = ActionLogModel.objects.filter(table=db_table).order_by('-created_at')[:100]
        return Response({
            'logs': ActionLogSerializer(logs, many=True).data,
        })


def _get_valid_actions_dict(state, username: str) -> dict:
    """GameStateからvalid_actionsのdictを構築"""
    player_state = next(
        (p for p in state.players if p.player_id == username), None
    )
    if not player_state:
        return {}

    actions = {}
    to_call = state.current_bet.amount - player_state.current_bet.amount
    player_chips = player_state.chips.amount

    actions['fold'] = {}

    if to_call == 0:
        actions['check'] = {}
        actions['bet'] = {'min': state.big_blind.amount, 'max': player_chips}
    else:
        actions['call'] = {'amount': min(to_call, player_chips)}
        min_raise_to = state.current_bet.amount * 2
        if player_chips + player_state.current_bet.amount > state.current_bet.amount:
            actions['raise'] = {
                'min': min(min_raise_to, player_chips + player_state.current_bet.amount),
                'max': player_chips + player_state.current_bet.amount,
            }

    if player_chips > 0:
        actions['all_in'] = {'amount': player_chips}

    return actions


# GameHand のインポート（ファイル内で使用）
from .models import GameHand
