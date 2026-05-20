import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "mira",
  description: "Market Intelligence Research Architecture for AI-driven competitor analysis"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
