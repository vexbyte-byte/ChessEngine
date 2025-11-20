// this is basically from engine.py, but translated to C++ for speed
#include <thread>       // for threading / multiprocessing
#include <chrono>       // for timing
#include <cmath>        // for math functions
#include <iostream>     // optional, for debugging/output
#include <map>
#include <string>
#include <tuple>
#include <vector>
#include <algorithm>
#include <mutex>
#include <atomic>
#include <limits>
#include <exception>
#include <any>


using namespace std;

// # ---------------------------
// # Utilities: board helpers
// # Board format: dict mapping 'A1'..'H8' -> piece names used in your main file
// # e.g. 'A2': 'white_pawn', 'E8': 'black_king', 'C3': 'empty'
// # ---------------------------

const string FILES = "ABCDEFGH";
const string RANKS = "12345678";

pair<int, int> square_to_coords(string square) {
    // Convert file letter to column index
    char file = toupper(square[0]);
    int col = FILES.find(file);  // index of the letter in FILES

    // Convert rank character to row index
    int row = (square[1] - '0') - 1;

    return make_pair(col, row);
}

string coords_to_square(int col, int row) {
    char file = FILES[col];          // get the file letter
    char rank = '0' + (row + 1);     // convert row index to character '1'..'8'
    string square = "";
    square += file;
    square += rank;
    return square;
}

bool in_bounds_colrow(int col, int row) {
    return col >= 0 && col <= 7 && row >= 0 && row <= 7;
}

map<string, string> copy_board(const map<string, string>& board) {
    return map<string, string>(board);
}

// # ---------------------------
// # Castling helpers
// # ---------------------------

map<string, map<string, bool>> infer_castling_rights_from_board(const map<string, string>& board) {
    map<string, map<string, bool>> rights;

    rights["white"]["K"] = false;
    rights["white"]["Q"] = false;
    rights["black"]["K"] = false;
    rights["black"]["Q"] = false;

    // White king side
    if (board.count("E1") && board.at("E1") == "white_king") {
        if (board.count("H1") && board.at("H1") == "white_rook") rights["white"]["K"] = true;
        if (board.count("A1") && board.at("A1") == "white_rook") rights["white"]["Q"] = true;
    }

    // Black king side
    if (board.count("E8") && board.at("E8") == "black_king") {
        if (board.count("H8") && board.at("H8") == "black_rook") rights["black"]["K"] = true;
        if (board.count("A8") && board.at("A8") == "black_rook") rights["black"]["Q"] = true;
    }

    return rights;
}

// # ---------------------------
// # Moves & simulation
// # ---------------------------

map<char, string> PROMO_MAP = {
    {'Q', "queen"},
    {'R', "rook"},
    {'B', "bishop"},
    {'N', "knight"}
};

// returns tuple: (newb, new_rights, new_en_passant)
tuple<BoardMap, map<string,map<string,bool>>, string>
simulate_move(const BoardMap &board, const string &from_sq, const string &to_sq,
              const map<string,map<string,bool>> *castling_rights = nullptr,
              const string *en_passant_target = nullptr) {

    // copy board
    BoardMap newb = board;
    string piece = newb.at(from_sq);

    // If to_sq carries a promotion letter (e.g. "E8Q"), separate it
    char promo = '\0';
    string real_to = to_sq;
    if (to_sq.size() > 2 && PROMO_MAP.count(to_sq[2]) > 0) {
        real_to = to_sq.substr(0, 2);
        promo = to_sq[2];
    }

    // default rights copy
    map<string,map<string,bool>> new_rights;
    if (castling_rights == nullptr) {
        new_rights = infer_castling_rights_from_board(board);
    } else {
        // shallow copy of nested map
        new_rights = *castling_rights;
    }

    // Prepare new en-passant target: reset unless set by double pawn move below
    string new_en_passant = ""; // empty string means None

    // Move piece (handle promotion)
    // clear origin
    newb[from_sq] = "empty";

    // handle promotion if any and piece is a pawn
    auto ends_with = [&](const string &s, const string &suffix){
        if (s.size() < suffix.size()) return false;
        return s.compare(s.size() - suffix.size(), suffix.size(), suffix) == 0;
    };

    if (promo != '\0' && ends_with(piece, "pawn")) {
        // color_label = piece.split("_",1)[0]
        size_t ppos = piece.find('_');
        string color_label = (ppos != string::npos) ? piece.substr(0, ppos) : piece;
        string promoted_type = PROMO_MAP.at(promo); // PROMO_MAP defined globally
        newb[real_to] = color_label + "_" + promoted_type;
    } else {
        newb[real_to] = piece;
    }

    // handle en-passant capture:
    if (ends_with(piece, "pawn") && en_passant_target != nullptr) {
        // Compare real_to with provided en_passant_target (must match exactly)
        if (real_to == *en_passant_target) {
            // verify the target square was empty on the original board:
            auto it_target_orig = board.find(real_to);
            string orig_target_value = (it_target_orig != board.end()) ? it_target_orig->second : string("");
            if (orig_target_value == "empty") {
                // determine which pawn is captured
                auto [tcol, trow] = square_to_coords(real_to);
                if (piece.rfind("white", 0) == 0) { // piece.startswith("white")
                    // white captures downward removed pawn at row -1 from target
                    int captured_row = trow - 1;
                    if (in_bounds_colrow(tcol, captured_row)) {
                        string captured_sq = coords_to_square(tcol, captured_row);
                        auto it_captured_orig = board.find(captured_sq);
                        if (it_captured_orig != board.end() && it_captured_orig->second == "black_pawn") {
                            newb[captured_sq] = "empty";
                        }
                    }
                } else {
                    // black captures upward removed pawn at row +1 from target
                    int captured_row = trow + 1;
                    if (in_bounds_colrow(tcol, captured_row)) {
                        string captured_sq = coords_to_square(tcol, captured_row);
                        auto it_captured_orig = board.find(captured_sq);
                        if (it_captured_orig != board.end() && it_captured_orig->second == "white_pawn") {
                            newb[captured_sq] = "empty";
                        }
                    }
                }
            }
        }
    }

    // handle castling rook relocation (use original to_sq semantics for castling detection)
    if (ends_with(piece, "king")) {
        if (piece == "white_king") {
            // king-side
            if (from_sq == "E1" && real_to == "G1") {
                // move rook H1 -> F1
                newb["H1"] = "empty";
                newb["F1"] = "white_rook";
            }
            // queen-side
            else if (from_sq == "E1" && real_to == "C1") {
                newb["A1"] = "empty";
                newb["D1"] = "white_rook";
            }
            // moving king revokes both rights
            new_rights["white"]["K"] = false;
            new_rights["white"]["Q"] = false;
        } else if (piece == "black_king") {
            if (from_sq == "E8" && real_to == "G8") {
                newb["H8"] = "empty";
                newb["F8"] = "black_rook";
            } else if (from_sq == "E8" && real_to == "C8") {
                newb["A8"] = "empty";
                newb["D8"] = "black_rook";
            }
            new_rights["black"]["K"] = false;
            new_rights["black"]["Q"] = false;
        }
    }

    // if a rook moved (or was captured), revoke corresponding rook-side rights
    if (ends_with(piece, "rook")) {
        if (piece == "white_rook") {
            if (from_sq == "H1") new_rights["white"]["K"] = false;
            else if (from_sq == "A1") new_rights["white"]["Q"] = false;
        } else if (piece == "black_rook") {
            if (from_sq == "H8") new_rights["black"]["K"] = false;
            else if (from_sq == "A8") new_rights["black"]["Q"] = false;
        }
    }

    // If a rook was captured on its original square, clear that right too
    // Check destination square: look at original board (before move) using real_to
    auto it_orig_target = board.find(real_to);
    string orig_target = (it_orig_target != board.end()) ? it_orig_target->second : string("");

    if (orig_target == "white_rook") {
        if (real_to == "H1") new_rights["white"]["K"] = false;
        else if (real_to == "A1") new_rights["white"]["Q"] = false;
    } else if (orig_target == "black_rook") {
        if (real_to == "H8") new_rights["black"]["K"] = false;
        else if (real_to == "A8") new_rights["black"]["Q"] = false;
    }

    // handle en-passant target creation: if the moved piece is a pawn and it moved two squares,
    if (ends_with(piece, "pawn")) {
        auto [fcol, frow] = square_to_coords(from_sq);
        auto [tcol, trow] = square_to_coords(real_to);
        if (abs(trow - frow) == 2) {
            // square passed over
            int mid_row = (frow + trow) / 2;
            new_en_passant = coords_to_square(tcol, mid_row);
        } else {
            new_en_passant = "";
        }
    } else {
        new_en_passant = "";
    }

    return make_tuple(newb, new_rights, new_en_passant);
}


