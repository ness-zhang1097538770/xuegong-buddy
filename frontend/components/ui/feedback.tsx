"use client";

import { AlertCircle, CheckCircle2, Loader2 } from "lucide-react";

export function Card({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`rounded-[16px] border border-border bg-surface shadow-[0_1px_2px_rgba(15,23,42,0.04),0_12px_28px_-18px_rgba(15,23,42,0.22)] ${className}`}
    >
      {children}
    </div>
  );
}

export function Alert({
  type = "error",
  message,
  onRetry,
}: {
  type?: "error" | "success" | "info";
  message: string;
  onRetry?: () => void;
}) {
  const styles = {
    error: "border-danger/20 bg-[#fef2f2] text-[#b91c1c]",
    success: "border-success/20 bg-[#f0fdf4] text-[#15803d]",
    info: "border-primary/20 bg-[#eff4ff] text-[#1d4ed8]",
  }[type];

  const Icon = type === "success" ? CheckCircle2 : AlertCircle;

  return (
    <div className={`flex items-start gap-2.5 rounded-[12px] border px-3.5 py-2.5 text-sm ${styles}`}>
      <Icon size={17} className="mt-0.5 shrink-0" />
      <span className="flex-1 whitespace-pre-wrap break-words leading-relaxed">{message}</span>
      {onRetry && (
        <button onClick={onRetry} className="shrink-0 font-medium underline">
          重试
        </button>
      )}
    </div>
  );
}

export function Spinner({ text }: { text?: string }) {
  return (
    <div className="flex items-center gap-2 text-sm text-muted">
      <Loader2 size={16} className="animate-spin" />
      {text}
    </div>
  );
}

export function EmptyState({ icon, title, desc }: { icon: React.ReactNode; title: string; desc?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-14 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-[16px] bg-primary-soft text-primary">
        {icon}
      </div>
      <p className="text-sm font-semibold text-text">{title}</p>
      {desc && <p className="max-w-sm text-xs leading-relaxed text-muted">{desc}</p>}
    </div>
  );
}

export function Badge({ children, tone = "default" }: { children: React.ReactNode; tone?: "default" | "success" | "danger" | "primary" }) {
  const tones = {
    default: "bg-[#f1f5f9] text-muted",
    success: "bg-[#f0fdf4] text-[#15803d]",
    danger: "bg-[#fef2f2] text-[#b91c1c]",
    primary: "bg-[#eff4ff] text-[#1d4ed8]",
  }[tone];
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${tones}`}>
      {children}
    </span>
  );
}
