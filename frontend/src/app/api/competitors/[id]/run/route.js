import { NextResponse } from "next/server";
import { apiFetch } from "@/lib/api";

export async function POST(request, { params }) {
  try {
    const result = await apiFetch(`/competitors/${params.id}/run`, {
      method: "POST",
    });
    return NextResponse.json(result);
  } catch (err) {
    return NextResponse.json({ error: err.message }, { status: 400 });
  }
}
