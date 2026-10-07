"use client";

import { Loader2 } from "lucide-react";
import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger";

const VARIANTS: Record<Variant, string> = {
  primary:
    "text-white bg-[linear-gradient(135deg,#2563eb_0%,#0ea5a4_100%)] shadow-[0_6px_16px_-8px_rgba(37,99,235,0.5)] hover:brightness-[1.05] hover:shadow-[0_8px_20px_-8px_rgba(37,99,235,0.6)] active:brightness-95 disabled:opacity-70 disabled:shadow-none",
  secondary: "bg-white text-text border border-border hover:bg-[#f1f5f9] disabled:text-muted",
  ghost: "bg-transparent text-muted hover:bg-[#f1f5f9] hover:text-text",
  danger: "bg-danger text-white hover:bg-[#dc2626] disabled:bg-[#f7a7a2]",
};

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  loading?: boolean;
  icon?: ReactNode;
}

export function Button({
  variant = "primary",
  loading = false,
  icon,
  children,
  className = "",
  disabled,
  ...rest
}: Props) {
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      className={`inline-flex shrink-0 items-center justify-center gap-2 whitespace-nowrap rounded-[10px] px-4 py-2 text-sm font-medium transition-all duration-150 disabled:cursor-not-allowed ${VARIANTS[variant]} ${className}`}
    >
      {loading ? <Loader2 size={16} className="animate-spin" /> : icon}
      {children}
    </button>
  );
}
