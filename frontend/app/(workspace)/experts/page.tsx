"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Bot, Plus, Send, Square, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Alert, Card, Spinner } from "@/components/ui/feedback";
import { Textarea } from "@/components/ui/field";
import { expertApi, streamExpertChat } from "@/lib/api";
import type { ExpertCitation, ExpertItem, ExpertSessionItem } from "@/lib/types";

const ACCENTS: Record<string, string> = {
  teal: "#0ea5a4",
  red: "#ef4444",
  blue: "#2563eb",
  amber: "#f59e0b",
  coral: "#f43f5e",
};

function accentOf(id?: string): string {
  return ACCENTS[id ?? "blue"] ?? "#2563eb";
}

interface Message {
  role: "user" | "assistant";
  content: string;
  streaming?: boolean;
  citations?: ExpertCitation[];
}

export default function ExpertsPage() {
  const [experts, setExperts] = useState<ExpertItem[]>([]);
  const [sessions, setSessions] = useState<ExpertSessionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [expertId, setExpertId] = useState<string>("");
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [deleting, setDeleting] = useState<number | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const currentExpert = useMemo(
    () => experts.find((e) => e.id === expertId) ?? null,
    [experts, expertId],
  );

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const res = await expertApi.list();
        if (!alive) return;
        setExperts(res.experts);
        setSessions(res.sessions);
        if (res.experts.length) setExpertId(res.experts[0].id);
      } catch (err) {
        if (alive) setError(err instanceof Error ? err.message : "专家列表加载失败");
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function selectExpert(id: string) {
    setExpertId(id);
    setSessionId(null);
    setMessages([]);
    setError("");
    setQuestion("");
    abortRef.current?.abort();
  }

  function newSession() {
    abortRef.current?.abort();
    setSessionId(null);
    setMessages([]);
    setQuestion("");
    setError("");
  }

  async function openSession(s: ExpertSessionItem) {
    abortRef.current?.abort();
    setError("");
    try {
      const res = await expertApi.sessions();
      const full = res.sessions.find((x) => x.id === s.id);
      if (full) {
        setExpertId(full.expert_id);
        setSessionId(full.id);
        setMessages((full.messages ?? []).map((m) => ({ role: m.role as "user" | "assistant", content: m.content })));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "会话加载失败");
    }
  }

  async function removeSession(id: number) {
    setDeleting(id);
    setError("");
    try {
      await expertApi.deleteSession(id);
      setSessions((prev) => prev.filter((s) => s.id !== id));
      if (sessionId === id) newSession();
    } catch (err) {
      setError(err instanceof Error ? err.message : "删除失败");
    } finally {
      setDeleting(null);
    }
  }

  async function send(q?: string) {
    const text = (q ?? question).trim();
    if (!text || streaming || !expertId) return;

    setError("");
    setQuestion("");
    setMessages((prev) => [
      ...prev,
      { role: "user", content: text },
      { role: "assistant", content: "", streaming: true },
    ]);
    setStreaming(true);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      await streamExpertChat(
        { expert_id: expertId, session_id: sessionId, messages: [{ role: "user", content: text }] },
        {
          onChunk: (t) =>
            setMessages((prev) => {
              const next = [...prev];
              const last = next[next.length - 1];
              next[next.length - 1] = { ...last, content: last.content + t };
              return next;
            }),
          onDone: (data) => {
            setSessionId(data.session_id);
            setMessages((prev) => {
              const next = [...prev];
              next[next.length - 1] = {
                role: "assistant",
                content: data.content,
                citations: data.citations,
              };
              return next;
            });
            // 刷新会话列表
            expertApi.list().then((r) => setSessions(r.sessions)).catch(() => {});
          },
          onError: (msg) => {
            setError(msg);
            setMessages((prev) => prev.slice(0, -1));
          },
        },
        controller.signal,
      );
    } catch {
      // 用户主动中断
    } finally {
      setMessages((prev) => {
        const next = [...prev];
        if (next[next.length - 1]?.streaming) {
          next[next.length - 1] = { ...next[next.length - 1], streaming: false };
        }
        return next;
      });
      setStreaming(false);
      abortRef.current = null;
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className="text-base font-semibold text-text">专家智能体</h2>
        <p className="mt-1 text-xs text-muted">
          5 位辅导员专家，按场景直接对话。AI 输出为草稿，涉及学生与危机内容须人工复核。
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-[320px_1fr]">
        {/* 左侧：专家列表 + 最近会话 */}
        <Card className="flex max-h-[calc(100vh-12rem)] flex-col p-4">
          {loading ? (
            <Spinner text="加载中…" />
          ) : (
            <div className="thin-scroll flex-1 overflow-y-auto pr-1">
              <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted/70">专家</p>
              <div className="flex flex-col gap-2">
                {experts.map((e) => {
                  const active = e.id === expertId;
                  const color = accentOf(e.accent);
                  return (
                    <button
                      key={e.id}
                      onClick={() => selectExpert(e.id)}
                      className={`flex items-start gap-3 rounded-[12px] border px-3 py-2.5 text-left transition-all ${
                        active
                          ? "bg-primary-soft shadow-[inset_0_0_0_1px_rgba(37,99,235,0.15)]"
                          : "border-border bg-[#fafbff] hover:border-primary/40"
                      }`}
                    >
                      <span
                        className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-[10px] text-white"
                        style={{ background: color }}
                      >
                        <Bot size={16} />
                      </span>
                      <span className="min-w-0">
                        <span className="block text-sm font-medium text-text">{e.name}</span>
                        <span className="mt-0.5 line-clamp-2 block text-xs text-muted">{e.desc}</span>
                      </span>
                    </button>
                  );
                })}
              </div>

              {sessions.length > 0 && (
                <>
                  <p className="mb-2 mt-5 text-xs font-medium uppercase tracking-wide text-muted/70">
                    最近会话
                  </p>
                  <div className="flex flex-col gap-1.5">
                    {sessions.map((s) => (
                      <div
                        key={s.id}
                        className="group flex items-center justify-between gap-2 rounded-[8px] px-2 py-1.5 hover:bg-[#f8fafc]"
                      >
                        <button
                          onClick={() => openSession(s)}
                          className="min-w-0 flex-1 truncate text-left text-xs text-text"
                        >
                          {s.title}
                        </button>
                        <button
                          onClick={() => removeSession(s.id)}
                          disabled={deleting === s.id}
                          className="shrink-0 rounded-[6px] p-1 text-muted opacity-0 transition-opacity hover:bg-[#f1f5f9] hover:text-danger group-hover:opacity-100"
                          title="删除会话"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}
        </Card>

        {/* 右侧：对话 */}
        <Card className="flex h-[calc(100dvh-14rem)] flex-col md:h-[calc(100vh-9rem)]">
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <div className="flex min-w-0 items-center gap-2">
              <span
                className="flex h-7 w-7 shrink-0 items-center justify-center rounded-[8px] text-white"
                style={{ background: accentOf(currentExpert?.accent) }}
              >
                <Bot size={15} />
              </span>
              <p className="truncate text-sm font-medium text-text">
                {currentExpert?.name ?? "请选择专家"}
              </p>
            </div>
            <Button variant="secondary" className="px-3 py-1.5 text-xs" onClick={newSession} icon={<Plus size={14} />}>
              新会话
            </Button>
          </div>

          <div className="thin-scroll flex-1 space-y-4 overflow-y-auto p-4">
            {messages.length === 0 && currentExpert && (
              <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
                <p className="text-sm font-medium text-text">{currentExpert.name}</p>
                <p className="max-w-md text-xs leading-relaxed text-muted">{currentExpert.desc}</p>
                {currentExpert.samples?.length > 0 && (
                  <div className="mt-2 flex max-w-md flex-wrap justify-center gap-2">
                    {currentExpert.samples.map((s) => (
                      <button
                        key={s}
                        onClick={() => send(s)}
                        className="rounded-full border border-border bg-[#fafbff] px-3 py-1.5 text-xs text-muted transition-colors hover:border-primary/40 hover:text-primary"
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                )}
                <p className="mt-2 max-w-sm text-xs text-muted/70">{currentExpert.boundary}</p>
              </div>
            )}

            {messages.map((m, i) => (
              <div
                key={i}
                className={m.role === "user" ? "flex flex-col items-end" : "flex flex-col items-start"}
              >
                <div
                  className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap shadow-[0_1px_2px_rgba(15,23,42,0.04)] ${
                    m.role === "user"
                      ? "bg-[linear-gradient(135deg,#2563eb_0%,#0ea5a4_100%)] text-white [border-bottom-right-radius:6px]"
                      : "border border-border bg-surface text-text [border-bottom-left-radius:6px]"
                  } ${m.streaming ? "stream-cursor" : ""}`}
                >
                  {m.content}
                </div>

                {m.role === "assistant" && m.citations && m.citations.length > 0 && !m.streaming && (
                  <details className="mt-1.5 max-w-[85%] rounded-[10px] border border-border bg-[#f8fafc] px-3 py-2 text-left">
                    <summary className="cursor-pointer select-none text-xs font-medium text-muted hover:text-text">
                      参考依据（{m.citations.length}）
                    </summary>
                    <ul className="mt-2 flex flex-col gap-2">
                      {m.citations.map((c) => (
                        <li key={c.index} className="text-xs leading-relaxed text-muted">
                          <span className="font-medium text-text">[{c.index}]</span>{" "}
                          {c.kb_type === "shared" ? "公共政策库" : "我的知识库"} · 《{c.doc_name}》
                          {c.distance != null && (
                            <span className="ml-1 text-muted/70">· 距离 {c.distance.toFixed(3)}</span>
                          )}
                          <p className="mt-0.5 line-clamp-3 text-muted/80">{c.chunk_text}</p>
                        </li>
                      ))}
                    </ul>
                  </details>
                )}
              </div>
            ))}
            <div ref={bottomRef} />
          </div>

          {error && (
            <div className="px-4 pb-2">
              <Alert message={error} />
            </div>
          )}

          <div className="border-t border-border p-3">
            <div className="flex items-end gap-2">
              <Textarea
                rows={2}
                className="min-w-0"
                value={question}
                placeholder="向当前专家提问，回车发送（Shift+回车换行）"
                disabled={!currentExpert}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    send();
                  }
                }}
              />
              {streaming ? (
                <Button variant="secondary" onClick={() => abortRef.current?.abort()}>
                  <Square size={14} />
                  停止
                </Button>
              ) : (
                <Button onClick={() => send()} disabled={!question.trim() || !currentExpert}>
                  <Send size={14} />
                  发送
                </Button>
              )}
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
