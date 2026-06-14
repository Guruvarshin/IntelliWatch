import { NextResponse } from "next/server";
import { apiFetch } from "@/lib/api";

export async function POST(request) {
  const body = await request.json();

  try {
    const competitor = await apiFetch("/competitors", {
      method: "POST",
      body: JSON.stringify(body),
    });
    return NextResponse.json(competitor);
  } catch (err) {
    return NextResponse.json({ error: err.message }, { status: 400 });
  }
}
