"use client";

import { useEffect, useState } from "react";
import { Check, ClipboardCheck, RotateCcw, ShieldAlert, Stamp, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Alert, Badge, Card, EmptyState, Spinner } from "@/components/ui/feedback";
import { Select, Textarea } from "@/components/ui/field";
import { approvalApi } from "@/lib/api";
import type { ApprovalDetail, ApprovalItem } from "@/lib/types";

const TYPE_TONES: Record<string, "default" | "primary" | "success" | "danger"> = {
  blue: "primary",
  green: "success",
  red: "danger",
  gray: "default",
};

const STATUS_LABEL: Record<string, string> = {
  pending: "待审批",
  approved: "已通过",
  rejected: "已驳回",
  returned: "已退回",
};

const STATUS_TONES: Record<string, "default" | "primary" | "success" | "danger"> = {
  pending: "primary",
  approved: "success",
  rejected: "danger",
  returned: "default",
};

function typeTone(color: string): "default" | "primary" | "success" | "danger" {
  return TYPE_TONES[color] ?? "default";
}

function statusTone(status: string): "default" | "primary" | "success" | "danger" {
  return STATUS_TONES[status] ?? "default";
}

export default function ApprovalsPage() {
  const [items, setItems] = useState<ApprovalItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [type, setType] = useState("");
  const [status, setStatus] = useState("");
  const [seeding, setSeeding] = useState(false);

  const [detail, setDetail] = useState<ApprovalDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [opinion, setOpinion] = useState("");
  const [acting, setActing] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      const res = await approvalApi.list({
        type: type || undefined,
        status: status || undefined,
        page: 1,
        size: 50,
      });
      setItems(res.items);
      setTotal(res.total);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "审批列表加载失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const res = await approvalApi.list({ page: 1, size: 50 });
        if (alive) {
          setItems(res.items);
          setTotal(res.total);
          setError("");
        }
      } catch (err) {
        if (alive) setError(err instanceof Error ? err.message : "审批列表加载失败");
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  function openDetail(id: number) {
    setDetailLoading(true);
    setDetail(null);
    setOpinion("");
    approvalApi
      .detail(id)
      .then(setDetail)
      .catch((err) => setError(err instanceof Error ? err.message : "详情加载失败"))
      .finally(() => setDetailLoading(false));
  }

  async function seedDemo() {
    setSeeding(true);
    setError("");
    try {
      const res = await approvalApi.seedDemo();
      setError(res.message);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "生成失败");
    } finally {
      setSeeding(false);
    }
  }

  async function resolve(action: "approve" | "reject" | "return") {
    if (!detail) return;
    if (action === "reject" && !opinion.trim()) {
      setError("驳回必须填写理由");
      return;
    }
    setActing(action);
    setError("");
    try {
      await approvalApi.resolve(detail.id, action, opinion.trim() || undefined);
      setDetail(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "处理失败");
    } finally {
      setActing(null);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-text">事务审批</h2>
          <p className="mt-1 text-xs text-muted">
            请假、奖助贷、违纪等审批单集中处理，风险标记先行提示。
          </p>
        </div>
        <Button variant="secondary" loading={seeding} onClick={seedDemo} icon={<Stamp size={15} />}>
          生成演示数据
        </Button>
      </div>

      <Card className="p-4">
        <div className="mb-3 flex flex-wrap gap-2">
          <Select className="w-auto" value={type} onChange={(e) => setType(e.target.value)}>
            <option value="">全部类型</option>
            <option value="leave">请假</option>
            <option value="aid">奖助贷</option>
            <option value="discipline">违纪</option>
            <option value="other">其他</option>
          </Select>
          <Select className="w-auto" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">全部状态</option>
            <option value="pending">待审批</option>
            <option value="approved">已通过</option>
            <option value="rejected">已驳回</option>
            <option value="returned">已退回</option>
          </Select>
          <Button variant="secondary" onClick={load}>
            筛选
          </Button>
        </div>

        {error && <Alert message={error} onRetry={load} />}

        {loading ? (
          <div className="flex justify-center py-10">
            <Spinner text="加载中…" />
          </div>
        ) : items.length === 0 ? (
          <EmptyState
            icon={<ClipboardCheck size={24} />}
            title="暂无审批单"
            desc="点右上角「生成演示数据」后可体验审批处理流程。"
          />
        ) : (
          <>
            <p className="mb-2 text-xs text-muted">共 {total} 条</p>
            <ul className="flex flex-col gap-2">
              {items.map((a) => (
                <li key={a.id}>
                  <button
                    onClick={() => openDetail(a.id)}
                    className="flex w-full flex-wrap items-center justify-between gap-3 rounded-[12px] border border-border bg-[#fafbff] px-3.5 py-3 text-left transition-colors hover:border-primary/40 hover:bg-primary-soft/50"
                  >
                    <div className="flex min-w-0 items-center gap-3">
                      <div className="shrink-0">
                        <Badge tone={typeTone(a.type_color)}>{a.type_label}</Badge>
                      </div>
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium text-text">{a.title}</p>
                        <p className="text-xs text-muted">
                          {a.applicant_name}
                          {a.applicant_student_id ? ` · ${a.applicant_student_id}` : ""} ·{" "}
                          {a.created_at.slice(0, 10)}
                        </p>
                      </div>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      {a.risk_flags.length > 0 && (
                        <span className="hidden items-center gap-1 text-xs text-danger sm:flex">
                          <ShieldAlert size={13} />
                          {a.risk_flags.length} 条风险
                        </span>
                      )}
                      <Badge tone={statusTone(a.status)}>{STATUS_LABEL[a.status] ?? a.status}</Badge>
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
                <h3 className="text-base font-semibold text-text">{detail.title}</h3>
                <p className="mt-1 text-xs text-muted">
                  {detail.applicant_name}
                  {detail.applicant_student_id ? ` · ${detail.applicant_student_id}` : ""}
                </p>
              </div>
              <button
                onClick={() => setDetail(null)}
                className="rounded-[8px] p-1.5 text-muted hover:bg-[#f1f5f9]"
              >
                <X size={18} />
              </button>
            </div>

            {detailLoading ? (
              <Spinner text="加载中…" />
            ) : (
              <>
                <div className="flex items-center gap-2">
                  <Badge tone={typeTone(detail.type_color)}>{detail.type_label}</Badge>
                  <Badge tone={statusTone(detail.status)}>{STATUS_LABEL[detail.status] ?? detail.status}</Badge>
                </div>

                {detail.risk_flags.length > 0 && (
                  <Card className="border-danger/20 bg-[#fef2f2] p-4">
                    <p className="mb-2 flex items-center gap-1.5 text-sm font-medium text-[#b91c1c]">
                      <ShieldAlert size={15} /> 风险标记
                    </p>
                    <ul className="flex flex-col gap-1.5">
                      {detail.risk_flags.map((f, i) => (
                        <li key={i} className="text-xs leading-relaxed text-[#991b1b]">
                          · {f}
                        </li>
                      ))}
                    </ul>
                  </Card>
                )}

                <Card className="p-4">
                  <p className="mb-2 text-sm font-medium text-text">申请内容</p>
                  <p className="whitespace-pre-wrap text-sm leading-relaxed text-text/90">
                    {detail.content || "（无）"}
                  </p>
                </Card>

                {detail.student && (
                  <Card className="p-4">
                    <p className="mb-3 text-sm font-medium text-text">学生画像</p>
                    <div className="flex flex-col gap-2 text-xs">
                      <p className="text-text">
                        {detail.student.name} · {detail.student.class_name}
                      </p>
                      <p className="text-muted">
                        GPA {detail.student.gpa.toFixed(1)} · 出勤 {detail.student.attendance.toFixed(0)}%
                        {detail.student.risk_score > 0 ? " · 风险分 " + detail.student.risk_score : ""}
                      </p>
                      {detail.student.tags.length > 0 && (
                        <div className="flex flex-wrap gap-1.5">
                          {detail.student.tags.map((t) => (
                            <Badge key={t}>{t}</Badge>
                          ))}
                        </div>
                      )}
                    </div>
                  </Card>
                )}

                {detail.status === "pending" ? (
                  <Card className="p-4">
                    <p className="mb-2 text-sm font-medium text-text">审批意见</p>
                    <Textarea
                      value={opinion}
                      onChange={(e) => setOpinion(e.target.value)}
                      placeholder="填写审批意见（驳回时必填）"
                      rows={3}
                    />
                    <div className="mt-3 flex gap-2">
                      <Button
                        className="flex-1"
                        loading={acting === "approve"}
                        onClick={() => resolve("approve")}
                        icon={<Check size={15} />}
                      >
                        通过
                      </Button>
                      <Button
                        variant="secondary"
                        className="flex-1"
                        loading={acting === "return"}
                        onClick={() => resolve("return")}
                        icon={<RotateCcw size={15} />}
                      >
                        退回
                      </Button>
                      <Button
                        variant="danger"
                        className="flex-1"
                        loading={acting === "reject"}
                        onClick={() => resolve("reject")}
                        icon={<X size={15} />}
                      >
                        驳回
                      </Button>
                    </div>
                  </Card>
                ) : (
                  <Card className="p-4">
                    <p className="mb-2 text-sm font-medium text-text">处理结果</p>
                    <p className="text-sm text-text/90">{detail.opinion || "（无意见）"}</p>
                    {detail.resolved_at && (
                      <p className="mt-2 text-xs text-muted">处理时间：{detail.resolved_at.slice(0, 19).replace("T", " ")}</p>
                    )}
                  </Card>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
