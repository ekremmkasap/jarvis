import { NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function normalizeBridgeUrl() {
  const rawUrl = process.env.BRIDGE_URL?.trim() || "http://127.0.0.1:8081";
  return rawUrl.endsWith("/") ? rawUrl.slice(0, -1) : rawUrl;
}

export async function POST() {
  const timestamp = Date.now();
  const email = `admin-test-${timestamp}@example.local`;
  const session = {
    id: `cs_admin_test_${timestamp}`,
    payment_status: "paid",
    customer: `cus_admin_test_${timestamp}`,
    customer_details: {
      email,
      name: "Admin Test"
    },
    metadata: {
      plan: "pro"
    }
  };

  const payload = {
    command: "stripe_webhook",
    data: { session },
    args: {
      text: JSON.stringify({
        source: "apps/web-ui/src/app/api/admin/stripe-test/route.ts",
        session
      })
    }
  };

  try {
    const response = await fetch(`${normalizeBridgeUrl()}/command`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload),
      cache: "no-store"
    });

    const bridgeBody = (await response.json().catch(() => ({}))) as Record<string, unknown>;
    if (!response.ok) {
      return NextResponse.json(
        { success: false, error: "Bridge stripe test istegi basarisiz oldu.", bridge: bridgeBody },
        { status: 502 }
      );
    }

    return NextResponse.json(
      {
        success: true,
        message: `Stripe test webhook gonderildi: ${email}`,
        bridge: bridgeBody
      },
      { status: 200 }
    );
  } catch (error) {
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "Bridge stripe test istegi basarisiz oldu."
      },
      { status: 502 }
    );
  }
}
