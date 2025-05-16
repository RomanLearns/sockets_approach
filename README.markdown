# Tic Tac Toe WebSocket Game

This is a multiplayer Tic Tac Toe game built using Python for the server with WebSockets and React for the client-side interface. Players can connect and play on the same machine or across different machines on the same Wi-Fi network.

## Prerequisites

- **Python 3.11+** with the `websockets` package:
  ```bash
  pip install websockets
  ```
- **Node.js and npm** for the React client.
- A modern web browser (e.g., Chrome, Firefox).

## Setup

### 1. Clone the Repository
```bash
git clone <repository-url>
cd <repository-folder>
```

### 2. Set Up the Server
- Navigate to the server directory (where `server_websocket.py` and `config.py` are located).
- Install the required Python package:
  ```bash
  pip install websockets
  ```
- Ensure `config.py` has `SERVER_HOST = '0.0.0.0'` and `SERVER_PORT = 8765` for network accessibility.

### 3. Set Up the Client
- Navigate to the client directory (where `index.js`, `App.js`, etc., are located).
- Install dependencies:
  ```bash
  npm install
  ```
- Ensure `config.js` (if present) sets `SERVER_URL = 'ws://localhost:8765'` for local testing, or adjust for network play (see below).

## Running the Game

### On a Single Machine (Two Terminals)

1. **Start the Server**:
   - Open a terminal and navigate to the server directory.
   - Run:
     ```bash
     python server_websocket.py
     ```
   - You should see: `--- TicTacToe WebSocket Server Starting ---` and `Listening on 0.0.0.0:8765`.

2. **Start the Client**:
   - Open a second terminal and navigate to the client directory.
   - Run:
     ```bash
     npm start
     ```
   - This will launch the app at `http://localhost:3000`. Open it in your browser.

3. **Play the Game**:
   - Enter a name in the input field and click "Enter Lobby".
   - One player clicks "Create Game" to start a new game.
   - The second player selects an available game from the list and clicks "Join".
   - Take turns clicking cells on the 3x3 board to place 'X' or 'O'. The game ends with a win or tie.

### On Different Machines on the Same Wi-Fi

1. **Find the Server Machine's IP**:
   - On the machine running the server, open a terminal and type:
     ```bash
     ipconfig (Windows) or ifconfig/ip (Mac/Linux)
     ```
   - Note the local IP address (e.g., `192.168.1.100`).

2. **Start the Server**:
   - On the server machine, run:
     ```bash
     python server_websocket.py
     ```
   - Ensure `SERVER_HOST = '0.0.0.0'` in `config.py` to allow external connections.

3. **Start the Client on All Machines**:
   - On each machine (including the server), navigate to the client directory.
   - Run:
     ```bash
     npm start
     ```
   - Open `http://localhost:3000` in each browser.

4. **Connect to the Server**:
   - On client machines, update `config.js` (if used) to `SERVER_URL = 'ws://<server-ip>:8765'` (e.g., `ws://192.168.1.100:8765`).
   - Alternatively, modify the `serverUrl` prop in `App.js` or `WebSocketContext.js` to use the server’s IP.

5. **Play the Game**:
   - Follow the same steps as above: one player creates a game, another joins, and take turns.

## Troubleshooting
- **Connection Issues**: Ensure the server is running and the port (8765) is not blocked by a firewall. Check client console logs for WebSocket errors.
- **Cross-Machine Play**: Verify all machines are on the same Wi-Fi network and the server IP is correct.

## How to Play
- Enter a unique name to join the lobby.
- Create or join a game to start playing.
- Click a cell to place your mark ('X' or 'O').
- The game ends when someone wins (three in a row) or it’s a tie.
- Use "Back to Lobby" to return and start a new game.

Happy gaming!