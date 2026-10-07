"use client";

export default function GlobalError({ reset }: { error: Error; reset: () => void }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-3 px-4 text-center">
      <p className="text-base font-semibold text-text">页面出错了</p>
      <p className="max-w-sm text-sm text-muted">
        请重试；若持续失败，确认后端服务 http://127.0.0.1:8000 是否在运行。
      </p>
      <button
        onClick={reset}
        className="rounded-[8px] bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-[#1d4ed8]"
      >
        重试
      </button>
    </div>
  );
}
