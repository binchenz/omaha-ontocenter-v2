import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'OntoCenter v3',
  description: 'AI-native data platform for Chinese SMEs',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
