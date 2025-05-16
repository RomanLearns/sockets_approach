import React from 'react';
import ReactDOM from 'react-dom/client'; // Use createRoot for React 18+
import AppWithWebSocket from './App'; // Import the wrapped App

const container = document.getElementById('root');
const root = ReactDOM.createRoot(container); // Create a root for React 18+

root.render(
  <React.StrictMode>
    <AppWithWebSocket /> {/* Render the App wrapped in WebSocketProvider */}
  </React.StrictMode>
);
