import pygame
import shared
import os

# Initialize Pygame
pygame.init()

# Constants
board_size = 8
square_size = 80  # initial, will scale
light_color = (240, 217, 181)
dark_color = (181, 136, 99)

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
current_board = shared.board_arrangement

# Drag & selection variables
dragging_piece = None
dragging_from = None
selected_square = None
frame_height = 40

def draw_board():
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

    # Draw pieces (skip dragging piece in original square)
    for square, piece in current_board.items():
        # print(square, piece)
        if piece == 'empty':
            continue
        if dragging_piece == piece and square == dragging_from:
            continue
        col = ord(square[0]) - ord('A')
        row = 8 - int(square[1])

        screen.blit(piece_textures[piece], (board_offset_x + col*square_size, board_offset_y + row*square_size))

    # Draw dragging piece on top
    if dragging_piece:
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
        return None
    return f"{chr(ord('a') + col)}{8 - row}"

def move_piece(start, end):
    piece = current_board.get(start)
    if piece is None:
        return
    current_board[start] = None
    current_board[end] = piece

# Main loop
running = True
clock = pygame.time.Clock()
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            running = False

        # Mouse click / start drag
        if event.type == pygame.MOUSEBUTTONDOWN:
            sq = get_square_from_mouse(event.pos)
            if sq is None:
                continue
            piece = current_board.get(sq)
            if piece:
                dragging_piece = piece
                dragging_from = sq
                mx, my = event.pos
                col = ord(sq[0]) - ord('a')
                row = 8 - int(sq[1])
                drag_offset_x = mx - col * square_size
                drag_offset_y = my - row * square_size
            else:
                selected_square = sq

        # Mouse release / drop
        if event.type == pygame.MOUSEBUTTONUP:
            sq = get_square_from_mouse(event.pos)
            if dragging_piece and sq:
                move_piece(dragging_from, sq)
            elif selected_square and sq:
                move_piece(selected_square, sq)
            dragging_piece = None
            dragging_from = None
            selected_square = None

    draw_board()
    pygame.display.flip()
    clock.tick(60)
    # break

pygame.quit()
