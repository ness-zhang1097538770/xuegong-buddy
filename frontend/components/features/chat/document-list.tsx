"use client";

import { FileText, Trash2 } from "lucide-react";
import { FileDrop } from "@/components/ui/file-drop";
import { EmptyState, Spinner } from "@/components/ui/feedback";
import type { DocumentItem } from "@/lib/types";

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

interface Props {
  docs: DocumentItem[];
  loading: boolean;
  onUpload: (files: File[]) => void;
  onDelete: (id: number) => void;
}

export function DocumentList({ docs, loading, onUpload, onDelete }: Props) {
  return (
    <div className="flex flex-col gap-3">
      <FileDrop
        accept=".pdf,.txt,.docx"
        hint="支持 PDF / Word / TXT"
        onFiles={onUpload}
      />

      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-text">我的知识库</p>
        <span className="text-xs text-muted">{docs.length} 个文档</span>
      </div>

      {loading ? (
        <Spinner text="加载中…" />
      ) : docs.length === 0 ? (
        <EmptyState
          icon={<FileText size={24} />}
          title="暂无文档"
          desc="上传学生手册、政策文件后即可基于其内容提问"
        />
      ) : (
        <ul className="thin-scroll flex max-h-[420px] flex-col gap-2 overflow-y-auto">
          {docs.map((doc) => (
            <li
              key={doc.id}
              className="group flex items-start gap-2.5 rounded-[12px] border border-border bg-white px-3 py-2.5 transition-colors hover:border-primary/50 hover:bg-[#fafbff]"
            >
              <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-[9px] bg-primary-soft text-primary">
                <FileText size={15} />
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-text">{doc.filename}</p>
                <p className="text-xs text-muted">
                  {formatSize(doc.size_bytes)} · {doc.chunk_count} 段 · {doc.status}
                </p>
              </div>
              <button
                onClick={() => onDelete(doc.id)}
                title="删除"
                className="shrink-0 rounded-[8px] p-1.5 text-muted opacity-0 transition-all hover:bg-[#fef2f2] hover:text-danger group-hover:opacity-100"
              >
                <Trash2 size={15} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
