import type { NextAuthOptions } from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";

export const authOptions: NextAuthOptions = {
  providers: [
    CredentialsProvider({
      name: "credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) return null;
        // Placeholder — Phase 6 integration will wire to Python API
        if (credentials.email === "demo@ontocenter.dev" && credentials.password === "demo123") {
          return { id: "demo", email: credentials.email, name: "Demo User", tenantId: "default" };
        }
        return null;
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.tenantId = (user as any).tenantId;
      }
      return token;
    },
    async session({ session, token }) {
      (session.user as any).tenantId = token.tenantId;
      return session;
    },
  },
  pages: { signIn: "/login" },
  session: { strategy: "jwt" },
};
