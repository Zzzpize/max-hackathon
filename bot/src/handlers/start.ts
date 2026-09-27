import type { Context } from "@maxhub/max-bot-api";
import { kb, openMiniappButton } from "../max.js";
import { resetState } from "../state.js";

export async function handleStart(ctx: Context): Promise<void> {
  const userId = ctx.message?.sender?.user_id ?? ctx.user?.user_id;
  if (userId) resetState(userId);

  const text =
    "Привет! Я помогу проверить контрольные работы класса.\n\n" +
    "Как это работает:\n" +
    "1. Открой мини-приложение и создай контрольную с заданиями и эталонами.\n" +
    "2. Отправь мне фото работы одного ученика.\n" +
    "3. Я распознаю ответы и подготовлю результат.\n" +
    "4. В мини-приложении ты подтвердишь или поправишь оценку одним свайпом.";

  await ctx.reply(text, {
    attachments: [
      kb.inlineKeyboard([[openMiniappButton("Открыть проверку")]]),
    ],
  });
}
