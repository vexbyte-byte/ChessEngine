from engine import engine_process_main
import shared
import multiprocessing as mp

def GetBestMove(board, color, depth=4, time_limit=100.0):
    task_q = mp.Queue()
    user_interrupt_q = mp.Queue()
    result_q = mp.Queue()

    engine_proc = mp.Process(target=engine_process_main, args=(task_q, user_interrupt_q, result_q))
    engine_proc.start()

    # send search task
    task_q.put(("SEARCH", shared.current_board_arrangement.copy(), "black", depth, None)) # You can replace None with time_limit (not recommended, as it causes errors)


    # wait for engine result
    res = result_q.get()  # blocks until engine finishes
    _, from_sq, to_sq, score = res

    print("Engine best:", from_sq, to_sq, "score", score)

    # --- update shared.py board ---
    piece = shared.current_board_arrangement[from_sq]
    shared.current_board_arrangement[to_sq] = piece
    shared.current_board_arrangement[from_sq] = "empty"

    # now shared.current_board_arrangement contains the new board

    # quit engine process
    task_q.put(("QUIT",))
    engine_proc.join()

    return from_sq, to_sq, score

if __name__ == "__main__":
    ...
