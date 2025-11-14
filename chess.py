# imports
import os
import re
import ast

# define values
red = "\033[91m"
d_green = "\033[32m"
b_green = "\033[92m"
purple = "\033[35m"

class utils():
    def clear_screen():
        try:
            os.system("cls" if os.name == "nt" else "clear")
            print("\033c", end="\033[92m")
        except Exception as e:
            pass

class values():
    # white
    white_pawn = 1
    white_rook = 5
    white_knight = 3
    white_bishop = 3
    white_queen = 9
    # black
    black_pawn = 1
    black_rook = 5
    black_knight = 3
    black_bishop = 3
    black_queen = 9

class legal_move_generator():
    def square_to_coords(square):
        col = ord(square[0].upper()) - ord('A')  # 'A' -> 0, 'B' -> 1 ...
        row = int(square[1]) - 1                 # '1' -> 0, '8' -> 7 ...
        return (col, row)

    def coords_to_square(col, row):
        return chr(col + ord('A')) + str(row + 1)

    def rook_moves(coordinate, board, legal_move_list, piece_name, color):
        col, row = legal_move_generator.square_to_coords(coordinate)
        # directions: up, down, left, right
        directions = [(0, 1), (0, -1), (-1, 0), (1, 0)]

        for dcol, drow in directions:
            c, r = col, row
            while True:
                c += dcol
                r += drow
                if not (0 <= c <= 7 and 0 <= r <= 7):
                    break  # off the board

                target_square = legal_move_generator.coords_to_square(c, r)
                # print(target_square)
                target_piece = board[target_square]
                # print(target_piece) -> pieces possibly to be taken down, eg. black_knight, black_pawn

                # Initialize the list if not already
                legal_move_list.setdefault(coordinate, [])

                if target_piece == "empty":
                    legal_move_list[coordinate].append(target_square)
                elif target_piece.startswith(color):  # block by own piece
                    break
                else:  # opponent piece: can capture
                    legal_move_list[coordinate].append(target_square)
                    break

        return legal_move_list
    
    def knight_moves(coordinate, board, legal_move_list, piece_name, color):
        col, row = legal_move_generator.square_to_coords(coordinate)

        # All 8 possible L-shaped moves
        knight_offsets = [
            (2, 1), (1, 2), (-1, 2), (-2, 1),
            (-2, -1), (-1, -2), (1, -2), (2, -1)
        ]

        for dc, dr in knight_offsets:
            c, r = col + dc, row + dr
            if 0 <= c <= 7 and 0 <= r <= 7:  # on board
                target_square = legal_move_generator.coords_to_square(c, r)
                target_piece = board[target_square]

                # Initialize list if not already
                legal_move_list.setdefault(coordinate, [])

                if target_piece == "empty":
                    legal_move_list[coordinate].append(target_square)
                elif target_piece.startswith(color):  # own piece blocks
                    continue
                else:  # opponent piece can be captured
                    legal_move_list[coordinate].append(target_square)

        return legal_move_list
    
    def bishop_moves(coordinate, board, legal_move_list, piece_name, color):
        col, row = legal_move_generator.square_to_coords(coordinate)
        
        # diagonal directions: top-right, top-left, bottom-left, bottom-right
        directions = [(1, 1), (-1, 1), (-1, -1), (1, -1)]
        
        for dcol, drow in directions:
            c, r = col, row
            while True:
                c += dcol
                r += drow
                if not (0 <= c <= 7 and 0 <= r <= 7):
                    break  # off the board
                
                target_square = legal_move_generator.coords_to_square(c, r)
                target_piece = board[target_square]
                
                # initialize list if not exists
                legal_move_list.setdefault(coordinate, [])
                
                if target_piece == "empty":
                    legal_move_list[coordinate].append(target_square)
                elif target_piece.startswith(color):  # block by own piece
                    break
                else:  # opponent piece can be captured
                    legal_move_list[coordinate].append(target_square)
                    break
                    
        return legal_move_list
    
    def queen_moves(coordinate, board, legal_move_list, piece_name, color):
        col, row = legal_move_generator.square_to_coords(coordinate)
        
        # all 8 directions: rook + bishop
        directions = [
            (0, 1), (0, -1), (-1, 0), (1, 0),  # rook directions
            (1, 1), (-1, 1), (-1, -1), (1, -1)  # bishop directions
        ]
        
        for dcol, drow in directions:
            c, r = col, row
            while True:
                c += dcol
                r += drow
                if not (0 <= c <= 7 and 0 <= r <= 7):
                    break  # off the board
                
                target_square = legal_move_generator.coords_to_square(c, r)
                target_piece = board[target_square]
                
                # initialize list if not exists
                legal_move_list.setdefault(coordinate, [])
                
                if target_piece == "empty":
                    legal_move_list[coordinate].append(target_square)
                elif target_piece.startswith(color):  # block by own piece
                    break
                else:  # opponent piece can be captured
                    legal_move_list[coordinate].append(target_square)
                    break
                    
        return legal_move_list
    
    def king_moves(coordinate, board, legal_move_list, piece_name, color):
        col, row = legal_move_generator.square_to_coords(coordinate)

        # All 8 possible directions
        directions = [
            (0, 1), (0, -1), (-1, 0), (1, 0),     # rook directions
            (1, 1), (-1, 1), (-1, -1), (1, -1)    # bishop directions
        ]

        for dcol, drow in directions:
            c, r = col + dcol, row + drow
            if 0 <= c <= 7 and 0 <= r <= 7:  # on the board
                target_square = legal_move_generator.coords_to_square(c, r)
                target_piece = board[target_square]

                # initialize list if not exists
                legal_move_list.setdefault(coordinate, [])

                if target_piece == "empty":
                    legal_move_list[coordinate].append(target_square)
                elif target_piece.startswith(color):  # own piece blocks
                    continue
                else:  # opponent piece can be captured
                    legal_move_list[coordinate].append(target_square)

        return legal_move_list
    
    def pawn_moves(coordinate, board, legal_move_list, piece_name, color):
        col, row = legal_move_generator.square_to_coords(coordinate)

        legal_move_list.setdefault(coordinate, [])

        if color == "white":
            # one step forward
            if row < 7:
                forward_square = legal_move_generator.coords_to_square(col, row + 1)
                if board[forward_square] == "empty":
                    legal_move_list[coordinate].append(forward_square)

                # two steps forward if on starting rank
                if row == 1:
                    double_forward = legal_move_generator.coords_to_square(col, row + 2)
                    if board[forward_square] == "empty" and board[double_forward] == "empty":
                        legal_move_list[coordinate].append(double_forward)

            # captures
            for dcol in [-1, 1]:
                capture_col = col + dcol
                capture_row = row + 1
                if 0 <= capture_col <= 7 and 0 <= capture_row <= 7:
                    capture_square = legal_move_generator.coords_to_square(capture_col, capture_row)
                    target_piece = board[capture_square]
                    if target_piece != "empty" and target_piece.startswith("black"):
                        legal_move_list[coordinate].append(capture_square)

        elif color == "black":
            # one step forward
            if row > 0:
                forward_square = legal_move_generator.coords_to_square(col, row - 1)
                if board[forward_square] == "empty":
                    legal_move_list[coordinate].append(forward_square)

                # two steps forward if on starting rank
                if row == 6:
                    double_forward = legal_move_generator.coords_to_square(col, row - 2)
                    if board[forward_square] == "empty" and board[double_forward] == "empty":
                        legal_move_list[coordinate].append(double_forward)

            # captures
            for dcol in [-1, 1]:
                capture_col = col + dcol
                capture_row = row - 1
                if 0 <= capture_col <= 7 and 0 <= capture_row <= 7:
                    capture_square = legal_move_generator.coords_to_square(capture_col, capture_row)
                    target_piece = board[capture_square]
                    if target_piece != "empty" and target_piece.startswith("white"):
                        legal_move_list[coordinate].append(capture_square)

        return legal_move_list

