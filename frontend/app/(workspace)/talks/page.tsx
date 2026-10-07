"use client";

import { useEffect, useMemo, useState } from "react";
import { CheckCircle2, FileText, History, Sparkles, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Alert, Badge, Card, EmptyState, Spinner } from "@/components/ui/feedback";
import { Input, Label, Select, Textarea } from "@/components/ui/field";
import { ApiError, studentApi, talkApi } from "@/lib/api";
import type { StudentListItem, TalkRecordItem } from "@/lib/types";

const METHODS = ["面谈", "电话", "线上", "家访"];
const MOODS = ["平稳", "低落", "焦虑", "激动", "其他"];
const TOPICS = ["学业", "心理", "家庭", "违纪", "资助", "就业", "其他"];

function parseDraftSections(draft: string): Record<string, string> {
  const out: Record<string, string> = {};
  const re = /【([^】]+)】/g;
  const segs: { key: string; labelEnd: number }[] = [];
  let m: RegExpExecArray | null;
  while ((m = re.exec(draft))) {
    segs.push({ key: m[1], labelEnd: m.index + m[0].length });
  }
  for (let i = 0; i < segs.length; i++) {
    const start = segs[i].labelEnd;
    const end =
      i + 1 < segs.length
        ? segs[i + 1].labelEnd - (segs[i + 1].key.length + 2)
        : draft.length;
    out[segs[i].key] = draft.slice(start, end).trim();
  }
  return out;
}

