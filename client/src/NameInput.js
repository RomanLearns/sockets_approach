import React, { useState } from 'react';
import './NameInput.css';

function NameInput({ onEnterLobby }) {
  const [name, setName] = useState('');
  const [error, setError] = useState(null);

  const handleSubmit = () => {
    if (name.trim() === '') {
      setError('Please enter a name.');
      return;
    }
    setError(null); // Clear previous errors

    try {
      // Generate UUID here and pass it up
      const uuid = `client-${Math.random().toString(36).substr(2, 9)}`;
      console.log('NameInput: Generated UUID and name:', { uuid, name });
      onEnterLobby(name.trim(), uuid); // Trim whitespace from name
    } catch (err) {
      console.error('NameInput: Error during name submission:', err);
      setError('An error occurred during submission. Please try again.');
    }
  };

   const handleKeyPress = (e) => {
       if (e.key === 'Enter') {
           handleSubmit();
       }
   };


  return (
    <div className="name-input-container">
      <h2>Enter Your Name</h2>
      <input
        type="text"
        value={name}
        onChange={(e) => setName(e.target.value)}
        onKeyPress={handleKeyPress} // Allow pressing Enter
        placeholder="Your name"
        disabled={!!error} // Disable input if there's an error? Maybe not ideal.
      />
      <button onClick={handleSubmit} disabled={!name.trim()}> {/* Disable button if name is empty */}
        Enter Lobby
      </button>
      {error && <div className="error-message">{error}</div>}
    </div>
  );
}

export default NameInput;
