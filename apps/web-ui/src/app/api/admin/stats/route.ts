import { NextResponse } from "next/server";
import { getAdminData } from "@/lib/adminData";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  const data = await getAdminData();
  return NextResponse.json(data, { status: 200 });
}
