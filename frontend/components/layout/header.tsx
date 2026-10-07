"use client";

import { useRouter } from "next/navigation";
import { LogOut } from "lucide-react";
import { clearSession } from "@/lib/auth";
import type { UserInfo } from "@/lib/types";

export function Header({ user }: { user: UserInfo | null }) {
  const router = useRouter();

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-surface/90 px-4 backdrop-blur md:px-6">
      <div className="flex items-center gap-2">
        <span className="hidden h-2.5 w-2.5 rounded-full bg-[linear-gradient(135deg,#2563eb_0%,#0ea5a4_100%)] sm:block" />
        <h1 className="text-sm font-medium text-muted">
          {user ? (
            <>
              欢迎回来，<span className="font-semibold text-text">{user.email}</span>
            </>
          ) : (
            "学工 Buddy"
          )}
        </h1>
      </div>
      <button
        onClick={() => {
          clearSession();
          router.replace("/login");
        }}
        className="flex items-center gap-1.5 rounded-[10px] px-3 py-1.5 text-sm text-muted transition-colors hover:bg-[#f1f5f9] hover:text-text"
      >
        <LogOut size={16} />
        退出
      </button>
    </header>
  );
}
