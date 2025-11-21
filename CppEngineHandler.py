import ctypes
import json
import shared
import os

user = os.getlogin()
engine = ctypes.CDLL(fr"C:\Users\{user}\AppData\Local\Python\Chess\engine.dll")

engine.get_best_move.argtypes = [
    ctypes.c_char_p,
    ctypes.c_char_p,
    ctypes.c_int,
    ctypes.c_char_p,
    ctypes.c_char_p,
    ctypes.POINTER(ctypes.c_double)
]

engine.get_best_move.restype = None

def GetBestMove(board, color, depth=4):
    board_json = json.dumps(board).encode()

    from_buf = ctypes.create_string_buffer(10)
    to_buf = ctypes.create_string_buffer(10)
    score = ctypes.c_double()

    engine.get_best_move(
        board_json,
        color.encode(),
        depth,
        from_buf,
        to_buf,
        ctypes.byref(score)
    )

    from_sq = from_buf.value.decode()
    to_sq = to_buf.value.decode()

    # --- update shared.py board ---
    print(from_sq)
    print(to_sq)
    piece = shared.current_board_arrangement[from_sq]
    shared.current_board_arrangement[to_sq] = piece
    shared.current_board_arrangement[from_sq] = "empty"

    return from_sq, to_sq, score.value
