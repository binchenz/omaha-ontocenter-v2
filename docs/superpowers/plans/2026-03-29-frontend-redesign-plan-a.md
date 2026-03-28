# Frontend Redesign Plan A: Foundation

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Ant Design with shadcn/ui + Tailwind CSS, add left sidebar navigation, and migrate Login, Register, and ProjectList pages.

**Architecture:** Install Tailwind + shadcn/ui alongside existing Ant Design. Build the new layout shell (Sidebar + MainLayout) first, then migrate pages one by one. Ant Design is removed only after all pages are migrated in Plan B.

**Tech Stack:** React 18, TypeScript, Vite, shadcn/ui, Tailwind CSS v3, react-router-dom v6, lucide-react (icons)

**Spec:** `docs/superpowers/specs/2026-03-29-frontend-redesign-design.md`

---

## Chunk 1: Tailwind + shadcn/ui Setup

### Task 1: Install Tailwind CSS

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/tailwind.config.js`
- Create: `frontend/postcss.config.js`
- Modify: `frontend/src/index.css`

- [ ] **Step 1: Install Tailwind and dependencies**

```bash
cd frontend
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

- [ ] **Step 2: Configure tailwind.config.js**

Replace generated content with:
```js
/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        background: '#0a0a0a',
        surface: '#111111',
        primary: '#2563EB',
      },
      fontFamily: {
        sans: ['Fira Sans', 'sans-serif'],
        mono: ['Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
}
```

- [ ] **Step 3: Add Tailwind directives to index.css**

Replace `frontend/src/index.css` content with:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500&family=Fira+Sans:wght@400;500;600;700&display=swap');

body {
  background-color: #0a0a0a;
  color: #f1f5f9;
  font-family: 'Fira Sans', sans-serif;
}
```

- [ ] **Step 4: Verify Tailwind works**

```bash
cd frontend
npm run build 2>&1 | head -20
```
Expected: build succeeds (warnings about unused vars are OK, errors are not)

- [ ] **Step 5: Commit**

```bash
git add frontend/tailwind.config.js frontend/postcss.config.js frontend/src/index.css frontend/package.json frontend/package-lock.json
git commit -m "feat: install Tailwind CSS"
```

---

### Task 2: Install shadcn/ui

**Files:**
- Modify: `frontend/components.json` (created by shadcn init)
- Create: `frontend/src/components/ui/` (shadcn primitives)
- Modify: `frontend/src/lib/utils.ts` (created by shadcn init)

- [ ] **Step 1: Install shadcn/ui CLI and init**

```bash
cd frontend
npm install -D @shadcn/ui
npx shadcn@latest init
```

When prompted:
- Style: Default
- Base color: Slate
- CSS variables: Yes

- [ ] **Step 2: Install required shadcn components**

```bash
cd frontend
npx shadcn@latest add button card input label tabs dialog table badge
```

- [ ] **Step 3: Install lucide-react for icons**

```bash
cd frontend
npm install lucide-react
```

- [ ] **Step 4: Verify components exist**

```bash
ls frontend/src/components/ui/
```
Expected: `button.tsx card.tsx input.tsx label.tsx tabs.tsx dialog.tsx table.tsx badge.tsx`

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/ frontend/src/lib/ frontend/components.json frontend/package.json frontend/package-lock.json
git commit -m "feat: install shadcn/ui components"
```

---

## Chunk 2: Sidebar Layout

### Task 3: Build Sidebar component

**Files:**
- Create: `frontend/src/components/Layout/Sidebar.tsx`

- [ ] **Step 1: Create Sidebar.tsx**

```tsx
import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { FolderOpen, Star, LogOut, User } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { cn } from '@/lib/utils';

const navItems = [
  { to: '/projects', icon: FolderOpen, label: 'Projects' },
  { to: '/watchlist', icon: Star, label: 'Watchlist' },
];

const Sidebar: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <aside className="fixed left-0 top-0 h-screen w-60 bg-surface border-r border-white/10 flex flex-col z-40">
      <div className="px-6 py-5 border-b border-white/10">
        <span className="text-white font-semibold text-sm tracking-wide font-mono">
          Omaha OntoCenter
        </span>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors',
                isActive
                  ? 'bg-primary/10 text-primary border-l-2 border-primary pl-[10px]'
                  : 'text-slate-400 hover:text-white hover:bg-white/5'
              )
            }
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="px-3 py-4 border-t border-white/10">
        <div className="flex items-center gap-3 px-3 py-2 text-sm text-slate-400">
          <User size={16} />
          <span className="flex-1 truncate">{user?.username}</span>
          <button
            onClick={handleLogout}
            className="hover:text-white transition-colors"
            title="Logout"
          >
            <LogOut size={16} />
          </button>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/Layout/Sidebar.tsx
git commit -m "feat: add Sidebar component"
```

