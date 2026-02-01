import pytest
from poker.poker_table import PokerTable


@pytest.fixture
def poker_table():
    """PokerTableインスタンスを作成するフィクスチャ"""
    return PokerTable(table_id=1)


class TestPokerTableAddPlayer:
    """PokerTableへのプレイヤー追加に関するテスト"""
    
    def test_add_single_player(self, poker_table):
        """単一のプレイヤーを追加するテスト"""
        poker_table.add_player('Player1')
        assert poker_table.get_player_count() == 1
        assert 'Player1' in poker_table.players
    
    def test_add_multiple_players(self, poker_table):
        """複数のプレイヤーを追加するテスト"""
        poker_table.add_player('Player1')
        poker_table.add_player('Player2')
        poker_table.add_player('Player3')
        
        assert poker_table.get_player_count() == 3
        assert 'Player1' in poker_table.players
        assert 'Player2' in poker_table.players
        assert 'Player3' in poker_table.players
    
    def test_add_same_player_twice(self, poker_table):
        """同じプレイヤーを2回追加するテスト"""
        poker_table.add_player('Player1')
        poker_table.add_player('Player1')
        
        assert poker_table.get_player_count() == 2
    
    def test_players_list_order(self, poker_table):
        """プレイヤーのリスト順序をテスト"""
        players = ['Alice', 'Bob', 'Charlie']
        for player in players:
            poker_table.add_player(player)
        
        assert poker_table.players == players


class TestPokerTableRemovePlayer:
    """PokerTableからのプレイヤー削除に関するテスト"""
    
    def test_remove_player(self, poker_table):
        """プレイヤーを削除するテスト"""
        poker_table.add_player('Player1')
        poker_table.add_player('Player2')
        assert poker_table.get_player_count() == 2
        
        poker_table.remove_player('Player1')
        assert poker_table.get_player_count() == 1
        assert 'Player1' not in poker_table.players
        assert 'Player2' in poker_table.players
    
    def test_remove_nonexistent_player(self, poker_table):
        """存在しないプレイヤーを削除しようとするテスト"""
        poker_table.add_player('Player1')
        
        with pytest.raises(ValueError):
            poker_table.remove_player('Player2')
    
    def test_player_count_after_add_and_remove(self, poker_table):
        """プレイヤーの追加と削除後のカウント確認テスト"""
        poker_table.add_player('Player1')
        poker_table.add_player('Player2')
        poker_table.add_player('Player3')
        assert poker_table.get_player_count() == 3
        
        poker_table.remove_player('Player2')
        assert poker_table.get_player_count() == 2
        
        poker_table.remove_player('Player1')
        assert poker_table.get_player_count() == 1


class TestPokerTableInitialization:
    """PokerTableの初期化に関するテスト"""
    
    def test_create_poker_table(self, poker_table):
        """PokerTableが正しく作成されることをテスト"""
        assert poker_table.table_id == 1
        assert poker_table.players == []
        assert poker_table.get_player_count() == 0
    
    def test_multiple_tables(self):
        """複数のPokerTableが独立していることをテスト"""
        table1 = PokerTable(table_id=1)
        table2 = PokerTable(table_id=2)
        
        table1.add_player('Player1')
        table2.add_player('Player2')
        
        assert table1.get_player_count() == 1
        assert table2.get_player_count() == 1
        assert 'Player1' in table1.players
        assert 'Player2' in table2.players
        assert 'Player1' not in table2.players