class chessboard():
    line_8 = ['A8', 'B8', 'C8', 'D8', 'E8', 'F8', 'G8', 'H8']
    line_7 = ['A7', 'B7', 'C7', 'D7', 'E7', 'F7', 'G7', 'H7']
    line_6 = ['A6', 'B6', 'C6', 'D6', 'E6', 'F6', 'G6', 'H6']
    line_5 = ['A5', 'B5', 'C5', 'D5', 'E5', 'F5', 'G5', 'H5']
    line_4 = ['A4', 'B4', 'C4', 'D4', 'E4', 'F4', 'G4', 'H4']
    line_3 = ['A3', 'B3', 'C3', 'D3', 'E3', 'F3', 'G3', 'H3']
    line_2 = ['A2', 'B2', 'C2', 'D2', 'E2', 'F2', 'G2', 'H2']
    line_1 = ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1', 'H1']

    # initial pieces:
    board_arrangement = {
        'A8': 'black_rook',
        'H8': 'black_rook',
        'B8': 'black_knight',
        'G8': 'black_knight',
        'C8': 'black_bishop',
        'F8': 'black_bishop',
        'D8': 'black_queen',
        'E8': 'black_king',
        'A1': 'white_rook',
        'H1': 'white_rook',
        'B1': 'white_knight',
        'G1': 'white_knight',
        'C1': 'white_bishop',
        'F1': 'white_bishop',
        'D1': 'white_queen',
        'E1': 'white_king',
        'A7': 'black_pawn',
        'A2': 'white_pawn',
        'B7': 'black_pawn',
        'B2': 'white_pawn',
        'C7': 'black_pawn',
        'C2': 'white_pawn',
        'D7': 'black_pawn',
        'D2': 'white_pawn',
        'E7': 'black_pawn',
        'E2': 'white_pawn',
        'F7': 'black_pawn',
        'F2': 'white_pawn',
        'G7': 'black_pawn',
        'G2': 'white_pawn',
        'H7': 'black_pawn',
        'H2': 'white_pawn',
        'A3': 'empty',
        'B3': 'empty',
        'C3': 'empty',
        'D3': 'empty',
        'E3': 'empty',
        'F3': 'empty',
        'G3': 'empty',
        'H3': 'empty',
        'A4': 'empty',
        'B4': 'empty',
        'C4': 'empty',
        'D4': 'empty',
        'E4': 'empty',
        'F4': 'empty',
        'G4': 'empty',
        'H4': 'empty',
        'A5': 'empty',
        'B5': 'empty',
        'C5': 'empty',
        'D5': 'empty',
        'E5': 'empty',
        'F5': 'empty',
        'G5': 'empty',
        'H5': 'empty',
        'A6': 'empty',
        'B6': 'empty',
        'C6': 'empty',
        'D6': 'empty',
        'E6': 'empty',
        'F6': 'empty',
        'G6': 'empty',
        'H6': 'empty',
    }
    
    current_board_arrangement = board_arrangement
    occupied_square = []
    legal_move_list = {}
    
    for coordinate in current_board_arrangement:
        # print(coordinate, current_board_arrangement[coordinate])
        piece_name = current_board_arrangement[coordinate]
        color = "white" if piece_name.startswith("white") else "black"
        # opponent = "black" if color == "white" else "white"
        if piece_name.endswith("rook"):
            legal_move_generator.rook_moves(coordinate, current_board_arrangement, legal_move_list, piece_name, color)
        if piece_name.endswith("knight"):
            legal_move_generator.knight_moves(coordinate, current_board_arrangement, legal_move_list, piece_name, color)
        if piece_name.endswith("bishop"):
            legal_move_generator.bishop_moves(coordinate, current_board_arrangement, legal_move_list, piece_name, color)
        if piece_name.endswith("queen"):
            legal_move_generator.queen_moves(coordinate, current_board_arrangement, legal_move_list, piece_name, color)
        if piece_name.endswith("king"):
            legal_move_generator.king_moves(coordinate, current_board_arrangement, legal_move_list, piece_name, color)
        if piece_name.endswith("pawn"):
            legal_move_generator.pawn_moves(coordinate, current_board_arrangement, legal_move_list, piece_name, color)


    print(legal_move_list)
    quit()

    # mapping pieces to symbols
    symbols = {
        'white_pawn': 'p', 'black_pawn': 'p',
        'white_rook': 'r', 'black_rook': 'r',
        'white_knight': 'h', 'black_knight': 'h',
        'white_bishop': 'b', 'black_bishop': 'b',
        'white_queen': 'q', 'black_queen': 'q',
        'white_king': 'k', 'black_king': 'k',
        'empty': '.'
    }

    board_lines = [line_8, line_7, line_6, line_5, line_4, line_3, line_2, line_1]
    @classmethod
    def interactive_board(cls):
        print(d_green)
        _count = 8
        while True:
            try:
                print("    +---+---+---+---+---+---+---+---+")
                for line in cls.board_lines:
                    row = [cls.symbols[cls.current_board_arrangement[square]] for square in line]
                    print(f" {purple}{_count}{d_green}  |", ' | '.join(row), "|")
                    print("    +---+---+---+---+---+---+---+---+")
                    _count -= 1
                _count = 8
                print(f"{purple}      A   B   C   D   E   F   G   H")

                # input moves
                move = input(f"\n{red}[Enter Your Move] {b_green}> ").upper()
                if re.match(r"^[A-Z]\d[A-Z]\d$", move.replace(" ", "")):
                    print("Pattern matched!")
                    initial_piece_location = move[:2]
                    initial_piece_to_move = chessboard.current_board_arrangement[initial_piece_location]
                    chessboard.current_board_arrangement[initial_piece_location] = "empty"
                    chessboard.current_board_arrangement[move[2:]] = initial_piece_to_move
                else:
                    raise ValueError()
            except Exception as e:
                print(f"{red} Invalid move!", e)
            finally:
                utils.clear_screen()
                print(move)


if __name__ == "__main__":
    utils.clear_screen()
    chessboard.interactive_board()