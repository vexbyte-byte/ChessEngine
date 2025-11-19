# engine.py
import shared
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


# ---------------------------
# Castling helpers
# ---------------------------

def infer_castling_rights_from_board(board):
    """Infer simple castling rights from piece placement: if king and rook are on their
    original squares, we assume the right exists. This is a best-effort fallback if the
    caller doesn't supply explicit rights.
    """
    rights = {"white": {"K": False, "Q": False}, "black": {"K": False, "Q": False}}
    if board.get("E1") == "white_king":
        if board.get("H1") == "white_rook":
            rights["white"]["K"] = True
        if board.get("A1") == "white_rook":
            rights["white"]["Q"] = True
    if board.get("E8") == "black_king":
        if board.get("H8") == "black_rook":
            rights["black"]["K"] = True
        if board.get("A8") == "black_rook":
            rights["black"]["Q"] = True
    return rights


# ---------------------------
# Moves & simulation
# ---------------------------

def simulate_move(board, from_sq, to_sq, castling_rights=None):
    """
    Apply move and return (new_board, new_castling_rights).
    Handles castling rook moves and updates castling rights when king/rook moves.
    NOTE: board is not modified in-place.
    """
    newb = board.copy()
    piece = newb[from_sq]

    # default rights copy
    new_rights = None
    if castling_rights is None:
        new_rights = infer_castling_rights_from_board(board)
    else:
        # shallow copy of nested dict
        new_rights = {s: dict(castling_rights.get(s, {})) for s in ("white", "black")}

    # move piece
    newb[to_sq] = piece
    newb[from_sq] = "empty"

    # handle castling rook relocation
    if piece.endswith("king"):
        # white
        if piece == "white_king":
            # king-side
            if from_sq == "E1" and to_sq == "G1":
                # move rook H1 -> F1
                newb["H1"] = "empty"
                newb["F1"] = "white_rook"
            # queen-side
            elif from_sq == "E1" and to_sq == "C1":
                newb["A1"] = "empty"
                newb["D1"] = "white_rook"
            # moving king revokes both rights
            new_rights["white"]["K"] = False
            new_rights["white"]["Q"] = False
        # black
        elif piece == "black_king":
            if from_sq == "E8" and to_sq == "G8":
                newb["H8"] = "empty"
                newb["F8"] = "black_rook"
            elif from_sq == "E8" and to_sq == "C8":
                newb["A8"] = "empty"
                newb["D8"] = "black_rook"
            new_rights["black"]["K"] = False
            new_rights["black"]["Q"] = False

    # if a rook moved (or was captured), revoke corresponding rook-side rights
    if piece.endswith("rook"):
        if piece == "white_rook":
            if from_sq == "H1":
                new_rights["white"]["K"] = False
            elif from_sq == "A1":
                new_rights["white"]["Q"] = False
        elif piece == "black_rook":
            if from_sq == "H8":
                new_rights["black"]["K"] = False
            elif from_sq == "A8":
                new_rights["black"]["Q"] = False

    # If a rook was captured on its original square, clear that right too
    # (to cover capture-by-en-passant or other subtleties - conservative)
    # Check destination square: if we captured an opponent rook on A1/H1/A8/H8, clear
    captured_sq = to_sq
    # We replaced to_sq above, but we can check the original board for a rook there
    orig_target = board.get(to_sq)
    if orig_target == "white_rook":
        if to_sq == "H1":
            new_rights["white"]["K"] = False
        elif to_sq == "A1":
            new_rights["white"]["Q"] = False
    elif orig_target == "black_rook":
        if to_sq == "H8":
            new_rights["black"]["K"] = False
        elif to_sq == "A8":
            new_rights["black"]["Q"] = False

    return newb, new_rights


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


def king_moves_from(square, board, color, castling_rights=None):
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

    # Castling: only include if castling_rights provided (so attack checks can be applied elsewhere)
    if castling_rights is not None:
        opponent = "black" if color == "white" else "white"
        # white
        if color == "white":
            # king-side
            if castling_rights.get("white", {}).get("K"):
                if board.get("F1") == "empty" and board.get("G1") == "empty":
                    # NOTE: attack checks (E1,F1,G1) must be performed by caller before declaring legal
                    moves.append("G1")
            # queen-side
            if castling_rights.get("white", {}).get("Q"):
                if board.get("B1") == "empty" and board.get("C1") == "empty" and board.get("D1") == "empty":
                    moves.append("C1")
        else:
            # black
            if castling_rights.get("black", {}).get("K"):
                if board.get("F8") == "empty" and board.get("G8") == "empty":
                    moves.append("G8")
            if castling_rights.get("black", {}).get("Q"):
                if board.get("B8") == "empty" and board.get("C8") == "empty" and board.get("D8") == "empty":
                    moves.append("C8")

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