// # ---------------------------
// # Generate pseudo-legal moves (ignores checks)
// # ---------------------------

vector<string> rook_moves_from(const string &square, const map<string,string> &board, const string &color) {
    auto [col, row] = square_to_coords(square);
    vector<pair<int,int>> directions = {{0,1}, {0,-1}, {-1,0}, {1,0}};
    vector<string> moves;

    for (auto [dc, dr] : directions) {
        int c = col;
        int r = row;
        while (true) {
            c += dc;
            r += dr;
            if (!in_bounds_colrow(c, r)) break;

            string sq = coords_to_square(c, r);
            auto it = board.find(sq);
            string target = (it != board.end()) ? it->second : "empty";

            if (target == "empty") {
                moves.push_back(sq);
            } else if (target.rfind(color, 0) == 0) { // target.startswith(color)
                break;
            } else {
                moves.push_back(sq);
                break;
            }
        }
    }

    return moves;
}

vector<string> bishop_moves_from(const string &square, const map<string,string> &board, const string &color) {
    auto [col, row] = square_to_coords(square);
    vector<pair<int,int>> directions = {{1,1}, {-1,1}, {-1,-1}, {1,-1}};
    vector<string> moves;

    for (auto [dc, dr] : directions) {
        int c = col;
        int r = row;
        while (true) {
            c += dc;
            r += dr;
            if (!in_bounds_colrow(c, r)) break;

            string sq = coords_to_square(c, r);
            auto it = board.find(sq);
            string target = (it != board.end()) ? it->second : "empty";

            if (target == "empty") {
                moves.push_back(sq);
            } else if (target.rfind(color, 0) == 0) { // target.startswith(color)
                break;
            } else {
                moves.push_back(sq);
                break;
            }
        }
    }

    return moves;
}

vector<string> queen_moves_from(const string &square, const map<string,string> &board, const string &color) {
    vector<string> moves = rook_moves_from(square, board, color);
    vector<string> bishop_moves = bishop_moves_from(square, board, color);
    moves.insert(moves.end(), bishop_moves.begin(), bishop_moves.end());
    return moves;
}

vector<string> knight_moves_from(const string &square, const map<string,string> &board, const string &color) {
    int col, row;
    tie(col, row) = square_to_coords(square); // assuming square_to_coords returns pair<int,int>
    vector<pair<int,int>> offsets = {{2,1},{1,2},{-1,2},{-2,1},{-2,-1},{-1,-2},{1,-2},{2,-1}};
    vector<string> moves;

    for (auto [dc, dr] : offsets) {
        int c = col + dc;
        int r = row + dr;
        if (!in_bounds_colrow(c, r)) continue;
        string sq = coords_to_square(c, r);
        string target = board.at(sq); // use .at() for map access
        if (target == "empty" || target.find(color) != 0) { // .startswith(color) equivalent
            moves.push_back(sq);
        }
    }

    return moves;
}

