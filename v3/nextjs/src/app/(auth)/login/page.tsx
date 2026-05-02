"use client";
import { useState } from "react";
import { signIn } from "next-auth/react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const [email, setEmail] = useState("demo@ontocenter.dev");
  const [password, setPassword] = useState("demo123");
  const [error, setError] = useState("");
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    const result = await signIn("credentials", { email, password, redirect: false });
    if (result?.ok) router.push("/chat");
    else setError("邮箱或密码错误");
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-root">
      <div className="w-96 bg-surface rounded-lg p-8 border border-gray-200">
        <h1 className="text-xl font-bold text-text-primary mb-1">
          OntoCenter <span className="text-accent">v3</span>
        </h1>
        <p className="text-xs text-text-secondary mb-6">AI 原生的中小企业数据分析平台</p>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label className="block text-sm text-text-secondary mb-1">邮箱</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 py-2 border border-gray-200 rounded bg-root text-sm text-text-primary"
            />
          </div>
          <div>
            <label className="block text-sm text-text-secondary mb-1">密码</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 border border-gray-200 rounded bg-root text-sm text-text-primary"
            />
          </div>
          {error && <p className="text-xs text-red-500">{error}</p>}
          <button type="submit" className="w-full py-2 bg-accent text-white rounded text-sm font-medium hover:bg-accent-hover transition-colors">
            登录
          </button>
        </form>
        <p className="text-xs text-text-secondary mt-4 pt-4 border-t border-gray-100">
          MVP 版本，使用预填的演示账号即可登录
        </p>
      </div>
    </div>
  );
}
