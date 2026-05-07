export function normalizeBridgeUrl() {
  const rawUrl = process.env.BRIDGE_URL?.trim() || 'http://127.0.0.1:8081';
  return rawUrl.endsWith('/') ? rawUrl.slice(0, -1) : rawUrl;
}

export async function fetchBridgeJson(pathname: string) {
  const response = await fetch(`${normalizeBridgeUrl()}${pathname}`, {
    cache: 'no-store',
  });

  const rawText = await response.text();
  let payload: unknown = {};
  try {
    payload = rawText ? JSON.parse(rawText) : {};
  } catch {
    payload = { error: rawText || 'Bridge JSON donmedi.' };
  }

  return {
    ok: response.ok,
    status: response.status,
    payload,
  };
}
