"use client";

import { getToken, clearSession } from "./auth";
import type {
  ChatDone,
  DocumentItem,
  DocGenerateResult,
  DocTaskItem,
  ExcelBatchResult,
  ExcelUploadResult,
  ExpertSessionItem,
  ExpertsResult,
  HomeSummary,
  LoginResult,
  NoticeTask,
  RefUploadResult,
  SiteGroup,
  StudentDetail,
  StudentListResult,
  TalkDraftResult,
  TalkListResult,
  TemplateDetail,
  TemplateItem,
  UserInfo,
  ApprovalDetail,
  ApprovalListResult,
  DormAnomaly,
  DormGridResult,
  ExpertCitation,
} from "./types";

const BASE = "/api/v1";

/** 登录态失效事件：请求层发出，布局层负责跳转。 */
export const UNAUTHORIZED_EVENT = "studybuddy:unauthorized";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/** 统一取错误信息：后端 HTTPException 用 detail，全局兜底用 error.message。 */
async function extractMessage(res: Response): Promise<string> {
  try {
    const data = await res.json();
    if (typeof data?.detail === "string") return data.detail;
    if (typeof data?.error?.message === "string") return data.error.message;
    return JSON.stringify(data);
  } catch {
    return `请求失败（${res.status}）`;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      ...(init.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...authHeaders(),
      ...(init.headers ?? {}),
    },
  });

  if (res.status === 401) {
    clearSession();
    // 跳转交给页面层（布局监听该事件后走 router.replace），避免在请求库内直接改地址
    if (typeof window !== "undefined") {
      window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
    }
    throw new ApiError("登录已失效，请重新登录", 401);
  }
  if (!res.ok) throw new ApiError(await extractMessage(res), res.status);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

// ============ 认证 ============

export const authApi = {
  login: (email: string, password: string) =>
    request<LoginResult>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  register: (email: string, password: string, inviteCode: string) =>
    request<{ user_id: number; email: string }>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, invite_code: inviteCode }),
    }),

  me: () => request<UserInfo>("/auth/me"),
};

// ============ 知识库 ============

export const kbApi = {
  list: () => request<{ documents: DocumentItem[]; total: number }>("/kb/documents"),

  upload: (file: File, category?: string) => {
    const fd = new FormData();
    fd.append("file", file);
    if (category) fd.append("category", category);
    return request<DocumentItem>("/kb/upload", { method: "POST", body: fd });
  },

  remove: (id: number) =>
    request<{ message: string }>(`/kb/documents/${id}`, { method: "DELETE" }),
};

/**
 * SSE 流式问答。后端事件：chunk / done / error。
 * 用 fetch 手动解析（EventSource 无法带 Authorization 头）。
 */
export async function streamChat(
  question: string,
  convId: number | null,
  handlers: {
    onChunk: (text: string) => void;
    onDone: (data: ChatDone) => void;
    onError: (message: string) => void;
  },
  signal?: AbortSignal,
): Promise<void> {
  const params = new URLSearchParams({ q: question });
  if (convId) params.set("conv_id", String(convId));

  const res = await fetch(`${BASE}/kb/chat?${params.toString()}`, {
    headers: { Accept: "text/event-stream", ...authHeaders() },
    signal,
  });

  if (!res.ok || !res.body) {
    handlers.onError(await extractMessage(res));
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() ?? "";

    for (const block of blocks) {
      const eventLine = block.split("\n").find((l) => l.startsWith("event:"));
      const dataLine = block.split("\n").find((l) => l.startsWith("data:"));
      if (!eventLine || !dataLine) continue;

      const event = eventLine.slice(6).trim();
      const raw = dataLine.slice(5).trim();
      try {
        const data = JSON.parse(raw);
        if (event === "chunk") handlers.onChunk(data.content ?? "");
        else if (event === "done") handlers.onDone(data as ChatDone);
        else if (event === "error") handlers.onError(data?.error?.message ?? "生成失败");
      } catch {
        // 忽略解析不了的片段
      }
    }
  }
}

// ============ 文稿生成 ============