vector<string> king_moves_from(
    const string &square,
    const map<string,string> &board,
    const string &color,
    const map<string, map<string,bool>> *castling_rights = nullptr
) {
    int col, row;
    tie(col, row) = square_to_coords(square);

    vector<pair<int,int>> offsets = {{0,1},{0,-1},{1,0},{-1,0},{1,1},{1,-1},{-1,1},{-1,-1}};
    vector<string> moves;

    for (auto [dc, dr] : offsets) {
        int c = col + dc;
        int r = row + dr;
        if (!in_bounds_colrow(c, r)) continue;
        string sq = coords_to_square(c, r);
        string target = board.at(sq); // throws if key not found
        if (target == "empty" || target.find(color) != 0) { // Python's not startswith
            moves.push_back(sq);
        }
    }

    // Castling: only include if castling_rights provided
    if (castling_rights != nullptr) {
        string opponent = (color == "white") ? "black" : "white";

        if (color == "white") {
            if (castling_rights->at("white").at("K")) {
                if (board.at("F1") == "empty" && board.at("G1") == "empty") {
                    moves.push_back("G1");
                }
            }
            if (castling_rights->at("white").at("Q")) {
                if (board.at("B1") == "empty" && board.at("C1") == "empty" && board.at("D1") == "empty") {
                    moves.push_back("C1");
                }
            }
        } else {
            if (castling_rights->at("black").at("K")) {
                if (board.at("F8") == "empty" && board.at("G8") == "empty") {
                    moves.push_back("G8");
                }
            }
            if (castling_rights->at("black").at("Q")) {
                if (board.at("B8") == "empty" && board.at("C8") == "empty" && board.at("D8") == "empty") {
                    moves.push_back("C8");
                }
            }
        }
    }

    return moves;
}

vector<string> pawn_moves_from(
    const string &square,
    const map<string,string> &board,
    const string &color,
    const string *en_passant_target = nullptr
) {
    int col, row;
    tie(col, row) = square_to_coords(square);
    vector<string> moves;

    // helper to append promotion variants when target is last rank
    auto append_promotions = [&](const string &target_sq) {
        for (char p : {'Q','R','B','N'}) {
            moves.push_back(target_sq + string(1, p));
        }
    };

    if (color == "white") {
        // forward
        if (row < 7) {
            string forward = coords_to_square(col, row + 1);
            auto it_forward = board.find(forward);
            string val_forward = (it_forward != board.end()) ? it_forward->second : string("empty");
            if (val_forward == "empty") {
                // promotion?
                if (row + 1 == 7) {
                    append_promotions(forward);
                } else {
                    moves.push_back(forward);
                    // double-step
                    if (row == 1) {
                        string double_sq = coords_to_square(col, row + 2);
                        auto it_double = board.find(double_sq);
                        string val_double = (it_double != board.end()) ? it_double->second : string("empty");
                        if (val_double == "empty") {
                            moves.push_back(double_sq);
                        }
                    }
                }
            }
        }

        // captures
        for (int dc : { -1, 1 }) {
            int c = col + dc;
            int r = row + 1;
            if (in_bounds_colrow(c, r)) {
                string sq = coords_to_square(c, r);
                auto it_sq = board.find(sq);
                string target = (it_sq != board.end()) ? it_sq->second : string("empty");
                if (target != "empty" && target.rfind("black", 0) == 0) { // startswith("black")
                    if (r == 7) append_promotions(sq);
                    else moves.push_back(sq);
                }
            }
        }

        // en-passant captures
        if (en_passant_target != nullptr && !en_passant_target->empty()) {
            // en_passant_target is where capturing pawn would land (e.g. 'd6')
            for (int dc : { -1, 1 }) {
                int c = col + dc;
                int r = row + 1;
                if (in_bounds_colrow(c, r)) {
                    string target_sq = coords_to_square(c, r);
                    if (target_sq == *en_passant_target) {
                        auto [tcol, trow] = square_to_coords(*en_passant_target);
                        int captured_row = trow - 1; // black pawn sits one row below the target for white capture
                        if (in_bounds_colrow(tcol, captured_row)) {
                            string captured_sq = coords_to_square(tcol, captured_row);
                            auto it_captured = board.find(captured_sq);
                            string capval = (it_captured != board.end()) ? it_captured->second : string("");
                            if (capval == "black_pawn") {
                                moves.push_back(*en_passant_target);
                            }
                        }
                    }
                }
            }
        }

    } else {
        // black pawns
        if (row > 0) {
            string forward = coords_to_square(col, row - 1);
            auto it_forward = board.find(forward);
            string val_forward = (it_forward != board.end()) ? it_forward->second : string("empty");
            if (val_forward == "empty") {
                if (row - 1 == 0) {
                    append_promotions(forward);
                } else {
                    moves.push_back(forward);
                    if (row == 6) {
                        string double_sq = coords_to_square(col, row - 2);
                        auto it_double = board.find(double_sq);
                        string val_double = (it_double != board.end()) ? it_double->second : string("empty");
                        if (val_double == "empty") moves.push_back(double_sq);
                    }
                }
            }
        }

        for (int dc : { -1, 1 }) {
            int c = col + dc;
            int r = row - 1;
            if (in_bounds_colrow(c, r)) {
                string sq = coords_to_square(c, r);
                auto it_sq = board.find(sq);
                string target = (it_sq != board.end()) ? it_sq->second : string("empty");
                if (target != "empty" && target.rfind("white", 0) == 0) { // startswith("white")
                    if (r == 0) append_promotions(sq);
                    else moves.push_back(sq);
                }
            }
        }

        // en-passant captures for black
        if (en_passant_target != nullptr && !en_passant_target->empty()) {
            for (int dc : { -1, 1 }) {
                int c = col + dc;
                int r = row - 1;
                if (in_bounds_colrow(c, r)) {
                    string target_sq = coords_to_square(c, r);
                    if (target_sq == *en_passant_target) {
                        auto [tcol, trow] = square_to_coords(*en_passant_target);
                        int captured_row = trow + 1; // white pawn sits one row above the target for black capture
                        if (in_bounds_colrow(tcol, captured_row)) {
                            string captured_sq = coords_to_square(tcol, captured_row);
                            auto it_captured = board.find(captured_sq);
                            string capval = (it_captured != board.end()) ? it_captured->second : string("");
                            if (capval == "white_pawn") {
                                moves.push_back(*en_passant_target);
                            }
                        }
                    }
                }
            }
        }
    }

    return moves;
}

