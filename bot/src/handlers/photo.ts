import type { Context } from "@maxhub/max-bot-api";
import { createSubmission, downloadPhoto, getState } from "../api.js";
import { kb, openMiniappButton } from "../max.js";

export async function handlePhoto(ctx: Context): Promise<boolean> {
  const attachments = ctx.message?.body?.attachments ?? [];
  const images = attachments.filter(
    (a: { type?: string }) => a.type === "image"
  );
  if (images.length === 0) return false;

  const userId = ctx.message?.sender?.user_id;
  if (!userId) return false;

  let state;
  try {
    state = await getState(String(userId));
  } catch {
    await ctx.reply("Не удалось прочитать текущий выбор. Попробуй ещё раз.");
    return true;
  }

  if (!state.current_work_id || !state.current_student_id) {
    await ctx.reply(
      "Сначала выбери работу (/work) и ученика (/student) - или открой мини-приложение.",
      { attachments: [kb.inlineKeyboard([[openMiniappButton("Открыть")]])] }
    );
    return true;
  }

  const photos: { buffer: Buffer; filename: string }[] = [];
  for (const [idx, att] of images.entries()) {
    const url = (att as { payload?: { url?: string } }).payload?.url;
    if (!url) continue;
    const buffer = await downloadPhoto(url);
    photos.push({ buffer, filename: `page-${idx}.jpg` });
  }

  if (photos.length === 0) {
    await ctx.reply("Не смог скачать фото. Попробуй ещё раз.");
    return true;
  }

  try {
    const submission = await createSubmission({
      teacherId: String(userId),
      workId: state.current_work_id,
      studentId: state.current_student_id,
      photos,
    });

    await ctx.reply(
      `Принял ${photos.length} фото, работа №${submission.id.slice(0, 8)} на проверке. ` +
        "Обычно занимает 30–60 секунд.",
      {
        attachments: [
          kb.inlineKeyboard([
            [openMiniappButton("Открыть результат", `submission_${submission.id}`)],
          ]),
        ],
      }
    );
  } catch (err) {
    await ctx.reply("Не удалось отправить работу на проверку. Попробуй ещё раз.");
    throw err;
  }

  return true;
}