export const docApi = {
  templates: (category?: string, style?: string) => {
    const params = new URLSearchParams();
    if (category) params.set("category", category);
    if (style) params.set("style", style);
    const qs = params.toString();
    return request<{ templates: TemplateItem[]; total: number }>(
      `/doc/templates${qs ? `?${qs}` : ""}`,
    );
  },

  templateDetail: (id: number) => request<TemplateDetail>(`/doc/templates/${id}`),

  uploadReference: (files: File[]) => {
    const fd = new FormData();
    files.forEach((f) => fd.append("files", f));
    return request<RefUploadResult>("/doc/upload-reference", { method: "POST", body: fd });
  },

  generate: (payload: {
    template_id: number;
    variables: Record<string, string>;
    style?: string;
    reference_ids?: string[];
  }) =>
    request<DocGenerateResult>("/doc/generate", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  tasks: () => request<DocTaskItem[]>("/doc/tasks"),
};

// ============ Excel 台账 ============

export const excelApi = {
  upload: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<ExcelUploadResult>("/excel/upload/read", { method: "POST", body: fd });
  },

  batchGenerate: (maxRows: number, templateId?: number) => {
    const params = new URLSearchParams({ max_rows: String(maxRows) });
    if (templateId) params.set("template_id", String(templateId));
    return request<ExcelBatchResult>(`/excel/batch-generate?${params.toString()}`, {
      method: "POST",
    });
  },
};

// ============ 常用网站 ============

export const sitesApi = {
  list: () => request<SiteGroup[]>("/websites"),
};

// ============ 副驾首页 ============

export const homeApi = {
  summary: () => request<HomeSummary>("/home/summary"),
  resolveTodo: (id: number) =>
    request<{ message: string; todo_id: number }>(`/home/todos/${id}/resolve`, {
      method: "POST",
    }),
  createTodo: (title: string, dueDate?: string, note?: string) => {
    const qs = new URLSearchParams({ title });
    if (dueDate) qs.set("due_date", dueDate);
    if (note) qs.set("note", note);
    return request<{ message: string; id: number }>(`/home/todos?${qs.toString()}`, {
      method: "POST",
    });
  },
};

// ============ 谈话记录仪 ============

export const talkApi = {
  list: (params?: { page?: number; size?: number; need_follow?: number }) => {
    const qs = new URLSearchParams();
    if (params?.page) qs.set("page", String(params.page));
    if (params?.size) qs.set("size", String(params.size));
    if (params?.need_follow !== undefined) qs.set("need_follow", String(params.need_follow));
    const s = qs.toString();
    return request<TalkListResult>(`/talks${s ? `?${s}` : ""}`);
  },

  create: (payload: {
    student_name: string;
    student_id_ref?: string;
    method?: string;
    topic?: string;
    content: string;
    conclusion?: string;
    mood?: string;
    need_follow?: boolean;
    follow_date?: string;
    is_sensitive?: boolean;
  }) => {
    const qs = new URLSearchParams();
    qs.set("student_name", payload.student_name);
    if (payload.student_id_ref) qs.set("student_id_ref", payload.student_id_ref);
    qs.set("method", payload.method ?? "面谈");
    qs.set("topic", payload.topic ?? "");
    qs.set("content", payload.content);
    qs.set("conclusion", payload.conclusion ?? "");
    qs.set("mood", payload.mood ?? "平稳");
    qs.set("need_follow", payload.need_follow ? "1" : "0");
    qs.set("follow_date", payload.follow_date ?? "");
    qs.set("is_sensitive", payload.is_sensitive ? "1" : "0");
    return request<{ message: string; id: number }>(`/talks?${qs.toString()}`, {
      method: "POST",
    });
  },

  draft: (payload: {
    student_name: string;
    method?: string;
    topic?: string;
    key_points: string;
    student_id_ref?: string;
  }) =>
    request<TalkDraftResult>("/talks/draft", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  closeFollow: (id: number, conclusion?: string) => {
    const qs = new URLSearchParams();
    if (conclusion) qs.set("conclusion", conclusion);
    const s = qs.toString();
    return request<{ message: string }>(`/talks/${id}/close-follow${s ? `?${s}` : ""}`, {
      method: "POST",
    });
  },

  transcribe: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<{ transcript: string }>("/talks/transcribe", { method: "POST", body: fd });
  },
};

