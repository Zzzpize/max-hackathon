const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init.headers ?? {}) },
    ...init,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

function qs(params: Record<string, string | undefined>): string {
  const filtered = Object.entries(params).filter(
    ([, v]) => v !== undefined && v !== ""
  ) as [string, string][];
  return filtered.length ? `?${new URLSearchParams(filtered).toString()}` : "";
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

export type Student = {
  id: string;
  teacher_id: string;
  class_id: string;
  display_name: string;
  grade: number;
  created_at: string;
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
  listWorks: (teacherId: string) =>
    request<WorkTemplate[]>(`/works${qs({ teacher_id: teacherId })}`),

  createWork: (payload: Omit<WorkTemplate, "id" | "created_at">) =>
    request<WorkTemplate>(`/works`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getWork: (workId: string, teacherId: string) =>
    request<WorkTemplate>(`/works/${workId}${qs({ teacher_id: teacherId })}`),

  listStudents: (teacherId: string, classId?: string) =>
    request<Student[]>(
      `/students${qs({ teacher_id: teacherId, class_id: classId })}`
    ),

  createStudent: (payload: Omit<Student, "id" | "created_at">) =>
    request<Student>(`/students`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  listSubmissions: (teacherId: string, status?: string) =>
    request<Submission[]>(
      `/submissions${qs({ teacher_id: teacherId, status })}`
    ),

  getSubmission: (id: string, teacherId: string) =>
    request<SubmissionResult>(
      `/submissions/${id}${qs({ teacher_id: teacherId })}`
    ),

  reviewSubmission: (
    id: string,
    teacherId: string,
    per_task: { task_index: number; is_correct: boolean; comment?: string }[]
  ) =>
    request<{ status: string }>(
      `/submissions/${id}/review${qs({ teacher_id: teacherId })}`,
      {
        method: "PATCH",
        body: JSON.stringify({ per_task }),
      }
    ),

  getStudentProfile: (id: string, teacherId: string) =>
    request<StudentProfile>(
      `/students/${id}/profile${qs({ teacher_id: teacherId })}`
    ),

  getClassDashboard: (classId: string, teacherId: string) =>
    request<ClassDashboard>(
      `/classes/${classId}/dashboard${qs({ teacher_id: teacherId })}`
    ),

  getState: (teacherId: string) =>
    request<TeacherState>(`/teachers/${teacherId}/state`),

  setState: (
    teacherId: string,
    patch: { current_work_id?: string | null; current_student_id?: string | null }
  ) =>
    request<TeacherState>(`/teachers/${teacherId}/state`, {
      method: "PUT",
      body: JSON.stringify(patch),
    }),

  submitWork: async (params: {
    teacherId: string;
    workId: string;
    studentId: string;
    photos: File[];
  }): Promise<Submission> => {
    const form = new FormData();
    form.append("teacher_id", params.teacherId);
    form.append("work_id", params.workId);
    form.append("student_id", params.studentId);
    for (const photo of params.photos) form.append("photos", photo);
    const res = await fetch(`${API_BASE}/submissions`, {
      method: "POST",
      body: form,
    });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    return res.json();
  },
};
