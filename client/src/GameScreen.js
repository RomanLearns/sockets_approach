import React, { useState, useEffect, useCallback } from 'react';
import { useWebSocket } from './WebSocketContext'; // Use the context hook
import './GameScreen.css';
import * as config from './config'; // Still need config for game channel prefix logic (conceptually)

function classNames(...classes) {
  return classes.filter(Boolean).join(' ');
}

// GameScreenInner is no longer needed as state is managed higher up
// Rename the main component back to GameScreen
function GameScreen({ gameState, userUuid, onBackToLobby, serverError, setServerError }) {
  const { sendMessage, isConnected } = useWebSocket(); // Get send function and connection status

  // gameState is now passed as a prop and updated by App.js's message handler
  // Use state derived directly from the gameState prop
  const { game_id, player_piece, initial_state } = gameState; // initial_state holds the current state received
  const { board, turn, status, players, winner, is_tie } = initial_state;


  // No need for useEffect to subscribe/unsubscribe or handle messages; App.js does this centrally.
  // The component just renders based on the gameState prop it receives.

  // However, we might want an effect to clear server errors when game state updates successfully?
   useEffect(() => {
       // When gameState prop changes (due to server updates), clear server errors
       if (serverError && status !== 'finished') { // Don't clear error if game just finished with one
            // Could be more specific, e.g., if board or turn changed, clear error
            setServerError(null);
       }
   }, [gameState, serverError, status, setServerError]); // Depend on gameState and serverError


  const handleCellClick = (y, x) => {
    console.log(`GameScreen: Attempting to make move at (${y}, ${x})`);
    console.log(`GameScreen: Current state - Status: ${status}, Turn: ${turn}, Player Piece: ${player_piece}, Cell Content: ${board[y][x]}`);

     // Basic client-side validation before sending
    if (!isConnected) {
        setServerError('Not connected to the server.');
        return;
    }
    if (status !== 'active') {
      console.log(`GameScreen: Cannot make move - Game status is ${status}`);
       setServerError(`Game status is ${status}`);
      return;
    }
    if (turn !== player_piece) {
      console.log(`GameScreen: Cannot make move - It's not your turn (Current turn: ${turn}, Your piece: ${player_piece})`);
       setServerError("It's not your turn.");
      return;
    }
    if (board[y][x]) {
      console.log(`GameScreen: Cannot make move - Cell (${y}, ${x}) is already occupied with ${board[y][x]}`);
       setServerError("Position already occupied.");
      return;
    }

    setServerError(null); // Clear any previous error before sending move

    console.log(`GameScreen: Sending make_move for (${y}, ${x}) with UUID: ${userUuid} for game ID: ${game_id}`);
    // Use the sendMessage function from context
    sendMessage({
      action: 'make_move',
      uuid: userUuid, // Include client UUID
      game_id: game_id, // Include game ID
      y: y,
      x: x,
    });
  };

  const getCellClass = (cellValue, y, x) => {
      const isClickable = status === 'active' && turn === player_piece && !board[y][x];
      return classNames(
          'cell',
          cellValue.toLowerCase(),
          { 'disabled': !isClickable }
      );
  };

  const getTurnIndicatorClass = () => {
       if (status !== 'active') return 'turn-indicator';
       return classNames('turn-indicator', `${turn.toLowerCase()}-turn`);
  }

  const getGameOverMessageClass = () => {
      if (status !== 'finished') return '';

      let resultClass = '';
      if (winner === 'X') {
          resultClass = 'winner-x';
      } else if (winner === 'O') {
          resultClass = 'winner-o';
      } else if (is_tie) { // Check is_tie flag specifically for tie message
          resultClass = 'tie';
      }
      return classNames('game-over-message', resultClass);
  }

  const getGameOverMessageText = () => {
       if (status !== 'finished') return '';
       if (is_tie) {
           return 'Tie Game!';
       } else if (winner) {
           // Find winner's name from the players object in gameState
            const winningPlayer = players?.[winner];
            if (winningPlayer?.name) {
                return `Winner: ${winningPlayer.name} (${winner})`;
            }
           return `Winner: ${winner}`; // Fallback if name not found
       }
       return 'Game Over.'; // Generic fallback
  }


  return (
    <div className="game-container">
      <h2>Game ID: {game_id}</h2>
      <p>You are: <strong className={classNames('player-piece', player_piece.toLowerCase())}>{player_piece}</strong></p>

       {/* Display server error from App.js */}
       {serverError && <div className="error-message">{serverError}</div>}
       {/* Display connection status if disconnected */}
       {!isConnected && <div className="info-message">Connection lost...</div>}


      <p className={getTurnIndicatorClass()}>
          {status === 'active' ? (
               <>Turn: <span className="player-piece">{turn}</span></>
          ) : (
               null
          )}
      </p>


      <div className="board">
        {board.map((row, y) =>
          row.map((cellValue, x) => (
            <div
              key={`${y}-${x}`}
              className={getCellClass(cellValue, y, x)}
              onClick={() => handleCellClick(y, x)}
            >
              {cellValue}
            </div>
          ))
        )}
      </div>

      {status === 'finished' && (
        <p className={getGameOverMessageClass()}>
          {getGameOverMessageText()}
        </p>
      )}

      <button onClick={onBackToLobby}>Back to Lobby</button>
    </div>
  );
}

// GameScreen now expects gameState, userUuid, onBackToLobby, serverError, setServerError as props
export default GameScreen;