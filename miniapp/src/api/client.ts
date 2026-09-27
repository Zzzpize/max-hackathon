const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init.headers ?? {}) },
    ...init,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

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
  reasoning_graph: { step: string; ok: boolean }[];
  photo_boxes: { photo_index: number; x: number; y: number; w: number; h: number }[];
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

export const api = {
  listSubmissions: (teacherId: string, status = "checked") =>
    request<Submission[]>(
      `/submissions?teacher_id=${encodeURIComponent(teacherId)}&status=${status}`
    ),
  getSubmission: (id: string) => request<SubmissionResult>(`/submissions/${id}`),
  reviewSubmission: (
    id: string,
    per_task: { task_index: number; is_correct: boolean; comment?: string }[]
  ) =>
    request<{ status: string }>(`/submissions/${id}/review`, {
      method: "PATCH",
      body: JSON.stringify({ per_task }),
    }),
  getStudentProfile: (id: string) => request<StudentProfile>(`/students/${id}/profile`),
  getClassDashboard: (classId: string) =>
    request<unknown>(`/classes/${classId}/dashboard`),
};
