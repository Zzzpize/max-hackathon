import { createServer, IncomingMessage, ServerResponse } from "node:http";
import { bot, kb, openMiniappButton } from "./max.js";

const INTERNAL_PORT = 3001;

type NotifyBody = {
  teacher_id: string | number;
  submission_id: string;
  event?: "submission_checked";
};

async function readJson(req: IncomingMessage): Promise<unknown> {
  const chunks: Buffer[] = [];
  for await (const chunk of req) chunks.push(chunk as Buffer);
  const raw = Buffer.concat(chunks).toString("utf-8");
  if (!raw) return {};
  return JSON.parse(raw);
}

function json(res: ServerResponse, status: number, body: unknown): void {
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json");
  res.end(JSON.stringify(body));
}

async function handleNotify(body: NotifyBody): Promise<void> {
  const teacherId = Number(body.teacher_id);
  if (!Number.isFinite(teacherId)) throw new Error("bad teacher_id");
  if (!body.submission_id) throw new Error("submission_id required");

  const text = "Работа готова к проверке.";
  const extra = {
    attachments: [
      kb.inlineKeyboard([
        [openMiniappButton("Открыть результат", `submission_${body.submission_id}`)],
      ]),
    ],
  };

  try {
    await bot.api.sendMessageToChat(teacherId, text, extra);
  } catch (err) {
    console.warn("[internal] sendMessageToChat failed, trying sendMessageToUser", err);
    await bot.api.sendMessageToUser(teacherId, text, extra);
  }
}

export function startInternalServer(): void {
  const server = createServer(async (req, res) => {
    try {
      if (req.method === "GET" && req.url === "/internal/health") {
        return json(res, 200, { status: "ok" });
      }
      if (req.method === "POST" && req.url === "/internal/notify") {
        const body = (await readJson(req)) as NotifyBody;
        await handleNotify(body);
        return json(res, 200, { ok: true });
      }
      return json(res, 404, { detail: "not found" });
    } catch (err) {
      console.error("[internal]", err);
      return json(res, 500, { detail: String(err) });
    }
  });

  server.listen(INTERNAL_PORT, "0.0.0.0", () => {
    console.log(`[bot] internal server on :${INTERNAL_PORT}`);
  });
}
