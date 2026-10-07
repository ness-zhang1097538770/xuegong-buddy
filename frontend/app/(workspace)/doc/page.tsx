"use client";

import { useEffect, useMemo, useState } from "react";
import { Download, FileText, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Alert, Badge, Card, EmptyState, Spinner } from "@/components/ui/feedback";
import { Input, Label, Select, Textarea } from "@/components/ui/field";
import { FileDrop } from "@/components/ui/file-drop";
import { ApiError, docApi, downloadFile } from "@/lib/api";
import type { DocGenerateResult, DocTaskItem, TemplateItem } from "@/lib/types";

const STYLES = [
  { value: "formal", label: "正式上报" },
  { value: "soft", label: "谈心柔和" },
  { value: "brief", label: "简洁简报" },
];

/** 常见变量名的中文标签，找不到就用原始 key，避免凭空猜测语义。 */
const VAR_LABELS: Record<string, string> = {
  student_name: "学生姓名",
  class_name: "班级",
  academic_year: "学年",
  academic_performance: "学业表现",
  activities: "活动参与",
  strengths: "优点",
  areas_to_improve: "待改进",
  date: "日期",
  teacher_name: "辅导员姓名",
  position: "职务",
  theme: "主题",
  topic: "议题",
  content: "内容",
  reason: "事由",
  summary: "总结",
};

function varLabel(key: string): string {
  return VAR_LABELS[key] ?? key;
}

function parseVariables(raw: string): string[] {
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.map(String) : [];
  } catch {
    return [];
  }
}

