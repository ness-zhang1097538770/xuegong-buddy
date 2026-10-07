"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { GraduationCap } from "lucide-react";
import { NAV_GROUPS, NAV_ITEMS } from "./nav-items";

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden w-60 shrink-0 flex-col border-r border-border bg-surface md:flex">
      <div className="flex items-center gap-2.5 px-5 py-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-[10px] bg-[linear-gradient(135deg,#2563eb_0%,#0ea5a4_100%)] text-white shadow-[0_6px_14px_-6px_rgba(37,99,235,0.6)]">
          <GraduationCap size={20} />
        </div>
        <div>
          <p className="text-sm font-semibold text-text">学工 Buddy</p>
          <p className="text-xs text-muted">辅导员 AI 副驾</p>
        </div>
      </div>

      <nav className="thin-scroll flex-1 space-y-4 overflow-y-auto px-3 pb-2">
        {NAV_GROUPS.map((group) => (
          <div key={group.label}>
            <p className="mb-1 px-3 text-[11px] font-medium uppercase tracking-wide text-muted/70">
              {group.label}
            </p>
            <div className="flex flex-col gap-1">
              {group.items.map((item) => {
                const active =
                  item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`flex items-center gap-3 rounded-[10px] px-3 py-2.5 text-sm transition-all ${
                      active
                        ? "bg-primary-soft font-medium text-primary shadow-[inset_0_0_0_1px_rgba(37,99,235,0.12)]"
                        : "text-muted hover:bg-[#f8fafc] hover:text-text"
                    }`}
                  >
                    <Icon size={18} className={active ? "text-primary" : ""} />
                    {item.label}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      <div className="mt-auto px-5 py-4">
        <p className="rounded-[12px] bg-primary-soft px-3 py-2.5 text-xs leading-relaxed text-primary/80">
          AI 输出仅为草稿，涉及学生评价、思政与危机材料必须人工复核。
        </p>
      </div>
    </aside>
  );
}

export function MobileNav() {
  const pathname = usePathname();

  return (
    <nav className="thin-scroll fixed bottom-0 left-0 z-20 flex w-full gap-0.5 overflow-x-auto border-t border-border bg-surface/95 px-1 py-1 backdrop-blur md:hidden">
      {NAV_ITEMS.map((item) => {
        const active =
          item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
        const Icon = item.icon;
        return (
          <Link
            key={item.href}
            href={item.href}
            className={`flex min-w-[52px] flex-1 flex-col items-center gap-1 rounded-[10px] px-1 py-2 text-[10px] leading-none transition-colors ${
              active ? "bg-primary-soft font-medium text-primary" : "text-muted"
            }`}
          >
            <Icon size={19} className={active ? "text-primary" : ""} />
            {item.shortLabel}
          </Link>
        );
      })}
    </nav>
  );
}
