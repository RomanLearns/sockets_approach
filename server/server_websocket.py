import asyncio
import websockets
import json
import sys
import uuid as sys_uuid
import time
from typing import Dict, Any, Optional

# Ensure config.py and tictactoe_game.py are accessible
from config import SERVER_HOST, SERVER_PORT, LOBBY_CONCEPT_NAME, GAME_CHANNEL_PREFIX
from tictactoe_game import TicTacToeGame
import logging

logging.basicConfig(level=logging.DEBUG) # Set logging level to DEBUG
logging.getLogger("websockets").setLevel(logging.DEBUG) # Specifically enable websockets logs

# Shared server state
# Client state: {uuid: {'name': str, 'websocket': WebSocketServerProtocol, 'current_game': str or None, 'status': str}}
CLIENTS: Dict[str, Dict[str, Any]] = {}
GAMES: Dict[str, TicTacToeGame] = {}
AVAILABLE_GAMES: Dict[str, Dict[str, str]] = {} # {game_id: {'game_id': id, 'player1_name': name, 'player1_uuid': uuid}}

# Lock for protecting access to shared data structures
STATE_LOCK = asyncio.Lock()

# Add this near the top of server_websocket.py
async def super_minimal_handler(websocket, path):
    """A handler that just prints and immediately finishes its execution."""
    print(f"[Server Super Minimal Handler] Connection received from {websocket.remote_address}")
    # We don't await websocket.recv() or websocket.send() or websocket.wait_closed()
    # Just let the handler function return. The websockets library will handle the connection lifecycle after this.
    pass


# Add this near the top of server_websocket.py
async def simple_test_handler(websocket, path):
    """A very basic handler to test if websockets.serve calls handlers correctly."""
    print(f"[Server Test Handler] Connection received from {websocket.remote_address} on path {path}")
    try:
        # Send a simple message back
        await websocket.send(json.dumps({"action": "info", "message": "Connected to test handler!"}))
        # Just keep the connection open until the client closes it
        await websocket.wait_closed()
    except Exception as e:
        print(f"[Server Test Handler] Error during test connection: {e}")
    finally:
        print(f"[Server Test Handler] Connection closed from {websocket.remote_address}")

async def send_message(websocket, message: Dict[str, Any]):
    """Helper function to send a dictionary message over a websocket."""
    try:
        # print(f"[Server Send] Sending to {websocket.remote_address}: {message.get('action')}") # Verbose logging
        await websocket.send(json.dumps(message))
    except websockets.exceptions.WebSocketException as e:
        print(f"[Server Send] Error sending message to {websocket.remote_address} (likely disconnected): {e}")
        # Let the handle_client loop catch the disconnection

async def send_message_to_client(client_uuid: str, message: Dict[str, Any]):
    """Sends a message to a specific client UUID."""
    async with STATE_LOCK:
        client_info = CLIENTS.get(client_uuid)
        if client_info and client_info.get('websocket'):
            websocket = client_info['websocket']
        else:
            # print(f"[Server Send] Warning: Attempted to send message to unknown or disconnected client: {client_uuid}") # Verbose
            return # Client not found or no active websocket

    # Send outside the lock
    if websocket:
        await send_message(websocket, message)

async def broadcast_game_message(game_id: str, message: Dict[str, Any]):
    """Broadcasts a message to all players in a specific game."""
    players_to_notify = []
    async with STATE_LOCK:
        game = GAMES.get(game_id)
        if not game:
            print(f"[Server Broadcast] Warning: Attempted to broadcast to non-existent game {game_id}.")
            return
        # Get UUIDs of players in the game
        for piece in ['X', 'O']:
            player_info = game.players.get(piece)
            if player_info and player_info.get('uuid'):
                 players_to_notify.append(player_info['uuid'])

    # Send messages outside the lock
    print(f"[Server Broadcast] Broadcasting game {game_id} message ({message.get('action')}) to {players_to_notify}")
    for player_uuid in players_to_notify:
        await send_message_to_client(player_uuid, message)

async def get_available_games_list() -> list:
    """Returns the list of available games suitable for broadcasting."""
    async with STATE_LOCK:
        # Create a copy to avoid holding lock during list comprehension if needed
        return [
            {"game_id": gid, "player1_name": info["player1_name"], "player1_uuid": info["player1_uuid"]}
            for gid, info in AVAILABLE_GAMES.items()
        ]

