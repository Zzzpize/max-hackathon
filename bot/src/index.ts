import type { Context, NextFn } from "@maxhub/max-bot-api";
import { config } from "./config.js";
import { handleOpenTab, handleStart } from "./handlers/start.js";
import { handlePhoto } from "./handlers/photo.js";
import { notifyChecked } from "./handlers/notify.js";
import {
  handleSelectStudent,
  handleSelectWork,
  handleStudentPicked,
  handleWorkPicked,
} from "./handlers/select.js";
import { startInternalServer } from "./internal.js";
import { bot } from "./max.js";

bot.api
  .setMyCommands([
    { name: "start", description: "О боте" },
    { name: "plan", description: "Открыть учебные планы" },
    { name: "homework", description: "Открыть домашки" },
    { name: "check", description: "Открыть проверку контрольных" },
    { name: "work", description: "Выбрать работу для проверки" },
    { name: "student", description: "Выбрать ученика" },
  ])
  .catch((err) => console.error("[bot] setMyCommands failed", err));

bot.on("bot_started", handleStart);
bot.command("start", handleStart);
bot.command("plan", (ctx) => handleOpenTab(ctx, "roadmap", "📋 Планы"));
bot.command("homework", (ctx) => handleOpenTab(ctx, "homework", "📝 Домашки"));
bot.command("check", (ctx) => handleOpenTab(ctx, "check", "✅ Проверка"));
bot.command("work", handleSelectWork);
bot.command("student", handleSelectStudent);

bot.action(/^work:(.+)$/, handleWorkPicked);
bot.action(/^student:(.+)$/, handleStudentPicked);

bot.on("message_created", async (ctx: Context, next: NextFn) => {
  const handled = await handlePhoto(ctx);
  if (!handled) return next();
});

bot.on("message_created", async (ctx: Context) => {
  const text = ctx.message?.body?.text?.trim();
  if (!text) return;
  if (text.startsWith("/")) return;
  await ctx.reply(
    "Пришли фото контрольной или открой мини-приложение через /start, " +
      "/plan, /homework или /check."
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

startInternalServer();

export { notifyChecked };
