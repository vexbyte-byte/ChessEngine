# chess.py
import os
import re
import json
import ctypes
# import shared
import pygame
import threading
# from CppEngineHandler import GetBestMove

red = "\033[91m"
d_green = "\033[32m"
b_green = "\033[92m"
purple = "\033[35m"
yellow = "\033[93m"
reset = "\033[0m"

class utils():
    def clear_screen():
        try:
            os.system("cls" if os.name == "nt" else "clear")
            print("\033c", end=b_green)
        except Exception as e: pass

class values():
    # self values
    depth = 4
    bot_from_square = None
    bot_to_square = None
    after_en_passant = None

    # other values
    white_pawn = 1
    white_rook = 5
    white_knight = 3
    white_bishop = 3
    white_queen = 9
    black_pawn = 1
    black_rook = 5
    black_knight = 3
    black_bishop = 3
    black_queen = 9

class legal_move_generator():
    @staticmethod
    def square_to_coords(square):
        col = ord(square[0].upper()) - ord('A')
        row = int(square[1]) - 1
        return (col, row)

    @staticmethod
    def coords_to_square(col, row):
        return chr(col + ord('A')) + str(row + 1)

    @staticmethod
    def rook_moves(coordinate, board, legal_move_list, piece_name, color):
        col, row = legal_move_generator.square_to_coords(coordinate)
        directions = [(0, 1), (0, -1), (-1, 0), (1, 0)]

        for dcol, drow in directions:
            c, r = col, row
            while True:
                c += dcol
                r += drow
                if not (0 <= c <= 7 and 0 <= r <= 7):
                    break

                target_square = legal_move_generator.coords_to_square(c, r)
                target_piece = board[target_square]
                legal_move_list.setdefault(coordinate, [])

                if target_piece == "empty":
                    legal_move_list[coordinate].append(target_square)
                elif target_piece.startswith(color):
                    break
                else:
                    legal_move_list[coordinate].append(target_square)
                    break

        return legal_move_list
    
    @staticmethod
    def knight_moves(coordinate, board, legal_move_list, piece_name, color):
        col, row = legal_move_generator.square_to_coords(coordinate)
        knight_offsets = [
            (2, 1), (1, 2), (-1, 2), (-2, 1),
            (-2, -1), (-1, -2), (1, -2), (2, -1)
        ]

        for dc, dr in knight_offsets:
            c, r = col + dc, row + dr
            if 0 <= c <= 7 and 0 <= r <= 7:
                target_square = legal_move_generator.coords_to_square(c, r)
                target_piece = board[target_square]
                legal_move_list.setdefault(coordinate, [])

                if target_piece == "empty":
                    legal_move_list[coordinate].append(target_square)
                elif target_piece.startswith(color):
                    continue
                else:
                    legal_move_list[coordinate].append(target_square)

        return legal_move_list
    
    @staticmethod
    def bishop_moves(coordinate, board, legal_move_list, piece_name, color):
        col, row = legal_move_generator.square_to_coords(coordinate)
        directions = [(1, 1), (-1, 1), (-1, -1), (1, -1)]
        
        for dcol, drow in directions:
            c, r = col, row
            while True:
                c += dcol
                r += drow
                if not (0 <= c <= 7 and 0 <= r <= 7):
                    break
                
                target_square = legal_move_generator.coords_to_square(c, r)
                target_piece = board[target_square]
                legal_move_list.setdefault(coordinate, [])
                
                if target_piece == "empty":
                    legal_move_list[coordinate].append(target_square)
                elif target_piece.startswith(color):
                    break
                else:
                    legal_move_list[coordinate].append(target_square)
                    break
                    
        return legal_move_list
    
    @staticmethod
    def queen_moves(coordinate, board, legal_move_list, piece_name, color):
        col, row = legal_move_generator.square_to_coords(coordinate)
        directions = [
            (0, 1), (0, -1), (-1, 0), (1, 0),
            (1, 1), (-1, 1), (-1, -1), (1, -1)
        ]
        
        for dcol, drow in directions:
            c, r = col, row
            while True:
                c += dcol
                r += drow
                if not (0 <= c <= 7 and 0 <= r <= 7):
                    break
                
                target_square = legal_move_generator.coords_to_square(c, r)
                target_piece = board[target_square]
                legal_move_list.setdefault(coordinate, [])
                
                if target_piece == "empty":
                    legal_move_list[coordinate].append(target_square)
                elif target_piece.startswith(color):
                    break
                else:
                    legal_move_list[coordinate].append(target_square)
                    break
                    
        return legal_move_list
    
    @staticmethod
    def king_moves(coordinate, board, legal_move_list, piece_name, color):
        col, row = legal_move_generator.square_to_coords(coordinate)
        directions = [
            (0, 1), (0, -1), (-1, 0), (1, 0),
            (1, 1), (-1, 1), (-1, -1), (1, -1)
        ]

        for dcol, drow in directions:
            c, r = col + dcol, row + drow
            if 0 <= c <= 7 and 0 <= r <= 7:
                target_square = legal_move_generator.coords_to_square(c, r)
                target_piece = board[target_square]
                legal_move_list.setdefault(coordinate, [])

                if target_piece == "empty":
                    legal_move_list[coordinate].append(target_square)
                elif target_piece.startswith(color):
                    continue
                else:
                    legal_move_list[coordinate].append(target_square)

        return legal_move_list
    
    @staticmethod
    def pawn_moves(coordinate, board, legal_move_list, piece_name, color):
        col, row = legal_move_generator.square_to_coords(coordinate)
        legal_move_list.setdefault(coordinate, [])

        if color == "white":
            if row < 7:
                forward_square = legal_move_generator.coords_to_square(col, row + 1)
                if board[forward_square] == "empty":
                    legal_move_list[coordinate].append(forward_square)

                if row == 1:
                    double_forward = legal_move_generator.coords_to_square(col, row + 2)
                    if board[forward_square] == "empty" and board[double_forward] == "empty":
                        legal_move_list[coordinate].append(double_forward)

            for dcol in [-1, 1]:
                capture_col = col + dcol
                capture_row = row + 1
                if 0 <= capture_col <= 7 and 0 <= capture_row <= 7:
                    capture_square = legal_move_generator.coords_to_square(capture_col, capture_row)
                    target_piece = board[capture_square]
                    if target_piece != "empty" and target_piece.startswith("black"):
                        legal_move_list[coordinate].append(capture_square)

        elif color == "black":
            if row > 0:
                forward_square = legal_move_generator.coords_to_square(col, row - 1)
                if board[forward_square] == "empty":
                    legal_move_list[coordinate].append(forward_square)

                if row == 6:
                    double_forward = legal_move_generator.coords_to_square(col, row - 2)
                    if board[forward_square] == "empty" and board[double_forward] == "empty":
                        legal_move_list[coordinate].append(double_forward)

            for dcol in [-1, 1]:
                capture_col = col + dcol
                capture_row = row - 1
                if 0 <= capture_col <= 7 and 0 <= capture_row <= 7:
                    capture_square = legal_move_generator.coords_to_square(capture_col, capture_row)
                    target_piece = board[capture_square]
                    if target_piece != "empty" and target_piece.startswith("white"):
                        legal_move_list[coordinate].append(capture_square)

        return legal_move_list
    
    @staticmethod
    def pawn_attacks(coordinate, board, attack_list, piece_name, color):
        col, row = legal_move_generator.square_to_coords(coordinate)
        attack_list.setdefault(coordinate, [])

        if color == "white":
            for dcol in [-1, 1]:
                capture_col = col + dcol
                capture_row = row + 1
                if 0 <= capture_col <= 7 and 0 <= capture_row <= 7:
                    capture_square = legal_move_generator.coords_to_square(capture_col, capture_row)
                    attack_list[coordinate].append(capture_square)

        elif color == "black":
            for dcol in [-1, 1]:
                capture_col = col + dcol
                capture_row = row - 1
                if 0 <= capture_col <= 7 and 0 <= capture_row <= 7:
                    capture_square = legal_move_generator.coords_to_square(capture_col, capture_row)
                    attack_list[coordinate].append(capture_square)

        return attack_list

