import { createSubmission } from "../api.js";
import { config } from "../config.js";
import { downloadAttachment, sendMessage, sendMiniappButton, type MaxUpdate } from "../max.js";

export async function handlePhoto(update: MaxUpdate): Promise<void> {
  const chatId = update.message?.recipient?.chat_id ?? update.message?.sender?.user_id;
  if (!chatId) return;

  const attachments = update.message?.body?.attachments ?? [];
  const photos: { buffer: Buffer; filename: string }[] = [];

  for (const [idx, att] of attachments.entries()) {
    // TODO(frontend/MAX): уточнить структуру attachment в MAX API из документации
    const url = (att as { payload?: { url?: string } }).payload?.url;
    if (!url) continue;
    const buffer = await downloadAttachment(url);
    photos.push({ buffer, filename: `page-${idx}.jpg` });
  }

  if (photos.length === 0) {
    await sendMessage(chatId, "Не увидел фото — попробуй ещё раз.");
    return;
  }

  // TODO(frontend/MAX): выбор work_id и student_id должен идти через
  // диалог с ботом или через мини-приложение до отправки фото.
  // Пока стаб — используем плейсхолдеры.
  const submission = await createSubmission({
    workId: "stub-work-id",
    studentId: "stub-student-id",
    photos,
  });

  const url = `${config.miniappUrl}?submission=${submission.id}`;
  await sendMiniappButton(chatId, "Работа принята на проверку.", url, "Открыть результат");
}
