#!/usr/bin/env python3
import socket
import threading
import random
import os
from typing import List, Dict, Set, Tuple


HOST = "0.0.0.0"
PORT = 8708

CONFIG_DIR = "configs"
BOARD_SIZE = 10
PLANES_TO_WIN = 3


class Player:
    def __init__(self, name: str, conn: socket.socket, addr):
        self.name = name
        self.conn = conn
        self.addr = addr

        # cate avioane/capete distincte a doborat clientul
        self.kills = 0

        # coordonate deja trase de client
        self.shots: Set[Tuple[int, int]] = set()

        # capete de avion deja lovite de client: A, B, C
        self.killed_planes: Set[str] = set()


class GameServer:
    def __init__(self):
        # lista de configuratii: (nume_fisier, tabla)
        self.configs: List[Tuple[str, List[List[str]]]] = []

        self.board: List[List[str]] = []
        self.players: Dict[str, Player] = {}

        # protejeaza tabla, scorurile si lista de clienti
        self.lock = threading.Lock()

    def load_configs(self):
        """
        Citeste toate fisierele .txt din CONFIG_DIR.
        Fiecare fisier trebuie sa contina o matrice 10x10.

        Valori acceptate:
        - 0 = gol / apa
        - 1 = corp avion
        - litere, ex A/B/C = capete de avion
        """
        if not os.path.isdir(CONFIG_DIR):
            raise RuntimeError(f"Directorul {CONFIG_DIR} nu exista.")

        for filename in os.listdir(CONFIG_DIR):
            if not filename.endswith(".txt"):
                continue

            path = os.path.join(CONFIG_DIR, filename)
            board = []

            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip().replace(" ", "")
                    if line:
                        board.append(list(line))

            if len(board) != BOARD_SIZE or any(len(row) != BOARD_SIZE for row in board):
                raise RuntimeError(f"Configuratie invalida in {path}")

            # validare caractere
            heads = set()

            for row in board:
                for cell in row:
                    if cell == "0" or cell == "1":
                        continue

                    if cell.isalpha() and len(cell) == 1:
                        heads.add(cell.upper())
                    else:
                        raise RuntimeError(f"Caracter invalid '{cell}' in {path}")

            if len(heads) != PLANES_TO_WIN:
                raise RuntimeError(
                    f"Configuratia {path} trebuie sa aiba exact "
                    f"{PLANES_TO_WIN} capete de avion distincte, gasite: {heads}"
                )

            self.configs.append((filename, board))

        if not self.configs:
            raise RuntimeError("Nu exista configuratii valide.")

        print(f"[SERVER] Am incarcat {len(self.configs)} configuratii.")

    def reset_game(self):
        """
        Alege o tabla noua si reseteaza scorurile/loviturile clientilor.
        Trebuie apelata doar cu lock-ul luat.
        """
        config_name, selected_board = random.choice(self.configs)
        self.board = [row[:] for row in selected_board]

        for player in self.players.values():
            player.kills = 0
            player.shots.clear()
            player.killed_planes.clear()

        print(f"[SERVER] Joc resetat cu configuratia: {config_name}")

    def send_line(self, conn: socket.socket, message: str):
        try:
            conn.sendall((message + "\n").encode("utf-8"))
        except OSError:
            pass

    def broadcast(self, message: str):
        """
        Trimite un mesaj tuturor clientilor conectati.
        """
        for player in list(self.players.values()):
            self.send_line(player.conn, message)

    def remove_player(self, name: str):
        with self.lock:
            if name in self.players:
                print(f"[SERVER] Client deconectat: {name}")
                del self.players[name]

    def handle_connect(self, conn: socket.socket, addr, parts: List[str]) -> str | None:
        if len(parts) != 2:
            self.send_line(conn, "ERR USAGE CONNECT <name>")
            return None

        name = parts[1].strip()

        if not name:
            self.send_line(conn, "ERR INVALID_NAME")
            return None

        with self.lock:
            if name in self.players:
                self.send_line(conn, "ERR NAME_TAKEN")
                return None

            player = Player(name, conn, addr)
            self.players[name] = player

        self.send_line(conn, f"OK CONNECTED {name}")
        print(f"[SERVER] Client conectat: {name} de la {addr}")
        return name

    def handle_shoot(self, player_name: str, parts: List[str]):
        if len(parts) != 3:
            with self.lock:
                player = self.players.get(player_name)
            if player:
                self.send_line(player.conn, "ERR USAGE SHOOT <row> <col>")
            return

        try:
            row = int(parts[1])
            col = int(parts[2])
        except ValueError:
            with self.lock:
                player = self.players.get(player_name)
            if player:
                self.send_line(player.conn, "ERR INVALID_COORDS")
            return

        if not (0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE):
            with self.lock:
                player = self.players.get(player_name)
            if player:
                self.send_line(player.conn, "ERR OUT_OF_RANGE")
            return

        with self.lock:
            player = self.players.get(player_name)
            if player is None:
                return

            coord = (row, col)

            if coord in player.shots:
                self.send_line(player.conn, "ERR ALREADY_SHOT")
                return

            player.shots.add(coord)

            cell = self.board[row][col].upper()

            if cell == "0":
                result = "0"

            elif cell == "1":
                result = "1"

            elif cell.isalpha():
                # Litera inseamna cap de avion.
                # Fiecare client are propria evidenta a avioanelor doborate.
                result = "X"

                if cell not in player.killed_planes:
                    player.killed_planes.add(cell)
                    player.kills += 1

            else:
                result = "0"

            self.send_line(player.conn, result)

            print(
                f"[SERVER] {player.name} a tras la ({row}, {col}) -> {result}; "
                f"avioane doborate: {player.kills}/{PLANES_TO_WIN}"
            )

            if player.kills >= PLANES_TO_WIN:
                winner = player.name

                self.broadcast(f"WINNER {winner}")
                self.reset_game()
                self.broadcast("RESET NEW_GAME")

    def client_thread(self, conn: socket.socket, addr):
        player_name = None

        try:
            file = conn.makefile("r", encoding="utf-8")

            self.send_line(conn, "WELCOME AVIOANE_SERVER")
            self.send_line(conn, "USE CONNECT <name>")

            for line in file:
                line = line.strip()
                if not line:
                    continue

                parts = line.split()
                command = parts[0].upper()

                if command == "CONNECT":
                    if player_name is not None:
                        self.send_line(conn, "ERR ALREADY_CONNECTED")
                        continue

                    player_name = self.handle_connect(conn, addr, parts)

                elif command == "SHOOT":
                    if player_name is None:
                        self.send_line(conn, "ERR NOT_CONNECTED")
                        continue

                    self.handle_shoot(player_name, parts)

                elif command == "QUIT":
                    self.send_line(conn, "OK BYE")
                    break

                else:
                    self.send_line(conn, "ERR UNKNOWN_COMMAND")

        except OSError:
            pass

        finally:
            if player_name:
                self.remove_player(player_name)

            try:
                conn.close()
            except OSError:
                pass

    def start(self):
        self.load_configs()

        with self.lock:
            self.reset_game()

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((HOST, PORT))
            server_socket.listen()

            print(f"[SERVER] Listening on {HOST}:{PORT}")

            while True:
                conn, addr = server_socket.accept()
                thread = threading.Thread(
                    target=self.client_thread,
                    args=(conn, addr),
                    daemon=True
                )
                thread.start()


if __name__ == "__main__":
    server = GameServer()
    server.start()

