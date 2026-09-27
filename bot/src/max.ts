import axios from "axios";
import { config } from "./config.js";

// TODO(frontend/MAX): заменить на официальный SDK / клиента MAX Bot API,
// как только организаторы пришлют документацию.
// Пока используется низкоуровневая обёртка над HTTPS-эндпоинтом.

const max = axios.create({
  baseURL: config.maxApiBase,
  timeout: 15_000,
  params: { access_token: config.maxBotToken },
});

export type MaxUpdate = {
  update_type: string;
  message?: {
    body?: { text?: string; attachments?: unknown[] };
    sender?: { user_id: number };
    recipient?: { chat_id?: number; user_id?: number };
  };
  callback?: {
    payload?: string;
    user?: { user_id: number };
    message?: { recipient?: { chat_id?: number } };
  };
};

export async function sendMessage(chatId: number, text: string, extra: Record<string, unknown> = {}) {
  return max.post("/messages", { text, ...extra }, { params: { chat_id: chatId } });
}

export async function sendMiniappButton(chatId: number, text: string, url: string, label = "Открыть проверку") {
  return sendMessage(chatId, text, {
    attachments: [
      {
        type: "inline_keyboard",
        payload: {
          buttons: [[{ type: "open_app", text: label, url }]],
        },
      },
    ],
  });
}

export async function downloadAttachment(url: string): Promise<Buffer> {
  const { data } = await axios.get<ArrayBuffer>(url, { responseType: "arraybuffer" });
  return Buffer.from(data);
}
