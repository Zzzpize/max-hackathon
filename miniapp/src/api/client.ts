import { maxBridge } from "../max/bridge";

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

function authHeaders(): HeadersInit {
  const initData = maxBridge.getInitData();
  return initData ? { "X-Init-Data": initData } : {};
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(init.headers ?? {}),
    },
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export function photoUrl(relativePath: string): string {
  const base = API_BASE.replace(/\/api$/, "");
  return `${base}/storage/${relativePath}`;
}

export type WorkTemplate = {
  id: string;
  teacher_id: string;
  title: string;
  subject: string;
  grade: number;
  tasks: {
    index: number;
    statement: string;
    expected_answer: string;
    max_points?: number;
  }[];
  created_at: string;
};

export type WorkTemplateCreate = Omit<
  WorkTemplate,
  "id" | "teacher_id" | "created_at"
>;

export type Student = {
  id: string;
  teacher_id: string;
  class_id: string;
  display_name: string;
  grade: number;
  created_at: string;
};

export type StudentCreate = {
  class_id: string;
  display_name: string;
  grade: number;
};

export type Submission = {
  id: string;
  work_id: string;
  student_id: string;
  status: "pending" | "checked" | "confirmed";
  created_at: string;
  photos: string[];
};

export type TaskCheck = {
  task_index: number;
  student_answer: string;
  expected_answer: string;
  is_correct: boolean;
  confidence: number;
  explanation: string;
  error_type?:
    | "вычислительная"
    | "методологическая"
    | "невнимательность"
    | "не распознано"
    | null;
  reasoning_graph: { step: string; ok: boolean }[];
  photo_boxes: {
    photo_index: number;
    x: number;
    y: number;
    w: number;
    h: number;
  }[];
  teacher_verdict: { is_correct: boolean; comment: string } | null;
};

export type SubmissionResult = Submission & {
  per_task: TaskCheck[];
  total_score: number;
  confidence: number;
};

export type StudentProfile = {
  student_id: string;
  submissions_count: number;
  avg_score: number;
  weak_topics: { topic: string; error_rate: number }[];
  recurring_mistakes: string[];
  trend: "improving" | "stable" | "regressing";
};

export type ClassDashboard = {
  class_id: string;
  students_count: number;
  avg_score: number;
  weak_topics: { topic: string; error_rate: number }[];
  students_needing_help: { student_id: string; reason: string }[];
};

export type TeacherState = {
  teacher_id: string;
  current_work_id: string | null;
  current_student_id: string | null;
  updated_at: string | null;
};

export const api = {
  listWorks: (limit = 50, offset = 0) =>
    request<WorkTemplate[]>(`/works?limit=${limit}&offset=${offset}`),

  createWork: (payload: WorkTemplateCreate) =>
    request<WorkTemplate>(`/works`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  generateWork: (topic: string, grade: number, n_tasks: number) =>
    request<WorkTemplate>(`/works/generate`, {
      method: "POST",
      body: JSON.stringify({ topic, grade, n_tasks }),
    }),

  getWork: (workId: string) => request<WorkTemplate>(`/works/${workId}`),

  listStudents: () => request<Student[]>(`/students`),

  createStudent: (payload: StudentCreate) =>
    request<Student>(`/students`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  deleteStudent: async (studentId: string): Promise<void> => {
    const res = await fetch(`${API_BASE}/students/${studentId}`, {
      method: "DELETE",
      headers: { ...authHeaders() },
    });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  },

  listSubmissions: (status?: string) =>
    request<Submission[]>(
      `/submissions${status ? `?status=${status}` : ""}`
    ),

  getSubmission: (id: string) =>
    request<SubmissionResult>(`/submissions/${id}`),

  reviewSubmission: (
    id: string,
    per_task: { task_index: number; is_correct: boolean; comment?: string }[]
  ) =>
    request<{ status: string }>(`/submissions/${id}/review`, {
      method: "PATCH",
      body: JSON.stringify({ per_task }),
    }),

  getStudentProfile: (id: string) =>
    request<StudentProfile>(`/students/${id}/profile`),

  getClassDashboard: (classId: string) =>
    request<ClassDashboard>(`/classes/${classId}/dashboard`),

  getState: () => request<TeacherState>(`/teachers/me/state`),

  setState: (patch: {
    current_work_id?: string | null;
    current_student_id?: string | null;
  }) =>
    request<TeacherState>(`/teachers/me/state`, {
      method: "PUT",
      body: JSON.stringify(patch),
    }),

  submitWork: async (params: {
    workId: string;
    studentId: string;
    photos: File[];
  }): Promise<Submission> => {
    const form = new FormData();
    form.append("work_id", params.workId);
    form.append("student_id", params.studentId);
    for (const photo of params.photos) form.append("photos", photo);
    const res = await fetch(`${API_BASE}/submissions`, {
      method: "POST",
      body: form,
      headers: { ...authHeaders() },
    });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    return res.json();
  },
};
