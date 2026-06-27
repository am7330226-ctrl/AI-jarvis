import React from 'react';

export default function Orb({ status }) {
  // Base status handles states like 'executing:open_application'
  const baseStatus = status.split(':')[0];

  return (
    <div className="orb-container">
      <div className={`orb state-${baseStatus}`}></div>
      <div className="orb-ring"></div>
      <div className="orb-ring-2"></div>
    </div>
  );
}
