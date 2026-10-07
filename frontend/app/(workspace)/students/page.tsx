"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Download, MessageSquareHeart, Search, Upload, UserRound, Users, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Alert, Badge, Card, EmptyState, Spinner } from "@/components/ui/feedback";
import { Input, Select } from "@/components/ui/field";
import { ApiError, studentApi } from "@/lib/api";
import type { StudentDetail, StudentListItem } from "@/lib/types";

function riskBadge(score: number) {
  if (score >= 3) return <Badge tone="danger">高风险</Badge>;
  if (score >= 1) return <Badge tone="primary">中风险</Badge>;
  return <Badge>低风险</Badge>;
}

function Progress({ label, value, max, danger }: { label: string; value: number; max: number; danger: boolean }) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-xs">
        <span className="text-muted">{label}</span>
        <span className={danger ? "font-medium text-danger" : "font-medium text-text"}>
          {value}
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-[#f1f5f9]">
        <div
          className={`h-full rounded-full ${danger ? "bg-danger" : "bg-[linear-gradient(135deg,#2563eb_0%,#0ea5a4_100%)]"}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export default function StudentsPage() {
  const [students, setStudents] = useState<StudentListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [grade, setGrade] = useState("");
  const [className, setClassName] = useState("");
  const [riskLevel, setRiskLevel] = useState("");
  const [grades, setGrades] = useState<string[]>([]);
  const [classes, setClasses] = useState<string[]>([]);

  const [detail, setDetail] = useState<StudentDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [seeding, setSeeding] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const res = await studentApi.list({
        page: 1,
        size: 200,
        search: search || undefined,
        grade: grade || undefined,
        class_name: className || undefined,
        risk_level: riskLevel || undefined,
      });
      setStudents(res.students);
      setTotal(res.total);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "学生列表加载失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const res = await studentApi.list({ page: 1, size: 200 });
        if (alive) {
          setStudents(res.students);
          setTotal(res.total);
          setError("");
        }
      } catch (err) {
        if (alive) setError(err instanceof Error ? err.message : "学生列表加载失败");
      } finally {
        if (alive) setLoading(false);
      }
    })();
    studentApi
      .filters()
      .then((r) => {
        setGrades(r.grades);
        setClasses(r.classes);
      })
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, []);

  function openDetail(id: number) {
    setDetailLoading(true);
    setDetail(null);
    studentApi
      .detail(id)
      .then(setDetail)
      .catch((err) => setError(err instanceof Error ? err.message : "详情加载失败"))
      .finally(() => setDetailLoading(false));
  }

  async function handleImport(files: File[]) {
    if (!files.length) return;
    setImporting(true);
    setError("");
    try {
      const res = await studentApi.import(files[0]);
      setError(`导入完成：成功 ${res.imported} 条，跳过 ${res.skipped} 条`);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "导入失败");
    } finally {
      setImporting(false);
    }
  }

  async function seedDemo() {
    setSeeding(true);
    setError("");
    try {
      const res = await studentApi.seedDemo();
      setError(res.message);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "生成失败");
    } finally {
      setSeeding(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-text">一人一页</h2>
          <p className="mt-1 text-xs text-muted">
            打开就能回答「这孩子啥情况」——基本信息、学业考勤、叙事时间轴、交接包。
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" loading={seeding} onClick={seedDemo}>
            <Users size={15} />
            生成演示数据
          </Button>
          <label className="inline-flex shrink-0 cursor-pointer items-center gap-2 rounded-[10px] border border-border bg-white px-4 py-2 text-sm font-medium text-text transition-colors hover:bg-[#f1f5f9]">
            <Upload size={15} className="text-muted" />
            {importing ? "导入中…" : "导入 Excel"}
            <input
              type="file"
              accept=".xlsx,.xls"
              className="hidden"
              disabled={importing}
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) handleImport([f]);
                e.target.value = "";
              }}
            />
          </label>
        </div>
      </div>

      <Card className="p-4">
        <div className="mb-3 flex flex-wrap gap-2">
          <div className="relative min-w-[200px] flex-1">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
            <Input
              className="pl-9"
              placeholder="搜索姓名 / 学号"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && load()}
            />
          </div>
          <Select className="w-auto" value={grade} onChange={(e) => { setGrade(e.target.value); }}>
            <option value="">全部年级</option>
            {grades.map((g) => (
              <option key={g} value={g}>{g}</option>
            ))}
          </Select>
          <Select className="w-auto" value={className} onChange={(e) => setClassName(e.target.value)}>
            <option value="">全部班级</option>
            {classes.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </Select>
          <Select className="w-auto" value={riskLevel} onChange={(e) => setRiskLevel(e.target.value)}>
            <option value="">全部风险</option>
            <option value="high">高风险</option>
            <option value="medium">中风险</option>
            <option value="none">低风险</option>
          </Select>
          <Button variant="secondary" onClick={load}>筛选</Button>
        </div>

        {error && <Alert message={error} onRetry={load} />}

        {loading ? (
          <div className="flex justify-center py-10">
            <Spinner text="加载中…" />
          </div>
        ) : students.length === 0 ? (
          <EmptyState
            icon={<UserRound size={24} />}
            title="暂无学生"
            desc="点右上角「生成演示数据」或导入学生 Excel 后开始。"
          />
        ) : (
          <>
            <p className="mb-2 text-xs text-muted">共 {total} 人</p>
            <ul className="flex flex-col gap-2">
              {students.map((s) => (
                <li key={s.id}>
                  <button
                    onClick={() => openDetail(s.id)}
                    className="flex w-full flex-wrap items-center justify-between gap-3 rounded-[12px] border border-border bg-[#fafbff] px-3.5 py-3 text-left transition-colors hover:border-primary/40 hover:bg-primary-soft/50"
                  >
                    <div className="flex min-w-0 items-center gap-3">
                      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary-soft text-primary">
                        <UserRound size={17} />
                      </div>
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium text-text">
                          {s.name}
                          <span className="ml-2 font-normal text-muted">{s.student_id}</span>
                        </p>
                        <p className="text-xs text-muted">{s.class_name} · {s.grade}</p>
                      </div>
                    </div>
                    <div className="flex shrink-0 items-center gap-3">
                      <span className="hidden text-xs text-muted sm:inline">
                        GPA {s.gpa.toFixed(1)} · 出勤 {s.attendance.toFixed(0)}%
                      </span>
                      {riskBadge(s.risk_score)}
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          </>
        )}
      </Card>

      {/* 详情抽屉 */}
      {detail && (
        <div className="fixed inset-0 z-30 flex justify-end">
          <div className="absolute inset-0 bg-black/20" onClick={() => setDetail(null)} />
          <div className="thin-scroll relative flex h-full w-full max-w-[460px] flex-col gap-4 overflow-y-auto bg-bg p-4 shadow-2xl">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-base font-semibold text-text">{detail.name}</h3>
                <p className="text-xs text-muted">{detail.student_id} · {detail.class_name} · {detail.grade}</p>
              </div>
              <button onClick={() => setDetail(null)} className="rounded-[8px] p-1.5 text-muted hover:bg-[#f1f5f9]">
                <X size={18} />
              </button>
            </div>

            {detailLoading ? (
              <Spinner text="加载中…" />
            ) : (
              <>
                <Card className="p-4">
                  <p className="mb-3 text-sm font-medium text-text">学业与考勤</p>
                  <div className="flex flex-col gap-3">
                    <Progress label="GPA" value={detail.gpa} max={4} danger={detail.gpa > 0 && detail.gpa < 2} />
                    <Progress label="出勤率" value={detail.attendance} max={100} danger={detail.attendance < 90} />
                  </div>
                  {detail.tags.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {detail.tags.map((t) => (
                        <Badge key={t}>{t}</Badge>
                      ))}
                    </div>
                  )}
                </Card>

                <Card className="p-4">
                  <div className="mb-2 flex items-center justify-between">
                    <p className="text-sm font-medium text-text">叙事时间轴</p>
                    <Button
                      variant="secondary"
                      className="px-3 py-1.5 text-xs"
                      onClick={() => studentApi.handover(detail.id).catch((err) => setError(err instanceof Error ? err.message : "导出失败"))}
                      icon={<Download size={14} />}
                    >
                      导出交接包
                    </Button>
                  </div>
                  {detail.talk_records.length === 0 ? (
                    <p className="py-4 text-center text-xs text-muted">暂无谈话记录</p>
                  ) : (
                    <div className="flex flex-col gap-2 border-l border-border pl-3">
                      {detail.talk_records.map((t) => (
                        <div key={t.id} className="rounded-[10px] border border-border bg-[#fafbff] px-3 py-2">
                          <p className="text-xs text-muted">
                            {t.created_at.slice(0, 10)} · {t.method}
                            {t.topic ? ` · ${t.topic}` : ""}
                          </p>
                          {t.conclusion && <p className="mt-1 text-xs leading-relaxed text-text">{t.conclusion}</p>}
                        </div>
                      ))}
                    </div>
                  )}
                </Card>

                <Link href="/talks">
                  <Button className="w-full" icon={<MessageSquareHeart size={15} />}>
                    发起一次谈话
                  </Button>
                </Link>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
