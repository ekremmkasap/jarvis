'use client';
import { AgentNode } from '@/hooks/useJarvisStore';

type Pos = { x: number; y: number };

const POSITIONS: Record<string, Pos> = {
  mission_control: { x: 210, y: 170 },
  planner:         { x: 210, y: 50 },
  repo_analyst:    { x: 50,  y: 130 },
  developer:       { x: 370, y: 130 },
  reviewer:        { x: 100, y: 260 },
  debug:           { x: 320, y: 260 },
  release:         { x: 450, y: 200 },
  docs:            { x: 50,  y: 330 },
  voice_narrator:  { x: 210, y: 340 },
};

const STATUS_COLOR: Record<string, string> = {
  idle:   '#1a3a26',
  active: '#4ade80',
  error:  '#f87171',
};

const STATUS_TEXT: Record<string, string> = {
  idle:   '#4ade8060',
  active: '#4ade80',
  error:  '#f87171',
};

const W = 80, H = 36;

export default function AgentGraph({ nodes }: { nodes: AgentNode[] }) {
  const edges = nodes
    .filter((n) => n.id !== 'mission_control')
    .map((n) => ({
      from: POSITIONS['mission_control'],
      to: POSITIONS[n.id],
      active: n.status === 'active',
    }));

  return (
    <svg
      width="100%"
      height="100%"
      viewBox="0 0 540 420"
      className="w-full h-full"
      preserveAspectRatio="xMidYMid meet"
    >
      {/* Edges */}
      {edges.map((e, i) => {
        if (!e.from || !e.to) return null;
        return (
          <line
            key={i}
            x1={e.from.x + W / 2}
            y1={e.from.y + H / 2}
            x2={e.to.x + W / 2}
            y2={e.to.y + H / 2}
            stroke={e.active ? '#4ade80' : '#1a3a26'}
            strokeWidth={e.active ? 1.5 : 1}
            strokeDasharray={e.active ? undefined : '4 4'}
            opacity={e.active ? 0.8 : 0.4}
          />
        );
      })}

      {/* Nodes */}
      {nodes.map((node) => {
        const pos = POSITIONS[node.id];
        if (!pos) return null;
        const col = STATUS_COLOR[node.status] || STATUS_COLOR.idle;
        const txt = STATUS_TEXT[node.status] || STATUS_TEXT.idle;
        const isActive = node.status === 'active';

        return (
          <g key={node.id} transform={`translate(${pos.x},${pos.y})`}>
            {isActive && (
              <rect
                x="-3" y="-3"
                width={W + 6} height={H + 6}
                rx="7"
                fill="none"
                stroke="#4ade80"
                strokeWidth="1"
                opacity="0.5"
              >
                <animate attributeName="opacity" values="0.2;0.6;0.2" dur="1.5s" repeatCount="indefinite" />
              </rect>
            )}
            <rect
              x="0" y="0"
              width={W} height={H}
              rx="4"
              fill="#0a0f1a"
              stroke={col}
              strokeWidth={isActive ? 1.5 : 1}
            />
            <text
              x={W / 2} y="14"
              textAnchor="middle"
              fill={txt}
              fontSize="9"
              fontFamily="monospace"
              fontWeight="bold"
            >
              {node.name}
            </text>
            <text
              x={W / 2} y="27"
              textAnchor="middle"
              fill="#1a3a26"
              fontSize="8"
              fontFamily="monospace"
            >
              {node.status}{node.task_count > 0 ? ` (${node.task_count})` : ''}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
