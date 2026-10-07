"use client";

import { useEffect, useState } from "react";
import { Download, Megaphone, Sparkles, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Alert, Badge, Card, EmptyState, Spinner } from "@/components/ui/feedback";
import { Input, Label, Textarea } from "@/components/ui/field";
import { ApiError, noticeApi } from "@/lib/api";
import type { NoticeTask } from "@/lib/types";

const TABS: { key: keyof NonNullable<NoticeTask["result"]>; label: string }[] = [
  { key: "notice_formal", label: "通知·正式版" },
  { key: "notice_group", label: "通知·群发版" },
  { key: "notice_parent", label: "通知·家长版" },
  { key: "meeting_plan", label: "班会方案" },
  { key: "signin_sheet", label: "签到表" },
  { key: "minutes_template", label: "纪要模板" },
];

export default function NoticePage() {
  const [theme, setTheme] = useState("");
  const [eventTime, setEventTime] = useState("");
  const [place, setPlace] = useState("");
  const [audience, setAudience] = useState("");
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");
  const [current, setCurrent] = useState<NoticeTask | null>(null);
  const [tab, setTab] = useState(0);
  const [tasks, setTasks] = useState<NoticeTask[]>([]);
  const [signinSheet, setSigninSheet] = useState("");
  const [signinStudents, setSigninStudents] = useState<
    { name: string; student_id: string; class_name: string }[]
  >([]);
  const [importing, setImporting] = useState(false);

  useEffect(() => {
    let alive = true;
    noticeApi
      .tasks()
      .then((r) => alive && setTasks(r))
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, []);

  async function generate() {
    if (!theme.trim()) return;
    setGenerating(true);
    setError("");
    setCurrent(null);
    try {
      const res = await noticeApi.generate({
        theme: theme.trim(),
        event_time: eventTime.trim(),
        place: place.trim(),
        audience: audience.trim(),
      });
      setCurrent(res);
      setTab(0);
      setTasks((prev) => [res, ...prev.filter((t) => t.id !== res.id)]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "生成失败");
    } finally {
      setGenerating(false);
    }
  }

  async function openTask(id: number) {
    setError("");
    try {
      const res = await noticeApi.task(id);
      setCurrent(res);
      setTab(0);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载失败");
    }
  }

  async function handleSigninImport(file: File) {
    setImporting(true);
    setError("");
    try {
      const res = await noticeApi.signinImport(file, {
        theme,
        event_time: eventTime,
        place,
      });
      setSigninSheet(res.signin_sheet);
      setSigninStudents(res.students);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "导入失败");
    } finally {
      setImporting(false);
    }
  }

  async function exportSignin() {
    setError("");
    try {
      await noticeApi.signinExport({
        theme,
        event_time: eventTime,
        place,
        students: signinStudents,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "导出失败");
    }
  }

  const result = current?.result && Object.keys(current.result).length > 0 ? current.result : null;

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className="text-base font-semibold text-text">通知变材料</h2>
        <p className="mt-1 text-xs text-muted">
          一句话主题，一次性产出通知三版 + 班会方案 + 签到表 + 纪要模板。AI 输出为草稿，发送前请人工复核。
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-[360px_1fr]">
        <div className="flex flex-col gap-4">
        <Card className="h-fit p-4">
          <div className="flex flex-col gap-3">
            <div>
              <Label>班会主题 *</Label>
              <Input
                value={theme}
                placeholder="例：防电诈主题班会"
                onChange={(e) => setTheme(e.target.value)}
              />
            </div>
            <div>
              <Label hint="可选">时间</Label>
              <Input
                value={eventTime}
                placeholder="例：本周日晚7点"
                onChange={(e) => setEventTime(e.target.value)}
              />
            </div>
            <div>
              <Label hint="可选">地点</Label>
              <Input
                value={place}
                placeholder="例：教三101教室"
                onChange={(e) => setPlace(e.target.value)}
              />
            </div>
            <div>
              <Label hint="可选">对象</Label>
              <Input
                value={audience}
                placeholder="例：计算机2301班全体学生"
                onChange={(e) => setAudience(e.target.value)}
              />
            </div>

            {error && <Alert message={error} />}

            <Button
              onClick={generate}
              loading={generating}
              disabled={!theme.trim()}
              icon={<Sparkles size={15} />}
              className="w-full"
            >
              {generating ? "AI 生成中（约 20–30 秒）…" : "生成全套材料"}
            </Button>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex flex-col gap-3">
            <div>
              <p className="text-sm font-medium text-text">签到表（导入名单生成）</p>
              <p className="mt-0.5 text-xs text-muted">
                上传班级学生名单 Excel（含「姓名」列），直接生成带真实姓名的签到表。
              </p>
            </div>
            <label className="inline-flex w-full cursor-pointer items-center justify-center gap-2 rounded-[10px] border border-border bg-white px-4 py-2 text-sm font-medium text-text transition-colors hover:bg-[#f1f5f9]">
              <Upload size={15} className="text-muted" />
              {importing ? "导入中…" : "导入学生名单 Excel"}
              <input
                type="file"
                accept=".xlsx,.xls"
                className="hidden"
                disabled={importing}
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) handleSigninImport(f);
                  e.target.value = "";
                }}
              />
            </label>
            {signinSheet && (
              <>
                <p className="text-xs text-muted">已导入 {signinStudents.length} 人</p>
                <Button variant="secondary" onClick={exportSignin} icon={<Download size={15} />}>
                  下载签到表 Word
                </Button>
                <Textarea
                  readOnly
                  value={signinSheet}
                  className="thin-scroll h-36 resize-none font-mono text-xs leading-relaxed"
                />
              </>
            )}
          </div>
        </Card>
        </div>

        <div className="flex flex-col gap-4">
          <Card className="flex min-h-[480px] flex-col p-4">
            {generating ? (
              <div className="flex flex-1 flex-col items-center justify-center gap-3">
                <Spinner text="正在生成六件套材料，请稍候…" />
                <p className="text-xs text-muted">一次生成约 20–30 秒，期间请不要重复点击。</p>
              </div>
            ) : !result ? (
              <EmptyState
                icon={<Megaphone size={24} />}
                title="尚未生成"
                desc="左侧填写主题后点击「生成全套材料」。"
              />
            ) : (
              <>
                <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                  <div className="thin-scroll flex max-w-full gap-1.5 overflow-x-auto">
                    {TABS.map((t, i) => (
                      <button
                        key={t.key}
                        onClick={() => setTab(i)}
                        className={`shrink-0 rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
                          tab === i
                            ? "bg-primary-soft text-primary"
                            : "text-muted hover:bg-[#f1f5f9]"
                        }`}
                      >
                        {t.label}
                      </button>
                    ))}
                  </div>
                  {current && (
                    <Button
                      variant="secondary"
                      className="px-3 py-1.5 text-xs"
                      onClick={() =>
                        noticeApi.download(current.id).catch((err) =>
                          setError(err instanceof Error ? err.message : "下载失败"),
                        )
                      }
                      icon={<Download size={14} />}
                    >
                      下载 Word
                    </Button>
                  )}
                </div>

                <div className="relative flex-1">
                  <span className="pointer-events-none absolute right-0 top-0 z-10 rotate-[-8deg] rounded border border-primary/40 bg-white/80 px-2 py-0.5 text-xs font-semibold text-primary/70">
                    草稿
                  </span>
                  <Textarea
                    readOnly
                    value={result[TABS[tab].key] ?? ""}
                    className="thin-scroll h-[380px] resize-none font-mono text-[13px] leading-relaxed"
                  />
                </div>
                <p className="mt-2 text-xs text-muted">
                  本材料由 AI 生成，仅作草稿；发送或归档前请人工核对事实与措辞。
                </p>
              </>
            )}
          </Card>

          {tasks.length > 0 && (
            <Card className="p-4">
              <p className="mb-3 text-sm font-medium text-text">历史任务</p>
              <ul className="flex flex-col gap-2">
                {tasks.slice(0, 8).map((t) => (
                  <li key={t.id}>
                    <button
                      onClick={() => openTask(t.id)}
                      className="flex w-full items-center justify-between gap-3 rounded-[10px] border border-border bg-[#fafbff] px-3 py-2 text-left hover:border-primary/40"
                    >
                      <div className="min-w-0">
                        <p className="truncate text-sm text-text">{t.theme}</p>
                        <p className="text-xs text-muted">
                          {t.created_at ? new Date(t.created_at).toLocaleString("zh-CN") : ""}
                          {t.audience ? ` · ${t.audience}` : ""}
                        </p>
                      </div>
                      <Badge tone={t.status === "done" ? "success" : "danger"}>{t.status}</Badge>
                    </button>
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
