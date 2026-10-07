"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { GraduationCap, MessagesSquare, FileText, Table2, Compass, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input, Label } from "@/components/ui/field";
import { Alert } from "@/components/ui/feedback";
import { authApi } from "@/lib/api";
import { setSession } from "@/lib/auth";

const FEATURES = [
  { icon: MessagesSquare, text: "基于知识库问答，回答带引用来源" },
  { icon: FileText, text: "模板化文稿生成，一键导出 Word" },
  { icon: Table2, text: "批量生成学生评语，导出台账" },
  { icon: Compass, text: "高频常用站点，一键直达" },
];

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [inviteCode, setInviteCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setNotice("");
    setLoading(true);
    try {
      if (mode === "login") {
        const res = await authApi.login(email.trim(), password);
        setSession(res.access_token, res.user);
        router.replace("/");
      } else {
        await authApi.register(email.trim(), password, inviteCode.trim());
        setNotice("注册成功，请登录");
        setMode("login");
        setPassword("");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "操作失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen bg-bg">
      {/* 品牌面板（桌面） */}
      <div className="relative hidden w-[46%] max-w-xl overflow-hidden bg-[linear-gradient(135deg,#2563eb_0%,#0ea5a4_100%)] lg:flex">
        <div className="absolute -right-24 -top-24 h-80 w-80 rounded-full bg-white/10 blur-2xl" />
        <div className="absolute -bottom-32 -left-16 h-80 w-80 rounded-full bg-white/10 blur-2xl" />
        <div className="relative z-10 flex w-full flex-col justify-between p-12 text-white">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-[12px] bg-white/15 backdrop-blur">
              <GraduationCap size={24} />
            </div>
            <span className="text-lg font-semibold">学工 Buddy</span>
          </div>

          <div className="space-y-3">
            <h1 className="text-3xl font-bold leading-snug">
              辅导员的
              <br />
              AI 工作助手
            </h1>
            <p className="max-w-sm text-sm leading-relaxed text-white/85">
              知识库问答、文稿生成、台账处理、常用站点，一个工作台全部搞定。
            </p>
          </div>

          <ul className="space-y-3">
            {FEATURES.map((f) => (
              <li key={f.text} className="flex items-center gap-3 text-sm text-white/90">
                <span className="flex h-8 w-8 items-center justify-center rounded-[10px] bg-white/15">
                  <f.icon size={16} />
                </span>
                {f.text}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* 表单区 */}
      <div className="flex w-full flex-col items-center justify-center px-4 py-10 lg:w-[54%]">
        {/* 移动端品牌 */}
        <div className="mb-8 flex flex-col items-center gap-2 lg:hidden">
          <div className="flex h-12 w-12 items-center justify-center rounded-[14px] bg-[linear-gradient(135deg,#2563eb_0%,#0ea5a4_100%)] text-white shadow-[0_8px_20px_-8px_rgba(37,99,235,0.6)]">
            <GraduationCap size={26} />
          </div>
          <h1 className="text-lg font-semibold text-text">学工 Buddy</h1>
          <p className="text-xs text-muted">高校辅导员 · 学工行政 AI 助手</p>
        </div>

        <div className="w-full max-w-sm">
          <div className="rounded-[20px] border border-border bg-surface p-7 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_12px_28px_-18px_rgba(15,23,42,0.22)]">
            <h2 className="mb-1 text-xl font-semibold text-text">
              {mode === "login" ? "欢迎回来" : "创建账号"}
            </h2>
            <p className="mb-6 text-sm text-muted">
              {mode === "login" ? "登录以继续使用工作台" : "使用邀请码注册新账号"}
            </p>

            <div className="mb-6 flex rounded-[12px] bg-[#f1f5f9] p-1">
              {(["login", "register"] as const).map((m) => (
                <button
                  key={m}
                  onClick={() => {
                    setMode(m);
                    setError("");
                    setNotice("");
                  }}
                  className={`flex-1 rounded-[9px] py-2 text-sm font-medium transition-all ${
                    mode === m ? "bg-white text-text shadow-sm" : "text-muted hover:text-text"
                  }`}
                >
                  {m === "login" ? "登录" : "注册"}
                </button>
              ))}
            </div>

            <form onSubmit={submit} className="flex flex-col gap-4">
              <div>
                <Label>邮箱</Label>
                <Input
                  type="email"
                  required
                  autoComplete="email"
                  placeholder="you@school.edu.cn"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>

              <div>
                <Label hint={mode === "register" ? "至少 6 位" : undefined}>密码</Label>
                <Input
                  type="password"
                  required
                  autoComplete={mode === "login" ? "current-password" : "new-password"}
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>

              {mode === "register" && (
                <div>
                  <Label hint="由管理员发放">邀请码</Label>
                  <Input
                    required
                    placeholder="请输入邀请码"
                    value={inviteCode}
                    onChange={(e) => setInviteCode(e.target.value)}
                  />
                </div>
              )}

              {error && <Alert message={error} />}
              {notice && <Alert type="success" message={notice} />}

              <Button type="submit" loading={loading} className="mt-1 w-full">
                {mode === "login" ? "登录" : "注册"}
              </Button>
            </form>
          </div>

          <div className="mt-4 flex items-center justify-center gap-1.5 text-xs text-muted">
            <ShieldCheck size={14} className="text-primary" />
            AI 生成内容仅为草稿，涉及学生评价与危机材料须人工复核。
          </div>
        </div>
      </div>
    </div>
  );
}
