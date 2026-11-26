"""
5-rindu Tic-Tac-Toe (Gomoku) ar Swap2 atklātni — bota modulis.

Modulis neko nepalaiž importēšanas brīdī un nemaina ieejas sarakstu `board`
(visas izmaiņas notiek kopijā).

Bota uzbūve:
  * rūtiņu novērtēšana pēc formām katrā virzienā (pieci, atvērtais četrinieks,
    četrinieks, atvērtais trijnieks ...);
  * piespiedu gājienu noteikumi (uzvarēt / bloķēt piecinieku / atvērtais četrinieks);
  * VCF meklēšana — uzvara ar nepārtrauktu četrinieku virkni;
  * negamax ar alfa-beta nogriešanu un iteratīvu padziļināšanu laika robežās.
"""

import random
import time

BOT_NAME: str = "Swap2 Alfa-Beta Bots"

SIZE = 15
EMPTY = "_"
DIRS = ((0, 1), (1, 0), (1, 1), (1, -1))

TIME_LIMIT = 0.85      # sekundes vienam gājienam (ar rezervi līdz 1.0 s)
VCF_BUDGET = 0.25      # cik no laika drīkst tērēt VCF meklēšanai
ROOT_WIDTH = 12        # cik kandidātus pārbauda saknē
NODE_WIDTH = 8         # cik kandidātus pārbauda dziļākos līmeņos

WIN = 10 ** 9
INF = 10 ** 12

# Rūtiņas vērtības līmeņi (sk. _value)
V_FIVE = 10 ** 8
V_OPEN4 = 10 ** 7      # atvērtais četrinieks vai dubultais četrinieks
V_43 = 10 ** 6         # četrinieks + atvērtais trijnieks
V_33 = 10 ** 5         # dubultais atvērtais trijnieks


class _Timeout(Exception):
    pass


def _opp(p):
    return "O" if p == "X" else "X"


# ---------------------------------------------------------------------------
# Iepriekš aprēķinātas struktūras
# ---------------------------------------------------------------------------

# _WIN_CELLS[r][c][d] — 11 elementu saraksts ap rūtiņu virzienā d:
# None = ārpus laukuma, True = pati rūtiņa, (rr, cc) = cita rūtiņa.
_WIN_CELLS = [[[None] * 4 for _ in range(SIZE)] for _ in range(SIZE)]
for _r in range(SIZE):
    for _c in range(SIZE):
        for _d, (_dr, _dc) in enumerate(DIRS):
            _w = []
            for _k in range(-5, 6):
                if _k == 0:
                    _w.append(True)
                    continue
                _rr, _cc = _r + _k * _dr, _c + _k * _dc
                _w.append((_rr, _cc) if 0 <= _rr < SIZE and 0 <= _cc < SIZE else None)
            _WIN_CELLS[_r][_c][_d] = _w

# Visas līnijas (rindas, kolonnas, diagonāles) ar garumu >= 5
_LINES = []
for _r in range(SIZE):
    _LINES.append([(_r, _c) for _c in range(SIZE)])
for _c in range(SIZE):
    _LINES.append([(_r, _c) for _r in range(SIZE)])
for _s in range(-(SIZE - 5), SIZE - 4):          # diagonāles  r - c = s
    _LINES.append([(_r, _r - _s) for _r in range(SIZE) if 0 <= _r - _s < SIZE])
for _s in range(4, 2 * SIZE - 5):                # antidiagonāles  r + c = s
    _LINES.append([(_r, _s - _r) for _r in range(SIZE) if 0 <= _s - _r < SIZE])
_NL = len(_LINES)
_CELL_LINES = [[[] for _ in range(SIZE)] for _ in range(SIZE)]
for _i, _ln in enumerate(_LINES):
    for (_r, _c) in _ln:
        _CELL_LINES[_r][_c].append(_i)

_TRANS = {
    "X": str.maketrans({"X": "1", "_": "0", "O": "2"}),
    "O": str.maketrans({"O": "1", "_": "0", "X": "2"}),
}


# ---------------------------------------------------------------------------
# Formas vienā virzienā caur rūtiņu (rūtiņa = centrs, indekss 5)
# ---------------------------------------------------------------------------