// ============ 一人一页 ============

export const studentApi = {
  list: (params?: {
    page?: number;
    size?: number;
    search?: string;
    grade?: string;
    class_name?: string;
    tag?: string;
    risk_level?: string;
  }) => {
    const qs = new URLSearchParams();
    if (params?.page) qs.set("page", String(params.page));
    if (params?.size) qs.set("size", String(params.size));
    if (params?.search) qs.set("search", params.search);
    if (params?.grade) qs.set("grade", params.grade);
    if (params?.class_name) qs.set("class_name", params.class_name);
    if (params?.tag) qs.set("tag", params.tag);
    if (params?.risk_level) qs.set("risk_level", params.risk_level);
    const s = qs.toString();
    return request<StudentListResult>(`/students${s ? `?${s}` : ""}`);
  },

  detail: (id: number) => request<StudentDetail>(`/students/${id}`),

  filters: () =>
    request<{ grades: string[]; classes: string[] }>("/students/filters"),

  handover: (id: number) =>
    downloadFile(`/students/${id}/handover`, `handover_${id}.docx`),

  import: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<{ imported: number; skipped: number; errors: string[] }>(
      "/students/import",
      { method: "POST", body: fd },
    );
  },

  seedDemo: () =>
    request<{ message: string }>("/students/seed-demo", { method: "POST" }),
};

// ============ 通知变材料 ============

