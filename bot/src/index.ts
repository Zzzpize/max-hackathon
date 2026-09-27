import type { Context, NextFn } from "@maxhub/max-bot-api";
import { config } from "./config.js";
import { handlePhoto } from "./handlers/photo.js";
import { handleStart } from "./handlers/start.js";
import { notifyChecked } from "./handlers/notify.js";
import { bot } from "./max.js";

bot.on("bot_started", handleStart);
bot.command("start", handleStart);

bot.on("message_created", async (ctx: Context, next: NextFn) => {
  const handled = await handlePhoto(ctx);
  if (!handled) return next();
});

bot.on("message_created", async (ctx: Context) => {
  const text = ctx.message?.body?.text?.trim();
  if (!text) return;
  if (text.startsWith("/")) return;
  await ctx.reply(
    "Пришли фото контрольной работы одного ученика. Одно или несколько снимков подряд."
  );
});

bot.catch((err: unknown) => {
  console.error("[bot] unhandled error", err);
});

if (config.webhookDomain) {
  bot.start({
    mode: "webhook",
    options: {
      domain: config.webhookDomain,
      port: config.port,
      secret: config.webhookSecret || undefined,
      allowedUpdates: ["message_created", "bot_started", "message_callback"],
    },
  });
  console.log(`[bot] webhook mode at ${config.webhookDomain}`);
} else {
  void bot.start();
  console.log("[bot] long polling mode");
}

// Внутренний HTTP-канал backend → bot для пуша учителю после проверки.
// MVP: примитивный http-сервер на том же порту не нужен при polling.
// TODO(frontend/MAX): вынести notifyChecked в отдельный HTTP endpoint
// когда бэкенд начнёт его вызывать. Пока экспортируем, чтобы не терять.
export { notifyChecked };
