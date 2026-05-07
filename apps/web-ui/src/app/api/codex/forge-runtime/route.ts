import os from 'os';
import path from 'path';
import { readFile, stat } from 'fs/promises';
import { NextResponse } from 'next/server';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const DEFAULT_FORGE_RUNTIME_PATH =
  process.env.FORGE_RUNTIME_MASTER_PATH?.trim() ||
  path.join(os.homedir(), 'Desktop', 'JARVIS_3LANE_FORGE_BRIDGE_RUNTIME_MASTER.txt');

const MAX_CHARS = 24000;

function clipContent(raw: string) {
  if (raw.length <= MAX_CHARS) {
    return { content: raw, truncated: false };
  }

  return {
    content: `${raw.slice(0, MAX_CHARS)}\n\n...[truncated]`,
    truncated: true,
  };
}

function normalizeError(error: unknown) {
  return error instanceof Error ? error.message : 'Dosya okunamadi.';
}

export async function GET() {
  try {
    const fileStat = await stat(DEFAULT_FORGE_RUNTIME_PATH);
    const raw = await readFile(DEFAULT_FORGE_RUNTIME_PATH, 'utf-8');
    const { content, truncated } = clipContent(raw);

    return NextResponse.json({
      slot_id: 'forge',
      status: 'ok',
      exists: true,
      path: DEFAULT_FORGE_RUNTIME_PATH,
      updated_at: fileStat.mtime.toISOString(),
      size_bytes: fileStat.size,
      line_count: raw.split(/\r?\n/).length,
      truncated,
      content,
      error: null,
    });
  } catch (error) {
    const code =
      typeof error === 'object' && error !== null && 'code' in error
        ? String((error as { code?: unknown }).code)
        : '';

    if (code === 'ENOENT') {
      return NextResponse.json({
        slot_id: 'forge',
        status: 'missing',
        exists: false,
        path: DEFAULT_FORGE_RUNTIME_PATH,
        updated_at: null,
        size_bytes: null,
        line_count: 0,
        truncated: false,
        content: '',
        error: 'Dosya bulunamadi. Pathi dogrulayin ya da FORGE_RUNTIME_MASTER_PATH ayarlayin.',
      });
    }

    return NextResponse.json({
      slot_id: 'forge',
      status: 'error',
      exists: false,
      path: DEFAULT_FORGE_RUNTIME_PATH,
      updated_at: null,
      size_bytes: null,
      line_count: 0,
      truncated: false,
      content: '',
      error: normalizeError(error),
    });
  }
}
