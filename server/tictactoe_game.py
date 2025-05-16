class TicTacToeGame:
    def __init__(self, game_id, player1_uuid, player1_name):
        self.game_id = game_id
        self.board = [['' for _ in range(3)] for _ in range(3)]
        self.players = {
            'X': {'uuid': player1_uuid, 'name': player1_name},
            'O': None
        }
        self.turn = 'X'
        self.status = 'waiting' # waiting, active, finished
        self.winner = None       # 'X', 'O', or None

    def add_player2(self, player2_uuid, player2_name):
        """Adds player 2 to the game and activates it."""
        if self.players['O'] is None:
            self.players['O'] = {'uuid': player2_uuid, 'name': player2_name}
            self.status = 'active'
            print(f"[TicTacToeGame] Player {player2_name} ({player2_uuid}) joined game {self.game_id}. Game status: {self.status}")
            return True
        print(f"[TicTacToeGame] Player {player2_uuid} failed to join game {self.game_id}. Player O slot is occupied.")
        return False

    def get_state(self):
        """Returns the current state of the game for client display."""
        # Note: Player UUIDs are included here, but could be filtered if privacy is a concern.
        return {
            'game_id': self.game_id,
            'board': self.board,
            'turn': self.turn, # Which piece's turn ('X' or 'O')
            'status': self.status,
            'players': {
                'X': self.players['X'] if self.players['X'] else None,
                'O': self.players['O'] if self.players['O'] else None,
            },
            'winner': self.winner # Winning piece ('X' or 'O') or None
        }

    def get_player_piece(self, player_uuid):
        """Gets the piece ('X' or 'O') for a given player UUID in this game."""
        if self.players['X'] and self.players['X']['uuid'] == player_uuid:
            return 'X'
        if self.players['O'] and self.players['O']['uuid'] == player_uuid:
            return 'O'
        return None

    def make_move(self, player_uuid, y, x):
        """Attempts to make a move for a player at a given position."""
        print(f"[TicTacToeGame] Attempting move in game {self.game_id} by {player_uuid} at ({y}, {x})")

        # Basic validation
        if self.status != 'active':
            print(f"[TicTacToeGame] Move rejected - Game status is {self.status}")
            return {"success": False, "reason": "Game is not active"}

        player_piece = self.get_player_piece(player_uuid)
        if not player_piece:
            print(f"[TicTacToeGame] Move rejected - Player {player_uuid} not in game {self.game_id}")
            return {"success": False, "reason": "Player not in game"}
        if player_piece != self.turn:
            print(f"[TicTacToeGame] Move rejected - Not {player_piece}'s turn (Current turn: {self.turn})")
            return {"success": False, "reason": "Not your turn"}

        if not (0 <= y < 3 and 0 <= x < 3):
            print(f"[TicTacToeGame] Move rejected - Invalid position ({y}, {x})")
            return {"success": False, "reason": "Invalid position"}
        if self.board[y][x] != '':
            print(f"[TicTacToeGame] Move rejected - Position ({y}, {x}) already occupied with {self.board[y][x]}")
            return {"success": False, "reason": "Position already occupied"}

        # Make the move
        self.board[y][x] = player_piece
        print(f"[TicTacToeGame] Move accepted - Placed {player_piece} at ({y}, {x}) in game {self.game_id}")

        # Check for end game conditions
        winner = self.check_winner()
        if winner:
            self.winner = winner
            self.status = 'finished'
            print(f"[TicTacToeGame] Game {self.game_id} finished. Winner: {winner}")
            return {
                "success": True,
                "board": self.board,
                "next_turn": None, # Game over, no next turn
                "game_over": True,
                "winner": winner,
                "is_tie": False
            }

        # Check for a tie
        if all(self.board[i][j] != '' for i in range(3) for j in range(3)):
            self.status = 'finished'
            print(f"[TicTacToeGame] Game {self.game_id} finished. Tie game.")
            return {
                "success": True,
                "board": self.board,
                "next_turn": None, # Game over, no next turn
                "game_over": True,
                "winner": None,
                "is_tie": True
            }

        # If game not over, switch turns
        self.turn = 'O' if self.turn == 'X' else 'X'
        print(f"[TicTacToeGame] Turn switched in game {self.game_id}. Next turn: {self.turn}")
        return {
            "success": True,
            "board": self.board,
            "next_turn": self.turn,
            "game_over": False,
            "winner": None,
            "is_tie": False
        }

    def check_winner(self):
        """Checks the board for a winning line."""
        # Check rows
        for i in range(3):
            if self.board[i][0] == self.board[i][1] == self.board[i][2] != '':
                return self.board[i][0]
        # Check columns
        for j in range(3):
            if self.board[0][j] == self.board[1][j] == self.board[2][j] != '':
                return self.board[0][j]
        # Check diagonals
        if self.board[0][0] == self.board[1][1] == self.board[2][2] != '':
            return self.board[0][0]
        if self.board[0][2] == self.board[1][1] == self.board[2][0] != '':
            return self.board[0][2]
        # No winner
        return None