async def broadcast_available_games():
    """Sends the current list of available games to all clients in the lobby."""
    games_list = await get_available_games_list() # Get list while holding lock briefly
    message = {"action": "available_games_update", "games": games_list}
    print(f"[Server Broadcast] Broadcasting available games update ({len(games_list)} games) to lobby clients.")

    clients_in_lobby = []
    async with STATE_LOCK:
        # Identify clients currently in the lobby (not in a game)
        for client_uuid, client_info in CLIENTS.items():
            if client_info['current_game'] is None and client_info.get('websocket'):
                clients_in_lobby.append(client_uuid)

    # Send outside the lock
    for client_uuid in clients_in_lobby:
        await send_message_to_client(client_uuid, message)

async def periodic_broadcast_available_games():
    """Task to periodically broadcast available games."""
    await asyncio.sleep(2) # Initial delay
    while True:
        try:
            await broadcast_available_games()
        except Exception as e:
            print(f"[Server Periodic Broadcast] Error during broadcast: {e}")
        await asyncio.sleep(5) # Broadcast every 5 seconds

async def handle_register(websocket, client_uuid: str, name: str):
    """Handles client registration or re-registration."""
    if not client_uuid or not isinstance(client_uuid, str) or not name:
        print(f"[Register] Error: Received register from {websocket.remote_address} with missing or invalid uuid/name.")
        await send_message(websocket, {"action": "error", "message": "Invalid register request: missing UUID or name."})
        # Keep connection open, wait for a valid register or close on next receive error
        return False # Registration failed validation

    async with STATE_LOCK:
        if client_uuid in CLIENTS:
            # Re-registering client
            old_websocket = CLIENTS[client_uuid].get('websocket')
            if old_websocket and old_websocket != websocket and not old_websocket.closed:
                 print(f"[Server] Client {client_uuid} re-registered. Closing old websocket.")
                 # Attempt to gracefully close the old connection
                 # Note: closing a websocket from another task is tricky, it's often
                 # better to send a "please disconnect" message to the old connection's handler.
                 # For simplicity here, we just let the new connection replace the old one.
                 # The old handler will eventually receive a close signal.
                 pass # Old websocket will be replaced below

            CLIENTS[client_uuid].update({'name': name, 'websocket': websocket, 'status': 'connected'})
            print(f"[Server] Client {client_uuid} ({name}) re-registered from {websocket.remote_address}.")
        else:
            # New client registration
            CLIENTS[client_uuid] = {'name': name, 'websocket': websocket, 'current_game': None, 'status': 'connected'}
            print(f"[Server] New client registered: {client_uuid} ({name}) from {websocket.remote_address}.")

    # Send registration success confirmation
    await send_message(websocket, {"action": "registered", "uuid": client_uuid, "name": name})

    # Check if client was in a game
    async with STATE_LOCK:
         current_game_id = CLIENTS[client_uuid].get('current_game')

    if current_game_id and current_game_id in GAMES:
         game = GAMES[current_game_id] # Access game object outside lock after checking existence
         player_piece = game.get_player_piece(client_uuid)
         print(f"[Server] Client {client_uuid} was in game {current_game_id}. Attempting rejoin.")
         await send_message(websocket, {
             "action": "rejoin_game",
             "game_id": current_game_id,
             "game_state": game.get_state(), # Send current state
             "player_piece": player_piece
         })
         # Don't send available games list if they rejoined a game
    else:
         # Ensure they are marked as not in a game (done above if new) and send lobby state
         async with STATE_LOCK:
             if client_uuid in CLIENTS: # Client might have disconnected already? Check again.
                  CLIENTS[client_uuid]["current_game"] = None # Ensure state is correct for lobby
         # Send initial list of available games
         await send_message(websocket, {"action": "available_games_update", "games": await get_available_games_list()})

    return True # Registration successful

