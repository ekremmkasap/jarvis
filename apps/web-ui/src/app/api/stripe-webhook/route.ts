import { NextResponse } from 'next/server';

type BridgeCommandPayload = {
  command: 'stripe_webhook';
  data: {
    session: Record<string, unknown>;
  };
  args: {
    text: string;
  };
};

const defaultBridgeUrl = 'http://127.0.0.1:8081';

export const runtime = 'nodejs';

function normalizeBridgeUrl() {
  const rawUrl = process.env.BRIDGE_URL?.trim() || defaultBridgeUrl;
  return rawUrl.endsWith('/') ? rawUrl.slice(0, -1) : rawUrl;
}

export async function POST(request: Request) {
  let StripeCtor: any;

  try {
    const dynamicImport = new Function('moduleName', 'return import(moduleName);') as (
      moduleName: string,
    ) => Promise<{ default: any }>;
    const stripeModule = await dynamicImport('stripe');
    StripeCtor = stripeModule.default;
  } catch (error) {
    console.error('stripe-webhook POST failed to import stripe', error);
    return NextResponse.json(
      { success: false, error: 'stripe npm paketi yuklu degil.' },
      { status: 500 },
    );
  }

  const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET?.trim();
  if (!webhookSecret) {
    return NextResponse.json(
      { success: false, error: 'STRIPE_WEBHOOK_SECRET tanimli degil.' },
      { status: 500 },
    );
  }

  const signature = request.headers.get('stripe-signature');
  if (!signature) {
    return NextResponse.json(
      { success: false, error: 'stripe-signature header eksik.' },
      { status: 400 },
    );
  }

  const rawBody = await request.text();
  const stripe = new StripeCtor('sk_test_placeholder');

  let event: { type: string; data: { object: Record<string, unknown> } };
  try {
    event = stripe.webhooks.constructEvent(rawBody, signature, webhookSecret) as typeof event;
  } catch (error) {
    console.error('stripe-webhook signature verification failed', error);
    return NextResponse.json(
      { success: false, error: 'Stripe webhook imzasi dogrulanamadi.' },
      { status: 400 },
    );
  }

  if (event.type !== 'checkout.session.completed') {
    return NextResponse.json({ success: true, ignored: true, eventType: event.type });
  }

  const session = event.data.object;
  const bridgePayload: BridgeCommandPayload = {
    command: 'stripe_webhook',
    data: { session },
    args: {
      text: JSON.stringify({
        eventType: event.type,
        session,
        payload: rawBody,
        signature,
        source: 'apps/web-ui/src/app/api/stripe-webhook/route.ts',
      }),
    },
  };

  try {
    const bridgeResponse = await fetch(`${normalizeBridgeUrl()}/command`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(bridgePayload),
      cache: 'no-store',
    });

    if (!bridgeResponse.ok) {
      const bridgeError = await bridgeResponse.text();
      console.error('stripe-webhook bridge forwarding failed', bridgeError);
      return NextResponse.json(
        { success: false, error: 'Bridge command endpoint hata verdi.' },
        { status: 502 },
      );
    }

    const bridgeResult = await bridgeResponse.json().catch(() => ({}));
    return NextResponse.json({ success: true, forwarded: true, bridge: bridgeResult });
  } catch (error) {
    console.error('stripe-webhook bridge request failed', error);
    return NextResponse.json(
      { success: false, error: 'Bridge endpoint ulasilamadi.' },
      { status: 502 },
    );
  }
}
