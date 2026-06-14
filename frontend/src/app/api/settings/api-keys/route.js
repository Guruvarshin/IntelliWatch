import { NextResponse } from "next/server";
import { apiFetch } from "@/lib/api";

export async function PUT(request) {
  const body = await request.json();

  try {
    const result = await apiFetch("/me/api-keys", {
      method: "PUT",
      body: JSON.stringify(body),
    });
    return NextResponse.json(result);
  } catch (err) {
    return NextResponse.json({ error: err.message }, { status: 400 });
  }
}
