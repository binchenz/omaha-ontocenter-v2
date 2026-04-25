import {
  MessageSquare, History, Database, GitBranch, HardDrive, Upload,
  LayoutDashboard, LayoutTemplate, AppWindow,
  Users, Workflow, Key, ClipboardList,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

export interface SubPage {
  label: string;
  path: string;
  icon: LucideIcon;
}

export interface NavModule {
  key: string;
  label: string;
  basePath: string;
  subPages: SubPage[];
}

export const NAV_MODULES: NavModule[] = [
  {
    key: 'assistant',
    label: 'AI助手',
    basePath: '/app/assistant',
    subPages: [
      { label: '对话', path: '/app/assistant', icon: MessageSquare },
      { label: '历史', path: '/app/assistant/history', icon: History },
    ],
  },
  {
    key: 'ontology',
    label: '本体',
    basePath: '/app/ontology',
    subPages: [
      { label: '对象浏览', path: '/app/ontology', icon: Database },
      { label: '关系图谱', path: '/app/ontology/graph', icon: GitBranch },
      { label: '数据源', path: '/app/ontology/datasources', icon: HardDrive },
      { label: '导入/建模', path: '/app/ontology/modeling', icon: Upload },
    ],
  },
  {
    key: 'dashboard',
    label: '看板',
    basePath: '/app/dashboard',
    subPages: [
      { label: '我的看板', path: '/app/dashboard', icon: LayoutDashboard },
      { label: '模板看板', path: '/app/dashboard/templates', icon: LayoutTemplate },
    ],
  },
  {
    key: 'apps',
    label: '应用',
    basePath: '/app/apps',
    subPages: [
      { label: '应用中心', path: '/app/apps', icon: AppWindow },
    ],
  },
  {
    key: 'settings',
    label: '设置',
    basePath: '/app/settings',
    subPages: [
      { label: '成员管理', path: '/app/settings', icon: Users },
      { label: 'Pipeline', path: '/app/settings/pipelines', icon: Workflow },
      { label: 'API密钥', path: '/app/settings/api-keys', icon: Key },
      { label: '审计日志', path: '/app/settings/audit', icon: ClipboardList },
    ],
  },
];

export function findModuleByPath(pathname: string): NavModule | undefined {
  return NAV_MODULES.find((m) => pathname.startsWith(m.basePath));
}