function addDays(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

export default function TalksPage() {
  const [talks, setTalks] = useState<TalkRecordItem[]>([]);
  const [students, setStudents] = useState<StudentListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [onlyFollow, setOnlyFollow] = useState(false);
  const [error, setError] = useState("");

  // 表单
  const [studentId, setStudentId] = useState("");
  const [studentName, setStudentName] = useState("");
  const [method, setMethod] = useState("面谈");
  const [topic, setTopic] = useState("");
  const [keyPoints, setKeyPoints] = useState("");
  const [content, setContent] = useState("");
  const [conclusion, setConclusion] = useState("");
  const [mood, setMood] = useState("平稳");
  const [needFollow, setNeedFollow] = useState(false);
  const [followDate, setFollowDate] = useState(addDays(7));
  const [isSensitive, setIsSensitive] = useState(false);

  const [drafting, setDrafting] = useState(false);
  const [draftPreview, setDraftPreview] = useState("");
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState("");
  const [transcribing, setTranscribing] = useState(false);

  async function loadTalks(needFollow?: number) {
    try {
      const res = await talkApi.list({ page: 1, size: 50, need_follow: needFollow });
      setTalks(res.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "历史加载失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const res = await talkApi.list({ page: 1, size: 50 });
        if (alive) setTalks(res.items);
      } catch (err) {
        if (alive) setError(err instanceof Error ? err.message : "历史加载失败");
      } finally {
        if (alive) setLoading(false);
      }
    })();
    studentApi
      .list({ page: 1, size: 200 })
      .then((r) => setStudents(r.students))
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, []);

  const grouped = useMemo(() => {
    const map = new Map<string, TalkRecordItem[]>();
    for (const t of talks) {
      const key = t.student_name || "未命名";
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(t);
    }
    return Array.from(map.entries());
  }, [talks]);

  function switchOnlyFollow(v: boolean) {
    setOnlyFollow(v);
    setLoading(true);
    loadTalks(v ? 1 : undefined);
  }

  function pickStudent(id: string) {
    setStudentId(id);
    const s = students.find((x) => String(x.id) === id);
    if (s) {
      setStudentName(s.name);
      // 关键：student_id_ref 用学号，保证归档进一人一页
    }
  }

  async function generateDraft(kp?: string) {
    const points = (kp ?? keyPoints).trim();
    if (!studentName.trim() || !points) {
      setError("请先填写学生姓名和本次要点");
      return;
    }
    setDrafting(true);
    setError("");
    setDraftPreview("");
    try {
      const selected = students.find((x) => String(x.id) === studentId);
      const res = await talkApi.draft({
        student_name: studentName.trim(),
        method,
        topic,
        key_points: points,
        student_id_ref: selected?.student_id ?? "",
      });
      setDraftPreview(res.draft);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "AI 初稿生成失败");
    } finally {
      setDrafting(false);
    }
  }

  async function handleTranscribe(file: File) {
    setTranscribing(true);
    setError("");
    setNotice("");
    try {
      const res = await talkApi.transcribe(file);
      setKeyPoints(res.transcript);
      if (studentName.trim()) {
        await generateDraft(res.transcript);
      } else {
        setNotice("录音已转文字，请填学生姓名后点「生成 AI 初稿」");
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "录音转写失败");
    } finally {
      setTranscribing(false);
    }
  }

  function applyDraft() {
    if (!draftPreview) return;
    const sec = parseDraftSections(draftPreview);
    setContent(sec["谈话内容"] ?? draftPreview);
    if (sec["处置建议"]) setConclusion(sec["处置建议"]);
    if (sec["问题归类"] && !topic) setTopic(sec["问题归类"]);
    setNotice("已采纳 AI 草稿，请人工核对后再保存。");
  }

  async function save() {
    if (!studentName.trim() || !content.trim()) {
      setError("学生姓名和谈话内容不能为空");
      return;
    }
    setSaving(true);
    setError("");
    setNotice("");
    try {
      const selected = students.find((x) => String(x.id) === studentId);
      await talkApi.create({
        student_name: studentName.trim(),
        student_id_ref: selected?.student_id ?? "",
        method,
        topic,
        content: content.trim(),
        conclusion: conclusion.trim(),
        mood,
        need_follow: needFollow,
        follow_date: needFollow ? followDate : "",
        is_sensitive: isSensitive,
      });
      setNotice("已保存并归档至该生一人一页。");
      // 重置表单
      setKeyPoints("");
      setContent("");
      setConclusion("");
      setDraftPreview("");
      setTopic("");
      setNeedFollow(false);
      setStudentId("");
      setStudentName("");
      loadTalks(onlyFollow ? 1 : undefined);
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存失败");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className="text-base font-semibold text-text">谈话记录仪</h2>
        <p className="mt-1 text-xs text-muted">
          录入即归档、归档即进档案，需要跟进自动回到待办。AI 只拟草稿，保存前请人工复核。
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-[2fr_3fr]">
        {/* 左侧历史时间轴 */}
        <Card className="flex max-h-[calc(100vh-14rem)] flex-col p-4">
          <div className="mb-3 flex items-center justify-between">
            <p className="flex items-center gap-1.5 text-sm font-medium text-text">
              <History size={16} className="text-muted" />
              历史记录
            </p>
            <label className="flex cursor-pointer items-center gap-1.5 text-xs text-muted">
              <input
                type="checkbox"
                checked={onlyFollow}
                onChange={(e) => switchOnlyFollow(e.target.checked)}
              />
              仅看待跟进
            </label>
          </div>

          <div className="thin-scroll flex-1 overflow-y-auto pr-1">
            {loading ? (
              <div className="flex justify-center py-8">
                <Spinner text="加载中…" />
              </div>
            ) : grouped.length === 0 ? (
              <EmptyState icon={<FileText size={24} />} title="暂无谈话记录" desc="右侧录入第一条谈话记录。" />
            ) : (
              <div className="flex flex-col gap-4">
                {grouped.map(([name, items]) => (
                  <div key={name}>
                    <p className="mb-1.5 text-xs font-semibold text-text">{name}</p>
                    <div className="relative flex flex-col gap-2 border-l border-border pl-4">
                      {items.map((t) => (
                        <div key={t.id} className="relative">
                          <span className="absolute -left-[21px] top-1.5 h-2 w-2 rounded-full bg-primary" />
                          <div className="rounded-[10px] border border-border bg-[#fafbff] px-3 py-2">
                            <div className="flex items-center justify-between gap-2">
                              <p className="text-xs text-muted">
                                {t.created_at.slice(0, 10)} · {t.method}
                                {t.topic ? ` · ${t.topic}` : ""}
                              </p>
                              {t.need_follow && (
                                <Badge tone={t.follow_closed ? "success" : "danger"}>
                                  {t.follow_closed ? "已闭环" : "待跟进"}
                                </Badge>
                              )}
                            </div>
                            {t.conclusion && (
                              <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-text">
                                {t.conclusion}
                              </p>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </Card>

        {/* 右侧录入区 */}
        <Card className="p-4">
          <div className="flex flex-col gap-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <Label hint="从一人一页选择，自动归档">学生</Label>
                <Select
                  value={studentId}
                  onChange={(e) => pickStudent(e.target.value)}
                >
                  <option value="">选择学生（或下方手填姓名）</option>
                  {students.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}（{s.student_id}）
                    </option>
                  ))}
                </Select>
              </div>
              <div>
                <Label>学生姓名</Label>
                <Input
                  value={studentName}
                  placeholder="必填"
                  onChange={(e) => setStudentName(e.target.value)}
                />
              </div>
              <div>
                <Label>谈话方式</Label>
                <Select value={method} onChange={(e) => setMethod(e.target.value)}>
                  {METHODS.map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </Select>
              </div>
              <div>
                <Label>主题标签</Label>
                <Select value={topic} onChange={(e) => setTopic(e.target.value)}>
                  <option value="">未归类</option>
                  {TOPICS.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </Select>
              </div>
            </div>

            <div>
              <Label hint="AI 初稿基于本次要点 + 该生历史生成">本次要点</Label>
              <Textarea
                rows={2}
                value={keyPoints}
                placeholder="例：连续两周旷课、三门挂科、宿舍打游戏、家长反映不接电话"
                onChange={(e) => setKeyPoints(e.target.value)}
              />
            </div>

            <Button
              variant="secondary"
              loading={drafting}
              disabled={!keyPoints.trim()}
              onClick={() => generateDraft()}
              icon={<Sparkles size={15} />}
            >
              {drafting ? "AI 拟稿中…" : "生成 AI 初稿"}
            </Button>

            <label className="inline-flex w-full cursor-pointer items-center justify-center gap-2 rounded-[10px] border border-border bg-white px-4 py-2 text-sm font-medium text-text transition-colors hover:bg-[#f1f5f9]">
              <Upload size={15} className="text-muted" />
              {transcribing ? "转写中…" : "导入录音（转文字）"}
              <input
                type="file"
                accept=".wav,.mp3,.m4a,.aac,.ogg,.flac,.webm,.amr"
                className="hidden"
                disabled={transcribing}
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) handleTranscribe(f);
                  e.target.value = "";
                }}
              />
            </label>

            {draftPreview && (
              <div className="relative rounded-[12px] border border-primary/25 bg-[#eff4ff] p-3">
                <span className="pointer-events-none absolute right-3 top-3 rotate-[-8deg] rounded border border-primary/40 px-2 py-0.5 text-xs font-semibold text-primary/70">
                  草稿
                </span>
                <pre className="thin-scroll max-h-48 overflow-y-auto whitespace-pre-wrap pr-14 text-xs leading-relaxed text-text">
                  {draftPreview}
                </pre>
                <div className="mt-2 flex items-center justify-between gap-2">
                  <p className="text-xs text-muted">AI 初稿仅作参考，须人工核对修改后再保存。</p>
                  <Button variant="secondary" className="px-3 py-1.5 text-xs" onClick={applyDraft}>
                    采纳到表单
                  </Button>
                </div>
              </div>
            )}

            <div>
              <Label>谈话内容</Label>
              <Textarea
                rows={5}
                value={content}
                placeholder="客观陈述事实，不做诊断、不下结论"
                onChange={(e) => setContent(e.target.value)}
              />
            </div>
            <div>
              <Label hint="结论与处置建议">结论</Label>
              <Textarea
                rows={3}
                value={conclusion}
                placeholder="例：协助梳理补考安排，两周后复盘"
                onChange={(e) => setConclusion(e.target.value)}
              />
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              <div>
                <Label>情绪状态</Label>
                <Select value={mood} onChange={(e) => setMood(e.target.value)}>
                  {MOODS.map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </Select>
              </div>
              <div>
                <Label>需要跟进</Label>
                <label className="flex h-[42px] cursor-pointer items-center gap-2 rounded-[10px] border border-border bg-white px-3.5 text-sm text-text">
                  <input
                    type="checkbox"
                    checked={needFollow}
                    onChange={(e) => setNeedFollow(e.target.checked)}
                  />
                  {needFollow ? "是" : "否"}
                </label>
              </div>
              {needFollow && (
                <div>
                  <Label>跟进日期</Label>
                  <Input
                    type="date"
                    value={followDate}
                    onChange={(e) => setFollowDate(e.target.value)}
                  />
                </div>
              )}
            </div>

            <label className="flex cursor-pointer items-center gap-2 text-xs text-muted">
              <input
                type="checkbox"
                checked={isSensitive}
                onChange={(e) => setIsSensitive(e.target.checked)}
              />
              敏感记录（心理/危机/家庭变故，仅本人与学院负责人可见）
            </label>

            {error && <Alert message={error} />}
            {notice && <Alert type="success" message={notice} />}

            <Button
              onClick={save}
              loading={saving}
              disabled={!studentName.trim() || !content.trim()}
              icon={<CheckCircle2 size={15} />}
              className="w-full"
            >
              保存并归档
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
}
