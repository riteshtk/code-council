"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { BookOpen, Home, Settings, History, Cpu } from "lucide-react";

const NAV_LINKS = [
  { href: "/", label: "Home", icon: Home },
  { href: "/sessions", label: "Sessions", icon: History },
  { href: "/config", label: "Config", icon: Settings },
];

export function TopBar() {
  const pathname = usePathname();

  return (
    <header
      className="sticky top-0 z-50 flex items-center justify-between px-6 py-3 border-b"
      style={{
        backgroundColor: "var(--cc-bg-card)",
        borderColor: "var(--cc-border)",
      }}
    >
      {/* Logo */}
      <Link href="/" className="flex items-center gap-2 group">
        <div
          className="flex items-center justify-center w-8 h-8 rounded-lg"
          style={{ backgroundColor: "var(--cc-accent)" }}
        >
          <Cpu className="w-5 h-5 text-white" />
        </div>
        <div>
          <span
            className="font-bold text-lg tracking-tight"
            style={{ color: "var(--cc-text)" }}
          >
            Code
          </span>
          <span
            className="font-bold text-lg tracking-tight"
            style={{ color: "var(--cc-accent)" }}
          >
            Council
          </span>
        </div>
      </Link>

      {/* Nav */}
      <nav className="flex items-center gap-1">
        {NAV_LINKS.map(({ href, label, icon: Icon }) => {
          const isActive =
            href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-colors",
                isActive
                  ? "text-white"
                  : "hover:opacity-80"
              )}
              style={{
                backgroundColor: isActive ? "var(--cc-accent)" : "transparent",
                color: isActive ? "white" : "var(--cc-text-muted)",
              }}
            >
              <Icon className="w-4 h-4" />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Status */}
      <div className="flex items-center gap-2">
        <BookOpen className="w-4 h-4" style={{ color: "var(--cc-text-muted)" }} />
        <span className="text-xs" style={{ color: "var(--cc-text-muted)" }}>
          v0.1.0
        </span>
      </div>
    </header>
  );
}