vector<string> pawn_attacks_from(
    const string &square,
    const map<string,string> &board,
    const string &color
) {
    int col, row;
    tie(col, row) = square_to_coords(square);
    vector<string> attacks;

    if (color == "white") {
        for (int dc : {-1, 1}) {
            int c = col + dc;
            int r = row + 1;
            if (in_bounds_colrow(c, r)) {
                attacks.push_back(coords_to_square(c, r));
            }
        }
    } else {
        for (int dc : {-1, 1}) {
            int c = col + dc;
            int r = row - 1;
            if (in_bounds_colrow(c, r)) {
                attacks.push_back(coords_to_square(c, r));
            }
        }
    }

    return attacks;
}

map<string, vector<string>> generate_pseudo_legal_moves(
    const map<string,string> &board,
    const string &color,
    const map<string, map<string,bool>> *castling_rights = nullptr,
    const string *en_passant_target = nullptr
) {
    auto ends_with = [&](const string &s, const string &suffix) {
        if (s.size() < suffix.size()) return false;
        return s.compare(s.size() - suffix.size(), suffix.size(), suffix) == 0;
    };

    map<string, vector<string>> moves;
    for (const auto &kv : board) {
        const string &sq = kv.first;
        const string &piece = kv.second;

        if (piece == "empty" || piece.rfind(color, 0) != 0) {
            continue;
        }

        vector<string> to_list;
        if (ends_with(piece, "rook")) {
            to_list = rook_moves_from(sq, board, color);
        } else if (ends_with(piece, "knight")) {
            to_list = knight_moves_from(sq, board, color);
        } else if (ends_with(piece, "bishop")) {
            to_list = bishop_moves_from(sq, board, color);
        } else if (ends_with(piece, "queen")) {
            to_list = queen_moves_from(sq, board, color);
        } else if (ends_with(piece, "king")) {
            to_list = king_moves_from(sq, board, color, castling_rights);
        } else if (ends_with(piece, "pawn")) {
            to_list = pawn_moves_from(sq, board, color, en_passant_target);
        } else {
            to_list = {};
        }

        if (!to_list.empty()) moves[sq] = to_list;
    }

    return moves;
}

// # ---------------------------
// # Attack & check detection
// # ---------------------------

bool is_square_attacked(const map<string,string> &board, const string &square, const string &by_color) {
    auto ends_with = [&](const string &s, const string &suffix) {
        if (s.size() < suffix.size()) return false;
        return s.compare(s.size() - suffix.size(), suffix.size(), suffix) == 0;
    };

    // Pawns
    for (const auto &kv : board) {
        const string &attacker_sq = kv.first;
        const string &piece = kv.second;
        if (piece == "empty" || piece.rfind(by_color, 0) != 0) continue;
        if (ends_with(piece, "pawn")) {
            vector<string> attacks = pawn_attacks_from(attacker_sq, board, by_color);
            if (find(attacks.begin(), attacks.end(), square) != attacks.end()) {
                return true;
            }
        }
    }

    // Knights
    for (const auto &kv : board) {
        const string &attacker_sq = kv.first;
        const string &piece = kv.second;
        if (piece == "empty" || piece.rfind(by_color, 0) != 0) continue;
        if (ends_with(piece, "knight")) {
            vector<string> moves = knight_moves_from(attacker_sq, board, by_color);
            if (find(moves.begin(), moves.end(), square) != moves.end()) return true;
        }
    }

    // King (adjacent) -- use king_moves_from without castling rights so castling squares aren't considered
    for (const auto &kv : board) {
        const string &attacker_sq = kv.first;
        const string &piece = kv.second;
        if (piece == "empty" || piece.rfind(by_color, 0) != 0) continue;
        if (ends_with(piece, "king")) {
            vector<string> moves = king_moves_from(attacker_sq, board, by_color, nullptr);
            if (find(moves.begin(), moves.end(), square) != moves.end()) return true;
        }
    }

    // Sliding: rook/queen orthogonal
    int col0, row0;
    tie(col0, row0) = square_to_coords(square);
    vector<tuple<int,int,pair<string,string>>> orth_dirs = {
        {0,1,{"rook","queen"}}, {0,-1,{"rook","queen"}}, {-1,0,{"rook","queen"}}, {1,0,{"rook","queen"}}
    };

    for (const auto &t : orth_dirs) {
        int dc = get<0>(t);
        int dr = get<1>(t);
        pair<string,string> attackers = get<2>(t);
        int c = col0 + dc;
        int r = row0 + dr;
        while (in_bounds_colrow(c, r)) {
            string sq = coords_to_square(c, r);
            auto it = board.find(sq);
            string piece = (it != board.end()) ? it->second : string("empty");
            if (piece != "empty") {
                if (piece.rfind(by_color, 0) == 0 &&
                    (ends_with(piece, attackers.first) || ends_with(piece, attackers.second))) {
                    return true;
                }
                break;
            }
            c += dc; r += dr;
        }
    }

    // Sliding: bishop/queen diagonal
    vector<pair<int,int>> diag_dirs = {{1,1},{1,-1},{-1,1},{-1,-1}};
    for (auto [dc, dr] : diag_dirs) {
        int c = col0 + dc;
        int r = row0 + dr;
        while (in_bounds_colrow(c, r)) {
            string sq = coords_to_square(c, r);
            auto it = board.find(sq);
            string piece = (it != board.end()) ? it->second : string("empty");
            if (piece != "empty") {
                if (piece.rfind(by_color, 0) == 0 &&
                    (ends_with(piece, "bishop") || ends_with(piece, "queen"))) {
                    return true;
                }
                break;
            }
            c += dc; r += dr;
        }
    }

    return false;
}

string find_king_square(const map<string,string> &board, const string &color) {
    string target_name = color + "_king";
    for (const auto &kv : board) {
        const string &sq = kv.first;
        const string &piece = kv.second;
        if (piece == target_name) {
            return sq;
        }
    }
    return ""; // equivalent to None in Python
}