async def handle_create_game(player1_uuid: str):
    """Handles a client's request to create a game."""
    print(f"[Create Game] Player {player1_uuid} creating a new game")

    async with STATE_LOCK:
        client_info = CLIENTS.get(player1_uuid)
        if not client_info:
            print(f"[Create Game] Error: Client {player1_uuid} not registered (unexpected).")
            return # Error handled in process_message if UUID is unknown
        if client_info.get('current_game'):
            print(f"[Create Game] Error: Client {player1_uuid} is already in game {client_info['current_game']}.")
            await send_message_to_client(player1_uuid, {"action": "error", "message": "You are already in a game."})
            return

        player1_name = client_info["name"]
        game_id = str(sys_uuid.uuid4())[:8] # Generate a unique 8-char game ID

        # Create game instance and add to server's state
        game = TicTacToeGame(game_id, player1_uuid, player1_name)
        GAMES[game_id] = game
        AVAILABLE_GAMES[game_id] = {"game_id": game_id, "player1_name": player1_name, "player1_uuid": player1_uuid}
        CLIENTS[player1_uuid]["current_game"] = game_id # Mark client as being in this game

        game_state = game.get_state()
        print(f"[Create Game] Game {game_id} created. State:", game_state)

    # Send game_created message to player 1
    await send_message_to_client(player1_uuid, {
        "action": "game_created",
        "game_id": game_id,
        "game_state": game_state,
         "player_piece": game.get_player_piece(player1_uuid) # Include piece
    })

    # Update the list of available games for all clients in the lobby
    await broadcast_available_games()

async def handle_join_game(player2_uuid: str, game_id: str):
    """Handles a client's request to join a game."""
    print(f"[Join Game] Player {player2_uuid} attempting to join game {game_id}")

    async with STATE_LOCK:
        client_info = CLIENTS.get(player2_uuid)
        if not client_info:
            print(f"[Join Game] Error: Client {player2_uuid} not registered (unexpected).")
            return # Error handled in process_message if UUID unknown
        if client_info.get('current_game'):
            print(f"[Join Game] Error: Client {player2_uuid} is already in game {client_info['current_game']}.")
            await send_message_to_client(player2_uuid, {"action": "error", "message": "You are already in a game."})
            return

        game = GAMES.get(game_id)
        # Check if game exists and is still available (not full)
        if not game or game_id not in AVAILABLE_GAMES:
            print(f"[Join Game] Error: Game {game_id} not found or is full.")
            await send_message_to_client(player2_uuid, {"action": "game_error", "game_id": game_id, "message": "Game not found or is full."})
            # Publish updated list in case their local list was stale
            await send_message_to_client(player2_uuid, {"action": "available_games_update", "games": await get_available_games_list()})
            return

        player2_name = client_info["name"]

        # Add player 2 to the game instance
        if game.add_player2(player2_uuid, player2_name):
            print(f"[Join Game] Player {player2_uuid} successfully added to game {game_id}")
            CLIENTS[player2_uuid]["current_game"] = game_id # Mark client as being in this game
            del AVAILABLE_GAMES[game_id] # Game is now full, remove from available list

            game_state = game.get_state()
            print(f"[Join Game] Game {game_id} started. State:", game_state)

        else:
             # Should not happen if game was in available_games, but handle defensively
             print(f"[Join Game] Error: Failed to add player {player2_uuid} to game {game_id}. Game might be full.")
             await send_message_to_client(player2_uuid, {"action": "error", "message": "Failed to join game. Game might be full."})
             await send_message_to_client(player2_uuid, {"action": "available_games_update", "games": await get_available_games_list()})
             return # Exit if player could not be added

    # Publish game_start to both players in the game
    await broadcast_game_message(game_id, {
        "action": "game_start",
        "game_id": game_id,
        "game_state": game_state,
         # Player pieces are available in game_state
    })

    # Update the list of available games (removes the joined game)
    await broadcast_available_games()


async def handle_make_move(client_uuid: str, game_id: str, y: Any, x: Any):
    """Handles a client's request to make a move."""
    print(f"[Move] Received make_move from {client_uuid} at ({y}, {x}) in game {game_id}")

    async with STATE_LOCK:
        game = GAMES.get(game_id)
        if not game:
            print(f"[Move] Error: Game {game_id} not found for move from {client_uuid}.")
            await send_message_to_client(client_uuid, {"action": "game_error", "game_id": game_id, "message": "Game not found."})
            return

    # Validate input types outside the lock
    try:
        y = int(y)
        x = int(x)
    except (ValueError, TypeError):
        print(f"[Move] Invalid coordinate types ({y}, {x}) from {client_uuid}")
        await send_message_to_client(client_uuid, {"action": "move_error", "game_id": game_id, "message": "Invalid coordinates."})
        return

    # make_move modifies the game object, which is safe as long as only one move per game
    # is processed at a time. Asyncio ensures only one task runs per websocket, so this is fine
    # as long as game methods are not async (which they aren't).
    result = game.make_move(client_uuid, y, x)

    if result["success"]:
        print(f"[Move] Move successful in game {game_id}. Next turn: {result['next_turn']}")
        if result["game_over"]:
            print(f"[Move] Game {game_id} finished. Winner: {result['winner']}, Is Tie: {result['is_tie']}")
            # Publish game_over message to both players
            await broadcast_game_message(game_id, {
                "action": "game_over",
                "game_id": game_id,
                "board": result["board"],
                "winner_piece": result["winner"],
                "is_tie": result["is_tie"]
            })
            # Clean up the game state on the server
            await cleanup_game(game_id)
        else:
            # Publish game_update message to both players
            await broadcast_game_message(game_id, {
                "action": "game_update",
                "game_id": game_id,
                "board": result["board"],
                "next_turn_piece": result["next_turn"],
            })
    else:
        # Publish move_error back to the specific client who made the invalid move
        print(f"[Move] Move failed in game {game_id} - Reason: {result['reason']} from {client_uuid}")
        await send_message_to_client(client_uuid, {
            "action": "move_error",
            "game_id": game_id,
            "message": result["reason"],
            "board": game.board # Send current board state back
        })

