#!/usr/bin/env python3
import socket
import threading
import sys


HOST = "127.0.0.1"
PORT = 8708


def receive_messages(sock: socket.socket):
    """
    Thread separat care asculta permanent mesajele de la server.
    Astfel putem primi si mesaje globale, de exemplu WINNER sau RESET.
    """
    try:
        while True:
            data = sock.recv(1024)
            if not data:
                print("\n[CLIENT] Serverul a inchis conexiunea.")
                break

            messages = data.decode("utf-8").strip().split("\n")
            for msg in messages:
                if msg:
                    print(f"\n[SERVER] {msg}")
                    print("> ", end="", flush=True)

    except OSError:
        pass


def main():
    host = HOST
    port = PORT

    if len(sys.argv) >= 2:
        host = sys.argv[1]

    if len(sys.argv) >= 3:
        port = int(sys.argv[2])

    name = input("Nume jucator: ").strip()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        print(f"[CLIENT] Conectare la {host}:{port} ...")
        sock.connect((host, port))

        receiver = threading.Thread(
            target=receive_messages,
            args=(sock,),
            daemon=True
        )
        receiver.start()

        sock.sendall(f"CONNECT {name}\n".encode("utf-8"))

        print("[CLIENT] Comenzi disponibile:")
        print("  SHOOT linie coloana")
        print("  QUIT")
        print("Exemplu: SHOOT 2 5")

        while True:
            command = input("> ").strip()

            if not command:
                continue

            if command.lower() == "quit":
                sock.sendall(b"QUIT\n")
                break

            if not command.upper().startswith("SHOOT "):
                print("[CLIENT] Comanda invalida. Foloseste: SHOOT linie coloana")
                continue

            sock.sendall((command + "\n").encode("utf-8"))

    print("[CLIENT] Conexiune inchisa.")


if __name__ == "__main__":
    main()