bool is_in_check(const map<string,string> &board, const string &color) {
    string king_sq = find_king_square(board, color);
    if (king_sq.empty()) {
        // no king? treat as not in check (or could be invalid)
        return false;
    }
    string opponent = (color == "white") ? "black" : "white";
    return is_square_attacked(board, king_sq, opponent);
}

// # ---------------------------
// # Legal moves (filter pseudo-legal by check)
// # ---------------------------

map<string, vector<string>> generate_legal_moves(
    const map<string,string> &board,
    const string &color,
    const map<string, map<string,bool>> *castling_rights = nullptr,
    const string *en_passant_target = nullptr
) {
    // helper: ends_with
    auto ends_with = [&](const string &s, const string &suffix) {
        if (s.size() < suffix.size()) return false;
        return s.compare(s.size() - suffix.size(), suffix.size(), suffix) == 0;
    };

    // pseudo = generate_pseudo_legal_moves(board, color, castling_rights, en_passant_target=en_passant_target)
    map<string, vector<string>> pseudo = generate_pseudo_legal_moves(board, color, castling_rights, en_passant_target);

    map<string, vector<string>> legal;
    for (const auto &kv : pseudo) {
        const string fr = kv.first;
        const vector<string> to_list = kv.second;

        vector<string> legal_targets;
        for (const string &to : to_list) {
            // simulate using current en_passant_target so en-passant capture is correctly handled
            BoardMap nb;
            map<string, map<string,bool>> new_rights;
            string new_en_passant;
            tie(nb, new_rights, new_en_passant) = simulate_move(board, fr, to, castling_rights, en_passant_target);

            // when castling pseudo-move was included we must ensure the king doesn't pass through or land on attacked squares
            auto it_fr = board.find(fr);
            if (it_fr != board.end() && ends_with(it_fr->second, "king") && castling_rights != nullptr) {
                // Only need to check castling-specific squares if move is castling
                // white
                if (fr == "E1" && to == "G1") {
                    if (is_square_attacked(board, "E1", "black") || is_square_attacked(board, "F1", "black") || is_square_attacked(board, "G1", "black")) {
                        continue;
                    }
                }
                if (fr == "E1" && to == "C1") {
                    if (is_square_attacked(board, "E1", "black") || is_square_attacked(board, "D1", "black") || is_square_attacked(board, "C1", "black")) {
                        continue;
                    }
                }
                // black
                if (fr == "E8" && to == "G8") {
                    if (is_square_attacked(board, "E8", "white") || is_square_attacked(board, "F8", "white") || is_square_attacked(board, "G8", "white")) {
                        continue;
                    }
                }
                if (fr == "E8" && to == "C8") {
                    if (is_square_attacked(board, "E8", "white") || is_square_attacked(board, "D8", "white") || is_square_attacked(board, "C8", "white")) {
                        continue;
                    }
                }
            }

            if (!is_in_check(nb, color)) {
                legal_targets.push_back(to);
            }
        }

        if (!legal_targets.empty()) {
            legal[fr] = legal_targets;
        }
    }

    return legal;
}

// # ---------------------------
// # Evaluation
// # ---------------------------

map<string, int> PIECE_VALUES = {
    {"pawn", 100},
    {"knight", 320},
    {"bishop", 330},
    {"rook", 500},
    {"queen", 900},
    {"king", 20000}
};


int evaluate_board(const map<string,string> &board, const string &perspective_color) {
    /*
    Basic static evaluation from perspective_color side.
    Positive means good for perspective_color.
    */
    int score = 0;
    for (const auto &kv : board) {
        const string &sq = kv.first;
        const string &piece = kv.second;
        if (piece == "empty") continue;

        // parts = piece.split("_", 1)
        vector<string> parts;
        size_t sep = piece.find('_');
        if (sep == string::npos) continue;
        parts.push_back(piece.substr(0, sep));
        parts.push_back(piece.substr(sep + 1));

        if (parts.size() != 2) continue;

        string color_label = parts[0];
        string ptype = parts[1];

        int pval = 0;
        auto it_val = PIECE_VALUES.find(ptype);
        if (it_val != PIECE_VALUES.end()) pval = it_val->second;

        if (color_label == perspective_color) {
            score += pval;
        } else {
            score -= pval;
        }
    }

    // small mobility bonus (optional)
    int own_moves = 0;
    auto own_pseudo = generate_pseudo_legal_moves(board, perspective_color);
    for (const auto &kv : own_pseudo) {
        const vector<string> &v = kv.second;
        own_moves += static_cast<int>(v.size());
    }

    string opp = (perspective_color == "white") ? "black" : "white";

    int opp_moves = 0;
    auto opp_pseudo = generate_pseudo_legal_moves(board, opp);
    for (const auto &kv : opp_pseudo) {
        const vector<string> &v = kv.second;
        opp_moves += static_cast<int>(v.size());
    }

    score += 2 * (own_moves - opp_moves);
    return score;
}

// # ---------------------------
// # Minimax with alpha-beta
// # ---------------------------

