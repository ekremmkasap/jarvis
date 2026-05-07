import MissionControlDashboard from '@/components/MissionControlDashboard';
import SaasMetricsPanel from '@/components/SaasMetricsPanel';
import SwarmTeamPanel from '@/components/SwarmTeamPanel';

export default function OpsPage() {
  return (
    <div className="flex flex-col gap-4">
      <MissionControlDashboard />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 px-4 pb-4">
        <SaasMetricsPanel />
        <SwarmTeamPanel />
      </div>
    </div>
  );
}
