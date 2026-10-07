import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "学工 Buddy · 辅导员 AI 助手",
  description: "高校辅导员 / 学工行政专用：知识库问答、文稿生成、台账处理、常用网站",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body className="min-h-screen bg-bg text-text">{children}</body>
    </html>
  );
}
