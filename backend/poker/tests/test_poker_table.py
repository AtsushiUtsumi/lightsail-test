import pytest
from poker_domain import PokerTable, Chips, PokerError, InvalidPlayerError, TableFullError


@pytest.fixture
def poker_table():
    """PokerTableインスタンスを作成するフィクスチャ"""
    return PokerTable(table_id="1", max_players=6)


class TestPokerTableAddPlayer:
    """PokerTableへのプレイヤー追加に関するテスト"""

    def test_add_single_player(self, poker_table):
        """単一のプレイヤーを追加するテスト"""
        poker_table.add_player("Player1", Chips(1000))
        state = poker_table.get_state()
        assert len(state.players) == 1
        assert state.players[0].player_id == "Player1"

    def test_add_multiple_players(self, poker_table):
        """複数のプレイヤーを追加するテスト"""
        poker_table.add_player("Player1", Chips(1000))
        poker_table.add_player("Player2", Chips(1000))
        poker_table.add_player("Player3", Chips(1000))

        state = poker_table.get_state()
        assert len(state.players) == 3
        player_ids = [p.player_id for p in state.players]
        assert "Player1" in player_ids
        assert "Player2" in player_ids
        assert "Player3" in player_ids

    def test_add_same_player_twice(self, poker_table):
        """同じプレイヤーを2回追加すると例外が発生するテスト"""
        poker_table.add_player("Player1", Chips(1000))
        with pytest.raises(InvalidPlayerError):
            poker_table.add_player("Player1", Chips(1000))


class TestPokerTableRemovePlayer:
    """PokerTableからのプレイヤー削除に関するテスト"""

    def test_remove_player(self, poker_table):
        """プレイヤーを削除するテスト"""
        poker_table.add_player("Player1", Chips(1000))
        poker_table.add_player("Player2", Chips(1000))
        state = poker_table.get_state()
        assert len(state.players) == 2

        poker_table.remove_player("Player1")
        state = poker_table.get_state()
        assert len(state.players) == 1
        assert state.players[0].player_id == "Player2"


class TestPokerTableInitialization:
    """PokerTableの初期化に関するテスト"""

    def test_create_poker_table(self, poker_table):
        """PokerTableが正しく作成されることをテスト"""
        state = poker_table.get_state()
        assert state.table_id == "1"
        assert len(state.players) == 0

    def test_multiple_tables(self):
        """複数のPokerTableが独立していることをテスト"""
        table1 = PokerTable(table_id="1")
        table2 = PokerTable(table_id="2")

        table1.add_player("Player1", Chips(1000))
        table2.add_player("Player2", Chips(1000))

        state1 = table1.get_state()
        state2 = table2.get_state()
        assert len(state1.players) == 1
        assert len(state2.players) == 1
        assert state1.players[0].player_id == "Player1"
        assert state2.players[0].player_id == "Player2"
