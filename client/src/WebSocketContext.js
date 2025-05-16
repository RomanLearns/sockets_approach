import React, { createContext, useContext, useState, useEffect, useRef } from 'react';

const WebSocketContext = createContext(null);

export const useWebSocket = () => useContext(WebSocketContext);

export const WebSocketProvider = ({ children, serverUrl }) => {
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState(null);
  const websocketRef = useRef(null); // Use ref to persist websocket instance across renders

  useEffect(() => {
    if (!serverUrl) {
        console.warn("WebSocketProvider: serverUrl is not provided.");
        return;
    }

    console.log(`WebSocketProvider: Attempting to connect to ${serverUrl}`);
    const ws = new WebSocket(serverUrl);
    websocketRef.current = ws; // Store the instance in the ref

    ws.onopen = () => {
      console.log('WebSocketProvider: WebSocket connection opened.');
      setIsConnected(true);
      setError(null); // Clear any previous error
    };

    ws.onmessage = (event) => {
      // Messages are handled by the central handler in App.js
      // The onmessage handler in App.js is set up *after* the websocket
      // instance is available via context.
       console.log('WebSocketProvider: Message received (passed to App.js handler).');
       // No action here, App.js handles it.
    };

    ws.onerror = (event) => {
      console.error('WebSocketProvider: WebSocket error:', event);
      setIsConnected(false); // Mark as disconnected
      setError('WebSocket connection error.'); // Set a generic error
    };

    ws.onclose = (event) => {
      console.log('WebSocketProvider: WebSocket connection closed:', event.code, event.reason);
      setIsConnected(false); // Mark as disconnected
      setError('WebSocket connection closed.'); // Set a generic error
      // Potentially try to reconnect here or trigger a reconnect logic in App.js
    };

    // Cleanup function: Close the WebSocket when the component unmounts
    return () => {
      console.log('WebSocketProvider: Cleaning up WebSocket connection.');
      if (websocketRef.current && websocketRef.current.readyState === WebSocket.OPEN) {
        websocketRef.current.close();
      }
    };
  }, [serverUrl]); // Effect runs when serverUrl changes (should only be once)


  // Function to send messages, provided via context
  const sendMessage = (message) => {
    if (websocketRef.current && websocketRef.current.readyState === WebSocket.OPEN) {
      try {
        // Ensure the message includes the client UUID if available
        // (UUID is added in components that call sendMessage)
        websocketRef.current.send(JSON.stringify(message));
        console.log('WebSocketProvider: Message sent:', message.action);
      } catch (e) {
        console.error('WebSocketProvider: Failed to send message:', e);
        setError("Failed to send message."); // Indicate sending error
      }
    } else {
       console.warn('WebSocketProvider: Cannot send message, WebSocket not open.', message.action);
       // Optionally set an error or queue the message
       // setError("Not connected to the server.");
    }
  };

   // Provide the websocket instance itself, connection status, send function, and error
  return (
    <WebSocketContext.Provider value={{ websocket: websocketRef.current, isConnected, sendMessage, error, setError }}>
      {children}
    </WebSocketContext.Provider>
  );
};