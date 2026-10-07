"use client";

import { useEffect, useState } from "react";
import { Building2, Check, Home, ShieldAlert, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Alert, Badge, Card, EmptyState, Spinner } from "@/components/ui/feedback";
import { Select, Textarea } from "@/components/ui/field";
import { dormApi } from "@/lib/api";
import type { DormAnomaly, DormRoom } from "@/lib/types";

const ABNORMAL_TYPES = ["夜不归宿", "违规电器", "拒查", "卫生"];

function roomStyle(status: string): string {
  if (status === "normal") return "border-success/30 bg-[#f0fdf4] hover:border-success";
  if (status === "abnormal") return "border-danger/30 bg-[#fef2f2] hover:border-danger";
  return "border-border bg-[#fafbff] hover:border-primary/40";
}

function roomDot(status: string): string {
  if (status === "normal") return "bg-success";
  if (status === "abnormal") return "bg-danger";
  return "bg-[#cbd5e1]";
}

function statusLabel(status: string): string {
  if (status === "normal") return "正常";
  if (status === "abnormal") return "异常";
  return "未查";
}

export default function DormPage() {
  const [buildings, setBuildings] = useState<Record<string, Record<string, DormRoom[]>>>({});
  const [buildingList, setBuildingList] = useState<string[]>([]);
  const [building, setBuilding] = useState("");
  const [anomalies, setAnomalies] = useState<DormAnomaly[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [seeding, setSeeding] = useState(false);

  const [selected, setSelected] = useState<DormRoom | null>(null);
  const [selBuilding, setSelBuilding] = useState("");
  const [selFloor, setSelFloor] = useState("");
  const [markStatus, setMarkStatus] = useState<"normal" | "abnormal">("normal");
  const [abnormalType, setAbnormalType] = useState("");
  const [note, setNote] = useState("");
  const [acting, setActing] = useState(false);

  async function load(buildingFilter?: string) {
    setLoading(true);
    try {
      const b = buildingFilter !== undefined ? buildingFilter : building;
      const res = await dormApi.grid(b || undefined);
      setBuildings(res.buildings);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "宿舍网格加载失败");
    } finally {
      setLoading(false);
    }
  }

  async function loadAnomalies() {
    try {
      const res = await dormApi.anomalies();
      setAnomalies(res.anomalies);
    } catch {
      // 异常列表非关键，失败静默
    }
  }

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const res = await dormApi.grid();
        if (alive) {
          setBuildings(res.buildings);
          setError("");
        }
      } catch (err) {
        if (alive) setError(err instanceof Error ? err.message : "宿舍网格加载失败");
      } finally {
        if (alive) setLoading(false);
      }
    })();
    dormApi
      .anomalies()
      .then((r) => {
        if (alive) setAnomalies(r.anomalies);
      })
      .catch(() => {});
    dormApi
      .buildings()
      .then((r) => {
        if (alive) setBuildingList(r.buildings);
      })
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, []);

  function openRoom(dorm: DormRoom, b: string, f: string) {
    setSelected(dorm);
    setSelBuilding(b);
    setSelFloor(f);
    setMarkStatus(dorm.status === "abnormal" ? "abnormal" : "normal");
    setAbnormalType(dorm.abnormal_type || "");
    setNote(dorm.note || "");
  }

  async function seedDemo() {
    setSeeding(true);
    setError("");
    try {
      const res = await dormApi.seedDemo();
      setError(res.message);
      load();
      loadAnomalies();
      dormApi.buildings().then((r) => setBuildingList(r.buildings)).catch(() => {});
    } catch (err) {
      setError(err instanceof Error ? err.message : "生成失败");
    } finally {
      setSeeding(false);
    }
  }

  async function submitMark() {
    if (!selected) return;
    if (markStatus === "abnormal" && !abnormalType) {
      setError("标记异常时请选择异常类型");
      return;
    }
    setActing(true);
    setError("");
    try {
      await dormApi.check(selected.id, markStatus, abnormalType || undefined, note.trim() || undefined);
      setSelected(null);
      await load();
      await loadAnomalies();
    } catch (err) {
      setError(err instanceof Error ? err.message : "标记失败");
    } finally {
      setActing(false);
    }
  }

  const buildingsEntries = Object.entries(buildings);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-text">查寝考勤</h2>
          <p className="mt-1 text-xs text-muted">
            宿舍三色网格，点房间即可标记正常 / 异常，异常自动生成待办。
          </p>
        </div>
        <Button variant="secondary" loading={seeding} onClick={seedDemo} icon={<Home size={15} />}>
          生成演示数据
        </Button>
      </div>

      <Card className="p-4">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <Select
            className="w-auto"
            value={building}
            onChange={(e) => {
              setBuilding(e.target.value);
              load(e.target.value);
            }}
          >
            <option value="">全部楼栋</option>
            {buildingList.map((b) => (
              <option key={b} value={b}>
                {b}
              </option>
            ))}
          </Select>
          <span className="flex items-center gap-3 text-xs text-muted">
            <span className="flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-success" /> 正常
            </span>
            <span className="flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-danger" /> 异常
            </span>
            <span className="flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-[#cbd5e1]" /> 未查
            </span>
          </span>
        </div>

        {error && <Alert message={error} onRetry={() => load()} />}

        {loading ? (
          <div className="flex justify-center py-10">
            <Spinner text="加载中…" />
          </div>
        ) : buildingsEntries.length === 0 ? (
          <EmptyState
            icon={<Building2 size={24} />}
            title="暂无宿舍数据"
            desc="点右上角「生成演示数据」后可体验查寝标记流程。"
          />
        ) : (
          <div className="flex flex-col gap-5">
            {buildingsEntries.map(([b, floors]) => (
              <section key={b}>
                <p className="mb-2 flex items-center gap-1.5 text-sm font-semibold text-text">
                  <Building2 size={15} className="text-primary" />
                  {b}
                </p>
                <div className="flex flex-col gap-3">
                  {Object.entries(floors).map(([floor, rooms]) => (
                    <div key={floor}>
                      <p className="mb-1.5 text-xs text-muted">{floor}</p>
                      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-5">
                        {rooms.map((r) => (
                          <button
                            key={r.id}
                            onClick={() => openRoom(r, b, floor)}
                            className={`rounded-[12px] border px-3 py-2.5 text-left transition-colors ${roomStyle(r.status)}`}
                          >
                            <div className="flex items-center justify-between">
                              <span className="text-sm font-medium text-text">{r.room}</span>
                              <span className={`h-2 w-2 rounded-full ${roomDot(r.status)}`} />
                            </div>
                            <p className="mt-1 truncate text-[11px] text-muted">
                              {r.members.length > 0 ? r.members.join("、") : "—"}
                            </p>
                            <p className="mt-0.5 text-[11px] text-muted">{statusLabel(r.status)}</p>
                          </button>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            ))}
          </div>
        )}
      </Card>

      {/* 今日异常宿舍 */}
      <Card className="p-4">
        <p className="mb-3 flex items-center gap-1.5 text-sm font-medium text-text">
          <ShieldAlert size={15} className="text-danger" />
          今日异常宿舍
        </p>
        {anomalies.length === 0 ? (
          <p className="py-3 text-center text-xs text-muted">今日暂无异常宿舍</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {anomalies.map((a) => (
              <li
                key={a.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-[12px] border border-danger/20 bg-[#fef2f2] px-3.5 py-3"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium text-text">
                    {a.building} {a.room}
                    <span className="ml-2">
                      <Badge tone="danger">{a.abnormal_type || "异常"}</Badge>
                    </span>
                  </p>
                  <p className="mt-1 text-xs text-muted">
                    {a.members.length > 0 ? `成员：${a.members.join("、")}` : "—"}
                    {a.note ? ` · ${a.note}` : ""}
                  </p>
                </div>
                <Button variant="secondary" className="px-3 py-1.5 text-xs" onClick={() => loadAnomalies()}>
                  刷新
                </Button>
              </li>
            ))}
          </ul>
        )}
      </Card>

      {/* 标记抽屉 */}
      {selected && (
        <div className="fixed inset-0 z-30 flex justify-end">
          <div className="absolute inset-0 bg-black/20" onClick={() => setSelected(null)} />
          <div className="thin-scroll relative flex h-full w-full max-w-[420px] flex-col gap-4 overflow-y-auto bg-bg p-4 shadow-2xl">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-base font-semibold text-text">
                  {selBuilding} {selFloor} {selected.room}
                </h3>
                <p className="mt-1 text-xs text-muted">
                  {selected.members.length > 0 ? `成员：${selected.members.join("、")}` : "暂无成员信息"}
                </p>
              </div>
              <button
                onClick={() => setSelected(null)}
                className="rounded-[8px] p-1.5 text-muted hover:bg-[#f1f5f9]"
              >
                <X size={18} />
              </button>
            </div>

            <Card className="p-4">
              <p className="mb-3 text-sm font-medium text-text">标记查寝结果</p>
              <div className="flex gap-2">
                <Button
                  variant={markStatus === "normal" ? "primary" : "secondary"}
                  className="flex-1"
                  onClick={() => setMarkStatus("normal")}
                  icon={<Check size={15} />}
                >
                  正常
                </Button>
                <Button
                  variant={markStatus === "abnormal" ? "danger" : "secondary"}
                  className="flex-1"
                  onClick={() => setMarkStatus("abnormal")}
                  icon={<ShieldAlert size={15} />}
                >
                  异常
                </Button>
              </div>

              {markStatus === "abnormal" && (
                <div className="mt-3 flex flex-col gap-3">
                  <Select value={abnormalType} onChange={(e) => setAbnormalType(e.target.value)}>
                    <option value="">选择异常类型</option>
                    {ABNORMAL_TYPES.map((t) => (
                      <option key={t} value={t}>
                        {t}
                      </option>
                    ))}
                  </Select>
                  <Textarea
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    placeholder="备注（可选）"
                    rows={2}
                  />
                </div>
              )}

              <Button className="mt-4 w-full" loading={acting} onClick={submitMark}>
                确认标记
              </Button>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
