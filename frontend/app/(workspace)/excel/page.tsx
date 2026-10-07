"use client";

import { useState } from "react";
import { Download, Sparkles, Table2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Alert, Badge, Card, EmptyState, Spinner } from "@/components/ui/feedback";
import { Input, Label } from "@/components/ui/field";
import { FileDrop } from "@/components/ui/file-drop";
import { ApiError, excelApi, downloadFile } from "@/lib/api";
import type { ExcelBatchResult, ExcelUploadResult } from "@/lib/types";

export default function ExcelPage() {
  const [upload, setUpload] = useState<ExcelUploadResult | null>(null);
  const [uploading, setUploading] = useState(false);
  const [maxRows, setMaxRows] = useState(50);
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState<ExcelBatchResult | null>(null);
  const [error, setError] = useState("");

  async function handleUpload(files: File[]) {
    setUploading(true);
    setError("");
    setResult(null);
    try {
      setUpload(await excelApi.upload(files[0]));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "读取失败");
    } finally {
      setUploading(false);
    }
  }

  async function generate() {
    setGenerating(true);
    setError("");
    setResult(null);
    try {
      setResult(await excelApi.batchGenerate(maxRows));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "生成失败");
    } finally {
      setGenerating(false);
    }
  }

  const previewRows = result?.preview ?? upload?.preview ?? [];
  const previewHeaders = result?.headers ?? upload?.headers ?? [];

  return (
    <div className="grid gap-4 lg:grid-cols-[380px_1fr]">
      <div className="lg:col-span-2">
        <h2 className="text-base font-semibold text-text">台账处理</h2>
        <p className="mt-1 text-xs text-muted">
          上传学生台账，批量生成评语并导出结果表格。
        </p>
      </div>
      <Card className="h-fit p-4">
        <div className="flex flex-col gap-4">
          <div>
            <Label hint=".xlsx / .xls，≤10MB">上传台账</Label>
            <FileDrop
              accept=".xlsx,.xls"
              hint="第一行需为表头"
              disabled={uploading}
              onFiles={handleUpload}
            />
          </div>

          {upload && (
            <div className="rounded-[8px] border border-border bg-[#f8fafc] px-3 py-2 text-xs text-muted">
              已读取 <span className="font-medium text-text">{upload.total_rows}</span> 行 ·{" "}
              {upload.headers.length} 列
            </div>
          )}

          <div>
            <Label hint="1–200">生成行数</Label>
            <Input
              type="number"
              min={1}
              max={200}
              value={maxRows}
              onChange={(e) => setMaxRows(Number(e.target.value))}
            />
          </div>

          {error && <Alert message={error} />}

          <Button
            onClick={generate}
            loading={generating}
            disabled={!upload}
            icon={<Sparkles size={15} />}
            className="w-full"
          >
            {generating ? "批量生成中…" : "批量生成评语"}
          </Button>
          {generating && (
            <p className="text-xs text-muted">并发处理中，行数越多耗时越长，请勿关闭页面。</p>
          )}
        </div>
      </Card>

      <Card className="flex min-h-[420px] flex-col p-4">
        <div className="mb-3 flex items-center justify-between">
          <p className="text-sm font-medium text-text">
            {result ? "生成结果预览" : "上传预览"}
          </p>
          {result && (
            <div className="flex items-center gap-2">
              <Badge tone="success">{result.row_count} 行已生成</Badge>
              <Button
                variant="secondary"
                icon={<Download size={15} />}
                onClick={() =>
                  downloadFile(result.download_url, `台账评语_${result.task_id}.xlsx`).catch(
                    (err) => setError(err instanceof Error ? err.message : "下载失败"),
                  )
                }
              >
                下载 Excel
              </Button>
            </div>
          )}
        </div>

        {generating ? (
          <div className="flex flex-1 items-center justify-center">
            <Spinner text="AI 正在逐行生成评语…" />
          </div>
        ) : previewRows.length === 0 ? (
          <EmptyState
            icon={<Table2 size={24} />}
            title="请上传 Excel"
            desc="上传后将显示前 10 行预览，确认无误再批量生成"
          />
        ) : (
          <div className="thin-scroll flex-1 overflow-auto rounded-[8px] border border-border">
            <table className="w-full border-collapse text-xs">
              <thead className="sticky top-0 bg-[#f8fafc]">
                <tr>
                  {previewHeaders.map((h) => (
                    <th
                      key={h}
                      className="border-b border-border px-3 py-2 text-left font-medium text-muted whitespace-nowrap"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {previewRows.map((row, i) => (
                  <tr key={i} className="hover:bg-[#f8fafc]">
                    {previewHeaders.map((h) => (
                      <td
                        key={h}
                        className="border-b border-border px-3 py-2 align-top text-text"
                      >
                        <span className="line-clamp-3">{String(row[h] ?? "")}</span>
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