export const noticeApi = {
  generate: (payload: {
    theme: string;
    event_time?: string;
    place?: string;
    audience?: string;
  }) =>
    request<NoticeTask>("/notice/generate", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  tasks: () => request<NoticeTask[]>("/notice/tasks"),

  task: (id: number) => request<NoticeTask>(`/notice/${id}`),

  download: (id: number) => downloadFile(`/notice/download/${id}`, `notice_${id}.docx`),

  signinImport: (
    file: File,
    opts?: { theme?: string; event_time?: string; place?: string },
  ) => {
    const qs = new URLSearchParams();
    if (opts?.theme) qs.set("theme", opts.theme);
    if (opts?.event_time) qs.set("event_time", opts.event_time);
    if (opts?.place) qs.set("place", opts.place);
    const s = qs.toString();
    const fd = new FormData();
    fd.append("file", file);
    return request<{
      signin_sheet: string;
      students: { name: string; student_id: string; class_name: string }[];
      count: number;
    }>(`/notice/signin/import${s ? `?${s}` : ""}`, { method: "POST", body: fd });
  },

  signinExport: (payload: {
    theme?: string;
    event_time?: string;
    place?: string;
    students: { name: string; student_id: string; class_name: string }[];
  }) => downloadFileWithBody("/notice/signin/export", payload, "signin_sheet.docx"),
};

// ============ 专家智能体 ============

export const expertApi = {
  list: () => request<ExpertsResult>("/experts"),

  sessions: (expertId?: string) => {
    const qs = expertId ? `?expert_id=${encodeURIComponent(expertId)}` : "";
    return request<{ sessions: ExpertSessionItem[] }>(`/experts/sessions${qs}`);
  },

  createSession: (expertId: string, title = "新会话") =>
    request<{ id: number; expert_id: string; title: string }>(
      `/experts/sessions?expert_id=${encodeURIComponent(expertId)}&title=${encodeURIComponent(title)}`,
      { method: "POST" },
    ),

  deleteSession: (id: number) =>
    request<{ message: string }>(`/experts/sessions/${id}`, { method: "DELETE" }),
};

/**
 * 专家对话 SSE 流式。后端事件：data:{token} 增量 / event:done / event:error。
 * 注意后端会先推一个无 session_id 的 done（来自模型流），再推带 session_id 的 done，
 * 这里只在拿到 session_id 时才算结束。
 */
export async function streamExpertChat(
  payload: {
    expert_id: string;
    session_id: number | null;
    messages: { role: string; content: string }[];
  },
  handlers: {
    onChunk: (text: string) => void;
    onDone: (data: { content: string; session_id: number; citations?: ExpertCitation[] }) => void;
    onError: (message: string) => void;
  },
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${BASE}/experts/chat`, {
    method: "POST",
    headers: { Accept: "text/event-stream", "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(payload),
    signal,
  });

  if (!res.ok || !res.body) {
    handlers.onError(await extractMessage(res));
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() ?? "";

    for (const block of blocks) {
      const eventLine = block.split("\n").find((l) => l.startsWith("event:"));
      const dataLine = block.split("\n").find((l) => l.startsWith("data:"));
      if (!dataLine) continue;

      const event = eventLine ? eventLine.slice(6).trim() : "";
      const raw = dataLine.slice(5).trim();
      try {
        const data = JSON.parse(raw);
        if (event === "done") {
          if (data?.session_id != null) handlers.onDone(data);
        } else if (event === "error") {
          handlers.onError(data?.error?.message ?? "生成失败");
        } else if (data?.token != null) {
          handlers.onChunk(data.token);
        }
      } catch {
        // 忽略解析不了的片段
      }
    }
  }
}

// ============ 事务审批 ============

export const approvalApi = {
  list: (params?: { type?: string; status?: string; page?: number; size?: number }) => {
    const qs = new URLSearchParams();
    if (params?.type) qs.set("type", params.type);
    if (params?.status) qs.set("status", params.status);
    if (params?.page) qs.set("page", String(params.page));
    if (params?.size) qs.set("size", String(params.size));
    const s = qs.toString();
    return request<ApprovalListResult>(`/approvals${s ? `?${s}` : ""}`);
  },

  detail: (id: number) => request<ApprovalDetail>(`/approvals/${id}`),

  resolve: (id: number, action: "approve" | "reject" | "return", opinion?: string) => {
    const qs = new URLSearchParams({ action });
    if (opinion) qs.set("opinion", opinion);
    return request<{ message: string; status: string }>(
      `/approvals/${id}/resolve?${qs.toString()}`,
      { method: "POST" },
    );
  },

  seedDemo: () => request<{ message: string }>("/approvals/seed-demo", { method: "POST" }),
};

// ============ 查寝考勤 ============

export const dormApi = {
  grid: (building?: string) => {
    const qs = building ? `?building=${encodeURIComponent(building)}` : "";
    return request<DormGridResult>(`/dorm/grid${qs}`);
  },

  buildings: () => request<{ buildings: string[] }>("/dorm/buildings"),

  anomalies: () => request<{ anomalies: DormAnomaly[] }>("/dorm/anomalies"),

  check: (
    dormId: number,
    status: "normal" | "abnormal",
    abnormalType?: string,
    note?: string,
  ) => {
    const qs = new URLSearchParams({ dorm_id: String(dormId), status });
    if (abnormalType) qs.set("abnormal_type", abnormalType);
    if (note) qs.set("note", note);
    return request<{ message: string; status: string }>(`/dorm/check?${qs.toString()}`, {
      method: "POST",
    });
  },

  seedDemo: () => request<{ message: string }>("/dorm/seed-demo", { method: "POST" }),
};

// ============ 下载（需带 token，不能直接用 <a href>）============

export async function downloadFile(path: string, filename: string): Promise<void> {
  // 后端返回的 download_url 自带 /api/v1 前缀，这里避免重复拼接
  const target = path.startsWith(BASE) ? path : `${BASE}${path}`;
  const res = await fetch(target, { headers: authHeaders() });
  if (!res.ok) throw new ApiError(await extractMessage(res), res.status);
  const blob = await res.blob();
  // 立即点击后再释放，避免部分浏览器拿到空 blob
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}

/** POST 下载（JSON 请求体）——如签到表导出。 */
export async function downloadFileWithBody(
  path: string,
  body: unknown,
  filename: string,
): Promise<void> {
  const target = path.startsWith(BASE) ? path : `${BASE}${path}`;
  const res = await fetch(target, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new ApiError(await extractMessage(res), res.status);
  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}