async def cleanup_game(game_id: str):
    """Cleans up server resources after a game ends."""
    print(f"[Cleanup] Attempting to clean up game {game_id}.")

    players_in_game = []
    async with STATE_LOCK:
        game = GAMES.get(game_id)
        if not game:
            print(f"[Cleanup] Warning: Tried to clean up non-existent game {game_id}")
            return

        # Reset current_game for the players involved
        for piece, player_info in game.players.items():
            if player_info and player_info.get("uuid"):
                player_uuid = player_info["uuid"]
                players_in_game.append(player_uuid)
                if player_uuid in CLIENTS:
                    print(f"[Cleanup] Resetting current_game for client {player_uuid}.")
                    CLIENTS[player_uuid]["current_game"] = None
                    # Optionally send a message indicating return to lobby
                    # await send_message_to_client(player_uuid, {"action": "return_to_lobby", "message": "Game finished."})


        # Remove game from server state
        if game_id in GAMES:
             del GAMES[game_id]
             print(f"[Cleanup] Removed game {game_id} from active games.")
        if game_id in AVAILABLE_GAMES:
             del AVAILABLE_GAMES[game_id]
             print(f"[Cleanup] Removed game {game_id} from available games.")

    # Broadcast updated list of available games *after* the lock is released
    await broadcast_available_games()
    print(f"[Cleanup] Game {game_id} cleanup complete.")


