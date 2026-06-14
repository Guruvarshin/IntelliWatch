import { SignJWT, jwtVerify } from "jose";

const secret = new TextEncoder().encode(process.env.AUTH_SECRET);

export default {
  session: { strategy: "jwt" },
  pages: {
    signIn: "/login",
  },
  providers: [],
  jwt: {
    encode: async ({ token }) => {
      return await new SignJWT(token)
        .setProtectedHeader({ alg: "HS256" })
        .setIssuedAt()
        .setExpirationTime("30d")
        .sign(secret);
    },
    decode: async ({ token }) => {
      if (!token) return null;
      const { payload } = await jwtVerify(token, secret);
      return payload;
    },
  },
  callbacks: {
    jwt: async ({ token, user }) => {
      if (user) {
        token.sub = user.id;
      }
      return token;
    },
    session: async ({ session, token }) => {
      if (token?.sub && session.user) {
        session.user.id = token.sub;
      }
      return session;
    },
  },
};