_SHAPE_TABLE = (
    (7, ("11111",)),
    (6, ("011110",)),
    (5, ("11110", "01111", "10111", "11011", "11101")),
    (4, ("001110", "011100", "010110", "011010")),
    (3, ("11100", "00111", "11010", "01011", "10110", "01101",
         "10011", "11001", "10101", "01110")),
    (2, ("001100", "011000", "000110", "010100", "001010", "010010")),
    (1, ("11000", "01100", "00110", "00011", "10100", "01010",
         "00101", "10010", "01001", "10001")),
)
_shape_cache = {}


def _shape(s):
    """7=pieci, 6=atv. četrinieks, 5=četrinieks, 4=atv. trijnieks,
    3=trijnieks, 2=atv. divnieks, 1=divnieks, 0=nekas."""
    v = _shape_cache.get(s)
    if v is not None:
        return v
    res = 0
    for code, pats in _SHAPE_TABLE:
        for pat in pats:
            start = s.find(pat)
            n = len(pat)
            while start != -1:
                if start <= 5 < start + n:
                    res = code
                    break
                start = s.find(pat, start + 1)
            if res:
                break
        if res:
            break
    _shape_cache[s] = res
    return res


def _window(b, r, c, d, p):
    out = []
    for pos in _WIN_CELLS[r][c][d]:
        if pos is None:
            out.append("2")
        elif pos is True:
            out.append("1")
        else:
            v = b[pos[0]][pos[1]]
            out.append("1" if v == p else ("0" if v == EMPTY else "2"))
    return "".join(out)


def _counts(b, r, c, p):
    cn = [0] * 8
    for d in range(4):
        cn[_shape(_window(b, r, c, d, p))] += 1
    return cn


def _value(cn):
    if cn[7]:
        return V_FIVE
    if cn[6] or cn[5] >= 2:
        return V_OPEN4
    if cn[5] and cn[4]:
        return V_43
    if cn[4] >= 2:
        return V_33
    return cn[5] * 6000 + cn[4] * 5000 + cn[3] * 700 + cn[2] * 500 + cn[1] * 100


# ---------------------------------------------------------------------------
# Līniju novērtējums (statiskā pozīcijas vērtība)
# ---------------------------------------------------------------------------

_LINE_PATS = (
    ("011110", 100000, 2),
    ("211110", 8000, 1), ("011112", 8000, 1),
    ("10111", 8000, 1), ("11011", 8000, 1), ("11101", 8000, 1),
    ("01110", 1000, 0), ("010110", 900, 0), ("011010", 900, 0),
    ("211100", 150, 0), ("001112", 150, 0), ("210110", 150, 0),
    ("011012", 150, 0), ("211010", 150, 0), ("010112", 150, 0),
    ("11001", 150, 0), ("10011", 150, 0), ("10101", 150, 0),
    ("0110", 100, 0), ("01010", 70, 0), ("010010", 40, 0),
)
_line_cache = {}


def _line_eval(s):
    v = _line_cache.get(s)
    if v is not None:
        return v
    if "11111" in s:
        v = (50000000, 5)
    else:
        score = 0
        fours = 0
        for pat, sc, f in _LINE_PATS:
            k = s.count(pat)
            if k:
                score += k * sc
                fours += k * f
        v = (score, fours)
    _line_cache[s] = v
    return v