class chessboard():
    line_8 = ['A8', 'B8', 'C8', 'D8', 'E8', 'F8', 'G8', 'H8']
    line_7 = ['A7', 'B7', 'C7', 'D7', 'E7', 'F7', 'G7', 'H7']
    line_6 = ['A6', 'B6', 'C6', 'D6', 'E6', 'F6', 'G6', 'H6']
    line_5 = ['A5', 'B5', 'C5', 'D5', 'E5', 'F5', 'G5', 'H5']
    line_4 = ['A4', 'B4', 'C4', 'D4', 'E4', 'F4', 'G4', 'H4']
    line_3 = ['A3', 'B3', 'C3', 'D3', 'E3', 'F3', 'G3', 'H3']
    line_2 = ['A2', 'B2', 'C2', 'D2', 'E2', 'F2', 'G2', 'H2']
    line_1 = ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1', 'H1']

    board_arrangement = {
        'A8': 'black_rook', 'H8': 'black_rook',
        'B8': 'black_knight', 'G8': 'black_knight',
        'C8': 'black_bishop', 'F8': 'black_bishop',
        'D8': 'black_queen', 'E8': 'black_king',
        'A1': 'white_rook', 'H1': 'white_rook',
        'B1': 'white_knight', 'G1': 'white_knight',
        'C1': 'white_bishop', 'F1': 'white_bishop',
        'D1': 'white_queen', 'E1': 'white_king',
        'A7': 'black_pawn', 'B7': 'black_pawn', 'C7': 'black_pawn', 'D7': 'black_pawn',
        'E7': 'black_pawn', 'F7': 'black_pawn', 'G7': 'black_pawn', 'H7': 'black_pawn',
        'A2': 'white_pawn', 'B2': 'white_pawn', 'C2': 'white_pawn', 'D2': 'white_pawn',
        'E2': 'white_pawn', 'F2': 'white_pawn', 'G2': 'white_pawn', 'H2': 'white_pawn',
        'A3': 'empty', 'B3': 'empty', 'C3': 'empty', 'D3': 'empty',
        'E3': 'empty', 'F3': 'empty', 'G3': 'empty', 'H3': 'empty',
        'A4': 'empty', 'B4': 'empty', 'C4': 'empty', 'D4': 'empty',
        'E4': 'empty', 'F4': 'empty', 'G4': 'empty', 'H4': 'empty',
        'A5': 'empty', 'B5': 'empty', 'C5': 'empty', 'D5': 'empty',
        'E5': 'empty', 'F5': 'empty', 'G5': 'empty', 'H5': 'empty',
        'A6': 'empty', 'B6': 'empty', 'C6': 'empty', 'D6': 'empty',
        'E6': 'empty', 'F6': 'empty', 'G6': 'empty', 'H6': 'empty',
    }

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
    
    current_board_arrangement = board_arrangement.copy()
    current_turn = "white"
    move_history = []
    white_current_square_under_attack = set()
    black_current_square_under_attack = set()

    symbols = {
        'white_pawn': 'P', 'black_pawn': 'p',
        'white_rook': 'R', 'black_rook': 'r',
        'white_knight': 'N', 'black_knight': 'n',
        'white_bishop': 'B', 'black_bishop': 'b',
        'white_queen': 'Q', 'black_queen': 'q',
        'white_king': 'K', 'black_king': 'k',
        'empty': '.'
    }

    @classmethod
    def find_king(cls, color, board=None):
        if board is None:
            board = cls.current_board_arrangement
        
        for square, piece in board.items():
            if piece == f"{color}_king":
                return square
        return None

    @classmethod
    def is_square_attacked(cls, square, by_color, board=None):
        if board is None:
            board = cls.current_board_arrangement
        
        temp_attack_moves = {}
        for coordinate in board:
            piece_name = board[coordinate]
            if piece_name == "empty" or not piece_name.startswith(by_color):
                continue
            
            if piece_name.endswith("rook"):
                legal_move_generator.rook_moves(coordinate, board, temp_attack_moves, piece_name, by_color)
            elif piece_name.endswith("knight"):
                legal_move_generator.knight_moves(coordinate, board, temp_attack_moves, piece_name, by_color)
            elif piece_name.endswith("bishop"):
                legal_move_generator.bishop_moves(coordinate, board, temp_attack_moves, piece_name, by_color)
            elif piece_name.endswith("queen"):
                legal_move_generator.queen_moves(coordinate, board, temp_attack_moves, piece_name, by_color)
            elif piece_name.endswith("king"):
                legal_move_generator.king_moves(coordinate, board, temp_attack_moves, piece_name, by_color)
            elif piece_name.endswith("pawn"):
                legal_move_generator.pawn_attacks(coordinate, board, temp_attack_moves, piece_name, by_color)
        
        for moves in temp_attack_moves.values():
            if square in moves: return True
        return False

    @classmethod
    def is_in_check(cls, color, board=None):
        if board is None: board = cls.current_board_arrangement
        
        king_square = cls.find_king(color, board)
        if not king_square: return False
        
        opponent = "black" if color == "white" else "white"
        return cls.is_square_attacked(king_square, opponent, board)

    @classmethod
    def simulate_move(cls, from_square, to_square):
        test_board = cls.current_board_arrangement.copy()
        test_board[to_square] = test_board[from_square]
        test_board[from_square] = "empty"
        return test_board

    @classmethod
    def generate_legal_moves(cls, filter_for_check=True):
        pseudo_legal_moves = {}
        for coordinate in cls.current_board_arrangement:
            piece_name = cls.current_board_arrangement[coordinate]
            if piece_name == "empty": continue
                
            color = "white" if piece_name.startswith("white") else "black"
            
            if piece_name.endswith("rook"):
                legal_move_generator.rook_moves(coordinate, cls.current_board_arrangement, pseudo_legal_moves, piece_name, color)
            elif piece_name.endswith("knight"):
                legal_move_generator.knight_moves(coordinate, cls.current_board_arrangement, pseudo_legal_moves, piece_name, color)
            elif piece_name.endswith("bishop"):
                legal_move_generator.bishop_moves(coordinate, cls.current_board_arrangement, pseudo_legal_moves, piece_name, color)
            elif piece_name.endswith("queen"):
                legal_move_generator.queen_moves(coordinate, cls.current_board_arrangement, pseudo_legal_moves, piece_name, color)
            elif piece_name.endswith("king"):
                legal_move_generator.king_moves(coordinate, cls.current_board_arrangement, pseudo_legal_moves, piece_name, color)
            elif piece_name.endswith("pawn"):
                legal_move_generator.pawn_moves(coordinate, cls.current_board_arrangement, pseudo_legal_moves, piece_name, color)
        
        if not filter_for_check: return pseudo_legal_moves
        
        legal_moves = {}
        for from_square, to_squares in pseudo_legal_moves.items():
            piece = cls.current_board_arrangement[from_square]
            color = "white" if piece.startswith("white") else "black"
            
            legal_moves[from_square] = []
            for to_square in to_squares:
                test_board = cls.simulate_move(from_square, to_square)
                if not cls.is_in_check(color, test_board):
                    legal_moves[from_square].append(to_square)
        
        return legal_moves

    @classmethod
    def is_checkmate(cls, color):
        if not cls.is_in_check(color): return False
        
        legal_moves = cls.generate_legal_moves(filter_for_check=True)
        for from_square, to_squares in legal_moves.items():
            piece = cls.current_board_arrangement[from_square]
            piece_color = "white" if piece.startswith("white") else "black"
            if piece_color == color and len(to_squares) > 0: return False
        
        return True

    @classmethod
    def is_stalemate(cls, color):
        if cls.is_in_check(color): return False
        
        legal_moves = cls.generate_legal_moves(filter_for_check=True)
        for from_square, to_squares in legal_moves.items():
            piece = cls.current_board_arrangement[from_square]
            piece_color = "white" if piece.startswith("white") else "black"
            if piece_color == color and len(to_squares) > 0: return False
        
        return True

    board_lines = [line_8, line_7, line_6, line_5, line_4, line_3, line_2, line_1]
    
    @classmethod
    def display_board(cls, last_move=None, status_message=None):
        print(d_green)
        _count = 8
        print("    +---+---+---+---+---+---+---+---+")
        for line in cls.board_lines:
            row_display = []
            for square in line:
                piece_symbol = cls.symbols[cls.current_board_arrangement[square]]
                if cls.current_board_arrangement[square].startswith("white"): row_display.append(f"{b_green}{piece_symbol}{d_green}")
                elif cls.current_board_arrangement[square].startswith("black"): row_display.append(f"{red}{piece_symbol}{d_green}")
                else: row_display.append(piece_symbol)
            
            print(f" {purple}{_count}{d_green}  |", ' | '.join(row_display), "|")
            print("    +---+---+---+---+---+---+---+---+")
            _count -= 1
        
        print(f"{purple}      A   B   C   D   E   F   G   H{reset}")
        if last_move: print(f"\n{yellow}Last move: {last_move}{reset}")
        if status_message: print(f"\n{red}*** {status_message} ***{reset}")
        print(f"\n{yellow}Current turn: {cls.current_turn.upper()}{reset}")
    
    # types: legal_moves = dict, current_square_under_attack = set
    def check_current_squares_under_attack(legal_moves):
        for coordinate in legal_moves:
            square = legal_moves[coordinate]

            # print("square:", square, coordinate)
            if chessboard.current_board_arrangement[coordinate].startswith('black'): chessboard.white_current_square_under_attack.update(square)
            elif chessboard.current_board_arrangement[coordinate].startswith('white'): chessboard.black_current_square_under_attack.update(square)
    
    # handle castle from input
    def handle_castle(move, from_square, to_square):
        # eg. E2E4, from_square -> E2 : to_square -> E4
        try:
            # white KING-SIDE castling
            if move == "E1G1":
                # king havent moved (can castle)
                if not chessboard.castling_rights['white_king_moved']:
                    # kingside rook havent moved (can castle kingside)
                    if chessboard.castling_rights['white_kingside']:
                        # check for open rank
                        if chessboard.current_board_arrangement['F1'] == 'empty':
                            if chessboard.current_board_arrangement['G1'] == 'empty':
                                # check for square under attack
                                if not 'E1' in chessboard.white_current_square_under_attack:
                                    if not 'F1' in chessboard.white_current_square_under_attack:
                                        if not 'G1' in chessboard.white_current_square_under_attack:
                                            chessboard.current_board_arrangement['E1'] = 'empty'
                                            chessboard.current_board_arrangement['F1'] = 'white_rook'
                                            chessboard.current_board_arrangement['G1'] = 'white_king'
                                            chessboard.current_board_arrangement['H1'] = 'empty'
                                        else: raise ValueError("G1 under attack!")
                                    else: raise ValueError("F1 under attack!")
                                else: raise ValueError("E1 under attack!")
                            else: raise ValueError("G1 not empty!")
                        else: raise ValueError("F1 not empty!")
                    else: raise ValueError("Rook Moved!")
                else: raise ValueError("King Moved!")
            
            # white QUEEN-SIDE castling
            elif move == "E1C1":
                # king havent moved (can castle)
                if not chessboard.castling_rights['white_king_moved']:
                    # queenside rook havent moved (can castle kingside)
                    if chessboard.castling_rights['white_queenside']:
                        # check for open rank
                        if chessboard.current_board_arrangement['B1'] == 'empty':
                            if chessboard.current_board_arrangement['C1'] == 'empty':
                                if chessboard.current_board_arrangement['D1'] == 'empty':
                                    # check for square under attack
                                    if not 'E1' in chessboard.white_current_square_under_attack:
                                        if not 'D1' in chessboard.white_current_square_under_attack:
                                            if not 'C1' in chessboard.white_current_square_under_attack:
                                                chessboard.current_board_arrangement['E1'] = 'empty'
                                                chessboard.current_board_arrangement['D1'] = 'white_rook'
                                                chessboard.current_board_arrangement['C1'] = 'white_king'
                                                chessboard.current_board_arrangement['A1'] = 'empty'
                                            else: raise ValueError("C1 under attack!")
                                        else: raise ValueError("D1 under attack!")
                                    else: raise ValueError("E1 under attack!")
                                else: raise ValueError("D1 not empty!")
                            else: raise ValueError("C1 not empty!")
                        else: raise ValueError("B1 not empty!")
                    else: raise ValueError("Rook Moved!")
                else: raise ValueError("King Moved!")

            # black KING-SIDE castling
            if move == "E8G8":
                # king havent moved (can castle)
                if not chessboard.castling_rights['black_king_moved']:
                    # kingside rook havent moved (can castle kingside)
                    if chessboard.castling_rights['black_kingside']:
                        # check for open rank
                        if chessboard.current_board_arrangement['F8'] == 'empty':
                            if chessboard.current_board_arrangement['G8'] == 'empty':
                                # check for square under attack
                                if not 'E8' in chessboard.black_current_square_under_attack:
                                    if not 'F8' in chessboard.black_current_square_under_attack:
                                        if not 'G8' in chessboard.black_current_square_under_attack:
                                            chessboard.current_board_arrangement['E8'] = 'empty'
                                            chessboard.current_board_arrangement['F8'] = 'black_rook'
                                            chessboard.current_board_arrangement['G8'] = 'black_king'
                                            chessboard.current_board_arrangement['H8'] = 'empty'
                                        else: raise ValueError("G8 under attack!")
                                    else: raise ValueError("F8 under attack!")
                                else: raise ValueError("E8 under attack!")
                            else: raise ValueError("G8 not empty!")
                        else: raise ValueError("F8 not empty!")
                    else: raise ValueError("Rook Moved!")
                else: raise ValueError("King Moved!")
            
            # black QUEEN-SIDE castling
            elif move == "E8C8":
                # king havent moved (can castle)
                if not chessboard.castling_rights['black_king_moved']:
                    # queenside rook havent moved (can castle kingside)
                    if chessboard.castling_rights['black_queenside']:
                        # check for open rank
                        if chessboard.current_board_arrangement['B8'] == 'empty':
                            if chessboard.current_board_arrangement['C8'] == 'empty':
                                if chessboard.current_board_arrangement['D8'] == 'empty':
                                    # check for square under attack
                                    if not 'E8' in chessboard.black_current_square_under_attack:
                                        if not 'D8' in chessboard.black_current_square_under_attack:
                                            if not 'C8' in chessboard.black_current_square_under_attack:
                                                chessboard.current_board_arrangement['E8'] = 'empty'
                                                chessboard.current_board_arrangement['D8'] = 'black_rook'
                                                chessboard.current_board_arrangement['C8'] = 'black_king'
                                                chessboard.current_board_arrangement['A8'] = 'empty'
                                            else: raise ValueError("C8 under attack!")
                                        else: raise ValueError("D8 under attack!")
                                    else: raise ValueError("E8 under attack!")
                                else: raise ValueError("D8 not empty!")
                            else: raise ValueError("C8 not empty!")
                        else: raise ValueError("B8 not empty!")
                    else: raise ValueError("Rook Moved!")
                else: raise ValueError("King Moved!")

        # handle exception
        except ValueError as e: 
            print(f'{red}[!]', e)
            input(f'\n{yellow}Press Enter To Continue . . . ')
            return 'illegal move'
        except Exception as e: print(f"{red}[!]", e)
    
    def horizontal_neighbors(square):
        file = square[0].upper()  # 'E'
        rank = square[1]           # '5'
        neighbors = []

        # Left neighbor
        if file > 'A':
            neighbors.append(chr(ord(file) - 1) + rank)

        # Right neighbor
        if file < 'H':
            neighbors.append(chr(ord(file) + 1) + rank)

        return neighbors

    @classmethod
    def interactive_board(cls):
        utils.clear_screen()
        last_move = None
        status_message = None

        # CppEngineHandler.py
        path = os.getcwd()
        # quit()
        engine = ctypes.CDLL(os.path.join(path, "engine.dll"))

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
            piece = chessboard.current_board_arrangement[from_sq]
            chessboard.current_board_arrangement[to_sq] = piece
            chessboard.current_board_arrangement[from_sq] = "empty"

            return from_sq, to_sq, score.value
        
        while True:
            if cls.is_checkmate(cls.current_turn):
                utils.clear_screen()
                cls.display_board(last_move)
                winner = "BLACK" if cls.current_turn == "white" else "WHITE"
                print(f"\n{red}{'='*50}")
                print(f"{red}CHECKMATE! {winner} WINS!{reset}")
                print(f"{red}{'='*50}{reset}\n")
                break
            
            if cls.is_stalemate(cls.current_turn):
                utils.clear_screen()
                cls.display_board(last_move)
                print(f"\n{yellow}{'='*50}")
                print(f"{yellow}STALEMATE! The game is a draw!{reset}")
                print(f"{yellow}{'='*50}{reset}\n")
                break
            
            if cls.is_in_check(cls.current_turn): status_message = f"{cls.current_turn.upper()} IS IN CHECK!"
            else: status_message = None
            
            cls.display_board(last_move, status_message)
            legal_moves = cls.generate_legal_moves()

            # reset squares under attack:
            chessboard.white_current_square_under_attack = set()
            chessboard.black_current_square_under_attack = set()
            # generate squares under attack once-again:
            chessboard.check_current_squares_under_attack(legal_moves)
            # print(chessboard.white_current_square_under_attack)
            # print(chessboard.black_current_square_under_attack)
            
            # input
            try:
                move = frontend.move
                # move = input(f"\n{b_green}[{cls.current_turn.upper()}] Enter your move (e.g., E2E4) or 'quit' to exit: {reset}").upper().strip()
                if move == "QUIT":
                    print(f"\n{yellow}Thanks for playing!{reset}")
                    break
                
                if not re.match(r"^[A-H][1-8][A-H][1-8]([QNRB])?$", move): raise ValueError("Invalid format! Use format like E2E4")
                
                from_square = move[:2]
                to_square = move[2:4]

                # piece name
                piece = cls.current_board_arrangement[from_square]
                # piece color (our move, not the bot's move)
                piece_color = "white" if piece.startswith("white") else "black"

                # temporary (debugging purpose only)
                # values.after_en_passant = 'E6' # temporary only.
                # values.bot_to_square = 'E5' # this is where the bot move his pawn to, temporary only.
                # values.bot_from_square = 'E7'

                # handle En-passant:
                if piece.endswith('pawn'):
                    # user playing as white
                    if piece_color == 'white': 
                        # we know user wants to en-passant (REPLACE == WITH != LATER)
                        if from_square[0] != to_square[0]: # check if pawn moved to different file
                            if from_square[1] == '5': 
                                # values.after_en_passant is where we can En-passant to.
                                # values.after_en_passant is a type (coordinate): eg. E6
                                if values.after_en_passant:
                                    if to_square == values.after_en_passant:
                                        if values.bot_from_square[1] == '7':
                                            if values.bot_to_square[1] == '5':
                                                neighbor = chessboard.horizontal_neighbors(values.bot_to_square)
                                                if from_square in neighbor:
                                                    chessboard.current_board_arrangement[to_square] = 'white_pawn'
                                                    chessboard.current_board_arrangement[from_square] = 'empty'
                                                    # remove captured pawn
                                                    chessboard.current_board_arrangement[values.bot_to_square] = 'empty'
                    
                    elif piece_color == 'black':
                        # we know user wants to en-passant (REPLACE == WITH != LATER)
                        if from_square[0] != to_square[0]: # check if pawn moved to different file
                            if from_square[1] == '4':
                                # values.after_en_passant is where we can En-passant to.
                                # values.after_en_passant is a type (coordinate): eg. E6
                                if values.after_en_passant:
                                    if to_square == values.after_en_passant:
                                        if values.bot_from_square[1] == '2':
                                            if values.bot_to_square[1] == '4':
                                                neighbor = chessboard.horizontal_neighbors(values.bot_to_square)
                                                if from_square in neighbor:
                                                    chessboard.current_board_arrangement[to_square] = 'black_pawn'
                                                    chessboard.current_board_arrangement[from_square] = 'empty'
                                                    # remove captured pawn
                                                    chessboard.current_board_arrangement[values.bot_to_square] = 'empty'
                
                
                # print(chessboard.horizontal_neighbors(values.after_en_passant))


                """
                # handle En-passant:
                for piece_coordinates in chessboard.current_board_arrangement:
                    if piece_color == 'white':
                        if values.after_en_passant: # values.after_en_passant is a type (coordinate): eg. E4
                            if chessboard.current_board_arrangement[values.after_en_passant].startswith('black'):
                                ..."""

                # record for rook moved
                if from_square == 'A1': chessboard.castling_rights['white_queenside'] = False
                if from_square == 'H1': chessboard.castling_rights['white_kingside'] = False
                if from_square == 'A8': chessboard.castling_rights['black_queenside'] = False
                if from_square == 'H8': chessboard.castling_rights['black_kingside'] = False

                # white castling
                if move == "E1G1" or move == "E1C1" or move == "E8G8" or move == "E8C8":
                    legal = chessboard.handle_castle(move, from_square, to_square)
                    if legal == 'illegal move': raise KeyError()  # skip other checks (smart move)
                    # record for king moved (must be handled after handle castling)
                    if from_square == 'E1': chessboard.castling_rights['white_king_moved'] = True
                    if from_square == 'E8': chessboard.castling_rights['black_king_moved'] = True
                    raise AttributeError()
                
                # record for king moved once again (must be handled after handle castling)
                if from_square == 'E1': chessboard.castling_rights['white_king_moved'] = True
                if from_square == 'E8': chessboard.castling_rights['black_king_moved'] = True

                # legal move check
                # if piece == "empty": raise ValueError(f"No piece at {from_square}!")
                if frontend.piece_color != cls.current_turn: raise ValueError(f"It's {cls.current_turn}'s turn! You selected a {frontend.piece_color} piece.")
                if frontend.from_square not in legal_moves or frontend.to_square not in legal_moves[frontend.from_square]:
                    if frontend.from_square in legal_moves:
                        available = ', '.join(legal_moves[frontend.from_square]) if legal_moves[frontend.from_square] else "none"
                        if cls.is_in_check(cls.current_turn): raise ValueError(f"You are in check! {piece} at {frontend.from_square} can move to: {available}")
                        else: raise ValueError(f"Illegal move! {piece} at {frontend.from_square} can move to: {available}")
                    else: raise ValueError(f"The {piece} at {frontend.from_square} has no legal moves!")
                
                captured_piece = cls.current_board_arrangement[to_square]
                cls.current_board_arrangement[to_square] = piece
                cls.current_board_arrangement[from_square] = "empty"
                
                move_notation = f"{from_square}{to_square}"
                if captured_piece != "empty": move_notation += f" (captured {captured_piece})"
                
                cls.move_history.append(move_notation)
                last_move = move_notation
                cls.current_turn = "black" if cls.current_turn == "white" else "white"

                # pawn promotion:
                promotion_list = {'Q': "queen", 'N': "knight", 'R': "rook", 'B': "bishop"}
                piece_to_promote = None

                if len(move) == 5: piece_to_promote = move[4]

                # white
                if piece.endswith('pawn'):
                    if piece_color == 'white':
                        if from_square.endswith('7'):
                            if to_square.endswith('8'):
                                if piece_to_promote:
                                    if piece.endswith('pawn'):
                                        chessboard.current_board_arrangement[to_square] = f'white_{promotion_list[piece_to_promote]}'
                                else: raise AssertionError('white')

                    # black
                    elif piece_color == 'black':
                        if from_square.endswith('2'):
                            if to_square.endswith('1'):
                                if piece_to_promote:
                                    if piece.endswith('pawn'):
                                        chessboard.current_board_arrangement[to_square] = f'black_{promotion_list[piece_to_promote]}'
                                else: raise AssertionError('black')
                # reset
                piece_to_promote = None

                # re-print board 
                utils.clear_screen()
                chessboard.display_board()
            
            # illegal move handling
            except ValueError as e:
                print(f"\n{red}Error: {e}{reset}")
                input(f"\n{yellow}Press Enter to continue...{reset}")
                utils.clear_screen()
                cls.current_turn = "white"
                continue

            # skipped from above
            except KeyError: 
                # re-print board 
                utils.clear_screen()
                chessboard.display_board()
                print(f"{red}[!] {yellow}Illegal Move, cannot castle!")
                input('\nPress Enter To Continue . . . ')
                cls.current_turn = "white"
                continue

            except AssertionError as color:
                utils.clear_screen()
                chessboard.current_board_arrangement[to_square] = captured_piece
                chessboard.current_board_arrangement[from_square] = f'{color}_pawn'
                print(f"{red}[!] {yellow}Illegal Move! You must specify which piece to promote.")
                print(f'{red}[!] {yellow}Use format like {d_green}E7E8{purple}Q {yellow}to promote')
                print(f'{b_green}\nQ: queen\nN: knight\nR: rook\nB: bishop')
                input('\nPress Enter To Continue . . . ')
                cls.current_turn = 'white'
                continue

            except AttributeError:
                utils.clear_screen()
                chessboard.display_board()
            
            # user exit game
            except KeyboardInterrupt:
                print(f"\n\n{yellow}Game interrupted. Thanks for playing!{reset}")
                break

            except Exception as e:
                print(f'{red}[!]', e)
                input()
            
            # update shared.py:
            # shared.current_board_arrangement = chessboard.current_board_arrangement.copy()

            # result returned by engines
            from_sq, to_sq, score = GetBestMove(chessboard.current_board_arrangement, "black", values.depth)
            utils.clear_screen()
            print(f"Engine plays {from_sq} -> {to_sq} (score {score})")

            # update shared.py once again:
            # shared.current_board_arrangement = chessboard.current_board_arrangement.copy()

            # white's turn:
            cls.current_turn = "white"

            # handle En-passant
            bot_moved_piece_name = chessboard.current_board_arrangement[from_sq] # -> e.g. black_pawn

            if bot_moved_piece_name.endswith('pawn'):
                # bot as black:
                if bot_moved_piece_name.startswith('black'):
                    if from_sq[1] == '7': # eg. E7
                        if to_sq[1] == '5': # eg. E5
                            values.after_en_passant = f'{to_sq[0]}6' # example: to_sq: eg. E5
                            values.bot_to_square = to_sq
                            values.bot_from_square = from_sq
                            
                # bot as white:
                elif bot_moved_piece_name.startswith('white'):
                    if from_sq[1] == '2': # eg. E2
                        if to_sq[1] == '4': # eg. E4
                            values.after_en_passant = f'{to_sq[0]}3'
                            values.bot_to_square = to_sq
                            values.bot_from_square = from_sq


            # handle bot's moves (done)
            # print(chessboard.current_board_arrangement[from_sq])
            # quit()

            # update current board
            # chessboard.current_board_arrangement = shared.current_board_arrangement.copy()
            '''
            bot_move_initial_piece_name = chessboard.current_board_arrangement[from_sq]
            chessboard.current_board_arrangement[from_sq] = "empty"
            chessboard.current_board_arrangement[to_sq] = bot_move_initial_piece_name

            # update the global board once again:
            shared.current_board_arrangement = chessboard.current_board_arrangement.copy()
            '''


