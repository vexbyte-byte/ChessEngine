# engine.py
import multiprocessing as mp
import copy
import time
import math

# ---------------------------
# Utilities: board helpers
# Board format: dict mapping 'A1'..'H8' -> piece names used in your main file
# e.g. 'A2': 'white_pawn', 'E8': 'black_king', 'C3': 'empty'
# ---------------------------

FILES = "ABCDEFGH"
RANKS = "12345678"

def square_to_coords(square):
    col = FILES.index(square[0].upper())
    row = int(square[1]) - 1
    return col, row

def coords_to_square(col, row):
    return FILES[col] + str(row + 1)

def in_bounds_colrow(col, row):
    return 0 <= col <= 7 and 0 <= row <= 7

def copy_board(board):
    # shallow copy is fine since values are strings, but we return a new dict
    return board.copy()

def simulate_move(board, from_sq, to_sq):
    newb = board.copy()
    newb[to_sq] = newb[from_sq]
    newb[from_sq] = "empty"
    return newb

# ---------------------------
# Generate pseudo-legal moves (ignores checks)
# ---------------------------
def rook_moves_from(square, board, color):
    col, row = square_to_coords(square)
    directions = [(0, 1), (0, -1), (-1, 0), (1, 0)]
    moves = []
    for dc, dr in directions:
        c, r = col, row
        while True:
            c += dc; r += dr
            if not in_bounds_colrow(c, r):
                break
            sq = coords_to_square(c, r)
            target = board[sq]
            if target == "empty":
                moves.append(sq)
            elif target.startswith(color):
                break
            else:
                moves.append(sq)
                break
    return moves

def bishop_moves_from(square, board, color):
    col, row = square_to_coords(square)
    directions = [(1, 1), (-1, 1), (-1, -1), (1, -1)]
    moves = []
    for dc, dr in directions:
        c, r = col, row
        while True:
            c += dc; r += dr
            if not in_bounds_colrow(c, r):
                break
            sq = coords_to_square(c, r)
            target = board[sq]
            if target == "empty":
                moves.append(sq)
            elif target.startswith(color):
                break
            else:
                moves.append(sq)
                break
    return moves

def queen_moves_from(square, board, color):
    return rook_moves_from(square, board, color) + bishop_moves_from(square, board, color)

def knight_moves_from(square, board, color):
    col, row = square_to_coords(square)
    offsets = [(2,1),(1,2),(-1,2),(-2,1),(-2,-1),(-1,-2),(1,-2),(2,-1)]
    moves = []
    for dc, dr in offsets:
        c, r = col+dc, row+dr
        if not in_bounds_colrow(c, r): continue
        sq = coords_to_square(c, r)
        target = board[sq]
        if target == "empty" or not target.startswith(color):
            moves.append(sq)
    return moves

def king_moves_from(square, board, color):
    col, row = square_to_coords(square)
    offsets = [(0,1),(0,-1),(1,0),(-1,0),(1,1),(1,-1),(-1,1),(-1,-1)]
    moves = []
    for dc, dr in offsets:
        c, r = col+dc, row+dr
        if not in_bounds_colrow(c, r): continue
        sq = coords_to_square(c, r)
        target = board[sq]
        if target == "empty" or not target.startswith(color):
            moves.append(sq)
    return moves

def pawn_moves_from(square, board, color):
    col, row = square_to_coords(square)
    moves = []
    if color == "white":
        # forward
        if row < 7:
            forward = coords_to_square(col, row+1)
            if board[forward] == "empty":
                moves.append(forward)
                # double-step
                if row == 1:
                    double = coords_to_square(col, row+2)
                    if board[double] == "empty":
                        moves.append(double)
        # captures
        for dc in (-1, 1):
            c = col + dc
            r = row + 1
            if in_bounds_colrow(c, r):
                sq = coords_to_square(c, r)
                if board[sq] != "empty" and board[sq].startswith("black"):
                    moves.append(sq)
    else:
        # black pawns
        if row > 0:
            forward = coords_to_square(col, row-1)
            if board[forward] == "empty":
                moves.append(forward)
                if row == 6:
                    double = coords_to_square(col, row-2)
                    if board[double] == "empty":
                        moves.append(double)
        for dc in (-1, 1):
            c = col + dc
            r = row - 1
            if in_bounds_colrow(c, r):
                sq = coords_to_square(c, r)
                if board[sq] != "empty" and board[sq].startswith("white"):
                    moves.append(sq)
    return moves

