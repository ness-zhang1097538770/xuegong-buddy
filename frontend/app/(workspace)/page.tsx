"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  Check,
  ClipboardList,
  LayoutDashboard,
  MessageSquareHeart,
  Plus,
  ShieldAlert,
  UserRound,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Alert, Card, EmptyState, Spinner } from "@/components/ui/feedback";
import { Select } from "@/components/ui/field";
import { homeApi } from "@/lib/api";
import type { HomeSummary, HomeTodo } from "@/lib/types";

type Period = "all" | "today" | "week" | "month";

function todayStr(): string {
  return new Date().toISOString().slice(0, 10);
}

function inRange(due: string, days: number): boolean {
  if (!due) return false;
  const t = new Date(todayStr()).getTime();
  const d = new Date(due).getTime();
  return d >= t && d <= t + days * 86400000;
}

function greeting(): string {
  const h = new Date().getHours();
  if (h < 6) return "夜深了";
  if (h < 12) return "早上好";
  if (h < 14) return "中午好";
  if (h < 18) return "下午好";
  return "晚上好";
}

/** 逾期 > 今天 > 未来 > 无日期，同段内按优先级降序。 */
function sortTodos(todos: HomeTodo[]): HomeTodo[] {
  const t = todayStr();
  return [...todos].sort((a, b) => {
    const rank = (x: HomeTodo) => {
      if (!x.due_date) return 3;
      if (x.due_date < t) return 0;
      if (x.due_date === t) return 1;
      return 2;
    };
    const r = rank(a) - rank(b);
    if (r !== 0) return r;
    return (b.priority ?? 0) - (a.priority ?? 0);
  });
}

const TODO_TYPE_LABEL: Record<string, string> = {
  approval: "审批",
  talk: "谈话跟进",
  dorm: "异常宿舍",
  reminder: "提醒",
  default: "待办",
};

function typeLabel(t: HomeTodo): string {
  return TODO_TYPE_LABEL[t.source_type] ?? TODO_TYPE_LABEL.default;
}

const STATS: {
  key: keyof HomeSummary["stats"];
  label: string;
  icon: typeof LayoutDashboard;
  href?: string;
  query?: string;
}[] = [
  { key: "pending_approvals", label: "待我审批", icon: ClipboardList, href: "/approvals" },
  { key: "pending_talks", label: "待跟进谈话", icon: MessageSquareHeart, href: "/talks", query: "need_follow=1" },
  { key: "abnormal_dorms", label: "今日异常宿舍", icon: ShieldAlert, href: "/dorm" },
  { key: "risk_students", label: "学业预警人数", icon: UserRound, href: "/students", query: "risk_level=high" },
];

