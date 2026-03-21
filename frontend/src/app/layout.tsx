import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { TopBar } from "@/components/shared/TopBar";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Toaster } from "@/components/ui/sonner";

const inter = Inter({
  variable: "--font-sans",
  subsets: ["latin"],
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "CodeCouncil — AI Code Review Council",
  description: "Multi-agent AI system for comprehensive code analysis and RFC generation",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} ${jetbrainsMono.variable} dark h-full`}>
      <body className="min-h-full flex flex-col font-sans antialiased">
        <TooltipProvider>
          <TopBar />
          <ErrorBoundary>
            <main className="flex-1 flex flex-col">{children}</main>
          </ErrorBoundary>
          <Toaster />
        </TooltipProvider>
      </body>
    </html>
  );
}