def pawn_attacks_from(square, board, color):
    # used for attack detection (separate from pawn_moves_from)
    col, row = square_to_coords(square)
    attacks = []
    if color == "white":
        for dc in (-1, 1):
            c = col + dc; r = row + 1
            if in_bounds_colrow(c, r):
                attacks.append(coords_to_square(c,r))
    else:
        for dc in (-1, 1):
            c = col + dc; r = row - 1
            if in_bounds_colrow(c, r):
                attacks.append(coords_to_square(c,r))
    return attacks

def generate_pseudo_legal_moves(board, color):
    """
    Returns dict: {from_square: [to_square, ...], ...}
    Only basic moves (no en-passant, no castling handling).
    """
    moves = {}
    for sq, piece in board.items():
        if piece == "empty" or not piece.startswith(color):
            continue
        if piece.endswith("rook"):
            to_list = rook_moves_from(sq, board, color)
        elif piece.endswith("knight"):
            to_list = knight_moves_from(sq, board, color)
        elif piece.endswith("bishop"):
            to_list = bishop_moves_from(sq, board, color)
        elif piece.endswith("queen"):
            to_list = queen_moves_from(sq, board, color)
        elif piece.endswith("king"):
            to_list = king_moves_from(sq, board, color)
        elif piece.endswith("pawn"):
            to_list = pawn_moves_from(sq, board, color)
        else:
            to_list = []
        if to_list:
            moves[sq] = to_list
    return moves

# ---------------------------
# Attack & check detection
# ---------------------------
def is_square_attacked(board, square, by_color):
    """
    Is `square` attacked by side `by_color` ('white'/'black')?
    """
    # Pawns
    for attacker_sq, piece in board.items():
        if piece == "empty" or not piece.startswith(by_color):
            continue
        if piece.endswith("pawn"):
            attacks = pawn_attacks_from(attacker_sq, board, by_color)
            if square in attacks:
                return True

    # Knights
    for attacker_sq, piece in board.items():
        if piece == "empty" or not piece.startswith(by_color): continue
        if piece.endswith("knight"):
            if square in knight_moves_from(attacker_sq, board, by_color):
                return True

    # King (adjacent)
    for attacker_sq, piece in board.items():
        if piece == "empty" or not piece.startswith(by_color): continue
        if piece.endswith("king"):
            if square in king_moves_from(attacker_sq, board, by_color):
                return True

    # Sliding: rook/queen orthogonal
    # check four directions
    col0, row0 = square_to_coords(square)
    for dc, dr, attackers in ((0,1,("rook","queen")),(0,-1,("rook","queen")),(-1,0,("rook","queen")),(1,0,("rook","queen"))):
        c, r = col0+dc, row0+dr
        while in_bounds_colrow(c, r):
            sq = coords_to_square(c, r)
            piece = board[sq]
            if piece != "empty":
                if piece.startswith(by_color) and (piece.endswith(attackers[0]) or piece.endswith(attackers[1])):
                    return True
                break
            c += dc; r += dr

    # Sliding: bishop/queen diagonal
    for dc, dr in ((1,1),(1,-1),(-1,1),(-1,-1)):
        c, r = col0+dc, row0+dr
        while in_bounds_colrow(c,r):
            sq = coords_to_square(c,r)
            piece = board[sq]
            if piece != "empty":
                if piece.startswith(by_color) and (piece.endswith("bishop") or piece.endswith("queen")):
                    return True
                break
            c += dc; r += dr

    return False

def find_king_square(board, color):
    target_name = f"{color}_king"
    for sq, piece in board.items():
        if piece == target_name:
            return sq
    return None

def is_in_check(board, color):
    king_sq = find_king_square(board, color)
    if not king_sq:
        # no king? treat as not in check (or could be invalid)
        return False
    opponent = "black" if color == "white" else "white"
    return is_square_attacked(board, king_sq, opponent)

# ---------------------------
# Legal moves (filter pseudo-legal by check)
# ---------------------------
def generate_legal_moves(board, color):
    pseudo = generate_pseudo_legal_moves(board, color)
    legal = {}
    for fr, to_list in pseudo.items():
        legal_targets = []
        for to in to_list:
            newb = simulate_move(board, fr, to)
            if not is_in_check(newb, color):
                legal_targets.append(to)
        if legal_targets:
            legal[fr] = legal_targets
    return legal