double minimax(
    const map<string,string> &board,
    const string &maximizing_color,
    const string &current_color,
    int depth,
    double alpha,
    double beta,
    const atomic<bool> *stop_event,
    const map<string, map<string,bool>> *castling_rights = nullptr,
    const string *en_passant_target = nullptr
) {
    // if stop_event.is_set():
    //     # aborted by main thread/user
    //     return 0
    if (stop_event != nullptr && stop_event->load()) {
        return 0.0;
    }

    if (depth == 0) {
        return static_cast<double>(evaluate_board(board, maximizing_color));
    }

    auto legal_moves = generate_legal_moves(board, current_color, castling_rights, en_passant_target);
    if (legal_moves.empty()) {
        // no legal moves: checkmate or stalemate
        if (is_in_check(board, current_color)) {
            // current_color is checkmated -> very bad for current_color
            double inf = numeric_limits<double>::infinity();
            return (current_color == maximizing_color) ? -inf : inf;
        } else {
            return 0.0;  // stalemate -> draw
        }
    }

    string next_color = (current_color == "white") ? "black" : "white";

    double inf = numeric_limits<double>::infinity();

    if (current_color == maximizing_color) {
        double value = -inf;
        for (const auto &kv : legal_moves) {
            const string &fr = kv.first;
            const vector<string> &tos = kv.second;
            for (const string &to : tos) {
                if (stop_event != nullptr && stop_event->load()) return 0.0;

                BoardMap nb;
                map<string, map<string,bool>> new_rights;
                string new_en_passant;
                tie(nb, new_rights, new_en_passant) = simulate_move(board, fr, to, castling_rights, en_passant_target);

                double score = minimax(nb, maximizing_color, next_color, depth - 1, alpha, beta,
                                       stop_event, &new_rights, &new_en_passant);

                value = max(value, score);
                alpha = max(alpha, value);
                if (alpha >= beta) {
                    return value;
                }
            }
        }
        return value;
    } else {
        double value = inf;
        for (const auto &kv : legal_moves) {
            const string &fr = kv.first;
            const vector<string> &tos = kv.second;
            for (const string &to : tos) {
                if (stop_event != nullptr && stop_event->load()) return 0.0;

                BoardMap nb;
                map<string, map<string,bool>> new_rights;
                string new_en_passant;
                tie(nb, new_rights, new_en_passant) = simulate_move(board, fr, to, castling_rights, en_passant_target);

                double score = minimax(nb, maximizing_color, next_color, depth - 1, alpha, beta,
                                       stop_event, &new_rights, &new_en_passant);

                value = min(value, score);
                beta = min(beta, value);
                if (alpha >= beta) {
                    return value;
                }
            }
        }
        return value;
    }
}

// worker_task (selective-stop version)

// Assumptions (defined elsewhere in your translation):
// - typedef map<string,string> BoardMap;
// - tuple<BoardMap, map<string,map<string,bool>>, string> simulate_move(...);
// - double minimax(..., const atomic<bool>* stop_event, ...);
// - A global mutex protecting writes to return_dict:
extern mutex return_dict_mutex;

void worker_task(
    const string &from_sq,
    const string &to_sq,
    const BoardMap &board,
    const string &maximizing_color,
    int root_depth,
    map<string,double> *return_dict,                     // pointer to shared result map
    const atomic<bool> *worker_stop_event,               // pointer to worker-local stop flag
    const atomic<bool> *master_stop_event,               // pointer to global stop flag
    const map<string, map<string,bool>> *castling_rights = nullptr,
    const string *en_passant_target = nullptr
) {
    try {
        // quick abort checks
        if ((worker_stop_event != nullptr && worker_stop_event->load()) ||
            (master_stop_event != nullptr && master_stop_event->load())) {
            return;
        }

        BoardMap nb;
        map<string,map<string,bool>> new_rights;
        string new_en_passant;

        // simulate_move(board, from_sq, to_sq, castling_rights, en_passant_target)
        tie(nb, new_rights, new_en_passant) = simulate_move(board, from_sq, to_sq, castling_rights, en_passant_target);

        // after root move, it's opponent's turn
        string opp = (maximizing_color == "white") ? "black" : "white";

        double neg_inf = -numeric_limits<double>::infinity();
        double pos_inf = numeric_limits<double>::infinity();

        // score = minimax(nb, maximizing_color, opp, root_depth - 1, -math.inf, math.inf,
        //                 stop_event=master_stop_event, castling_rights=new_rights, en_passant_target=new_en_passant)
        double score = minimax(
            nb,
            maximizing_color,
            opp,
            root_depth - 1,
            neg_inf,
            pos_inf,
            master_stop_event,
            &new_rights,
            &new_en_passant
        );

        // worker_stop_event might have been set while minimax was running; ensure not storing stale results
        if (!((worker_stop_event != nullptr && worker_stop_event->load()) ||
              (master_stop_event != nullptr && master_stop_event->load()))) {

            // store result in return_dict (thread-safe with mutex)
            if (return_dict != nullptr) {
                lock_guard<mutex> lock(return_dict_mutex);
                (*return_dict)[from_sq + to_sq] = score;
            }
        }
    }
    catch (...) {
        // don't crash the worker silently; store a low score to mark failure
        if (return_dict != nullptr) {
            lock_guard<mutex> lock(return_dict_mutex);
            (*return_dict)[from_sq + to_sq] = -9999999.0;
        }
    }
}


// engine_search (selective termination) - C++ translation
// Assumes presence of BoardMap = map<string,string>, simulate_move, minimax, generate_legal_moves, infer_castling_rights_from_board
// Assumes existence of ThreadSafeQueue<string> with bool try_pop(string &out) for non-blocking pop