class _State:
    """Laukuma kopija ar inkrementāli uzturētu novērtējumu."""

    def __init__(self, board):
        self.b = [list(row) for row in board]
        self.ls = {"X": [0] * _NL, "O": [0] * _NL}
        self.lf = {"X": [0] * _NL, "O": [0] * _NL}
        self.tot = {"X": 0, "O": 0}
        self.fours = {"X": 0, "O": 0}
        self.stones = set()
        for r in range(SIZE):
            for c in range(SIZE):
                if self.b[r][c] != EMPTY:
                    self.stones.add((r, c))
        for i in range(_NL):
            self._upd(i)

    def _upd(self, i):
        b = self.b
        raw = "".join([b[r][c] for r, c in _LINES[i]])
        for p in ("X", "O"):
            sc, f = _line_eval("2" + raw.translate(_TRANS[p]) + "2")
            ls = self.ls[p]
            lf = self.lf[p]
            self.tot[p] += sc - ls[i]
            ls[i] = sc
            self.fours[p] += f - lf[i]
            lf[i] = f

    def place(self, r, c, p):
        self.b[r][c] = p
        self.stones.add((r, c))
        for i in _CELL_LINES[r][c]:
            self._upd(i)

    def undo(self, r, c):
        self.b[r][c] = EMPTY
        self.stones.discard((r, c))
        for i in _CELL_LINES[r][c]:
            self._upd(i)

    def evaluate(self, p):
        """Statiskā vērtība no gājiena veicēja `p` skatpunkta."""
        o = _opp(p)
        if self.fours[p] > 0:
            return WIN // 2          # p var tūlīt izveidot pieci
        if self.fours[o] >= 2:
            return -(WIN // 2)       # pretiniekam divi pieci draudi
        return int(self.tot[p] * 1.15) - self.tot[o]

    def candidates(self, radius=2):
        b = self.b
        res = set()
        for (r, c) in self.stones:
            for rr in range(max(0, r - radius), min(SIZE, r + radius + 1)):
                row = b[rr]
                for cc in range(max(0, c - radius), min(SIZE, c + radius + 1)):
                    if row[cc] == EMPTY:
                        res.add((rr, cc))
        return res

    def scored_moves(self, p):
        """[(atk, def, four_flag, r, c)] visiem kandidātiem."""
        o = _opp(p)
        b = self.b
        out = []
        for (r, c) in self.candidates():
            ca = _counts(b, r, c, p)
            cd = _counts(b, r, c, o)
            out.append((_value(ca), _value(cd), ca[5] + ca[6] + ca[7] > 0, r, c))
        return out

    def five_cells_through(self, r, c, p):
        """Brīvās rūtiņas uz līnijām caur (r, c), kurās p izveidotu pieci."""
        res = []
        b = self.b
        for d, (dr, dc) in enumerate(DIRS):
            for k in range(-4, 5):
                if k == 0:
                    continue
                rr, cc = r + k * dr, c + k * dc
                if 0 <= rr < SIZE and 0 <= cc < SIZE and b[rr][cc] == EMPTY:
                    if _shape(_window(b, rr, cc, d, p)) == 7:
                        res.append((rr, cc))
        return res


# ---------------------------------------------------------------------------
# Meklēšana
# ---------------------------------------------------------------------------

def _order_key(m):
    return -(m[0] + m[1] * 0.85)


def _filter_moves(moves, ply):
    """Piespiedu noteikumi. Atgriež (vērtība, None) ja pozīcija izšķirta,
    vai (None, gājienu_saraksts)."""
    best_a = max(m[0] for m in moves)
    if best_a >= V_FIVE:
        return WIN - ply, None
    blocks = [m for m in moves if m[1] >= V_FIVE]
    if blocks:
        if len(blocks) >= 2:
            # vienu piecinieku bloķēt nevar abus — zaudējums, bet spēlējam labāko
            return None, sorted(blocks, key=_order_key)[:1]
        return None, blocks
    if best_a >= V_OPEN4:
        return WIN - ply - 2, None
    threat = max(m[1] for m in moves)
    if threat >= V_OPEN4:
        # pretinieks draud ar atvērto četrinieku: bloķēt vai spēlēt savu četrinieku
        sel = [m for m in moves if m[1] >= V_33 or m[2]]
        if sel:
            return None, sel
    return None, moves


def _negamax(st, p, depth, alpha, beta, deadline, ply):
    if time.perf_counter() > deadline:
        raise _Timeout
    if depth == 0:
        return st.evaluate(p)
    moves = st.scored_moves(p)
    if not moves:
        return 0
    val, moves = _filter_moves(moves, ply)
    if val is not None:
        return val
    moves.sort(key=_order_key)
    o = _opp(p)
    best = -INF
    for m in moves[:NODE_WIDTH]:
        r, c = m[3], m[4]
        st.place(r, c, p)
        try:
            v = -_negamax(st, o, depth - 1, -beta, -alpha, deadline, ply + 1)
        finally:
            st.undo(r, c)
        if v > best:
            best = v
        if v > alpha:
            alpha = v
        if alpha >= beta:
            break
    return best


def _vcf(st, p, depth, deadline):
    """Uzvara ar nepārtrauktiem četriniekiem. Atgriež pirmo gājienu vai None."""
    if depth <= 0 or time.perf_counter() > deadline:
        return None
    o = _opp(p)
    b = st.b
    fours = []
    for (r, c) in st.candidates():
        cn = _counts(b, r, c, p)
        if cn[7] or cn[6] or cn[5] >= 2:
            return (r, c)
        if cn[5]:
            fours.append((-(cn[4] * 10 + cn[3]), r, c))
    fours.sort()
    for _, r, c in fours:
        st.place(r, c, p)
        blocks = st.five_cells_through(r, c, p)
        ok = len(blocks) == 1 and st.fours[o] == 0
        res = None
        if ok:
            br, bc = blocks[0]
            st.place(br, bc, o)
            if st.fours[o] == 0:
                res = _vcf(st, p, depth - 1, deadline)
            st.undo(br, bc)
        st.undo(r, c)
        if res is not None:
            return (r, c)
    return None


def _search(board, p, time_limit=TIME_LIMIT, use_vcf=True):
    """Atgriež (gājiens, vērtība no p skatpunkta)."""
    start = time.perf_counter()
    deadline = start + time_limit
    st = _State(board)

    if not st.stones:
        return (SIZE // 2, SIZE // 2), 0

    moves = st.scored_moves(p)
    if not moves:
        for r in range(SIZE):
            for c in range(SIZE):
                if st.b[r][c] == EMPTY:
                    return (r, c), 0
        return (SIZE // 2, SIZE // 2), 0

    moves.sort(key=_order_key)
    val, filtered = _filter_moves(moves, 0)
    if val is not None:
        # tūlītēja uzvara vai atvērtais četrinieks
        best = max(moves, key=lambda m: (m[0], m[1]))
        return (best[3], best[4]), val
    if len(filtered) == 1:
        m = filtered[0]
        return (m[3], m[4]), 0

    if use_vcf:
        win = _vcf(st, p, 12, min(deadline, start + VCF_BUDGET))
        if win is not None:
            return win, WIN - 10

    root = sorted(filtered, key=_order_key)[:ROOT_WIDTH]
    o = _opp(p)
    best_move = (root[0][3], root[0][4])
    best_val = -INF
    depth = 1
    while depth <= 12:
        alpha = -INF
        cur_best = None
        try:
            for m in root:
                r, c = m[3], m[4]
                st.place(r, c, p)
                try:
                    v = -_negamax(st, o, depth - 1, -INF, -alpha, deadline, 1)
                finally:
                    st.undo(r, c)
                if v > alpha:
                    alpha = v
                    cur_best = m
        except _Timeout:
            if cur_best is not None and cur_best is root[0]:
                pass  # iepriekšējais labākais joprojām labākais
            elif cur_best is not None and alpha > best_val - 1:
                best_move = (cur_best[3], cur_best[4])
            break
        best_move = (cur_best[3], cur_best[4])
        best_val = alpha
        # labāko gājienu pārbaudām pirmo nākamajā iterācijā
        root.remove(cur_best)
        root.insert(0, cur_best)
        if abs(alpha) >= WIN - 100:
            break
        depth += 1
    return best_move, best_val


# ---------------------------------------------------------------------------
# Obligātās funkcijas
# ---------------------------------------------------------------------------

def get_move(board, player):
    """Atgriež (rinda, kolonna) brīvai rūtiņai."""
    move, _ = _search(board, player)
    r, c = move
    if board[r][c] != EMPTY:  # drošības tīkls — nekad nevajadzētu notikt
        for rr in range(SIZE):
            for cc in range(SIZE):
                if board[rr][cc] == EMPTY:
                    return (rr, cc)
    return (int(r), int(c))


# Sākuma pozīcijas: (rinda, kolonna, simbols); laukuma centrs ir (7, 7).
_OPENINGS = (
    [(7, 7, "X"), (7, 8, "O"), (8, 9, "X")],
    [(7, 7, "X"), (8, 8, "O"), (6, 9, "X")],
    [(7, 7, "X"), (6, 7, "O"), (8, 9, "X")],
    [(7, 7, "X"), (8, 7, "O"), (6, 9, "X")],
)


def swap2_propose(board):
    """Novieto 3 figūras (divi X, viens O) uz tukša laukuma."""
    cells = [(r, c) for r in range(SIZE) for c in range(SIZE) if board[r][c] == EMPTY]
    cells.sort(key=lambda rc: abs(rc[0] - 7) + abs(rc[1] - 7))
    if len(cells) < 3:
        return []
    for opening in random.sample(_OPENINGS, len(_OPENINGS)):
        free = [(r, c, s) for r, c, s in opening if board[r][c] == EMPTY]
        if len(free) == 3:
            return free
    return [(cells[0][0], cells[0][1], "X"), (cells[1][0], cells[1][1], "O"),
            (cells[2][0], cells[2][1], "X")]


def _next_symbol(board):
    nx = sum(row.count("X") for row in board)
    no = sum(row.count("O") for row in board)
    return "X" if nx == no else "O"


def swap2_respond(board):
    """Izvēlas TAKE_X, TAKE_O vai PLACE_TWO."""
    # Pēc 3 figūrām gājiens ir O. Vērtējam no O skatpunkta.
    _, v = _search(board, "O", time_limit=0.35, use_vcf=False)
    if v > 300:
        return {"action": "TAKE_O"}
    if v < -300:
        return {"action": "TAKE_X"}
    # Pozīcija līdzsvarota — pieliekam O labāko gājienu un X labāko atbildi
    work = [row[:] for row in board]
    (ro, co), _ = _search(work, "O", time_limit=0.25, use_vcf=False)
    work[ro][co] = "O"
    (rx, cx), _ = _search(work, "X", time_limit=0.25, use_vcf=False)
    if (rx, cx) == (ro, co) or work[rx][cx] != EMPTY:
        for r in range(SIZE):
            for c in range(SIZE):
                if work[r][c] == EMPTY:
                    rx, cx = r, c
                    break
            else:
                continue
            break
    return {"action": "PLACE_TWO", "moves": [(rx, cx, "X"), (ro, co, "O")]}


def swap2_final_choice(board):
    """Pēc PLACE_TWO izvēlas 'X' vai 'O'."""
    to_move = _next_symbol(board)
    _, v = _search(board, to_move, time_limit=0.7, use_vcf=True)
    if to_move == "O":
        return "O" if v > 0 else "X"
    return "X" if v > 0 else "O"


# ===========================================================================
# GRAFISKAIS INTERFEISS (GUI)
# ---------------------------------------------------------------------------
# Palaižas TIKAI ar:  python bot.py
# Importējot šo moduli (turnīra dzinējs), GUI netiek palaists un tkinter
# netiek ielādēts. GUI tikai nolasa laukumu, padod to augstāk esošajām
# bota funkcijām un attēlo rezultātu — AI loģika GUI kodā nav.
# ===========================================================================

GUI_CELL = 38
GUI_MARGIN = 30
GUI_TIME_LIMIT = 1.0
HUMAN = "Cilvēks"


def _gui_discover_bots():
    import glob
    import importlib.util
    import os
    import sys
    here = os.path.dirname(os.path.abspath(__file__))
    bots = {f"{BOT_NAME} (šis fails)": sys.modules[__name__]}
    for path in sorted(glob.glob(os.path.join(here, "studenti", "*", "bot.py"))):
        if os.path.abspath(path) == os.path.abspath(__file__):
            continue
        folder = os.path.basename(os.path.dirname(path))
        try:
            spec = importlib.util.spec_from_file_location(f"bot_{folder}", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            bots[f"{getattr(mod, 'BOT_NAME', folder)} ({folder})"] = mod
        except Exception as exc:
            print(f"Neizdevās ielādēt {path}: {exc}")
    return bots


def _gui_winning_line(board, r, c):
    p = board[r][c]
    for dr, dc in DIRS:
        cells = [(r, c)]
        for s in (1, -1):
            rr, cc = r + s * dr, c + s * dc
            while 0 <= rr < SIZE and 0 <= cc < SIZE and board[rr][cc] == p:
                cells.append((rr, cc))
                rr += s * dr
                cc += s * dc
        if len(cells) >= 5:
            return cells
    return None


def _gui_is_free(board, r, c):
    return (isinstance(r, int) and isinstance(c, int)
            and 0 <= r < SIZE and 0 <= c < SIZE and board[r][c] == EMPTY)


def run_gui():
    import copy
    import threading
    import tkinter as tk
    from tkinter import ttk

    class App:
        def __init__(self, root):
            self.root = root
            root.title("5-rindu Tic-Tac-Toe (Swap2)")
            self.bots = _gui_discover_bots()
            options = [HUMAN] + list(self.bots)

            side = ttk.Frame(root, padding=10)
            side.pack(side=tk.RIGHT, fill=tk.Y)
            ttk.Label(side, text="1. spēlētājs (sāk atklātni):").pack(anchor="w")
            self.p1_var = tk.StringVar(value=HUMAN)
            ttk.Combobox(side, textvariable=self.p1_var, values=options,
                         state="readonly", width=32).pack(anchor="w", pady=(0, 8))
            ttk.Label(side, text="2. spēlētājs:").pack(anchor="w")
            self.p2_var = tk.StringVar(value=options[1])
            ttk.Combobox(side, textvariable=self.p2_var, values=options,
                         state="readonly", width=32).pack(anchor="w", pady=(0, 8))
            ttk.Button(side, text="Jauna spēle", command=self.new_game).pack(anchor="w", pady=4)

            self.colors_lbl = ttk.Label(side, text="", justify="left")
            self.colors_lbl.pack(anchor="w", pady=(10, 4))
            self.status = ttk.Label(side, text="", wraplength=260, justify="left",
                                    font=("TkDefaultFont", 10, "bold"))
            self.status.pack(anchor="w", pady=4)
            self.actions = ttk.Frame(side)
            self.actions.pack(anchor="w", pady=6)
            ttk.Label(side, text="Žurnāls:").pack(anchor="w", pady=(10, 0))
            self.log = tk.Text(side, width=36, height=18, state="disabled", font=("Courier", 9))
            self.log.pack(anchor="w", fill=tk.BOTH, expand=True)

            px = GUI_MARGIN * 2 + GUI_CELL * SIZE
            self.canvas = tk.Canvas(root, width=px, height=px, bg="#DDB56A", highlightthickness=0)
            self.canvas.pack(side=tk.LEFT, padx=10, pady=10)
            self.canvas.bind("<Button-1>", self.on_click)

            self.game_id = 0
            self.new_game()

        # ---------- palīgfunkcijas ----------
        def write_log(self, text):
            self.log.configure(state="normal")
            self.log.insert(tk.END, text + "\n")
            self.log.see(tk.END)
            self.log.configure(state="disabled")

        def set_status(self, text):
            self.status.configure(text=text)

        def clear_actions(self):
            for w in self.actions.winfo_children():
                w.destroy()

        def add_action(self, text, cmd):
            ttk.Button(self.actions, text=text, command=cmd).pack(fill=tk.X, pady=2)

        def is_human(self, idx):
            return self.players[idx] is None

        def turn_index(self):
            sym = _next_symbol(self.board)
            return sym, (0 if self.color[0] == sym else 1)

        # ---------- spēles sākums ----------
        def new_game(self):
            self.game_id += 1
            self.board = [[EMPTY] * SIZE for _ in range(SIZE)]
            self.names = [self.p1_var.get(), self.p2_var.get()]
            self.players = [None if n == HUMAN else self.bots[n] for n in self.names]
            self.color = {0: None, 1: None}
            self.pending = []
            self.last = None
            self.win_cells = None
            self.phase = "propose"
            self.busy = False
            self.clear_actions()
            self.log.configure(state="normal")
            self.log.delete("1.0", tk.END)
            self.log.configure(state="disabled")
            self.write_log(f"1: {self.names[0]}")
            self.write_log(f"2: {self.names[1]}")
            self.update_colors()
            self.draw()
            self.advance()

        def update_colors(self):
            c = lambda i: self.color[i] or "?"
            self.colors_lbl.configure(
                text=f"1. {self.names[0]}: {c(0)}\n2. {self.names[1]}: {c(1)}")

        # ---------- zīmēšana ----------
        def xy(self, r, c):
            return (GUI_MARGIN + c * GUI_CELL + GUI_CELL // 2,
                    GUI_MARGIN + r * GUI_CELL + GUI_CELL // 2)

        def draw(self):
            cv = self.canvas
            cv.delete("all")
            left = GUI_MARGIN
            right = GUI_MARGIN + GUI_CELL * SIZE
            top = GUI_MARGIN
            bottom = GUI_MARGIN + GUI_CELL * SIZE
            for i in range(SIZE):
                pos = left + i * GUI_CELL
                cv.create_line(pos, top, pos, bottom)
                cv.create_line(left, pos, right, pos)
                cv.create_text(pos + GUI_CELL // 2, GUI_MARGIN - 18, text=str(i),
                               font=("TkDefaultFont", 8))
                cv.create_text(GUI_MARGIN - 18, pos + GUI_CELL // 2, text=str(i),
                               font=("TkDefaultFont", 8))
            cv.create_line(right, top, right, bottom)
            cv.create_line(left, bottom, right, bottom)
            for (r, c) in ((3, 3), (3, 11), (7, 7), (11, 3), (11, 11)):
                x, y = self.xy(r, c)
                cv.create_oval(x - 3, y - 3, x + 3, y + 3, fill="black")
            for r in range(SIZE):
                for c in range(SIZE):
                    s = self.board[r][c]
                    if s == EMPTY:
                        continue
                    x, y = self.xy(r, c)
                    cv.create_text(x, y, text=s, fill="black" if s == "X" else "#555",
                                   font=("Arial", 20, "bold"))
            if self.last:
                x, y = self.xy(*self.last)
                cv.create_oval(x - 4, y - 4, x + 4, y + 4, fill="red", outline="red")
            if self.win_cells:
                for (r, c) in self.win_cells:
                    x, y = self.xy(r, c)
                    cv.create_rectangle(x - GUI_CELL // 2 + 3, y - GUI_CELL // 2 + 3,
                                        x + GUI_CELL // 2 - 3, y + GUI_CELL // 2 - 3,
                                        outline="red", width=3)

        # ---------- spēles plūsma ----------
        def advance(self):
            self.clear_actions()
            self.update_colors()
            if self.phase == "propose":
                if self.is_human(0):
                    self.pending = ["X", "X", "O"]
                    self.set_status("1. spēlētājs: novietojiet 2× X un 1× O (tagad: X).")
                else:
                    self.set_status("1. spēlētājs (bots) novieto 3 figūras...")
                    self.run_bot(0, "swap2_propose", self.on_propose)
            elif self.phase == "respond":
                if self.is_human(1):
                    self.set_status("2. spēlētājs: izvēlieties darbību.")
                    self.add_action("Ņemt X (TAKE_X)",
                                    lambda: self.apply_respond({"action": "TAKE_X"}))
                    self.add_action("Ņemt O (TAKE_O)",
                                    lambda: self.apply_respond({"action": "TAKE_O"}))
                    self.add_action("Novietot vēl divas (PLACE_TWO)", self.human_place_two)
                else:
                    self.set_status("2. spēlētājs (bots) izvēlas...")
                    self.run_bot(1, "swap2_respond", self.apply_respond)
            elif self.phase == "place_two":
                self.set_status(f"2. spēlētājs: novietojiet {self.pending[0]}.")
            elif self.phase == "final":
                if self.is_human(0):
                    self.set_status("1. spēlētājs: izvēlieties savu krāsu.")
                    self.add_action("Spēlēt ar X", lambda: self.apply_final("X"))
                    self.add_action("Spēlēt ar O", lambda: self.apply_final("O"))
                else:
                    self.set_status("1. spēlētājs (bots) izvēlas krāsu...")
                    self.run_bot(0, "swap2_final_choice", self.apply_final)
            elif self.phase == "play":
                sym, idx = self.turn_index()
                if self.is_human(idx):
                    self.set_status(f"Jūsu gājiens ({sym}).")
                else:
                    self.set_status(f"{self.names[idx]} domā ({sym})...")
                    self.run_bot(idx, "get_move", self.on_bot_move, sym)

        def run_bot(self, idx, func_name, callback, *extra):
            mod = self.players[idx]
            board_copy = copy.deepcopy(self.board)
            gid = self.game_id
            box = {}

            def work():
                t = time.perf_counter()
                try:
                    box["res"] = getattr(mod, func_name)(board_copy, *extra)
                except Exception as exc:
                    box["err"] = exc
                box["dt"] = time.perf_counter() - t

            self.busy = True
            th = threading.Thread(target=work, daemon=True)
            th.start()

            def poll():
                if gid != self.game_id:
                    return
                if th.is_alive():
                    self.root.after(30, poll)
                    return
                self.busy = False
                if box["dt"] > GUI_TIME_LIMIT:
                    self.write_log(f"! {func_name}: {box['dt']:.2f}s > {GUI_TIME_LIMIT}s")
                if "err" in box:
                    self.forfeit(idx, f"kļūda {func_name}: {box['err']}")
                    return
                callback(box["res"])

            self.root.after(30, poll)

        def forfeit(self, idx, reason):
            self.phase = "over"
            self.clear_actions()
            self.write_log(f"{self.names[idx]} zaudē: {reason}")
            self.set_status(f"{self.names[idx]} zaudē ({reason}). Uzvar {self.names[1 - idx]}.")

        # ---------- atklātne ----------
        def on_propose(self, res):
            try:
                assert isinstance(res, (list, tuple)) and len(res) == 3
                assert sorted(str(m[2]) for m in res) == ["O", "X", "X"]
                seen = set()
                for r, c, s in res:
                    assert _gui_is_free(self.board, r, c) and (r, c) not in seen
                    seen.add((r, c))
            except Exception:
                self.forfeit(0, f"nederīgs swap2_propose: {res!r}")
                return
            for r, c, s in res:
                self.board[r][c] = s
                self.write_log(f"atklātne: {s} ({r},{c})")
            self.draw()
            self.phase = "respond"
            self.advance()

        def apply_respond(self, res):
            action = res.get("action") if isinstance(res, dict) else None
            if action in ("TAKE_X", "TAKE_O"):
                sym = "X" if action == "TAKE_X" else "O"
                self.color[1] = sym
                self.color[0] = _opp(sym)
                self.write_log(f"2. spēlētājs: {action}")
                self.phase = "play"
                self.advance()
                return
            if action == "PLACE_TWO":
                try:
                    moves = res["moves"]
                    assert len(moves) == 2
                    (r1, c1, s1), (r2, c2, s2) = moves
                    assert sorted([s1, s2]) == ["O", "X"]
                    assert _gui_is_free(self.board, r1, c1) and _gui_is_free(self.board, r2, c2)
                    assert (r1, c1) != (r2, c2)
                except Exception:
                    self.forfeit(1, f"nederīgs swap2_respond: {res!r}")
                    return
                for r, c, s in moves:
                    self.board[r][c] = s
                    self.write_log(f"PLACE_TWO: {s} ({r},{c})")
                self.draw()
                self.phase = "final"
                self.advance()
                return
            self.forfeit(1, f"nederīgs swap2_respond: {res!r}")

        def human_place_two(self):
            self.write_log("2. spēlētājs: PLACE_TWO")
            self.pending = ["X", "O"]
            self.phase = "place_two"
            self.advance()

        def apply_final(self, sym):
            if sym not in ("X", "O"):
                self.forfeit(0, f"nederīgs swap2_final_choice: {sym!r}")
                return
            self.color[0] = sym
            self.color[1] = _opp(sym)
            self.write_log(f"1. spēlētājs izvēlas: {sym}")
            self.phase = "play"
            self.advance()

        # ---------- pamatspēle ----------
        def on_bot_move(self, res):
            sym, idx = self.turn_index()
            try:
                r, c = res
                r, c = int(r), int(c)
                assert _gui_is_free(self.board, r, c)
            except Exception:
                self.forfeit(idx, f"nederīgs gājiens: {res!r}")
                return
            self.make_move(r, c, sym, idx)

        def make_move(self, r, c, sym, idx):
            self.board[r][c] = sym
            self.last = (r, c)
            self.write_log(f"{sym} ({r},{c})")
            line = _gui_winning_line(self.board, r, c)
            if line:
                self.win_cells = line
                self.phase = "over"
                self.draw()
                self.set_status(f"Uzvar {self.names[idx]} ({sym})!")
                self.write_log(f"Uzvar {self.names[idx]} ({sym})")
                return
            if all(EMPTY not in row for row in self.board):
                self.phase = "over"
                self.draw()
                self.set_status("Neizšķirts!")
                self.write_log("Neizšķirts")
                return
            self.draw()
            self.advance()

        def on_click(self, event):
            if self.busy or self.phase == "over":
                return
            c = (event.x - GUI_MARGIN) // GUI_CELL
            r = (event.y - GUI_MARGIN) // GUI_CELL
            if not _gui_is_free(self.board, r, c):
                return
            if self.phase == "propose" and self.is_human(0) and self.pending:
                s = self.pending.pop(0)
                self.board[r][c] = s
                self.write_log(f"atklātne: {s} ({r},{c})")
                self.draw()
                if self.pending:
                    self.set_status(f"1. spēlētājs: novietojiet nākamo figūru ({self.pending[0]}).")
                else:
                    self.phase = "respond"
                    self.advance()
            elif self.phase == "place_two" and self.is_human(1) and self.pending:
                s = self.pending.pop(0)
                self.board[r][c] = s
                self.write_log(f"PLACE_TWO: {s} ({r},{c})")
                self.draw()
                if not self.pending:
                    self.phase = "final"
                self.advance()
            elif self.phase == "play":
                sym, idx = self.turn_index()
                if self.is_human(idx):
                    self.make_move(r, c, sym, idx)

    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    run_gui()