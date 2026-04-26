import { LayoutDashboard } from 'lucide-react';
export default function DashboardPage() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-gray-500">
      <LayoutDashboard size={48} className="mb-4 text-gray-600" />
      <h2 className="text-lg font-medium text-gray-300">数据看板</h2>
      <p className="text-sm mt-2">即将推出 — 从AI对话中"钉"图表到看板</p>
    </div>
  );
}
