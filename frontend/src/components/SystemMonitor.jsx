import React from 'react';

export default function SystemMonitor({ metrics }) {
  return (
    <div className="metrics-container">
      <div className="metric">
        <div className="metric-header">
          <span>CPU Usage</span>
          <span>{metrics.cpu.toFixed(1)}%</span>
        </div>
        <div className="metric-bar-bg">
          <div 
            className={`metric-bar-fill ${metrics.cpu > 80 ? 'high' : metrics.cpu > 50 ? 'medium' : ''}`}
            style={{ width: `${metrics.cpu}%` }}
          ></div>
        </div>
      </div>
      
      <div className="metric">
        <div className="metric-header">
          <span>RAM Usage</span>
          <span>{metrics.ram.toFixed(1)}%</span>
        </div>
        <div className="metric-bar-bg">
          <div 
            className={`metric-bar-fill ${metrics.ram > 80 ? 'high' : metrics.ram > 50 ? 'medium' : ''}`}
            style={{ width: `${metrics.ram}%` }}
          ></div>
        </div>
      </div>
    </div>
  );
}
