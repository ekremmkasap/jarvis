"use client";

import { useEffect, useState } from "react";

const AGENTS = [
  { id: "seda", name: "SEDA", color: "#00ff88" },
  { id: "mert", name: "MERT", color: "#ffdd00" },
  { id: "buse", name: "BUSE", color: "#ff69b4" },
  { id: "eren", name: "EREN", color: "#ff8c00" },
  { id: "luna", name: "LUNA", color: "#9b59b6" },
  { id: "sab", name: "SAB", color: "#95a5a6" },
  { id: "sbr", name: "SBR", color: "#e74c3c" },
];

export default function SwarmStatusBar() {
  const [activeAgents, setActiveAgents] = useState<string[]>([]);

  useEffect(() => {
    let isMounted = true;
    
    const fetchStatus = async () => {
      try {
        const res = await fetch("/api/swarm-status");
        if (!res.ok) throw new Error("Failed to fetch");
        const data = await res.json();
        
        // Handles both {"active": [...]} and {"active_agents": [...]}
        const active = Array.isArray(data.active) 
          ? data.active 
          : Array.isArray(data.active_agents) 
            ? data.active_agents 
            : [];
            
        if (isMounted) setActiveAgents(active);
      } catch (e) {
        if (isMounted) setActiveAgents([]);
      }
    };

    fetchStatus();
    const intervalId = setInterval(fetchStatus, 4000);
    return () => {
      isMounted = false;
      clearInterval(intervalId);
    };
  }, []);

  return (
    <div className="fixed top-0 left-0 w-full z-50 flex justify-center py-2 shrink-0 pointer-events-none">
      <div className="bg-gray-900/80 backdrop-blur-md border border-gray-700/50 rounded-full px-6 py-2 flex items-center gap-4 shadow-xl">
        {AGENTS.map((agent) => {
          const isActive = activeAgents.includes(agent.id) || activeAgents.includes(agent.name.toLowerCase());
          return (
            <div
              key={agent.id}
              className="flex items-center gap-2 transition-all duration-500"
              style={{
                opacity: isActive ? 1 : 0.3,
                textShadow: isActive ? `0 0 10px ${agent.color}` : "none",
                color: isActive ? agent.color : "#9ca3af",
              }}
            >
              <div
                className="w-2.5 h-2.5 rounded-full"
                style={{
                  backgroundColor: isActive ? agent.color : "#4b5563",
                  boxShadow: isActive ? `0 0 12px ${agent.color}, 0 0 24px ${agent.color}` : "none",
                  animation: isActive ? "pulse-glow 1.5s infinite" : "none",
                }}
              />
              <span className="text-xs font-bold font-mono tracking-wider">{agent.name}</span>
            </div>
          );
        })}
      </div>
      <style dangerouslySetInnerHTML={{__html: `
        @keyframes pulse-glow {
          0%, 100% { transform: scale(1); filter: brightness(1); }
          50% { transform: scale(1.3); filter: brightness(1.5); }
        }
      `}} />
    </div>
  );
}
