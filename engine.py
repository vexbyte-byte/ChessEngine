from multiprocessing import Process, Queue

def worker(in_q, out_q):
    while True:
        position = in_q.get()
        if position == "quit":
            break
        out_q.put("bestmove e2e4")

if __name__ == "__main__":
    in_q = Queue()
    out_q = Queue()

    p = Process(target=worker, args=(in_q, out_q))
    p.start()

    in_q.put("some FEN")

    print(out_q.get())

    in_q.put("quit")
    p.join()
