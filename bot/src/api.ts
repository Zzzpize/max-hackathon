import axios from "axios";
import FormData from "form-data";
import { config } from "./config.js";

const http = axios.create({
  baseURL: config.backendUrl,
  timeout: 30_000,
});

export async function createSubmission(params: {
  workId: string;
  studentId: string;
  photos: { buffer: Buffer; filename: string }[];
}): Promise<{ id: string }> {
  const form = new FormData();
  form.append("work_id", params.workId);
  form.append("student_id", params.studentId);
  for (const p of params.photos) {
    form.append("photos", p.buffer, { filename: p.filename });
  }
  const { data } = await http.post("/submissions", form, {
    headers: form.getHeaders(),
  });
  return data;
}

export async function listPending(teacherId: string) {
  const { data } = await http.get("/submissions", {
    params: { teacher_id: teacherId, status: "checked" },
  });
  return data;
}
