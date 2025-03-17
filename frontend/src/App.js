import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './App.css';

const App = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [currentCharacter, setCurrentCharacter] = useState(null);
  const chatRef = useRef(null);
  const endpoint = 'http://localhost:8080/safety_bot'; // Local Flask endpoint

  const mockCharacters = [
    {
      name: "Dory",
      intro: "Hiya, pal! I’m Dory, your forgetful fish friend here to help with safety! Ask me anything!",
      style: "Cheerful, a bit scatterbrained, but super encouraging.",
      exit: "Bye-bye, pal! Keep swimming safe!"
    },
    {
      name: "Po",
      intro: "Hey, awesome human! I’m Po, the panda with a big heart to keep you safe! What’s up?",
      style: "Warm, goofy, and protective.",
      exit: "See ya, awesome friend! Stay safe!"
    },
    {
      name: "Mrs. Potts",
      intro: "Oh, my dear! I’m Mrs. Potts, your cozy teapot guide for safety. How can I help?",
      style: "Kind, maternal, and soothing.",
      exit: "Farewell, dearie! Be safe!"
    }
  ];

  useEffect(() => {
    const randomChar = mockCharacters[Math.floor(Math.random() * mockCharacters.length)];
    setCurrentCharacter(randomChar);
    setMessages([
      { text: randomChar.intro, isBot: true, timestamp: new Date() },
      { text: "Ask me about helplines, police stations, shelters, legal resources, or safety tips!", isBot: true, timestamp: new Date() }
    ]);
  }, []);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = { text: input, isBot: false, timestamp: new Date() };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await axios.post(endpoint, { query: input }, {
        headers: { 'Content-Type': 'application/json' }
      });

      const { response: botResponse, intro } = response.data;

      if (input.toLowerCase() === "exit") {
        setCurrentCharacter(null);
      }

      let responseText = botResponse;
      if (intro && messages.length === 2) {
        responseText = intro;
      }

      setMessages((prev) => [...prev, { text: responseText, isBot: true, timestamp: new Date() }]);
    } catch (error) {
      console.error('Error:', error);
      let errorText = `${currentCharacter.name}: Oops, something went wrong, pal! Try again?`;
      setMessages((prev) => [...prev, { text: errorText, isBot: true, timestamp: new Date() }]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight;
    }
  }, [messages]);

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !isLoading) sendMessage();
  };

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="app">
      <header className="header">
        <h1>SafetyBot</h1>
        <p className="character-info">With {currentCharacter?.name || 'a friend'}</p>
      </header>
      
      <div className="chat-container" ref={chatRef}>
        {messages.length === 0 && (
          <div className="welcome-message">
            Loading your safety companion...
          </div>
        )}
        {messages.map((msg, index) => (
          <div 
            key={index} 
            className={`message ${msg.isBot ? 'bot-message' : 'user-message'} ${msg.isBot ? currentCharacter?.name.toLowerCase().replace(' ', '-') : ''}`}
          >
            <div className="message-content">
              <span className="sender">{msg.isBot ? currentCharacter?.name || 'SafetyBot' : 'You'}</span>
              <p>{msg.text}</p>
              <span className="timestamp">{formatTimestamp(msg.timestamp)}</span>
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="loading">
            <span className="dot-flashing"></span> Thinking...
          </div>
        )}
      </div>

      <div className="input-container">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder={`Ask ${currentCharacter?.name || 'me'} about safety...`}
          disabled={isLoading || !currentCharacter}
        />
        <button 
          onClick={sendMessage} 
          disabled={isLoading || !currentCharacter}
        >
          {isLoading ? 'Sending...' : 'Send'}
        </button>
      </div>
    </div>
  );
};

export default App;