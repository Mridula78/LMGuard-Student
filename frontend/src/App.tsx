import React from 'react';
import ChatBox from './components/ChatBox';

function App() {
  return (
    <div className="min-h-screen bg-gray-100">
      <div className="container mx-auto px-4 py-8">
        <header className="mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">
            LMGuard Student Tutor
          </h1>
          <p className="text-gray-600">
            AI-powered tutoring with built-in safety guardrails
          </p>
        </header>
        <ChatBox />
      </div>
    </div>
  );
}

export default App;


