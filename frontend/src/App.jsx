import { useState, useEffect, useRef } from 'react';
import Orb from './components/Orb';
import Transcript from './components/Transcript';
import SystemMonitor from './components/SystemMonitor';
import ActionLog from './components/ActionLog';

function App() {
  const [status, setStatus] = useState('idle');
  const [messages, setMessages] = useState([]);
  const [systemMetrics, setSystemMetrics] = useState({ cpu: 0, ram: 0 });
  const [logs, setLogs] = useState([]);
  
  const ws = useRef(null);

  useEffect(() => {
    const connect = () => {
      ws.current = new WebSocket('ws://localhost:8765/ws');
      
      ws.current.onopen = () => {
        console.log('Connected to Jarvis backend');
        setStatus('idle');
      };
      
      ws.current.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        switch (data.type) {
          case 'status':
            // "listening", "thinking", "speaking", "idle", etc.
            setStatus(data.state);
            break;
            
          case 'transcript':
            setMessages((prev) => [
              ...prev,
              { role: data.role, text: data.text, id: Date.now() + Math.random() }
            ]);
            break;
            
          case 'system':
            setSystemMetrics({ cpu: data.cpu, ram: data.ram });
            break;
            
          case 'tool_call':
            setLogs((prev) => [
              ...prev,
              { 
                time: new Date(data.timestamp).toLocaleTimeString(), 
                tool: data.name, 
                result: data.result,
                id: Date.now() + Math.random()
              }
            ]);
            break;
            
          default:
            break;
        }
      };
      
      ws.current.onclose = () => {
        console.log('Disconnected from Jarvis backend, retrying...');
        setTimeout(connect, 3000);
      };
    };

    connect();

    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, []);

  return (
    <div className="dashboard-container">
      {/* Left Panel: Transcript */}
      <div className="glass-panel">
        <h2 className="panel-title">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
          Conversation
        </h2>
        <Transcript messages={messages} />
      </div>

      {/* Center Panel: Orb & Status */}
      <div className="center-section">
        <Orb status={status} />
        <div className={`status-text state-${status.split(':')[0]}`}>
          {status.split(':')[0]}
        </div>
      </div>

      {/* Right Panel: Metrics & Logs */}
      <div className="glass-panel">
        <h2 className="panel-title">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"></path></svg>
          System Core
        </h2>
        
        <SystemMonitor metrics={systemMetrics} />
        
        <h2 className="panel-title" style={{ marginTop: '2rem' }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="4 17 10 11 4 5"></polyline><line x1="12" y1="19" x2="20" y2="19"></line></svg>
          Action Log
        </h2>
        <ActionLog logs={logs} />
      </div>
    </div>
  );
}

export default App;
