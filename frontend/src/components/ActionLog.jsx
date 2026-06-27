import React, { useEffect, useRef } from 'react';

export default function ActionLog({ logs }) {
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div className="log-list" ref={scrollRef}>
      {logs.length === 0 ? (
        <div style={{ opacity: 0.3, textAlign: 'center' }}>No actions executed yet.</div>
      ) : (
        logs.map((log) => (
          <div key={log.id} className={`log-entry ${log.result?.includes('Error') ? 'error' : 'success'}`}>
            <div>
              <span className="log-time">[{log.time}]</span>
              <span className="log-tool">{log.tool}</span>
            </div>
            {log.result && (
              <div style={{ marginTop: '4px', opacity: 0.8 }}>
                → {log.result}
              </div>
            )}
          </div>
        ))
      )}
    </div>
  );
}
