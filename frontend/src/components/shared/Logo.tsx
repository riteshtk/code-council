"use client";

export function Logo({ size = 32, className = "" }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 512 512"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <defs>
        <linearGradient id="cc-bg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#7c6cf0" />
          <stop offset="100%" stopColor="#5a4bd4" />
        </linearGradient>
      </defs>

      {/* Rounded square background */}
      <rect width="512" height="512" rx="96" fill="url(#cc-bg)" />

      {/* Subtle top shine */}
      <rect width="512" height="256" rx="96" fill="white" opacity="0.07" />

      {/* First C (code bracket) */}
      <path
        d="M220 160 L140 256 L220 352"
        stroke="white"
        strokeWidth="36"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* Second C (code bracket, offset) */}
      <path
        d="M295 160 L215 256 L295 352"
        stroke="white"
        strokeWidth="36"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity="0.5"
      />

      {/* Closing bracket for balance */}
      <path
        d="M340 180 L400 256 L340 332"
        stroke="white"
        strokeWidth="28"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity="0.7"
      />

      {/* 4 agent dots */}
      <circle cx="108" cy="108" r="18" fill="#d4a574" />
      <circle cx="404" cy="108" r="18" fill="#ff6b6b" />
      <circle cx="108" cy="404" r="18" fill="#4ecdc4" />
      <circle cx="404" cy="404" r="18" fill="#00d68f" />
    </svg>
  );
}
