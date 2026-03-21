"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Home, Settings, History } from "lucide-react";
import { Logo } from "./Logo";

const NAV_LINKS = [
  { href: "/", label: "Home", icon: Home },
  { href: "/sessions", label: "Sessions", icon: History },
  { href: "/config", label: "Config", icon: Settings },
];

export function TopBar() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 border-b border-[var(--cc-border)] glass">
      <div className="flex items-center justify-between px-6 h-14 max-w-7xl mx-auto w-full">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2.5 group">
          <Logo size={32} className="rounded-lg shadow-[0_2px_10px_rgba(108,92,231,0.4)] group-hover:shadow-[0_4px_20px_rgba(108,92,231,0.55)] transition-all duration-300" />
          <span className="font-bold text-lg tracking-tight">
            <span className="text-[var(--cc-text)]">Code</span>
            <span className="text-[var(--cc-accent)]">Council</span>
          </span>
        </Link>

        {/* Nav */}
        <nav aria-label="Main navigation" className="flex items-center gap-1 bg-[var(--cc-bg-elevated)] rounded-xl p-1 border border-[var(--cc-border)]">
          {NAV_LINKS.map(({ href, label, icon: Icon }) => {
            const isActive = href === "/" ? pathname === "/" : pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "flex items-center gap-2 px-4 py-1.5 rounded-lg text-sm font-medium transition-all duration-300",
                  isActive
                    ? "bg-[var(--cc-accent)] text-white shadow-[0_2px_10px_rgba(108,92,231,0.35)] glow-sm"
                    : "text-[var(--cc-text-muted)] hover:text-[var(--cc-text)] hover:bg-[var(--cc-bg-hover)]"
                )}
              >
                <Icon className="w-4 h-4" />
                {label}
              </Link>
            );
          })}
        </nav>

        {/* Status */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[var(--cc-bg-elevated)] border border-[var(--cc-border)]">
            <div className="w-2 h-2 rounded-full bg-[var(--cc-green)] animate-pulse-glow" />
            <span className="text-xs font-medium text-[var(--cc-text-secondary)]">Online</span>
          </div>
          <span className="text-xs font-mono text-[var(--cc-text-muted)]">v0.1.0</span>
        </div>
      </div>
    </header>
  );
}
