import type { Metadata } from 'next';
import PulseGame from './PulseGame';

export const metadata: Metadata = {
  title: 'Pulse Siege | Jarvis Mission Control',
  description: 'Deterministic arcade route for Jarvis Mission Control.',
};

export default function GamePage() {
  return <PulseGame />;
}
