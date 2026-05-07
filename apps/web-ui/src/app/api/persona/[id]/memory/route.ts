import { NextRequest, NextResponse } from 'next/server';
import { fetchBridgeJson } from '@/lib/bridgeProxy';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

type RouteContext = {
  params: {
    id: string;
  };
};

export async function GET(request: NextRequest, context: RouteContext) {
  const personaId = encodeURIComponent(String(context.params.id || '').trim());
  const limit = request.nextUrl.searchParams.get('limit');
  const query = limit ? `?limit=${encodeURIComponent(limit)}` : '';

  try {
    const bridge = await fetchBridgeJson(`/api/persona/${personaId}/memory${query}`);
    return NextResponse.json(bridge.payload, {
      status: bridge.ok ? bridge.status : bridge.status || 502,
    });
  } catch (error) {
    return NextResponse.json(
      {
        error: error instanceof Error ? error.message : 'Bridge persona memory istegi basarisiz.',
      },
      { status: 502 },
    );
  }
}
