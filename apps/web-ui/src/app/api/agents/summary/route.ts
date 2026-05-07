import { NextResponse } from 'next/server';
import { fetchBridgeJson } from '@/lib/bridgeProxy';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const bridge = await fetchBridgeJson('/api/agents/summary');
    return NextResponse.json(bridge.payload, {
      status: bridge.ok ? bridge.status : bridge.status || 502,
    });
  } catch (error) {
    return NextResponse.json(
      {
        error: error instanceof Error ? error.message : 'Bridge summary istegi basarisiz.',
      },
      { status: 502 },
    );
  }
}
