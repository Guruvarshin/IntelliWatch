import NextAuth from "next-auth";
import { NextResponse } from "next/server";
import authConfig from "./auth.config";

const { auth } = NextAuth(authConfig);

const PUBLIC_PATHS = ["/login", "/signup"];

export default auth((req) => {
  const isPublic = PUBLIC_PATHS.some((path) =>
    req.nextUrl.pathname.startsWith(path)
  );
  const isApiAuth = req.nextUrl.pathname.startsWith("/api/auth");
  const isApiSignup = req.nextUrl.pathname.startsWith("/api/signup");

  if (!req.auth && !isPublic && !isApiAuth && !isApiSignup) {
    const loginUrl = new URL("/login", req.nextUrl.origin);
    return NextResponse.redirect(loginUrl);
  }
});

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
