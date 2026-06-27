import React, { useEffect, useRef } from 'react';

export default function Transcript({ messages }) {
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <div className="transcript-list" ref={scrollRef}>
      {messages.length === 0 ? (
        <div style={{ opacity: 0.5, textAlign: 'center', marginTop: '2rem' }}>
          Waiting for voice input...
        </div>
      ) : (
        messages.map((msg) => (
          <div key={msg.id} className={`message ${msg.role}`}>
            <div className="message-role">{msg.role}</div>
            <div className="message-text">{msg.text}</div>
          </div>
        ))
      )}
    </div>
  );
}
