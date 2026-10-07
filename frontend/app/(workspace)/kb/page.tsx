"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ChevronDown, Send, Square } from "lucide-react";
import { DocumentList } from "@/components/features/chat/document-list";
import { Button } from "@/components/ui/button";
import { Alert, Card } from "@/components/ui/feedback";
import { Textarea } from "@/components/ui/field";
import { ApiError, kbApi, streamChat } from "@/lib/api";
import type { Citation, DocumentItem } from "@/lib/types";

interface Message {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  streaming?: boolean;
}

export default function ChatPage() {
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [docsLoading, setDocsLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState("");
  const [convId, setConvId] = useState<number | null>(null);
  const [docsOpen, setDocsOpen] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const loadDocs = useCallback(async () => {
    setDocsLoading(true);
    try {
      const res = await kbApi.list();
      setDocs(res.documents);
    } catch (err) {
      setError(err instanceof Error ? err.message : "文档列表加载失败");
    } finally {
      setDocsLoading(false);
    }
  }, []);

  // 首屏异步拉取文档列表（setState 在 await 之后，不在同步渲染链上）
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const res = await kbApi.list();
        if (alive) setDocs(res.documents);
      } catch (err) {
        if (alive) setError(err instanceof Error ? err.message : "文档列表加载失败");
      } finally {
        if (alive) setDocsLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleUpload(files: File[]) {
    setUploading(true);
    setError("");
    try {
      for (const file of files) await kbApi.upload(file);
      await loadDocs();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "上传失败");
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(id: number) {
    try {
      await kbApi.remove(id);
      setDocs((prev) => prev.filter((d) => d.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "删除失败");
    }
  }

  async function send() {
    const q = question.trim();
    if (!q || streaming) return;

    setError("");
    setQuestion("");
    setMessages((prev) => [
      ...prev,
      { role: "user", content: q },
      { role: "assistant", content: "", streaming: true },
    ]);
    setStreaming(true);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      await streamChat(
        q,
        convId,
        {
          onChunk: (text) =>
            setMessages((prev) => {
              const next = [...prev];
              const last = next[next.length - 1];
              next[next.length - 1] = { ...last, content: last.content + text };
              return next;
            }),
          onDone: (data) => {
            setConvId(data.conv_id);
            setMessages((prev) => {
              const next = [...prev];
              next[next.length - 1] = {
                role: "assistant",
                content: data.content,
                citations: data.citations,
              };
              return next;
            });
          },
          onError: (msg) => {
            setError(msg);
            setMessages((prev) => prev.slice(0, -1));
          },
        },
        controller.signal,
      );
    } catch {
      // 用户主动中断（abort）不做处理
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
    <div className="grid gap-4 lg:grid-cols-[300px_1fr]">
      <div className="lg:col-span-2">
        <h2 className="text-base font-semibold text-text">知识库问答</h2>
        <p className="mt-1 text-xs text-muted">
          基于你上传的制度文件作答，回答只引用知识库内容并标注来源。
        </p>
      </div>
      <Card className="h-fit p-4">
        <button
          type="button"
          onClick={() => setDocsOpen((v) => !v)}
          className="flex w-full items-center justify-between text-sm font-medium text-text lg:hidden"
        >
          <span>知识库文档（{docs.length}）</span>
          <ChevronDown
            size={16}
            className={`text-muted transition-transform ${docsOpen ? "rotate-180" : ""}`}
          />
        </button>
        <div className={docsOpen ? "mt-3 lg:mt-0" : "hidden lg:block"}>
          {uploading && <p className="mb-2 text-xs text-primary">上传解析中…</p>}
          <DocumentList
            docs={docs}
            loading={docsLoading}
            onUpload={handleUpload}
            onDelete={handleDelete}
          />
        </div>
      </Card>

      <Card className="flex h-[calc(100dvh-14rem)] flex-col md:h-[calc(100vh-8.5rem)]">
        <div className="thin-scroll flex-1 space-y-4 overflow-y-auto p-4">
          {messages.length === 0 && (
            <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
              <p className="text-sm font-medium text-text">基于你的知识库提问</p>
              <p className="max-w-md text-xs text-muted">
                回答只引用你上传的文档内容，并标注来源。知识库为空时请先上传文档。
              </p>
            </div>
          )}

          {messages.map((m, i) => (
            <div key={i} className={m.role === "user" ? "flex justify-end" : ""}>
              <div
                className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap shadow-[0_1px_2px_rgba(15,23,42,0.04)] ${
                  m.role === "user"
                    ? "bg-[linear-gradient(135deg,#2563eb_0%,#0ea5a4_100%)] text-white [border-bottom-right-radius:6px]"
                    : "border border-border bg-surface text-text [border-bottom-left-radius:6px]"
                } ${m.streaming ? "stream-cursor" : ""}`}
              >
                {m.content}
                {m.citations && m.citations.length > 0 && (
                  <div className="mt-3 border-t border-border pt-2">
                    <p className="mb-1 text-xs font-medium text-muted">引用来源</p>
                    <ul className="space-y-1">
                      {m.citations.map((c, j) => (
                        <li key={j} className="text-xs text-muted">
                          <span className="font-medium text-text">· {c.doc_name}</span>
                          <span className="ml-1 line-clamp-2">{c.chunk_text}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
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
              placeholder="输入问题，回车发送（Shift+回车换行）"
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
              <Button onClick={send} disabled={!question.trim()}>
                <Send size={14} />
                发送
              </Button>
            )}
          </div>
        </div>
      </Card>
    </div>
  );
}
