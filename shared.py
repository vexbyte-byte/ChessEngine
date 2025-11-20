# shared.py
# This file handles shared variable across 3 other files
# - Chess.py
# - EngineHandler.py
# - Engine.py

# Variables
# ---------
current_board_arrangement = {}   # your board dict (dictionary)

castling_rights = {
    # Initial
    'white_kingside': True,
    'white_queenside': True,
    'black_kingside': True,
    'black_queenside': True,

    # king moved
    'white_king_moved': False,
    'black_king_moved': False,
}

