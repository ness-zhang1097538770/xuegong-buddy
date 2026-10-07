/** 与后端 schema 一一对应的类型定义。 */

export interface UserInfo {
  id: number;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface LoginResult {
  access_token: string;
  token_type: string;
  user: UserInfo;
}

export interface DocumentItem {
  id: number;
  filename: string;
  file_type: string;
  category: string;
  status: string;
  chunk_count: number;
  size_bytes: number;
  created_at: string;
}

export interface Citation {
  doc_name: string;
  chunk_text: string;
}

export interface ChatDone {
  conv_id: number;
  message_id: number;
  content: string;
  citations: Citation[];
}

export interface TemplateItem {
  id: number;
  name: string;
  category: string;
  description: string;
  style: string;
  variables: string; // JSON 字符串数组
  is_builtin: boolean;
  created_at: string;
}

export interface TemplateDetail extends TemplateItem {
  system_prompt: string;
  user_prompt_template: string;
}

export interface DocGenerateResult {
  task_id: number;
  template_name: string;
  status: string;
  content: string;
}

export interface DocTaskItem {
  id: number;
  template_name: string;
  style: string;
  status: string;
  created_at: string;
}

export interface RefUploadResult {
  ref_ids: string[];
  filenames: string[];
  total_chars: number;
}

export interface ExcelUploadResult {
  task_id: string;
  headers: string[];
  preview: Record<string, unknown>[];
  total_rows: number;
}

export interface ExcelBatchResult {
  task_id: string;
  row_count: number;
  download_url: string;
  headers: string[];
  preview: Record<string, unknown>[];
}

export interface SiteItem {
  name: string;
  url: string;
  desc: string;
}

export interface SiteGroup {
  category: string;
  sites: SiteItem[];
}

// ============ 副驾首页 ============

export interface HomeStats {
  pending_approvals: number;
  pending_talks: number;
  abnormal_dorms: number;
  risk_students: number;
}

export interface HomeTodo {
  id: number;
  source_type: string;
  title: string;
  target_name: string;
  due_date: string;
  priority: number;
  status: string;
}

export interface HomeSummary {
  stats: HomeStats;
  todos: HomeTodo[];
  user_info: { email: string; role: string };
}

// ============ 谈话记录仪 ============

export interface TalkRecordItem {
  id: number;
  student_name: string;
  method: string;
  topic: string;
  content: string;
  conclusion: string;
  mood: string;
  need_follow: boolean;
  follow_date: string;
  follow_closed: boolean;
  created_at: string;
}

export interface TalkListResult {
  total: number;
  items: TalkRecordItem[];
}

export interface TalkDraftResult {
  draft: string;
  is_draft: boolean;
}

// ============ 一人一页 ============

export interface StudentListItem {
  id: number;
  student_id: string;
  name: string;
  class_name: string;
  grade: string;
  gender: string;
  dorm_building: string;
  dorm_room: string;
  gpa: number;
  attendance: number;
  tags: string[];
  risk_score: number;
}

export interface StudentListResult {
  total: number;
  page: number;
  size: number;
  students: StudentListItem[];
}

export interface StudentDetail extends StudentListItem {
  phone: string;
  status: string;
  talk_records: TalkRecordItem[];
}

// ============ 通知变材料 ============

export interface NoticeResult {
  notice_formal: string;
  notice_group: string;
  notice_parent: string;
  meeting_plan: string;
  signin_sheet: string;
  minutes_template: string;
}

export interface NoticeTask {
  id: number;
  theme: string;
  event_time: string;
  place: string;
  audience: string;
  status: string;
  result: NoticeResult | Record<string, never>;
  created_at: string;
}

// ============ 专家智能体 ============

export interface ExpertItem {
  id: string;
  name: string;
  category: string;
  desc: string;
  accent: string;
  temperature: number;
  prompt_file: string;
  platform_bot_id: string;
  sort: number;
  samples: string[];
  trigger_words: string[];
  boundary: string;
}

export interface ExpertCategory {
  id: string;
  name: string;
}

export interface ExpertSessionItem {
  id: number;
  expert_id: string;
  title: string;
  updated_at: string;
  created_at?: string;
  messages?: { role: string; content: string }[];
}

export interface ExpertsResult {
  categories: ExpertCategory[];
  experts: ExpertItem[];
  sessions: ExpertSessionItem[];
}

export interface ExpertCitation {
  index: number;
  doc_name: string;
  kb_type: string;
  chunk_text: string;
  distance: number | null;
}

// ============ 事务审批 ============

export interface ApprovalItem {
  id: number;
  type: string;
  type_label: string;
  type_color: string;
  title: string;
  applicant_name: string;
  applicant_student_id: string;
  content: string;
  attachments: string[];
  status: string;
  opinion: string;
  risk_flags: string[];
  created_at: string;
}

export interface ApprovalListResult {
  total: number;
  page: number;
  items: ApprovalItem[];
}

export interface ApprovalDetail extends ApprovalItem {
  student: {
    name: string;
    class_name: string;
    gpa: number;
    attendance: number;
    tags: string[];
    risk_score: number;
  } | null;
  resolved_at: string;
}

// ============ 查寝考勤 ============

export interface DormRoom {
  id: number;
  room: string;
  members: string[];
  status: string; // unchecked / normal / abnormal
  abnormal_type: string;
  note: string;
}

export interface DormGridResult {
  buildings: Record<string, Record<string, DormRoom[]>>;
  today: string;
}

export interface DormAnomaly {
  id: number;
  dorm_id: number;
  building: string;
  room: string;
  abnormal_type: string;
  note: string;
  members: string[];
}