export default function DocPage() {
  const [templates, setTemplates] = useState<TemplateItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [templateId, setTemplateId] = useState<number | null>(null);
  const [style, setStyle] = useState("formal");
  const [variables, setVariables] = useState<Record<string, string>>({});
  const [refIds, setRefIds] = useState<string[]>([]);
  const [refNames, setRefNames] = useState<string[]>([]);
  const [uploadingRef, setUploadingRef] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState<DocGenerateResult | null>(null);
  const [error, setError] = useState("");
  const [tasks, setTasks] = useState<DocTaskItem[]>([]);

  const current = useMemo(
    () => templates.find((t) => t.id === templateId) ?? null,
    [templates, templateId],
  );
  const varNames = useMemo(
    () => (current ? parseVariables(current.variables) : []),
    [current],
  );

  useEffect(() => {
    (async () => {
      try {
        const res = await docApi.templates();
        setTemplates(res.templates);
        if (res.templates.length) {
          setTemplateId(res.templates[0].id);
          setStyle(res.templates[0].style || "formal");
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "模板加载失败");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  async function loadTasks() {
    try {
      setTasks(await docApi.tasks());
    } catch {
      // 历史任务加载失败不影响主流程
    }
  }

  // 首屏异步拉取历史任务
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const list = await docApi.tasks();
        if (alive) setTasks(list);
      } catch {
        // 历史任务加载失败不影响主流程
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  function switchTemplate(id: number) {
    setTemplateId(id);
    setVariables({});
    setResult(null);
    setError("");
    const t = templates.find((x) => x.id === id);
    if (t) setStyle(t.style || "formal");
  }

  async function handleRefUpload(files: File[]) {
    setUploadingRef(true);
    setError("");
    try {
      const res = await docApi.uploadReference(files);
      setRefIds((prev) => [...prev, ...res.ref_ids]);
      setRefNames((prev) => [...prev, ...res.filenames]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "参考文件上传失败");
    } finally {
      setUploadingRef(false);
    }
  }

  async function generate() {
    if (!templateId) return;
    setGenerating(true);
    setError("");
    setResult(null);
    try {
      const res = await docApi.generate({
        template_id: templateId,
        variables,
        style,
        reference_ids: refIds,
      });
      setResult(res);
      loadTasks();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "生成失败");
    } finally {
      setGenerating(false);
    }
  }

  const missingVars = varNames.filter((v) => !variables[v]?.trim());

  return (
    <div className="grid gap-4 lg:grid-cols-[380px_1fr]">
      <div className="lg:col-span-2">
        <h2 className="text-base font-semibold text-text">文稿生成</h2>
        <p className="mt-1 text-xs text-muted">
          选择模板、填写变量，生成可一键导出 Word 的公文草稿。
        </p>
      </div>
      <Card className="h-fit p-4">
        {loading ? (
          <Spinner text="模板加载中…" />
        ) : templates.length === 0 ? (
          <EmptyState icon={<FileText size={24} />} title="无可用模板" />
        ) : (
          <div className="flex flex-col gap-4">
            <div>
              <Label>选择模板</Label>
              <Select value={templateId ?? ""} onChange={(e) => switchTemplate(Number(e.target.value))}>
                {templates.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}（{t.category}）
                  </option>
                ))}
              </Select>
              {current?.description && (
                <p className="mt-1.5 text-xs text-muted">{current.description}</p>
              )}
            </div>

            <div>
              <Label>文风</Label>
              <Select value={style} onChange={(e) => setStyle(e.target.value)}>
                {STYLES.map((s) => (
                  <option key={s.value} value={s.value}>
                    {s.label}
                  </option>
                ))}
              </Select>
            </div>

            {varNames.length > 0 && (
              <div className="flex flex-col gap-3">
                <Label hint="未填将留占位">填写信息</Label>
                {varNames.map((v) => (
                  <div key={v}>
                    <p className="mb-1 text-xs text-muted">
                      {varLabel(v)}
                      {varLabel(v) !== v && <span className="ml-1 text-[#94a3b8]">{v}</span>}
                    </p>
                    <Input
                      value={variables[v] ?? ""}
                      placeholder={`请输入${varLabel(v)}`}
                      onChange={(e) =>
                        setVariables((prev) => ({ ...prev, [v]: e.target.value }))
                      }
                    />
                  </div>
                ))}
              </div>
            )}

            <div>
              <Label hint="可选 · 最多 5 个">参考文件</Label>
              <FileDrop
                accept=".pdf,.txt,.docx"
                multiple
                hint="PDF / Word / TXT，作为生成依据"
                disabled={uploadingRef}
                onFiles={handleRefUpload}
              />
              {refNames.length > 0 && (
                <ul className="mt-2 flex flex-wrap gap-1.5">
                  {refNames.map((n, i) => (
                    <li key={i}>
                      <Badge tone="primary">{n}</Badge>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {error && <Alert message={error} />}

            <Button
              onClick={generate}
              loading={generating}
              disabled={!templateId}
              icon={<Sparkles size={15} />}
              className="w-full"
            >
              {generating ? "AI 生成中…" : "生成文稿"}
            </Button>
            {missingVars.length > 0 && (
              <p className="text-xs text-muted">
                未填写：{missingVars.join("、")}（将留占位符）
              </p>
            )}
          </div>
        )}
      </Card>

      <div className="flex flex-col gap-4">
        <Card className="flex min-h-[420px] flex-col p-4">
          <div className="mb-3 flex items-center justify-between">
            <p className="text-sm font-medium text-text">生成结果</p>
            {result && (
              <Button
                variant="secondary"
                onClick={() =>
                  downloadFile(
                    `/doc/download/${result.task_id}`,
                    `${result.template_name}.docx`,
                  ).catch((err) =>
                    setError(err instanceof Error ? err.message : "下载失败"),
                  )
                }
                icon={<Download size={15} />}
              >
                下载 Word
              </Button>
            )}
          </div>

          {generating ? (
            <div className="flex flex-1 items-center justify-center">
              <Spinner text="正在生成，请稍候…" />
            </div>
          ) : result ? (
            <Textarea
              readOnly
              value={result.content}
              className="thin-scroll flex-1 resize-none font-mono text-[13px]"
            />
          ) : (
            <EmptyState
              icon={<FileText size={24} />}
              title="尚未生成"
              desc="左侧选模板、填信息后点击「生成文稿」"
            />
          )}
        </Card>

        {tasks.length > 0 && (
          <Card className="p-4">
            <p className="mb-3 text-sm font-medium text-text">最近生成</p>
            <ul className="flex flex-col gap-2">
              {tasks.slice(0, 8).map((t) => (
                <li
                  key={t.id}
                  className="flex items-center justify-between rounded-[8px] border border-border bg-[#f8fafc] px-3 py-2"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm text-text">{t.template_name}</p>
                    <p className="text-xs text-muted">
                      {new Date(t.created_at).toLocaleString("zh-CN")} · {t.style}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge tone={t.status === "done" ? "success" : "danger"}>{t.status}</Badge>
                    {t.status === "done" && (
                      <button
                        onClick={() =>
                          downloadFile(`/doc/download/${t.id}`, `${t.template_name}.docx`).catch(
                            (err) => setError(err instanceof Error ? err.message : "下载失败"),
                          )
                        }
                        className="rounded-[6px] p-1 text-muted hover:bg-[#f1f5f9] hover:text-primary"
                        title="下载"
                      >
                        <Download size={15} />
                      </button>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          </Card>
        )}
      </div>
    </div>
  );
}
