import axios from "axios";
import FormData from "form-data";
import { config } from "./config.js";

const http = axios.create({
  baseURL: config.backendUrl,
  timeout: 60_000,
});

export type SubmissionOut = {
  id: string;
  work_id: string;
  student_id: string;
  status: "pending" | "checked" | "confirmed";
  created_at: string;
  photos: string[];
};

export async function createSubmission(params: {
  workId: string;
  studentId: string;
  photos: { buffer: Buffer; filename: string }[];
}): Promise<SubmissionOut> {
  const form = new FormData();
  form.append("work_id", params.workId);
  form.append("student_id", params.studentId);
  for (const p of params.photos) {
    form.append("photos", p.buffer, { filename: p.filename });
  }
  const { data } = await http.post<SubmissionOut>("/submissions", form, {
    headers: form.getHeaders(),
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
