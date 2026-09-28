import type { Context } from "@maxhub/max-bot-api";
import { kb, openMiniappButton } from "../max.js";

export async function handleStart(ctx: Context): Promise<void> {
  const text =
    "Привет! Я помогу проверить контрольные работы класса.\n\n" +
    "Как это работает:\n" +
    "1. Открой мини-приложение и создай контрольную с заданиями и эталонами.\n" +
    "2. Добавь учеников класса.\n" +
    "3. Выбери работу и ученика - здесь через /work и /student или в мини-приложении.\n" +
    "4. Отправь фото прямо в чат - или загрузи через мини-приложение.\n" +
    "5. В мини-приложении подтверди или поправь оценку одним свайпом.";

  await ctx.reply(text, {
    attachments: [
      kb.inlineKeyboard([[openMiniappButton("Открыть мини-приложение")]]),
    ],
  });
}