export default function HomePage() {
  const [data, setData] = useState<HomeSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [period, setPeriod] = useState<Period>("all");
  const [resolving, setResolving] = useState<number | null>(null);
  const [showAdd, setShowAdd] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newDate, setNewDate] = useState("");
  const [newNote, setNewNote] = useState("");
  const [adding, setAdding] = useState(false);

  async function load() {
    try {
      setData(await homeApi.summary());
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const res = await homeApi.summary();
        if (alive) {
          setData(res);
          setError("");
        }
      } catch (err) {
        if (alive) setError(err instanceof Error ? err.message : "加载失败");
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  const filtered = useMemo(() => {
    if (!data) return [];
    const sorted = sortTodos(data.todos);
    if (period === "all") return sorted;
    const days = { today: 0, week: 6, month: 29 }[period];
    return sorted.filter((t) => inRange(t.due_date, days));
  }, [data, period]);

  async function resolveTodo(id: number) {
    setResolving(id);
    setError("");
    try {
      await homeApi.resolveTodo(id);
      setData((prev) =>
        prev
          ? {
              ...prev,
              todos: prev.todos.map((t) => (t.id === id ? { ...t, status: "done" } : t)),
            }
          : prev,
      );
      // 待办完成后刷新 4 数字计数（部分数字来源待办）
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "处理失败");
    } finally {
      setResolving(null);
    }
  }

  async function addTodo() {
    if (!newTitle.trim()) return;
    setAdding(true);
    setError("");
    try {
      await homeApi.createTodo(newTitle.trim(), newDate, newNote);
      setShowAdd(false);
      setNewTitle("");
      setNewDate("");
      setNewNote("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "新增失败");
    } finally {
      setAdding(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Hero：身份 + 周期 + 4 数字，≤160px（桌面） */}
      <Card className="flex flex-col gap-3 p-4 md:h-[160px] md:flex-row md:items-center md:justify-between md:gap-6">
        <div className="flex min-w-0 items-center justify-between gap-3 md:block">
          <div className="min-w-0">
            <p className="truncate text-base font-semibold text-text">
              {greeting()}，{data?.user_info?.email?.split("@")[0] ?? "辅导员"}
            </p>
            <p className="mt-0.5 text-xs text-muted">辅导员个人副驾 · 关键时刻不掉链子</p>
          </div>
          <div className="mt-0 md:mt-3 md:max-w-[180px]">
            <Select
              value={period}
              onChange={(e) => setPeriod(e.target.value as Period)}
              aria-label="周期"
              className="w-auto"
            >
              <option value="all">全部待办</option>
              <option value="today">今天</option>
              <option value="week">本周</option>
              <option value="month">本月</option>
            </Select>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2 md:grid-cols-4 md:gap-3">
          {STATS.map((s) => {
            const value = data?.stats?.[s.key] ?? 0;
            const Icon = s.icon;
            const inner = (
              <>
                <p className="text-xl font-semibold leading-none text-text md:text-2xl">{value}</p>
                <p className="mt-1 text-[11px] text-muted md:text-xs">{s.label}</p>
              </>
            );
            const cls =
              "flex flex-col justify-center rounded-[12px] border border-border bg-[#fafbff] px-3 py-2.5 transition-colors md:min-w-[108px] md:px-4 md:py-3";
            if (s.href) {
              return (
                <Link
                  key={s.key}
                  href={s.query ? `${s.href}?${s.query}` : s.href}
                  className={`${cls} hover:border-primary/40 hover:bg-primary-soft`}
                >
                  <span className="mb-1 flex h-6 w-6 items-center justify-center rounded-[6px] bg-primary-soft text-primary">
                    <Icon size={14} />
                  </span>
                  {inner}
                </Link>
              );
            }
            return (
              <div key={s.key} className={cls} title="该模块 V0.3-B 上线">
                <span className="mb-1 flex h-6 w-6 items-center justify-center rounded-[6px] bg-[#f1f5f9] text-muted">
                  <Icon size={14} />
                </span>
                {inner}
              </div>
            );
          })}
        </div>
      </Card>

      {/* 待办清单 */}
      <Card className="p-4">
        <div className="mb-3 flex items-center justify-between">
          <p className="text-sm font-medium text-text">待办清单</p>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted">{filtered.length} 条</span>
            <Button
              variant="secondary"
              className="px-3 py-1.5 text-xs"
              onClick={() => setShowAdd((v) => !v)}
              icon={<Plus size={14} />}
            >
              新增
            </Button>
          </div>
        </div>

        {showAdd && (
          <div className="mb-3 rounded-[12px] border border-primary/25 bg-primary-soft/40 p-3">
            <div className="grid gap-2 sm:grid-cols-[1fr_150px]">
              <input
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                placeholder="标题，如：今天10:00 美术学2班301室班会"
                className="rounded-[10px] border border-border bg-white px-3 py-2 text-sm text-text outline-none placeholder:text-muted focus:border-primary"
              />
              <input
                type="date"
                value={newDate}
                onChange={(e) => setNewDate(e.target.value)}
                className="rounded-[10px] border border-border bg-white px-3 py-2 text-sm text-text outline-none focus:border-primary"
              />
            </div>
            <input
              value={newNote}
              onChange={(e) => setNewNote(e.target.value)}
              placeholder="备注（可选）"
              className="mt-2 w-full rounded-[10px] border border-border bg-white px-3 py-2 text-sm text-text outline-none placeholder:text-muted focus:border-primary"
            />
            <div className="mt-2 flex justify-end gap-2">
              <Button variant="ghost" className="px-3 py-1.5 text-xs" onClick={() => setShowAdd(false)}>
                取消
              </Button>
              <Button
                loading={adding}
                disabled={!newTitle.trim()}
                onClick={addTodo}
                className="px-3 py-1.5 text-xs"
              >
                保存提醒
              </Button>
            </div>
          </div>
        )}

        {error && (
          <div className="mb-3">
            <Alert message={error} onRetry={load} />
          </div>
        )}

        {loading ? (
          <div className="flex justify-center py-10">
            <Spinner text="加载中…" />
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState icon={<Check size={24} />} title="今日无待办" desc="没有需要你现在处理的事项。" />
        ) : (
          <ul className="flex flex-col gap-2">
            {filtered.map((t) => {
              const overdue = t.due_date && t.due_date < todayStr();
              return (
                <li
                  key={t.id}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-[12px] border border-border bg-[#fafbff] px-3.5 py-3"
                >
                  <div className="flex min-w-0 items-center gap-3">
                    <span
                      className={`h-2 w-2 shrink-0 rounded-full ${
                        overdue ? "bg-danger" : t.due_date === todayStr() ? "bg-[#f59e0b]" : "bg-success"
                      }`}
                    />
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-text">{t.title}</p>
                      <p className="text-xs text-muted">
                        {typeLabel(t)}
                        {t.due_date ? ` · ${overdue ? "已逾期" : "截止"} ${t.due_date}` : ""}
                      </p>
                      {t.target_name && (
                        <p className="truncate text-xs text-muted/80">备注：{t.target_name}</p>
                      )}
                    </div>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    {t.source_type === "talk" && (
                      <Link href="/talks">
                        <Button variant="secondary" className="px-3 py-1.5 text-xs">
                          去跟进
                        </Button>
                      </Link>
                    )}
                    <Button
                      variant="secondary"
                      loading={resolving === t.id}
                      onClick={() => resolveTodo(t.id)}
                      className="px-3 py-1.5 text-xs"
                    >
                      标记完成
                    </Button>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </Card>
    </div>
  );
}
