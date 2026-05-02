"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { MessageSquare, Database, Box, Puzzle, Settings } from "lucide-react";

const items = [
  { label: "对话", href: "/chat", Icon: MessageSquare },
  { label: "本体", href: "/ontology", Icon: Box },
  { label: "数据源", href: "/datasources", Icon: Database },
  { label: "能力中心", href: "/skills", Icon: Puzzle },
  { label: "设置", href: "/settings", Icon: Settings },
];

export default function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="w-56 h-screen bg-surface border-r border-gray-200 flex flex-col p-3">
      <Link href="/" className="text-lg font-bold text-accent mb-8 px-2 py-2">
        OntoCenter<span className="text-text-secondary text-sm font-normal ml-1">v3</span>
      </Link>
      <nav className="flex flex-col gap-1">
        {items.map(({ label, href, Icon }) => {
          const active = pathname?.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-2 px-2 py-2 rounded text-sm transition-colors ${
                active
                  ? "bg-accent-glow text-accent font-medium"
                  : "text-text-secondary hover:text-text-primary hover:bg-data"
              }`}
            >
              <Icon size={18} />
              {label}
            </Link>
          );
        })}
      </nav>
      <div className="mt-auto pt-4 border-t border-gray-200 text-xs text-text-secondary">
        v0.1.0 MVP
      </div>
    </aside>
  );
}
