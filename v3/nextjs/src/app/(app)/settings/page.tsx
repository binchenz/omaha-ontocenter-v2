"use client";
import Link from "next/link";
import { signOut } from "next-auth/react";

export default function SettingsPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold text-text-primary mb-6">设置</h1>
      <div className="space-y-4">
        <Link href="/settings/api-keys" className="block bg-surface border border-gray-200 rounded-lg p-4 hover:border-accent transition-colors">
          <h3 className="font-medium text-text-primary">API Keys</h3>
          <p className="text-sm text-text-secondary mt-1">管理 MCP 外部访问的 API 密钥</p>
        </Link>
        <div className="bg-surface border border-gray-200 rounded-lg p-4">
          <h3 className="font-medium text-text-primary">账户信息</h3>
          <p className="text-sm text-text-secondary mt-1">OntoCenter v3 MVP · demo 账户</p>
        </div>
        <button onClick={() => signOut()} className="block w-full text-left bg-surface border border-gray-200 rounded-lg p-4 hover:border-red-300 transition-colors">
          <h3 className="font-medium text-red-500">退出登录</h3>
        </button>
      </div>
    </div>
  );
}