class frontend():
    # values
    move = str()
    piece_color = str()
    from_square = str()
    to_square = str()
    current_turn = 'white'

    def display_screen():
        last_move_square = 'empty'
        # Initialize Pygame
        pygame.init()

        # Constants
        board_size = 8
        square_size = 80  # initial, will scale
        light_color = (240, 217, 181)
        dark_color = (181, 136, 99)
        default_highlight_color = (75, 100, 75, 100)

        # Screen setup
        info = pygame.display.Info()
        width, height = info.current_w, info.current_h
        square_size = int((height // board_size) / 1.5)
        screen = pygame.display.set_mode(((square_size * 8) + 300, square_size * board_size), pygame.NOFRAME)
        pygame.display.set_caption("Chess")
        screen.fill((100, 100, 100))  # white background
        board_offset_x = 0 # shift right (pixels)
        board_offset_y = 0 # shift down (pixels)

        # Load pieces
        piece_textures = {}
        asset_folder = os.path.join(os.getcwd(), "pieces")
        for piece in ['white_pawn', 'white_rook', 'white_knight', 'white_bishop', 'white_queen', 'white_king',
                    'black_pawn', 'black_rook', 'black_knight', 'black_bishop', 'black_queen', 'black_king']:
            path = os.path.join(asset_folder, f"{piece}.png")
            img = pygame.image.load(path).convert_alpha()
            img = pygame.transform.smoothscale(img, (square_size, square_size))
            piece_textures[piece] = img

        # Board state
        current_board = chessboard.current_board_arrangement

        # Drag & selection variables
        dragging_piece = 'empty'
        dragging_from = 'empty'
        selected_square = 'empty'
        frame_height = 40

        def highlight_square(square, color=(75, 100, 75, 255)): # rgba format
            """Draw a semi-transparent highlight on a square."""
            if square == 'empty':
                return
            col = ord(square[0].upper()) - ord('A')
            row = 8 - int(square[1])
            highlight_rect = pygame.Rect(
                board_offset_x + col*square_size,
                board_offset_y + row*square_size,
                square_size,
                square_size
            )
            s = pygame.Surface((square_size, square_size), pygame.SRCALPHA)  # allows alpha
            s.fill(color)
            screen.blit(s, highlight_rect.topleft)
        
        def draw_board():
            # nonlocal last_move_square
            # Draw squares
            for row in range(board_size):
                for col in range(board_size):
                    rect = pygame.Rect(
                        board_offset_x + col*square_size,
                        board_offset_y + row*square_size,
                        square_size,
                        square_size
                    )
                    color = light_color if (row + col) % 2 == 0 else dark_color
                    pygame.draw.rect(screen, color, rect)

            # Draw pieces
            for square, piece in current_board.items():
                if piece == 'empty':
                    continue
                if dragging_piece == piece and square == dragging_from:
                    pass
                col = ord(square[0]) - ord('A')
                row = 8 - int(square[1])
                screen.blit(piece_textures[piece], (board_offset_x + col*square_size, board_offset_y + row*square_size))

            # Draw persistent highlight for selected square

            if selected_square != 'empty':
                highlight_square(selected_square, color=default_highlight_color)  # lighter green, semi-transparent
            
            if last_move_square != 'empty':
                highlight_square(last_move_square, color=default_highlight_color)

            # Draw dragging piece on top
            if dragging_piece != 'empty':
                mx, my = pygame.mouse.get_pos()
                screen.blit(
                    piece_textures[dragging_piece],
                    (mx - drag_offset_x, my - drag_offset_y)
                )



        def get_square_from_mouse(pos):
            x, y = pos
            col = int(x // square_size)
            row = int(y // square_size)
            if col < 0 or col > 7 or row < 0 or row > 7:
                return 'empty'
            return f"{chr(ord('a') + col)}{8 - row}"

        def move_piece(start, end):
            # print(start, end)
            frontend.from_square = start
            frontend.to_square = end
            piece = current_board.get(start)
            frontend.piece_color = 'white' if piece.startswith('white') else 'black'
            
            if end in chessboard.generate_legal_moves()[start] and frontend.current_turn == frontend.piece_color:
                if piece == 'empty':
                    return
                current_board[start] = 'empty'
                current_board[end] = piece
                frontend.move = f'{start}{end}'
                if start != end:
                    frontend.current_turn = 'black' if piece.startswith('white') else 'white'
                    threading.Thread(target=chessboard.interactive_board).start()

        # Main loop
        running = True
        clock = pygame.time.Clock()
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    running = False

                # Mouse click / start drag or click
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    sq = get_square_from_mouse(event.pos).upper()
                    if sq == 'empty': continue

                    piece = current_board.get(sq)

                    if piece != 'empty':
                        # Either start dragging OR select for click move
                        dragging_piece = piece
                        dragging_from = sq
                        selected_square = sq  # mark as selected for click move
                        mx, my = event.pos
                        col = ord(sq[0]) - ord('A')
                        row = 8 - int(sq[1])
                        drag_offset_x = mx - col * square_size
                        drag_offset_y = my - row * square_size
                        print(selected_square)
                        move_piece(selected_square, sq)
                    
                    # else: pass
                        # selected_square = 'empty'
                        

                # Mouse release / drop or click move
                if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    sq = get_square_from_mouse(event.pos).upper()
                    if sq == 'empty':
                        dragging_piece = 'empty'
                        dragging_from = 'empty'
                        selected_square = 'empty'
                        continue

                    if dragging_piece != 'empty':
                        # highlight_square(sq)
                        move_piece(dragging_from, sq)
                        last_move_square = sq
                    elif selected_square != 'empty':
                        # highlight_square(sq)
                        move_piece(selected_square, sq)
                        last_move_square = sq

                    # Reset everything
                    dragging_piece = 'empty'
                    dragging_from = 'empty'
                    # selected_square = 'empty' # dont reset this


            draw_board()
            pygame.display.flip()
            clock.tick(60)
            # break

        pygame.quit()


if __name__ == "__main__":
    utils.clear_screen()
    # print(f"{b_green}{'='*50}")
    # print(f"{'COMMAND-LINE CHESS GAME':^50}")
    # print(f"{'='*50}{reset}\n")
    # print(f"{yellow}How to play:{reset}")
    # print(f"  - White pieces are shown in {b_green}GREEN{reset}")
    # print(f"  - Black pieces are shown in {red}RED{reset}")
    # print(f"  - Enter moves in format: E2E4 (from square to square)")
    # print(f"  - Type 'quit' to exit the game\n")
    # input(f"{yellow}Press Enter to start...{reset}")

    # mainloop
    threading.Thread(target=chessboard.interactive_board).start()
    # chessboard.interactive_board()
    frontend.display_screen()