# ---------------------------
# Evaluation
# ---------------------------
PIECE_VALUES = {
    'pawn': 100, 'knight': 320, 'bishop': 330, 'rook': 500, 'queen': 900, 'king': 20000
}

def evaluate_board(board, perspective_color):
    """
    Basic static evaluation from perspective_color side.
    Positive means good for perspective_color.
    """
    score = 0
    for sq, piece in board.items():
        if piece == "empty": continue
        parts = piece.split("_", 1)
        if len(parts) != 2: continue
        color_label, ptype = parts
        pval = PIECE_VALUES.get(ptype, 0)
        if color_label == perspective_color:
            score += pval
        else:
            score -= pval
    # small mobility bonus (optional)
    own_moves = sum(len(v) for v in generate_pseudo_legal_moves(board, perspective_color).values())
    opp = "black" if perspective_color == "white" else "white"
    opp_moves = sum(len(v) for v in generate_pseudo_legal_moves(board, opp).values())
    score += 2 * (own_moves - opp_moves)
    return score

# ---------------------------
# Minimax with alpha-beta
# ---------------------------
def minimax(board, maximizing_color, current_color, depth, alpha, beta, stop_event):
    """
    Returns evaluation score from perspective of maximizing_color.
    current_color is side to move in this node.
    """
    if stop_event.is_set():
        # aborted by main thread/user
        return 0

    if depth == 0:
        return evaluate_board(board, maximizing_color)

    legal_moves = generate_legal_moves(board, current_color)
    if not legal_moves:
        # no legal moves: checkmate or stalemate
        if is_in_check(board, current_color):
            # current_color is checkmated -> very bad for current_color
            return -math.inf if current_color == maximizing_color else math.inf
        else:
            return 0  # stalemate -> draw

    if current_color == maximizing_color:
        value = -math.inf
        for fr, tos in legal_moves.items():
            for to in tos:
                if stop_event.is_set():
                    return 0
                nb = simulate_move(board, fr, to)
                score = minimax(nb, maximizing_color, "black" if current_color == "white" else "white", depth-1, alpha, beta, stop_event)
                value = max(value, score)
                alpha = max(alpha, value)
                if alpha >= beta:
                    return value
        return value
    else:
        value = math.inf
        for fr, tos in legal_moves.items():
            for to in tos:
                if stop_event.is_set():
                    return 0
                nb = simulate_move(board, fr, to)
                score = minimax(nb, maximizing_color, "black" if current_color == "white" else "white", depth-1, alpha, beta, stop_event)
                value = min(value, score)
                beta = min(beta, value)
                if alpha >= beta:
                    return value
        return value

# ---------------------------
# Worker task run in separate process per root move
# ---------------------------
def worker_task(from_sq, to_sq, board, maximizing_color, root_depth, return_dict, stop_event):
    """
    Apply the root move, then run minimax for depth-1 (since root move consumes one ply).
    Saves evaluation into return_dict as return_dict["E2E4"] = score
    """
    try:
        # quick abort check
        if stop_event.is_set():
            return
        nb = simulate_move(board, from_sq, to_sq)
        # after root move, it's opponent's turn
        opp = "black" if maximizing_color == "white" else "white"
        score = minimax(nb, maximizing_color, opp, root_depth - 1, -math.inf, math.inf, stop_event)
        if not stop_event.is_set():
            return_dict[f"{from_sq}{to_sq}"] = score
    except Exception as e:
        # ensure worker doesn't crash silently
        return_dict[f"{from_sq}{to_sq}"] = -9999999

