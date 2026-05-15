import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CompeteScope AI",
  description: "AI-driven competitor analysis Agent collaboration system"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}

