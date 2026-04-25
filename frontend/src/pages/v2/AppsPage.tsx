import { AppWindow } from 'lucide-react';
export default function AppsPage() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-gray-500">
      <AppWindow size={48} className="mb-4 text-gray-600" />
      <h2 className="text-lg font-medium text-gray-300">应用中心</h2>
      <p className="text-sm mt-2">即将推出 — 表单、看板、提醒等轻应用</p>
    </div>
  );
}