def generate_pseudo_legal_moves(board, color, castling_rights=None):
    """
    Returns dict: {from_square: [to_square, ...], ...}
    Only basic moves (en-passant still not implemented). Castling pseudo-moves are included
    when castling_rights is provided; callers must still filter by attack squares to make them legal.
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
            to_list = king_moves_from(sq, board, color, castling_rights)
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

    # King (adjacent) -- use king_moves_from without castling rights so castling squares aren't considered
    for attacker_sq, piece in board.items():
        if piece == "empty" or not piece.startswith(by_color): continue
        if piece.endswith("king"):
            if square in king_moves_from(attacker_sq, board, by_color):
                return True

    # Sliding: rook/queen orthogonal
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

def generate_legal_moves(board, color, castling_rights=None):
    pseudo = generate_pseudo_legal_moves(board, color, castling_rights)
    legal = {}
    for fr, to_list in pseudo.items():
        legal_targets = []
        for to in to_list:
            nb, new_rights = simulate_move(board, fr, to, castling_rights)
            # when castling pseudo-move was included we must ensure the king doesn't pass through or land on attacked squares
            if board.get(fr) and board[fr].endswith("king") and castling_rights is not None:
                # Only need to check castling-specific squares if move is castling
                # white
                if fr == "E1" and to == "G1":
                    if is_square_attacked(board, "E1", "black") or is_square_attacked(board, "F1", "black") or is_square_attacked(board, "G1", "black"):
                        continue
                if fr == "E1" and to == "C1":
                    if is_square_attacked(board, "E1", "black") or is_square_attacked(board, "D1", "black") or is_square_attacked(board, "C1", "black"):
                        continue
                # black
                if fr == "E8" and to == "G8":
                    if is_square_attacked(board, "E8", "white") or is_square_attacked(board, "F8", "white") or is_square_attacked(board, "G8", "white"):
                        continue
                if fr == "E8" and to == "C8":
                    if is_square_attacked(board, "E8", "white") or is_square_attacked(board, "D8", "white") or is_square_attacked(board, "C8", "white"):
                        continue

            if not is_in_check(nb, color):
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

def minimax(board, maximizing_color, current_color, depth, alpha, beta, stop_event, castling_rights=None):
    """
    Returns evaluation score from perspective of maximizing_color.
    current_color is side to move in this node.
    castling_rights is the rights for the current board state and will be updated when moves are simulated.
    """
    if stop_event.is_set():
        # aborted by main thread/user
        return 0

    if depth == 0:
        return evaluate_board(board, maximizing_color)

    legal_moves = generate_legal_moves(board, current_color, castling_rights)
    if not legal_moves:
        # no legal moves: checkmate or stalemate
        if is_in_check(board, current_color):
            # current_color is checkmated -> very bad for current_color
            return -math.inf if current_color == maximizing_color else math.inf
        else:
            return 0  # stalemate -> draw

    next_color = "black" if current_color == "white" else "white"

    if current_color == maximizing_color:
        value = -math.inf
        for fr, tos in legal_moves.items():
            for to in tos:
                if stop_event.is_set():
                    return 0
                nb, new_rights = simulate_move(board, fr, to, castling_rights)
                score = minimax(nb, maximizing_color, next_color, depth-1, alpha, beta, stop_event, castling_rights=new_rights)
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
                nb, new_rights = simulate_move(board, fr, to, castling_rights)
                score = minimax(nb, maximizing_color, next_color, depth-1, alpha, beta, stop_event, castling_rights=new_rights)
                value = min(value, score)
                beta = min(beta, value)
                if alpha >= beta:
                    return value
        return value


# worker_task (selective-stop version)
def worker_task(from_sq, to_sq, board, maximizing_color, root_depth, return_dict, worker_stop_event, master_stop_event, castling_rights=None):
    """
    Apply the root move, then run minimax for depth-1.
    Worker listens to two events:
      - worker_stop_event: this worker-only event (set by engine_search when user chooses a different move)
      - master_stop_event: global (time limit / full abort)
    """
    try:
        # quick abort checks
        if worker_stop_event.is_set() or master_stop_event.is_set():
            return
        nb, new_rights = simulate_move(board, from_sq, to_sq, castling_rights)
        # after root move, it's opponent's turn
        opp = "black" if maximizing_color == "white" else "white"
        score = minimax(nb, maximizing_color, opp, root_depth - 1, -math.inf, math.inf,
                        stop_event=master_stop_event, castling_rights=new_rights)
        # worker_stop_event might have been set while minimax was running; ensure not storing stale results
        if not worker_stop_event.is_set() and not master_stop_event.is_set():
            return_dict[f"{from_sq}{to_sq}"] = score
    except Exception:
        # don't crash the worker silently; store a low score to mark failure
        return_dict[f"{from_sq}{to_sq}"] = -9999999


# engine_search (selective termination)
def engine_search(board, color, depth, user_move_queue=None, time_limit=None, max_workers=None, castling_rights=None):
    """
    Multiprocess search that supports selective termination.
    castling_rights (optional): dict as produced by infer_castling_rights_from_board or your game controller.
    """
    manager = mp.Manager()
    return_dict = manager.dict()
    master_stop_event = mp.Event()   # global (time limit / full abort)

    if castling_rights is None:
        castling_rights = infer_castling_rights_from_board(board)

    # generate root legal moves for engine side
    legal = generate_legal_moves(board, color, castling_rights)
    roots = []
    for fr, tos in legal.items():
        for to in tos:
            roots.append((fr, to))
    if not roots:
        return None, None, None

    if max_workers is None:
        max_workers = mp.cpu_count()

    # Start processes with their own worker_stop_event
    processes = []               # list of Process
    worker_events = {}           # move_key -> Event
    proc_map = {}                # move_key -> Process

    for fr, to in roots:
        move_key = f"{fr}{to}"
        worker_stop_event = mp.Event()
        p = mp.Process(
            target=worker_task,
            args=(fr, to, board, color, depth, return_dict, worker_stop_event, master_stop_event, castling_rights)
        )
        p.start()
        processes.append(p)
        worker_events[move_key] = worker_stop_event
        proc_map[move_key] = p

    start_time = time.time()
    try:
        # monitor processes and user interrupt queue
        while True:
            alive = any(p.is_alive() for p in processes)
            if not alive:
                break

            # user interrupt: selective stop logic
            if user_move_queue is not None:
                try:
                    user_move = user_move_queue.get_nowait()  # non-blocking
                    if user_move is not None:
                        # normalize input (expect "E2E4")
                        user_move_str = user_move.strip().upper()
                        # If this user_move matches exactly one root worker, stop all others
                        if user_move_str in worker_events:
                            # stop every worker except the one matching user_move_str
                            for key, evt in worker_events.items():
                                if key != user_move_str:
                                    evt.set()
                            # continue to wait for the matching worker (or timeout)
                        else:
                            # user move doesn't match any root – abort all workers (safe)
                            master_stop_event.set()
                except Exception:
                    pass

            # time limit
            if time_limit is not None and (time.time() - start_time) > time_limit:
                master_stop_event.set()
                break

            time.sleep(0.03)
    finally:
        # ensure processes terminate
        for key, p in proc_map.items():
            p.join(timeout=0.1)
            if p.is_alive():
                try:
                    p.terminate()
                except Exception:
                    pass
        # give small window for return_dict writes to flush
        time.sleep(0.02)

    # choose best available result
    if len(return_dict) == 0:
        return None, None, None

    best_key, best_score = max(return_dict.items(), key=lambda kv: kv[1])
    best_from = best_key[:2]
    best_to = best_key[2:4]
    return best_from, best_to, best_score


# ---------------------------
# Engine process wrapper: run in its own process, accept tasks via task_queue, return moves via result_queue
# Task tuple format: ('SEARCH', board_dict, color, depth, time_limit [, castling_rights])
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
            # support two formats: with or without castling_rights
            if len(task) >= 6:
                _, board, color, depth, time_limit, castling_rights = task
            else:
                _, board, color, depth, time_limit = task
                castling_rights = infer_castling_rights_from_board(board)
            # We pass the same user_move_queue through so engine_search can monitor it
            from_sq, to_sq, score = engine_search(board, color, depth, user_move_queue=user_move_queue, time_limit=time_limit, castling_rights=castling_rights)
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
#     # send a search task. Optionally include castling rights as 6th element:
#     # task_q.put(("SEARCH", chessboard.current_board_arrangement.copy(), "black", 4, 10.0, castling_rights_dict))
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