# ---------------------------
# Engine search orchestrator
# ---------------------------
def engine_search(board, color, depth, user_move_queue=None, time_limit=None, max_workers=None):
    """
    Run multiprocess search for `color` to `depth` plies.
    - board: dict boarda
    - color: 'white' or 'black' (engine side)
    - depth: integer >= 1 (plies)
    - user_move_queue: mp.Queue-like; if any item appears there, engine will stop and attempt to abort workers
    - time_limit: optional seconds; if exceeded set stop_event
    - max_workers: optional limit for concurrent worker processes (defaults to cpu_count)
    Returns (best_from, best_to, best_score) or (None, None, None) if aborted/no result.
    """
    manager = mp.Manager()
    return_dict = manager.dict()
    stop_event = mp.Event()

    # generate root legal moves for engine side
    legal = generate_legal_moves(board, color)
    roots = []
    for fr, tos in legal.items():
        for to in tos:
            roots.append((fr, to))
    if not roots:
        return None, None, None

    if max_workers is None:
        max_workers = mp.cpu_count()

    processes = []
    # start a process per root move
    for fr, to in roots:
        p = mp.Process(target=worker_task, args=(fr, to, board, color, depth, return_dict, stop_event))
        p.start()
        processes.append(p)

    start_time = time.time()
    try:
        # monitor processes and user interrupt queue
        while True:
            alive = any(p.is_alive() for p in processes)
            if not alive:
                break
            # user interrupt
            if user_move_queue is not None:
                # non-blocking check
                try:
                    # Throws if empty, but use get_nowait
                    user_move = user_move_queue.get_nowait()
                    # If user produced a move, we stop all workers (they consult stop_event)
                    stop_event.set()
                    break
                except Exception:
                    pass
            # time limit
            if time_limit is not None and (time.time() - start_time) > time_limit:
                stop_event.set()
                break
            time.sleep(0.03)
    finally:
        # ensure processes terminate
        for p in processes:
            p.join(timeout=0.1)
            if p.is_alive():
                try:
                    p.terminate()
                except Exception:
                    pass
        # small sleep to let return_dict fill
        time.sleep(0.02)

    # pick best move if any
    if len(return_dict) == 0:
        return None, None, None

    # return best move maximizing engine's evaluation (since evaluate signed to engine side)
    best_key, best_score = max(return_dict.items(), key=lambda kv: kv[1])
    best_from = best_key[:2]
    best_to = best_key[2:4]
    return best_from, best_to, best_score

# ---------------------------
# Engine process wrapper: run in its own process, accept tasks via task_queue, return moves via result_queue
# This allows main script to spawn one engine process and talk to it via Queues.
# Task tuple format: ('SEARCH', board_dict, color, depth)
# Interrupt by sending ('INTERRUPT', user_move_string) on user_move_queue which is forwarded to engine_search
# Result put back as ('RESULT', from_sq, to_sq, score)
# ---------------------------
def engine_process_main(task_queue, user_move_queue, result_queue):
    """
    Loop that waits for a SEARCH task.
    Note: must be started in a separate process from main (use mp.Process(target=engine_process_main, ...))
    """
    while True:
        task = task_queue.get()
        if task is None:
            break
        if not isinstance(task, tuple):
            continue
        cmd = task[0]
        if cmd == "SEARCH":
            _, board, color, depth, time_limit = task
            # We pass the same user_move_queue through so engine_search can monitor it
            from_sq, to_sq, score = engine_search(board, color, depth, user_move_queue=user_move_queue, time_limit=time_limit)
            result_queue.put(("RESULT", from_sq, to_sq, score))
        elif cmd == "QUIT":
            break
        else:
            # unknown commands ignored
            continue

# ---------------------------
# Usage example (main script)
# ---------------------------
# In your main program (chess_game.py) do something like:
#
# from engine import engine_process_main
# import multiprocessing as mp
#
# if __name__ == "__main__":
#     task_q = mp.Queue()
#     user_interrupt_q = mp.Queue()
#     result_q = mp.Queue()
#
#     # spawn engine process (this process will spawn worker processes per root move)
#     engine_proc = mp.Process(target=engine_process_main, args=(task_q, user_interrupt_q, result_q))
#     engine_proc.start()
#
#     # send a search task (board must be a dict in your format)
#     task_q.put(("SEARCH", chessboard.current_board_arrangement.copy(), "black", 4, 10.0))  # depth=4, time_limit=10s
#
#     # Meanwhile main thread can continue: if user inputs a move, forward it to engine to interrupt:
#     # user_interrupt_q.put("E2E4")
#
#     # get result (blocks until engine finishes or result arrives)
#     res = result_q.get()
#     _, from_sq, to_sq, score = res
#     print("Engine best:", from_sq, to_sq, "score", score)
#
#     # tell engine to quit when done
#     task_q.put(("QUIT",))
#     engine_proc.join()
#
# NOTE: On Windows and some Android environments, make sure you spawn the engine process inside
# `if __name__ == "__main__":` guard in your main script.
# ---------------------------
