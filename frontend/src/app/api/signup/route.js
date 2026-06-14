import { NextResponse } from "next/server";
import bcrypt from "bcryptjs";
import clientPromise from "@/lib/mongodb";

export async function POST(request) {
  const { email, password } = await request.json();

  if (!email || !password || password.length < 8) {
    return NextResponse.json(
      { error: "Email and password (min 8 characters) are required." },
      { status: 400 }
    );
  }

  const client = await clientPromise;
  const db = client.db();
  const users = db.collection("users");

  const existing = await users.findOne({ email });
  if (existing) {
    return NextResponse.json(
      { error: "An account with this email already exists." },
      { status: 409 }
    );
  }

  const hashedPassword = await bcrypt.hash(password, 10);

  await users.insertOne({
    email,
    hashedPassword,
    createdAt: new Date(),
  });

  return NextResponse.json({ success: true });
}
