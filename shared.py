# shared.py
# This file handles shared variable across 3 other files
# - Chess.py
# - EngineHandler.py
# - Engine.py

# Variables
# ---------
current_board_arrangement = {}   # your board dict (dictionary)
last_user_move = None
engine_result = None

castling_rights = {
    # Initial
    'white_kingside': True,
    'white_queenside': True,
    'black_kingside': True,
    'black_queenside': True,

    # king moved
    'white_king_moved': False,
    'black_king_moved': False,

    # rook moved
    # 'white_rook_1_moved': False,
    # 'black_rook_1_moved': False,
    # 'white_rook_2_moved': False,
    # 'black_rook_2_moved': False,

    # attacked coordinates
    # 'white_kingside_attacked': [''],
}

