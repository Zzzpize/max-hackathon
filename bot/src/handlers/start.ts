import type { Context } from "@maxhub/max-bot-api";
import { kb, openMiniappButton } from "../max.js";

export async function handleStart(ctx: Context): Promise<void> {
  const text =
    "Привет! Я помощник учителя математики 1–4 класса. Умею три вещи:\n\n" +
    "📋 Планы — годовой учебный план по математике для класса\n" +
    "📝 Домашние задания — набор задач по теме с ответами\n" +
    "✅ Проверка — распознавание работ учеников по фото\n\n" +
    "Открой мини-приложение — там всё под рукой. " +
    "Или пришли фото контрольной сразу в чат.";

  await ctx.reply(text, {
    attachments: [
      kb.inlineKeyboard([[openMiniappButton("Открыть мини-приложение")]]),
    ],
  });
}

export async function handleOpenTab(
  ctx: Context,
  tab: "roadmap" | "homework" | "check",
  label: string
): Promise<void> {
  await ctx.reply(`Открываю: ${label}`, {
    attachments: [
      kb.inlineKeyboard([[openMiniappButton(label, `tab_${tab}`)]]),
    ],
  });
}
