import ctypes
import json
import os
import shared

# Load the DLL
user = os.getlogin()
engine = ctypes.CDLL(fr"C:\Users\{user}\AppData\Local\Python\Chess\engine.dll")

# Define argument types for clarity (optional but safer)
engine.get_best_move_c.argtypes = [
    ctypes.c_char_p,  # board_json
    ctypes.c_char_p,  # color
    ctypes.c_int,     # depth
    ctypes.c_double,  # time_limit #c_double
    ctypes.c_int,     # max_workers
    ctypes.c_char_p,  # move_out
    ctypes.POINTER(ctypes.c_double)  # score_out
]

engine.get_best_move_c.restype = None

def GetBestMove(board_dict, color, depth=4, time_limit=0.0, max_workers=8):
    # Convert Python dict to proper JSON string
    board_json = json.dumps(board_dict)
    
    # Prepare output buffer
    move_out = ctypes.create_string_buffer(32)  # adjust size if needed
    score_out = ctypes.c_double()
    
    # Call the DLL
    engine.get_best_move_c(
        ctypes.c_char_p(board_json.encode('utf-8')),
        ctypes.c_char_p(color.encode('utf-8')),
        ctypes.c_int(depth),
        ctypes.c_double(time_limit),
        ctypes.c_int(max_workers),
        move_out,
        ctypes.byref(score_out)
    )
    
    # Decode the move string (like "E2E4") into from/to squares
    move_str = move_out.value.decode()
    from_sq = move_str[:2]
    to_sq = move_str[2:4]

    piece = shared.current_board_arrangement[from_sq]
    shared.current_board_arrangement[from_sq] = None
    shared.current_board_arrangement[to_sq] = piece
    
    return from_sq, to_sq, score_out.value
