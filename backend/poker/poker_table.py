class PokerTable:
    def __init__(self, table_id):
        self.table_id = table_id
        self.players = []

    def add_player(self, player):
        self.players.append(player)

    def remove_player(self, player):
        self.players.remove(player)

    def get_player_count(self):
        return len(self.players)