---

### Task 4: Update MainLayout to use Sidebar

**Files:**
- Modify: `frontend/src/components/Layout/MainLayout.tsx`

- [ ] **Step 1: Rewrite MainLayout.tsx**

```tsx
import React from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';

const MainLayout: React.FC = () => {
  return (
    <div className="min-h-screen bg-background text-white">
      <Sidebar />
      <main className="ml-60 p-6 min-h-screen">
        <Outlet />
      </main>
    </div>
  );
};

export default MainLayout;
```

- [ ] **Step 2: Verify layout compiles**

```bash
cd frontend && npm run build 2>&1 | tail -5
```
Expected: build succeeds. (Manual check: run `npm run dev` yourself to visually confirm sidebar appears.)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/Layout/MainLayout.tsx
git commit -m "feat: replace header with sidebar layout"
```

---

## Chunk 3: Page Migrations

### Task 5: Migrate Login page

**Files:**
- Modify: `frontend/src/pages/Login.tsx`

- [ ] **Step 1: Rewrite Login.tsx**

```tsx
import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

const Login: React.FC = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();
  const { login } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(username, password);
      navigate('/projects');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center">
      <Card className="w-96 bg-surface border-white/10">
        <CardHeader>
          <CardTitle className="text-white text-center">Login</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1">
              <Label htmlFor="username" className="text-slate-300">Username</Label>
              <Input
                id="username"
                value={username}
                onChange={e => setUsername(e.target.value)}
                required
                className="bg-background border-white/10 text-white"
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="password" className="text-slate-300">Password</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                className="bg-background border-white/10 text-white"
              />
            </div>
            {error && <p className="text-red-400 text-sm">{error}</p>}
            <Button type="submit" disabled={loading} className="w-full bg-primary hover:bg-primary/90">
              {loading ? 'Logging in...' : 'Login'}
            </Button>
            <p className="text-center text-sm text-slate-400">
              Don't have an account?{' '}
              <Link to="/register" className="text-primary hover:underline">Register</Link>
            </p>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};

export default Login;
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/Login.tsx
git commit -m "feat: migrate Login to shadcn/ui"
```

---

### Task 6: Migrate Register page

**Files:**
- Modify: `frontend/src/pages/Register.tsx`

- [ ] **Step 1: Rewrite Register.tsx**

```tsx
import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { authService } from '@/services/auth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

const Register: React.FC = () => {
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (password.length < 8) { setError('Password must be at least 8 characters'); return; }
    setLoading(true);
    try {
      await authService.register({ email, username, full_name: fullName, password });
      navigate('/login');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center">
      <Card className="w-96 bg-surface border-white/10">
        <CardHeader>
          <CardTitle className="text-white text-center">Register</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1">
              <Label htmlFor="email" className="text-slate-300">Email *</Label>
              <Input id="email" type="email" value={email} onChange={e => setEmail(e.target.value)}
                required className="bg-background border-white/10 text-white" />
            </div>
            <div className="space-y-1">
              <Label htmlFor="username" className="text-slate-300">Username *</Label>
              <Input id="username" value={username} onChange={e => setUsername(e.target.value)}
                required minLength={3} className="bg-background border-white/10 text-white" />
            </div>
            <div className="space-y-1">
              <Label htmlFor="fullName" className="text-slate-300">Full Name</Label>
              <Input id="fullName" value={fullName} onChange={e => setFullName(e.target.value)}
                className="bg-background border-white/10 text-white" />
            </div>
            <div className="space-y-1">
              <Label htmlFor="password" className="text-slate-300">Password *</Label>
              <Input id="password" type="password" value={password} onChange={e => setPassword(e.target.value)}
                required className="bg-background border-white/10 text-white" />
            </div>
            {error && <p className="text-red-400 text-sm">{error}</p>}
            <Button type="submit" disabled={loading} className="w-full bg-primary hover:bg-primary/90">
              {loading ? 'Registering...' : 'Register'}
            </Button>
            <p className="text-center text-sm text-slate-400">
              Already have an account?{' '}
              <Link to="/login" className="text-primary hover:underline">Login</Link>
            </p>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};

export default Register;
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/Register.tsx
git commit -m "feat: migrate Register to shadcn/ui"
```

---

### Task 7: Migrate ProjectList page

**Files:**
- Modify: `frontend/src/pages/ProjectList.tsx`

- [ ] **Step 1: Install shadcn table and dialog if not already added**

```bash
cd frontend
npx shadcn@latest add table dialog
```

- [ ] **Step 2: Rewrite ProjectList.tsx**

Replace Ant Design Table/Modal/Form/Button with shadcn equivalents:
- `Table` → shadcn `Table, TableHeader, TableBody, TableRow, TableHead, TableCell`
- `Modal` → shadcn `Dialog, DialogContent, DialogHeader, DialogTitle`
- `Button` → shadcn `Button`
- `Input/TextArea` → shadcn `Input` + native `textarea`
- Remove all `antd` and `@ant-design/icons` imports
- Use `lucide-react` icons: `Plus`, `Pencil`, `Trash2`
- Confirmation before delete: use `window.confirm()` (simple, no extra component needed)

```tsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Pencil, Trash2, Settings } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { projectService } from '@/services/project';
import { Project } from '@/types';

