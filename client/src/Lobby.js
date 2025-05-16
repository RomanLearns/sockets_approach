import React, { useState, useEffect } from 'react';
import { useWebSocket } from './WebSocketContext'; // Use the context hook
import './Lobby.css';
import * as config from './config'; // Still need config for message structure

function Lobby({ userName, userUuid, availableGames, onEnterGame, serverError, setServerError }) {
  // Use the websocket context to get the send function and connection status
  const { isConnected, sendMessage } = useWebSocket();

  // State for component-specific error messages (optional, App.js handles server errors)
  // const [localError, setLocalError] = useState(null);


  // Effect to register and request games when connected and UUID is ready
  useEffect(() => {
      console.log('Lobby Effect: Checking connection/registration status.', { isConnected, userUuid, userName });
      if (isConnected && userUuid && userName) {
          // 1. Send registration message upon connection *if* we have the user info
           console.log('Lobby Effect: Sending register message.');
           sendMessage({ action: 'register', uuid: userUuid, name: userName });

           // 2. Request list of games after (or as part of) registration
           // The server is designed to send available_games_update after registration
           // and periodically, so an explicit list_games call might not be strictly necessary
           // immediately, but it ensures the client gets the list if they miss the broadcast.
           console.log('Lobby Effect: Sending list_games message.');
           sendMessage({ action: 'list_games', uuid: userUuid });
      } else {
          console.log('Lobby Effect: Conditions not met for registration/list_games.', { isConnected, userUuid, userName });
      }
      // Depend on isConnected, userUuid, userName - ensures register is sent on connection/refresh
  }, [isConnected, userUuid, userName, sendMessage]);

   // No need for the periodic fetchGames interval here; the server broadcasts.

  const createGame = () => {
    // Check if connected before sending
    if (!isConnected) {
      // setLocalError('Not connected to the server.');
      setServerError('Not connected to the server.');
      return;
    }
     setServerError(null); // Clear previous errors
    console.log('Lobby: Sending create_game message with UUID:', userUuid);
    sendMessage({ action: 'create_game', uuid: userUuid });
  };

  const joinGame = (gameId) => {
     // Check if connected before sending
    if (!isConnected) {
      // setLocalError('Not connected to the server.');
      setServerError('Not connected to the server.');
      return;
    }
     setServerError(null); // Clear previous errors
    console.log(`Lobby: Sending join_game message for ID ${gameId} with UUID: ${userUuid}`);
    sendMessage({ action: 'join_game', uuid: userUuid, game_id: gameId });
  };

  // Filter out games created by the current user that are still waiting
  // (The server removes games from available_games once player 2 joins)
  // The server also doesn't list games where the player1_uuid is the requesting client's uuid
  // unless that player is NOT currently in a game. Let's rely on the server's list.
  // The server's available_games list already only contains games waiting for player 2.
   const filteredGames = availableGames;


  const isButtonDisabled = !isConnected; // Disable buttons if not connected
  // console.log('Lobby: Button disabled state:', { isButtonDisabled, isConnected });


  return (
    <div className="lobby-container">
      <h2>Welcome, {userName}</h2>

       {/* Display server error from App.js */}
      {serverError && <div className="error-message">{serverError}</div>}
      {/* Display connection status if disconnected */}
      {!isConnected && <div className="info-message">Connecting to server...</div>}


      <button onClick={createGame} disabled={isButtonDisabled}>
        Create Game
      </button>

      <h3>Available Games</h3>
      <ul>
        {filteredGames.length > 0 ? (
          filteredGames.map((game) => (
            <li key={game.game_id}>
              {game.player1_name}'s Game (ID: {game.game_id})
              <button onClick={() => joinGame(game.game_id)} disabled={isButtonDisabled}>
                Join
              </button>
            </li>
          ))
        ) : (
          <li className="no-games">No available games</li>
        )}
      </ul>
    </div>
  );
}

// Lobby now expects userUuid, userName, availableGames, onEnterGame, serverError, setServerError as props
export default Lobby;