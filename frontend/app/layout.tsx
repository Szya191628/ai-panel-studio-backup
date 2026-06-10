import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Panel Studio — Virtual Roundtable Broadcasting",
  description: "AI-powered virtual roundtable discussions with expert panels",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body>
        {children}
      </body>
    </html>
  );
}
