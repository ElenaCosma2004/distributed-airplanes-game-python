# Running the Project

## 1. Start the Server

From the root directory of the project, run:

```bash
docker compose up --build
```

The server will start on port `8708`.

Example output:

```text
[SERVER] Am incarcat 2 configuratii.
[SERVER] Joc resetat cu configuratia: config1.txt
[SERVER] Listening on 0.0.0.0:8708
```

---

## 2. Start a Client

Open a new terminal and run:

```bash
python3 client.py 127.0.0.1 8708
```

Enter a unique player name when prompted.

Example:

```text
Nume jucator: Ana
```

To connect additional clients, open new terminals and run the same command.

---

# Available Commands

## Shoot

```text
SHOOT <row> <column>
```

Example:

```text
SHOOT 2 5
```

---

## Quit

```text
QUIT
```

---

# Server Responses

```text
0 -> no airplane hit
1 -> airplane body hit
X -> airplane head hit
```

Possible error responses:

```text
ERR NAME_TAKEN
ERR INVALID_COORDS
ERR OUT_OF_RANGE
ERR ALREADY_SHOT
ERR UNKNOWN_COMMAND
```

Winner notification:

```text
WINNER <player_name>
```

Automatic reset notification:

```text
RESET NEW_GAME
```
