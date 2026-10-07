"use client";

import { useEffect, useState } from "react";
import {
  Briefcase,
  Compass,
  ExternalLink,
  Flag,
  GraduationCap,
  Newspaper,
} from "lucide-react";
import { Alert, Card, EmptyState, Spinner } from "@/components/ui/feedback";
import { sitesApi } from "@/lib/api";
import type { SiteGroup } from "@/lib/types";

interface CategoryStyle {
  match: string;
  color: string;
  soft: string;
  icon: typeof Flag;
}

/** 四个栏目各配一个主色，视觉上一眼区分。 */
const CATEGORY_STYLES: CategoryStyle[] = [
  { match: "思政主阵地", color: "#dc2626", soft: "#fef2f2", icon: Flag },
  { match: "政策与资讯", color: "#2563eb", soft: "#eff4ff", icon: Newspaper },
  { match: "工作实操", color: "#0d9488", soft: "#f0fdfa", icon: Briefcase },
  { match: "专业成长", color: "#d97706", soft: "#fffbeb", icon: GraduationCap },
];

const DEFAULT_STYLE = CATEGORY_STYLES[1];

function styleOf(category: string): CategoryStyle {
  const name = category.split("·")[0].trim();
  return CATEGORY_STYLES.find((s) => name.includes(s.match)) ?? DEFAULT_STYLE;
}

export default function SitesPage() {
  const [groups, setGroups] = useState<SiteGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    sitesApi
      .list()
      .then(setGroups)
      .catch((err) => setError(err instanceof Error ? err.message : "加载失败"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h2 className="text-base font-semibold text-text">常用网站</h2>
        <p className="mt-1 text-xs text-muted">辅导员高频站点直达，点击在新标签页打开。</p>
      </div>

      {loading ? (
        <Spinner text="加载中…" />
      ) : error ? (
        <Alert message={error} onRetry={() => window.location.reload()} />
      ) : groups.length === 0 ? (
        <EmptyState icon={<Compass size={24} />} title="暂无站点" />
      ) : (
        groups.map((group) => {
          const st = styleOf(group.category);
          const Icon = st.icon;
          const [name, hint] = group.category.split("·").map((s) => s.trim());

          return (
            <section
              key={group.category}
              className="rounded-[16px] border p-4"
              style={{ background: st.soft, borderColor: `${st.color}30` }}
            >
              <div className="mb-3 flex items-center gap-2.5">
                <span
                  className="flex h-9 w-9 items-center justify-center rounded-[12px] text-white shadow-[0_4px_12px_-4px_rgba(0,0,0,0.35)]"
                  style={{ background: st.color }}
                >
                  <Icon size={17} />
                </span>
                <div className="min-w-0">
                  <p className="text-sm font-semibold" style={{ color: st.color }}>
                    {name}
                  </p>
                  {hint && <p className="text-[11px] text-muted">{hint}</p>}
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                {group.sites.map((site) => (
                  <a key={site.url} href={site.url} target="_blank" rel="noopener noreferrer" className="group">
                    <Card
                      className="h-full p-4 transition-all group-hover:-translate-y-0.5 group-hover:shadow-[0_6px_20px_-10px_rgba(15,23,42,0.25)]"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-sm font-medium text-text">{site.name}</p>
                        <ExternalLink size={15} className="shrink-0 text-muted" />
                      </div>
                      {site.desc && (
                        <p className="mt-1.5 text-xs leading-relaxed text-muted">{site.desc}</p>
                      )}
                    </Card>
                  </a>
                ))}
              </div>
            </section>
          );
        })
      )}
    </div>
  );
}
