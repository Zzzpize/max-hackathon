export const config = {
  botToken: process.env.MAX_BOT_TOKEN ?? "",
  botUsername: process.env.MAX_BOT_USERNAME ?? "",
  webhookDomain: process.env.MAX_WEBHOOK_DOMAIN ?? "",
  webhookSecret: process.env.MAX_WEBHOOK_SECRET ?? "",
  backendUrl: process.env.BACKEND_URL ?? "http://backend:8000",
  miniappUrl: process.env.MINIAPP_PUBLIC_URL ?? "",
  port: Number(process.env.BOT_PORT ?? 3000),
};

if (!config.botToken) {
  throw new Error("MAX_BOT_TOKEN is required");
}