const ProjectList: React.FC = () => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Project | null>(null);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const navigate = useNavigate();

  useEffect(() => { loadProjects(); }, []);

  const loadProjects = async () => {
    setLoading(true);
    try { setProjects(await projectService.list()); }
    catch { /* error handled silently */ }
    finally { setLoading(false); }
  };

  const openCreate = () => { setEditing(null); setName(''); setDescription(''); setModalOpen(true); };
  const openEdit = (p: Project) => { setEditing(p); setName(p.name); setDescription(p.description || ''); setModalOpen(true); };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Delete this project?')) return;
    await projectService.delete(id);
    loadProjects();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (editing) {
      await projectService.update(editing.id, { name, description });
    } else {
      await projectService.create({ name, description });
    }
    setModalOpen(false);
    loadProjects();
  };

  return (
    <Card className="bg-surface border-white/10">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-white">Projects</CardTitle>
        <Button onClick={openCreate} size="sm" className="bg-primary hover:bg-primary/90">
          <Plus size={16} className="mr-2" /> New Project
        </Button>
      </CardHeader>
      <CardContent>
        {loading ? (
          <p className="text-slate-400 text-sm">Loading...</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow className="border-white/10">
                <TableHead className="text-slate-400">Name</TableHead>
                <TableHead className="text-slate-400">Description</TableHead>
                <TableHead className="text-slate-400">Created</TableHead>
                <TableHead className="text-slate-400">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {projects.map(p => (
                <TableRow key={p.id} className="border-white/10 hover:bg-white/5">
                  <TableCell className="text-white font-medium">{p.name}</TableCell>
                  <TableCell className="text-slate-400">{p.description}</TableCell>
                  <TableCell className="text-slate-400 font-mono text-xs">
                    {new Date(p.created_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-2">
                      <Button variant="ghost" size="sm" onClick={() => navigate(`/projects/${p.id}`)}>
                        <Settings size={14} />
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => openEdit(p)}>
                        <Pencil size={14} />
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => handleDelete(p.id)}
                        className="text-red-400 hover:text-red-300">
                        <Trash2 size={14} />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>

      <Dialog open={modalOpen} onOpenChange={setModalOpen}>
        <DialogContent className="bg-surface border-white/10 text-white">
          <DialogHeader>
            <DialogTitle>{editing ? 'Edit Project' : 'Create Project'}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1">
              <Label className="text-slate-300">Name *</Label>
              <Input value={name} onChange={e => setName(e.target.value)} required
                className="bg-background border-white/10 text-white" />
            </div>
            <div className="space-y-1">
              <Label className="text-slate-300">Description</Label>
              <textarea value={description} onChange={e => setDescription(e.target.value)}
                rows={3}
                className="w-full rounded-md border border-white/10 bg-background px-3 py-2 text-sm text-white resize-none focus:outline-none focus:ring-2 focus:ring-primary" />
            </div>
            <div className="flex gap-2 justify-end">
              <Button type="button" variant="ghost" onClick={() => setModalOpen(false)}>Cancel</Button>
              <Button type="submit" className="bg-primary hover:bg-primary/90">
                {editing ? 'Update' : 'Create'}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </Card>
  );
};

export default ProjectList;
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/ProjectList.tsx
git commit -m "feat: migrate ProjectList to shadcn/ui"
```

---

## Chunk 4: Cleanup and Verification

### Task 8: Add dark class to html element

**Files:**
- Modify: `frontend/index.html`

- [ ] **Step 1: Add dark class**

In `frontend/index.html`, change:
```html
<html lang="en">
```
to:
```html
<html lang="en" class="dark">
```

- [ ] **Step 2: Commit**

```bash
git add frontend/index.html
git commit -m "feat: enable dark mode class on html element"
```

---

### Task 9: Verify Plan A build

- [ ] **Step 1: Run build**

```bash
cd frontend && npm run build 2>&1
```
Expected: build succeeds with no errors (TypeScript errors must be fixed before proceeding)

- [ ] **Step 2: Manual smoke test** *(run by human, not agent)*

Run `npm run dev` manually, verify:
- Sidebar appears with Projects + Watchlist links
- Login page renders with dark theme
- ProjectList renders with dark table
- No Ant Design styles bleeding in on migrated pages

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "feat: Plan A complete - Tailwind + shadcn/ui foundation"
```