async def process_message(websocket, message_str: str, client_uuid: Optional[str]):
    """Processes an incoming message from a client."""
    try:
        message = json.loads(message_str)
    except json.JSONDecodeError:
        print(f"[Server] Received invalid JSON from {websocket.remote_address}. Closing connection.")
        await send_message(websocket, {"action": "error", "message": "Invalid JSON received."})
        return # Don't process further, let handler close

    action = message.get('action')
    received_uuid = message.get('uuid') # Client sends their UUID in the message payload

    # Basic validation: Ensure UUID is present for most actions
    # Register is special: the UUID passed here might be None initially
    if action != 'register' and (not received_uuid or not isinstance(received_uuid, str)):
         print(f"[Server] Received message with action '{action}' but no valid UUID from {websocket.remote_address}. Message: {message}")
         await send_message(websocket, {"action": "error", "message": f"Action '{action}' requires a valid UUID."})
         return # Invalid message

    # Use the UUID from the message payload for routing/identification
    # This handles cases where the websocket might not be fully mapped yet during registration
    effective_client_uuid = received_uuid if received_uuid else client_uuid

    if not effective_client_uuid:
         # This case should ideally be caught by the check above for non-register actions
         # or indicate a serious issue if register was invalid
         print(f"[Server] Could not determine client UUID for message: {message}")
         await send_message(websocket, {"action": "error", "message": "Could not identify client."})
         return

    print(f"[Received from {effective_client_uuid}] Action: {action}, Data: {message}") # Log action

    async with STATE_LOCK:
        client_info = CLIENTS.get(effective_client_uuid)

    # Handle 'register' first, it's essential for mapping UUID to websocket
    if action == "register":
        # handle_register will validate the UUID and name
        await handle_register(websocket, effective_client_uuid, message.get('name', 'Anonymous'))
        return # Registration handled

    # For any action other than 'register', the client must be registered
    if not client_info or client_info.get('websocket') != websocket:
         # This client UUID is either unknown or this websocket connection
         # is not the current primary connection for that UUID.
         # This could happen if a client connects, sends a message, but hasn't
         # completed the 'register' handshake, or if an old websocket sends a message
         # after a new one connected.
         print(f"[Server] Received action '{action}' from unknown or non-primary websocket for UUID {effective_client_uuid}. Ignoring.")
         await send_message(websocket, {"action": "error", "message": "Client not fully registered or using an old connection."})
         # Optionally close the connection if it's clearly not the primary one, but let's keep it simple.
         return

    # Now we know the client is registered and this is their active websocket.
    # Route based on client's game state.
    current_game_id = client_info.get('current_game')

    if current_game_id is None: # Client is in the lobby (conceptually)
        if action == "create_game":
            await handle_create_game(effective_client_uuid)
        elif action == "join_game":
            game_id = message.get('game_id')
            if game_id:
                await handle_join_game(effective_client_uuid, game_id)
            else:
                await send_message_to_client(effective_client_uuid, {"action": "error", "message": "Join game request missing game_id."})
        elif action == "list_games":
             # Client explicitly requested list, send it directly
             await send_message_to_client(effective_client_uuid, {"action": "available_games_update", "games": await get_available_games_list()})
        else:
            print(f"[Server] Unknown or inappropriate lobby action '{action}' from {effective_client_uuid}. Ignoring.")
            await send_message_to_client(effective_client_uuid, {"action": "error", "message": f"Unknown action '{action}' in lobby state."})

    elif current_game_id in GAMES: # Client is in a specific game
        # Access game object outside the lock. Game methods are synchronous and modify
        # the game instance, which is safe as this message handling is sequential per client/websocket.
        game = GAMES[current_game_id]
        if action == 'make_move':
            y = message.get('y')
            x = message.get('x')
            await handle_make_move(effective_client_uuid, current_game_id, y, x)
        # Add other potential game actions (e.g., leave game)
        else:
             print(f"[Server] Unknown or inappropriate game action '{action}' in game {current_game_id} from {effective_client_uuid}. Ignoring.")
             await send_message_to_client(effective_client_uuid, {"action": "error", "message": "Unknown game action."})

    else:
        # Client marked as being in a game that doesn't exist? (Shouldn't happen with cleanup)
        print(f"[Server] Client {effective_client_uuid} marked in non-existent game {current_game_id}. Resetting state.")
        async with STATE_LOCK:
             if effective_client_uuid in CLIENTS:
                 CLIENTS[effective_client_uuid]['current_game'] = None
        await send_message_to_client(effective_client_uuid, {"action": "error", "message": "Was in invalid game state, returning to lobby."})
        await send_message_to_client(effective_client_uuid, {"action": "available_games_update", "games": await get_available_games_list()})


async def handle_client(websocket, path=None):
    print(websocket)
    """Handles a new WebSocket connection."""
    # Initial state: Client is not registered with a UUID yet
    client_uuid = None
    print(f"[Server] New connection from {websocket.remote_address}")

    try:
        # The first message *must* be 'register' and must contain the client's UUID and name.
        # We wait for this message specifically.
        message_str = await websocket.recv()
        try:
             message = json.loads(message_str)
             if message.get('action') == 'register' and message.get('uuid') and isinstance(message.get('uuid'), str):
                  client_uuid = message['uuid']
             else:
                 print(f"[Server] First message from {websocket.remote_address} was not a valid 'register' message. Closing.")
                 await send_message(websocket, {"action": "error", "message": "First message must be a valid register request."})
                 await websocket.close()
                 return # Close connection

        except json.JSONDecodeError:
             print(f"[Server] Received invalid JSON as first message from {websocket.remote_address}. Closing connection.")
             await send_message(websocket, {"action": "error", "message": "Invalid JSON received."})
             await websocket.close()
             return # Close connection

        # Process the initial register message
        # handle_register will associate the UUID with this websocket in the CLIENTS dictionary
        registration_successful = await handle_register(websocket, client_uuid, message.get('name', 'Anonymous'))

        if not registration_successful:
             # If handle_register failed (e.g. invalid data), it might close the connection
             # depending on its implementation. Here it just returns False. We will close it.
             await websocket.close()
             return

        # Now that the client is registered, process subsequent messages in a loop
        async for message_str in websocket:
            # process_message will handle routing based on the message content and client state
            await process_message(websocket, message_str, client_uuid) # Pass client_uuid for lookup

    except websockets.exceptions.ConnectionClosedOK:
        # Client closed connection normally
        print(f"[Server] Connection closed normally by client {client_uuid or websocket.remote_address}")
    except websockets.exceptions.ConnectionClosedError as e:
        # Client closed connection due to an error
        print(f"[Server] Connection closed with error by client {client_uuid or websocket.remote_address}: {e}")
    except Exception as e:
        # Catch any other unexpected exceptions during communication
        print(f"[Server] Unhandled exception for client {client_uuid or websocket.remote_address}: {e}")
    finally:
        # Clean up client state when the connection is closed for any reason
        print(f"[Server] Cleaning up state for client {client_uuid or websocket.remote_address}.")
        if client_uuid:
            await cleanup_client(client_uuid)
        else:
            # If client never registered, nothing to clean up in CLIENTS state
            pass # Socket is closed by the exception handling

