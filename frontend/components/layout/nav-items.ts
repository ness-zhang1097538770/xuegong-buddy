"use client";

import {
  Bot,
  Building2,
  ClipboardCheck,
  Compass,
  FileText,
  LayoutDashboard,
  Megaphone,
  MessagesSquare,
  Table2,
  UserRound,
} from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  shortLabel: string;
  icon: typeof LayoutDashboard;
}

export interface NavGroup {
  label: string;
  items: NavItem[];
}

/** 副驾在上、生产在下、其他收尾（PRD V0.3 第四节）。 */
export const NAV_GROUPS: NavGroup[] = [
  {
    label: "副驾",
    items: [
      { href: "/", label: "副驾首页", shortLabel: "首页", icon: LayoutDashboard },
      { href: "/talks", label: "谈话记录仪", shortLabel: "谈话", icon: MessagesSquare },
      { href: "/students", label: "一人一页", shortLabel: "一人一页", icon: UserRound },
      { href: "/notice", label: "通知变材料", shortLabel: "通知", icon: Megaphone },
      { href: "/approvals", label: "事务审批", shortLabel: "审批", icon: ClipboardCheck },
      { href: "/dorm", label: "查寝考勤", shortLabel: "查寝", icon: Building2 },
    ],
  },
  {
    label: "生产",
    items: [
      { href: "/kb", label: "知识库问答", shortLabel: "问答", icon: MessagesSquare },
      { href: "/doc", label: "文稿生成", shortLabel: "文稿", icon: FileText },
      { href: "/excel", label: "台账处理", shortLabel: "台账", icon: Table2 },
      { href: "/experts", label: "专家智能体", shortLabel: "专家", icon: Bot },
    ],
  },
  {
    label: "其他",
    items: [
      { href: "/sites", label: "常用网站", shortLabel: "网站", icon: Compass },
    ],
  },
];

/** 扁平化列表（供移动端底部导航横向滚动用）。 */
export const NAV_ITEMS: NavItem[] = NAV_GROUPS.flatMap((g) => g.items);
