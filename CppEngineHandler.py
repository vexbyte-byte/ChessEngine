import ctypes
import json

engine = ctypes.CDLL("./engine.dll")

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

    return from_buf.value.decode(), to_buf.value.decode(), score.value
