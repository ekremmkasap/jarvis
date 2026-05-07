import { existsSync } from 'fs';
import { mkdir, readFile, writeFile } from 'fs/promises';
import path from 'path';
import { NextResponse } from 'next/server';

type BetaSignupPayload = {
  name?: unknown;
  email?: unknown;
  company?: unknown;
  plan?: unknown;
};

type BetaSignupRecord = {
  name: string;
  email: string;
  company: string;
  plan: 'Starter' | 'Pro' | 'Agency';
  createdAt: string;
};

const allowedPlans = new Set(['Starter', 'Pro', 'Agency']);

export const runtime = 'nodejs';

function findRepoRoot() {
  const candidates = [
    process.cwd(),
    path.resolve(process.cwd(), '..'),
    path.resolve(process.cwd(), '..', '..'),
  ];

  const match = candidates.find((candidate) => existsSync(path.join(candidate, 'server')));
  return match ?? path.resolve(process.cwd(), '..', '..');
}

function normalizePayload(payload: BetaSignupPayload): BetaSignupRecord {
  const name = typeof payload.name === 'string' ? payload.name.trim() : '';
  const email = typeof payload.email === 'string' ? payload.email.trim() : '';
  const company = typeof payload.company === 'string' ? payload.company.trim() : '';
  const plan = typeof payload.plan === 'string' ? payload.plan.trim() : '';

  if (!name || !email || !allowedPlans.has(plan)) {
    throw new Error('Geçersiz başvuru verisi.');
  }

  return {
    name,
    email,
    company,
    plan: plan as BetaSignupRecord['plan'],
    createdAt: new Date().toISOString(),
  };
}

async function readExistingSignups(filePath: string) {
  try {
    const fileContents = await readFile(filePath, 'utf-8');
    const parsed = JSON.parse(fileContents);

    return Array.isArray(parsed) ? parsed : [];
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === 'ENOENT') {
      return [];
    }

    throw error;
  }
}

export async function POST(request: Request) {
  try {
    const payload = (await request.json()) as BetaSignupPayload;
    const signup = normalizePayload(payload);

    const repoRoot = findRepoRoot();
    const dataDir = path.join(repoRoot, 'server', 'data');
    const filePath = path.join(dataDir, 'beta_signups.json');

    await mkdir(dataDir, { recursive: true });

    const existingSignups = await readExistingSignups(filePath);
    existingSignups.push(signup);

    await writeFile(filePath, JSON.stringify(existingSignups, null, 2), 'utf-8');

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('beta-signup POST failed', error);
    return NextResponse.json({ success: false }, { status: 500 });
  }
}