tuple<string, string, double> engine_search(
    const BoardMap &board,
    const string &color,
    int depth,
    ThreadSafeQueue<string> *user_move_queue = nullptr,   // non-blocking try_pop required
    double time_limit = -1.0,                             // seconds, negative means none
    int max_workers = 0,                                  // 0 means auto (hardware_concurrency)
    const map<string, map<string,bool>> *castling_rights = nullptr,
    const string *en_passant_target = nullptr
) {
    // Manager/return_dict replacement:
    // We use a threadsafe return_dict (map protected by mutex)
    map<string,double> return_dict;
    mutex return_dict_mutex;

    // Global stop event (atomic bool)
    atomic<bool> master_stop_event(false);

    // If castling_rights is nullptr, infer from board
    map<string, map<string,bool>> inferred_rights_local;
    const map<string, map<string,bool>> *castling_rights_ptr = castling_rights;
    if (castling_rights_ptr == nullptr) {
        inferred_rights_local = infer_castling_rights_from_board(board);
        castling_rights_ptr = &inferred_rights_local;
    }

    // generate root legal moves for engine side
    map<string, vector<string>> legal = generate_legal_moves(board, color, castling_rights_ptr, en_passant_target);
    vector<pair<string,string>> roots;
    for (const auto &kv : legal) {
        const string &fr = kv.first;
        for (const string &to : kv.second) {
            roots.emplace_back(fr, to);
        }
    }
    if (roots.empty()) {
        // return None, None, None -> use empty strings and NaN for score
        return make_tuple(string(""), string(""), numeric_limits<double>::quiet_NaN());
    }

    if (max_workers <= 0) {
        max_workers = static_cast<int>(thread::hardware_concurrency());
        if (max_workers <= 0) max_workers = 1;
    }

    // Start threads (one per root). We keep:
    // - threads (processes)
    // - worker_events: map move_key -> pointer to atomic<bool> (worker-local stop flag)
    // - proc_map: map move_key -> thread object
    vector<thread> processes;                            // store threads so we can join later
    map<string, atomic<bool>*> worker_events;           // move_key -> worker_stop_event pointer
    map<string, bool> worker_running;                   // move_key -> running flag (for monitoring)
    map<string, thread::id> proc_map;                   // move_key -> thread id (informational)

    // Launch threads
    for (const auto &rt : roots) {
        const string &fr = rt.first;
        const string &to = rt.second;
        string move_key = fr + to;

        // worker-local stop flag (allocated on heap so lambda can capture pointer safely)
        atomic<bool> *worker_stop_event = new atomic<bool>(false);
        worker_events[move_key] = worker_stop_event;
        worker_running[move_key] = true;

        // Launch a thread that performs worker work inline (equivalent to worker_task)
        // It will write into return_dict under return_dict_mutex.
        processes.emplace_back([=, &return_dict, &return_dict_mutex, &worker_running, &proc_map, &master_stop_event]() mutable {
            // register thread id
            proc_map[move_key] = this_thread::get_id();
            try {
                // quick abort checks
                if (worker_stop_event->load() || master_stop_event.load()) {
                    worker_running[move_key] = false;
                    delete worker_stop_event;
                    return;
                }

                // simulate_move(board, from_sq, to_sq, castling_rights, en_passant_target)
                BoardMap nb;
                map<string, map<string,bool>> new_rights;
                string new_en_passant;
                tie(nb, new_rights, new_en_passant) = simulate_move(board, fr, to, castling_rights_ptr, en_passant_target);

                // after root move, it's opponent's turn
                string opp = (color == "white") ? "black" : "white";

                double neg_inf = -numeric_limits<double>::infinity();
                double pos_inf = numeric_limits<double>::infinity();

                double score = minimax(
                    nb,
                    color,            // maximizing_color
                    opp,              // current_color (opponent to move)
                    depth - 1,
                    neg_inf,
                    pos_inf,
                    &master_stop_event,
                    &new_rights,
                    &new_en_passant
                );

                // Ensure worker_stop_event not set while writing and master_stop_event not set
                if (!worker_stop_event->load() && !master_stop_event.load()) {
                    lock_guard<mutex> lg(return_dict_mutex);
                    return_dict[move_key] = score;
                }
            } catch (...) {
                lock_guard<mutex> lg(return_dict_mutex);
                return_dict[move_key] = -9999999.0;
            }
            worker_running[move_key] = false;
            delete worker_stop_event;
        });

        // If number of launched threads equals max_workers, we might want to wait/Throttle - original started all processes.
        // We follow original behaviour and start all threads (but we limited max_workers to hardware concurrency only as guidance).
    }

    // start_time
    auto start_time = chrono::steady_clock::now();

    try {
        // monitor threads and user interrupt queue
        while (true) {
            // alive = any thread still running
            bool alive = false;
            for (const auto &kv : worker_running) {
                if (kv.second) { alive = true; break; }
            }
            if (!alive) break;

            // user interrupt: selective stop logic
            if (user_move_queue != nullptr) {
                // try non-blocking pop
                string user_move;
                bool got = user_move_queue->try_pop(user_move); // requires ThreadSafeQueue::try_pop
                if (got) {
                    if (!user_move.empty()) {
                        string user_move_str = user_move;
                        // normalize: uppercase and strip whitespace
                        transform(user_move_str.begin(), user_move_str.end(), user_move_str.begin(), ::toupper);
                        // remove leading/trailing spaces
                        auto first_non = user_move_str.find_first_not_of(" \t\n\r");
                        auto last_non = user_move_str.find_last_not_of(" \t\n\r");
                        if (first_non != string::npos && last_non != string::npos) {
                            user_move_str = user_move_str.substr(first_non, last_non - first_non + 1);
                        }

                        // If this user_move matches exactly one root worker, stop all others
                        if (worker_events.count(user_move_str) > 0) {
                            for (auto &kv : worker_events) {
                                const string &key = kv.first;
                                atomic<bool> *evt = kv.second;
                                if (key != user_move_str) evt->store(true);
                            }
                            // continue to wait for the matching worker
                        } else {
                            // user move doesn't match any root – abort all workers (safe)
                            master_stop_event.store(true);
                        }
                    }
                }
            }

            // time limit
            if (time_limit >= 0.0) {
                auto elapsed = chrono::duration<double>(chrono::steady_clock::now() - start_time).count();
                if (elapsed > time_limit) {
                    master_stop_event.store(true);
                    break;
                }
            }

            this_thread::sleep_for(chrono::milliseconds(30));
        }
    } catch (...) {
        // pass through to finally-clause replacement
    }

    // finally: ensure threads terminate
    for (auto &th : processes) {
        if (th.joinable()) {
            // give small time slice to allow thread to finish
            // we can't forcefully terminate std::thread in portable C++ - we signal via master_stop_event
            // join with short timeout isn't available; so just join (threads should respect master_stop_event and exit soon)
            try {
                th.join();
            } catch (...) {
                // swallow join error
            }
        }
    }
    // small window for return_dict writes to flush
    this_thread::sleep_for(chrono::milliseconds(20));

    // choose best available result
    {
        lock_guard<mutex> lg(return_dict_mutex);
        if (return_dict.empty()) {
            return make_tuple(string(""), string(""), numeric_limits<double>::quiet_NaN());
        }
    }

    // find max by value
    string best_key = "";
    double best_score = -numeric_limits<double>::infinity();
    {
        lock_guard<mutex> lg(return_dict_mutex);
        for (const auto &kv : return_dict) {
            if (kv.second > best_score) {
                best_score = kv.second;
                best_key = kv.first;
            }
        }
    }

    string best_from = "";
    string best_to = "";
    if (!best_key.empty()) {
        if (best_key.size() >= 4) {
            best_from = best_key.substr(0,2);
            best_to = best_key.substr(2); // allow promotion suffix
        } else if (best_key.size() >= 2) {
            best_from = best_key.substr(0,2);
            best_to = (best_key.size() > 2) ? best_key.substr(2) : string("");
        }
    }

    return make_tuple(best_from, best_to, best_score);
}

