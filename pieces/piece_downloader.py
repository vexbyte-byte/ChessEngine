import os
import requests

# Map short codes to full names
pieces = {
    "wp": "white_pawn",
    "wR": "white_rook",
    "wN": "white_knight",
    "wB": "white_bishop",
    "wQ": "white_queen",
    "wK": "white_king",
    "bp": "black_pawn",
    "bR": "black_rook",
    "bN": "black_knight",
    "bB": "black_bishop",
    "bQ": "black_queen",
    "bK": "black_king",
}

hash_code = "ejgfv"
size = 150

# Create folder if it doesn't exist
os.makedirs("pieces", exist_ok=True)

for short_name, full_name in pieces.items():
    url = f"https://assets-themes.chess.com/image/{hash_code}/{size}/{short_name}.png".lower()
    r = requests.get(url)
    if r.status_code == 200:
        file_path = os.path.join("pieces", f"{full_name}.png")
        with open(file_path, "wb") as f:
            f.write(r.content)
        print(f"Downloaded {full_name}.png")
    else:
        print(f"Failed to download {short_name}")