async def cleanup_client(client_uuid: str):
    """Removes client from state and handles game abandonment."""
    print(f"[Cleanup] Cleaning up client {client_uuid}.")
    async with STATE_LOCK:
        client_info = CLIENTS.get(client_uuid)
        if not client_info:
            print(f"[Cleanup] Warning: Tried to clean up non-existent client {client_uuid}")
            return

        # Handle client leaving a game
        game_id = client_info.get('current_game')
        if game_id in GAMES:
            game = GAMES[game_id] # Access game object (state access needs lock if modifying game outside its methods)
            print(f"[Cleanup] Client {client_uuid} was in game {game_id}. Handling game abandonment.")
            game.status = 'finished' # Mark game as finished due to abandonment

            # Notify the other player (if any) that the opponent left
            opponent_uuid = None
            for piece, player_info in game.players.items():
                if player_info and player_info.get('uuid') != client_uuid:
                    opponent_uuid = player_info.get('uuid')
                    break

            if opponent_uuid:
                 # Send outside the lock to avoid await within lock
                 pass # opponent_uuid is captured

            # Clean up the game (removes from GAMES and AVAILABLE_GAMES, resets player states)
            # Note: This calls cleanup_game which also broadcasts lobby updates
            # await cleanup_game(game_id) # Call cleanup_game after releasing lock
        # Remove client from the server's active clients list
        del CLIENTS[client_uuid]
        print(f"[Cleanup] Client {client_uuid} removed from active clients.")

    # Send opponent_disconnected message and cleanup game outside the lock
    if game_id in GAMES: # Check again outside lock, though cleanup_game handles non-existent games
         if opponent_uuid:
              # We need the name of the player who left, which is now removed from CLIENTS
              # A better approach might be to pass necessary info (player name, game_id)
              # or fetch it from the game object *before* deleting the client.
              # For simplicity, let's get the name from the game object if available before cleanup.
              leaving_player_name = "Opponent"
              async with STATE_LOCK: # Re-acquire lock briefly to get game state before it's deleted
                  game_before_cleanup = GAMES.get(game_id)
                  if game_before_cleanup:
                       for piece, player_info in game_before_cleanup.players.items():
                            if player_info and player_info.get('uuid') == client_uuid:
                                leaving_player_name = player_info.get('name', 'Opponent')
                                break

              await send_message_to_client(opponent_uuid, {
                  "action": "opponent_disconnected",
                  "game_id": game_id,
                  "message": f"{leaving_player_name} disconnected. Game ended."
              })
         await cleanup_game(game_id) # This also broadcasts available games update

    else:
        # If the client wasn't in a game or the game was already cleaned up,
        # just broadcast available games because a player count changed (the client left lobby)
        await broadcast_available_games()
        

async def main():
    """Starts the WebSocket server and background tasks."""
    asyncio.create_task(periodic_broadcast_available_games())

    print(f"--- TicTacToe WebSocket Server Starting ---")
    print(f"Listening on {SERVER_HOST}:{SERVER_PORT}")
    print("------------------------------------------")
    try:
        server = await websockets.serve(
            handle_client,  # Use handle_client instead of super_minimal_handler
            SERVER_HOST,
            SERVER_PORT
        )
        print("[Server] Server started.")
        await server.wait_closed()
    except OSError as e:
        print(f"[Server] Error starting server: {e}")
        print(f"Please ensure port {SERVER_PORT} is not already in use.")
        sys.exit(1)
    except Exception as e:
        print(f"[Server] An unexpected error occurred: {e}")
        sys.exit(1)
        
        
# --- THIS BLOCK IS ESSENTIAL ---
if __name__ == "__main__":
    try:
        asyncio.run(main()) # This actually runs the main function
    except KeyboardInterrupt:
        print("\n[Server] Ctrl+C detected. Shutting down.")
        # asyncio.run will handle graceful shutdown of tasks