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

/**
 * Скачать файл по авторизованному эндпойнту. Обычный <a href> не передаёт
 * X-Init-Data / Bearer, поэтому серверный export возвращает 401. Здесь мы
 * дёргаем fetch с auth-заголовками, получаем blob и триггерим скачивание.
 */
export async function downloadAuthorized(
  path: string,
  suggestedFilename: string
): Promise<void> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { ...authHeaders() },
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = suggestedFilename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
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
  student_work?: string[];
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

export type RoadmapSegment = {
  index: number;
  weeks: string;
  topic: string;
  objectives: string;
  hours: number;
  materials_hint?: string;
};

export type Roadmap = {
  id: string;
  teacher_id: string;
  title: string;
  subject: string;
  grade: number;
  prompt: string;
  content: { segments: RoadmapSegment[] };
  created_at: string;
  updated_at: string;
};

export type RoadmapCreate = {
  title?: string;
  subject: string;
  grade: number;
  prompt: string;
};

export type RoadmapPatch = {
  title?: string;
  content?: { segments: RoadmapSegment[] };
};

export type HomeworkTask = {
  index: number;
  statement: string;
  expected_answer: string;
  difficulty?: "easy" | "medium" | "hard";
};

export type Homework = {
  id: string;
  teacher_id: string;
  title: string;
  subject: string;
  grade: number;
  topic: string;
  prompt: string;
  tasks: HomeworkTask[];
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type HomeworkCreate = {
  title?: string;
  subject: string;
  grade: number;
  topic: string;
  n_tasks: number;
  prompt: string;
};

export type HomeworkPatch = {
  title?: string;
  notes?: string | null;
  tasks?: HomeworkTask[];
};

export type ExtractedReference = {
  title: string;
  subject: string | null;
  grade: number | null;
  tasks: {
    index: string;
    statement: string;
    expected_answer: string;
    confidence: number;
  }[];
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

  deleteWork: async (workId: string): Promise<void> => {
    const res = await fetch(`${API_BASE}/works/${workId}`, {
      method: "DELETE",
      headers: { ...authHeaders() },
    });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  },

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

  extractReference: async (file: File): Promise<ExtractedReference> => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_BASE}/works/extract-reference`, {
      method: "POST",
      body: form,
      headers: { ...authHeaders() },
    });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    return res.json();
  },

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

  listRoadmaps: (limit = 50, offset = 0) =>
    request<Roadmap[]>(`/roadmaps?limit=${limit}&offset=${offset}`),

  createRoadmap: (payload: RoadmapCreate) =>
    request<Roadmap>(`/roadmaps`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getRoadmap: (id: string) => request<Roadmap>(`/roadmaps/${id}`),

  patchRoadmap: (id: string, payload: RoadmapPatch) =>
    request<Roadmap>(`/roadmaps/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  regenerateRoadmapSegment: (
    id: string,
    index: number,
    refine_prompt?: string
  ) =>
    request<Roadmap>(`/roadmaps/${id}/segments/${index}`, {
      method: "PATCH",
      body: JSON.stringify({ refine_prompt: refine_prompt ?? "" }),
    }),

  deleteRoadmap: async (id: string): Promise<void> => {
    const res = await fetch(`${API_BASE}/roadmaps/${id}`, {
      method: "DELETE",
      headers: { ...authHeaders() },
    });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  },

  roadmapExportUrl: (id: string, format: "txt" | "pdf" = "txt"): string =>
    `${API_BASE}/roadmaps/${id}/export?format=${format}`,

  listHomework: (params?: {
    limit?: number;
    offset?: number;
    subject?: string;
    grade?: number;
    topic?: string;
  }) => {
    const q = new URLSearchParams();
    q.set("limit", String(params?.limit ?? 50));
    q.set("offset", String(params?.offset ?? 0));
    if (params?.subject) q.set("subject", params.subject);
    if (params?.grade) q.set("grade", String(params.grade));
    if (params?.topic) q.set("topic", params.topic);
    return request<Homework[]>(`/homework?${q.toString()}`);
  },

  createHomework: (payload: HomeworkCreate) =>
    request<Homework>(`/homework`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getHomework: (id: string) => request<Homework>(`/homework/${id}`),

  patchHomework: (id: string, payload: HomeworkPatch) =>
    request<Homework>(`/homework/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  regenerateHomework: (id: string, extra_prompt?: string) =>
    request<Homework>(`/homework/${id}/regenerate`, {
      method: "POST",
      body: JSON.stringify({ extra_prompt: extra_prompt ?? "" }),
    }),

  deleteHomework: async (id: string): Promise<void> => {
    const res = await fetch(`${API_BASE}/homework/${id}`, {
      method: "DELETE",
      headers: { ...authHeaders() },
    });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  },

  homeworkExportUrl: (id: string, format: "txt" | "pdf" = "txt"): string =>
    `${API_BASE}/homework/${id}/export?format=${format}`,

  submitBatch: async (params: {
    workId: string;
    students: { studentId: string; photos: File[] }[];
    concurrency?: number;
    onProgress?: (done: number, total: number) => void;
  }): Promise<{ studentId: string; result: Submission | Error }[]> => {
    const { workId, students, concurrency = 5, onProgress } = params;
    const total = students.length;
    let done = 0;
    const results: { studentId: string; result: Submission | Error }[] = [];

    const queue = [...students];
    const workers = Array.from({ length: Math.min(concurrency, total) }, async () => {
      while (queue.length > 0) {
        const item = queue.shift();
        if (!item) break;
        try {
          const sub = await api.submitWork({
            workId,
            studentId: item.studentId,
            photos: item.photos,
          });
          results.push({ studentId: item.studentId, result: sub });
        } catch (e) {
          results.push({
            studentId: item.studentId,
            result: e instanceof Error ? e : new Error(String(e)),
          });
        }
        done++;
        onProgress?.(done, total);
      }
    });

    await Promise.all(workers);
    return results;
  },
};
