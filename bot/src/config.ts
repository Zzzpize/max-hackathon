export const config = {
  maxBotToken: process.env.MAX_BOT_TOKEN ?? "",
  maxApiBase: process.env.MAX_API_BASE ?? "https://botapi.max.ru",
  backendUrl: process.env.BACKEND_URL ?? "http://backend:8000",
  miniappUrl: process.env.MINIAPP_PUBLIC_URL ?? "",
  port: Number(process.env.BOT_PORT ?? 3000),
};
