import { config } from "../config.js";
import { sendMiniappButton, type MaxUpdate } from "../max.js";

export async function handleStart(update: MaxUpdate): Promise<void> {
  const chatId = update.message?.recipient?.chat_id ?? update.message?.sender?.user_id;
  if (!chatId) return;

  const text =
    "Привет! Я помогу проверить контрольные работы класса.\n" +
    "Отправь фото работы одного ученика — я распознаю ответы, " +
    "сверю с эталоном и покажу результат в мини-приложении.";

  await sendMiniappButton(chatId, text, config.miniappUrl || "https://example.com");
}
