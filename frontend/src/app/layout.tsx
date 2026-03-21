import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { TopBar } from "@/components/shared/TopBar";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Toaster } from "@/components/ui/sonner";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "CodeCouncil — AI Code Review Council",
  description:
    "Multi-agent AI system for comprehensive code analysis and RFC generation",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} dark h-full antialiased`}
    >
      <body
        className="min-h-full flex flex-col"
        style={{ backgroundColor: "var(--cc-bg)", color: "var(--cc-text)" }}
      >
        <TooltipProvider>
          <TopBar />
          <main className="flex-1 flex flex-col">{children}</main>
          <Toaster />
        </TooltipProvider>
      </body>
    </html>
  );
}
