import axios from "axios";
import FormData from "form-data";
import { config } from "./config.js";

const http = axios.create({
  baseURL: config.backendUrl,
  timeout: 60_000,
  headers: {
    Authorization: `Bearer ${config.botToken}`,
  },
});

function authHeaders(teacherId: string): Record<string, string> {
  return {
    Authorization: `Bearer ${config.botToken}`,
    "X-Teacher-Id": String(teacherId),
  };
}

export type SubmissionOut = {
  id: string;
  work_id: string;
  student_id: string;
  status: "pending" | "checked" | "confirmed";
  created_at: string;
  photos: string[];
};

export type WorkTemplate = {
  id: string;
  teacher_id: string;
  title: string;
  subject: string;
  grade: number;
  tasks: { index: number; statement: string; expected_answer: string }[];
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

export type TeacherState = {
  teacher_id: string;
  current_work_id: string | null;
  current_student_id: string | null;
  updated_at: string | null;
};

export async function createSubmission(params: {
  teacherId: string;
  workId: string;
  studentId: string;
  photos: { buffer: Buffer; filename: string; contentType?: string }[];
}): Promise<SubmissionOut> {
  const form = new FormData();
  form.append("work_id", params.workId);
  form.append("student_id", params.studentId);
  for (const p of params.photos) {
    form.append("photos", p.buffer, {
      filename: p.filename,
      contentType: p.contentType ?? "image/jpeg",
    });
  }
  const { data } = await http.post<SubmissionOut>("/submissions", form, {
    headers: { ...authHeaders(params.teacherId), ...form.getHeaders() },
  });
  return data;
}

export async function getState(teacherId: string): Promise<TeacherState> {
  const { data } = await http.get<TeacherState>(`/teachers/me/state`, {
    headers: authHeaders(teacherId),
  });
  return data;
}

export async function setState(
  teacherId: string,
  patch: { current_work_id?: string | null; current_student_id?: string | null }
): Promise<TeacherState> {
  const { data } = await http.put<TeacherState>(
    `/teachers/me/state`,
    patch,
    { headers: authHeaders(teacherId) }
  );
  return data;
}

export async function listWorks(teacherId: string): Promise<WorkTemplate[]> {
  const { data } = await http.get<WorkTemplate[]>(`/works`, {
    headers: authHeaders(teacherId),
  });
  return data;
}

export async function listStudents(teacherId: string): Promise<Student[]> {
  const { data } = await http.get<Student[]>(`/students`, {
    headers: authHeaders(teacherId),
  });
  return data;
}

export async function downloadPhoto(url: string): Promise<Buffer> {
  const { data } = await axios.get<ArrayBuffer>(url, {
    responseType: "arraybuffer",
    timeout: 30_000,
  });
  return Buffer.from(data);
}
