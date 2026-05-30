import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { AppShell } from "@/components/AppShell";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "AI Infrastructure Monitoring Dashboard",
  description:
    "Monitoring & intelligence dashboard for AI infrastructure: servers, metrics, and AI-driven reports.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full bg-[#0f1117] text-[#e2e8f0]">
        {/* AppShell renders the sidebar/header + session timeout on protected
            routes, and renders public routes (login, unauthorized) bare. */}
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