// # ---------------------------
// # Engine process wrapper: run in its own process, accept tasks via task_queue, return moves via result_queue
// # Task tuple format: ('SEARCH', board_dict, color, depth, time_limit [, castling_rights [, en_passant_target]])
// # Note: en_passant_target is optional and should be a square (e.g. "E3") or None.
// # ---------------------------

// Assumptions:
// - You have a ThreadSafeQueue<T> type with methods:
//     T pop();               // blocking pop (waits until an item is available) and returns it
//     void push(const T& v); // push item
// - BoardMap = map<string,string>
// - castling rights type = map<string, map<string,bool>>
// - engine_search signature matches previously translated version:
//     tuple<string,string,double> engine_search(const BoardMap &board, const string &color, int depth,
//         ThreadSafeQueue<string> *user_move_queue = nullptr, double time_limit = -1.0,
//         int max_workers = 0, const map<string,map<string,bool>> *castling_rights = nullptr,
//         const string *en_passant_target = nullptr);
// - result_queue will accept vector<any> where we push {"RESULT", from_sq, to_sq, score}

// Task: vector<any> where first element is a string command, others are positional args
void engine_process_main(
    ThreadSafeQueue<vector<any>> *task_queue,
    ThreadSafeQueue<string> *user_move_queue,
    ThreadSafeQueue<vector<any>> *result_queue
) {
    while (true) {
        // blocking wait for a task
        vector<any> task = task_queue->pop();

        // if task is empty, loop again
        if (task.empty()) continue;

        // must be a tuple-like vector where first element is command string
        try {
            if (task[0].type() != typeid(string)) {
                // not a command string -> ignore
                continue;
            }
        } catch (...) {
            continue;
        }

        string cmd;
        try {
            cmd = any_cast<string>(task[0]);
        } catch (...) {
            continue;
        }

        if (cmd == "SEARCH") {
            // Support formats:
            // ('SEARCH', board, color, depth, time_limit)
            // ('SEARCH', board, color, depth, time_limit, castling_rights)
            // ('SEARCH', board, color, depth, time_limit, castling_rights, en_passant_target)

            // keep same variable names as requested
            map<string, map<string,bool>> *castling_rights = nullptr;
            string en_passant_target;           // empty string == None
            BoardMap board;
            string color;
            int depth = 0;
            double time_limit = -1.0;

            // parse required args robustly
            try {
                // we expect at least 5 items: [0]=cmd, [1]=board, [2]=color, [3]=depth, [4]=time_limit
                if (task.size() < 5) {
                    // malformed search task -> ignore
                    continue;
                }

                // board (task[1]) should be a BoardMap
                board = any_cast<BoardMap>(task[1]);

                // color (task[2]) should be a string
                color = any_cast<string>(task[2]);

                // depth (task[3]) should be int (or convertible)
                if (task[3].type() == typeid(int)) depth = any_cast<int>(task[3]);
                else if (task[3].type() == typeid(long)) depth = static_cast<int>(any_cast<long>(task[3]));
                else if (task[3].type() == typeid(double)) depth = static_cast<int>(any_cast<double>(task[3]));
                else depth = stoi(any_cast<string>(task[3])); // fallback

                // time_limit (task[4]) double
                if (task[4].type() == typeid(double)) time_limit = any_cast<double>(task[4]);
                else if (task[4].type() == typeid(int)) time_limit = static_cast<double>(any_cast<int>(task[4]));
                else if (task[4].type() == typeid(long)) time_limit = static_cast<double>(any_cast<long>(task[4]));
                else time_limit = stod(any_cast<string>(task[4]));
                
                // optional castling_rights (task[5])
                if (task.size() >= 6) {
                    // attempt to extract a map<string,map<string,bool>>
                    try {
                        static map<string, map<string,bool>> castling_rights_storage; // reused storage
                        castling_rights_storage = any_cast<map<string,map<string,bool>>>(task[5]);
                        castling_rights = &castling_rights_storage;
                    } catch (...) {
                        // if castling arg not present or wrong type, leave nullptr (engine_search will infer)
                        castling_rights = nullptr;
                    }
                }

                // optional en_passant_target (task[6])
                if (task.size() >= 7) {
                    try {
                        en_passant_target = any_cast<string>(task[6]);
                    } catch (...) {
                        en_passant_target.clear();
                    }
                }

            } catch (...) {
                // malformed task -> ignore and continue loop
                continue;
            }

            // call engine_search; pass en_passant_target as pointer if non-empty
            const string *en_passant_ptr = nullptr;
            if (!en_passant_target.empty()) en_passant_ptr = &en_passant_target;

            string from_sq, to_sq;
            double score;

            try {
                // engine_search returns tuple<string,string,double>
                tuple<string,string,double> res = engine_search(
                    board,
                    color,
                    depth,
                    user_move_queue,
                    time_limit,
                    0,                 // max_workers = 0 -> engine_search decides (match Python default)
                    castling_rights,
                    en_passant_ptr
                );

                from_sq = get<0>(res);
                to_sq   = get<1>(res);
                score   = get<2>(res);
            } catch (...) {
                // engine_search failed; return a RESULT with empty move and NaN score
                from_sq.clear();
                to_sq.clear();
                score = numeric_limits<double>::quiet_NaN();
            }

            // push result as ("RESULT", from_sq, to_sq, score)
            vector<any> result_msg;
            result_msg.push_back(string("RESULT"));
            result_msg.push_back(from_sq);
            result_msg.push_back(to_sq);
            result_msg.push_back(score);
            result_queue->push(result_msg);

        } else if (cmd == "QUIT") {
            break;
        } else {
            // unknown commands ignored
            continue;
        }
    } // while true
}
