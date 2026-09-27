import Fastify from "fastify";
import { config } from "./config.js";
import { handlePhoto } from "./handlers/photo.js";
import { handleStart } from "./handlers/start.js";
import type { MaxUpdate } from "./max.js";

const app = Fastify({ logger: true });

app.get("/health", async () => ({ status: "ok" }));

app.post("/webhook", async (req, reply) => {
  const update = req.body as MaxUpdate;
  try {
    if (update.update_type === "message_created") {
      const text = update.message?.body?.text?.trim() ?? "";
      const attachments = update.message?.body?.attachments ?? [];

      if (attachments.length > 0) {
        await handlePhoto(update);
      } else if (text.startsWith("/start")) {
        await handleStart(update);
      }
    }
    // TODO(frontend/MAX): расширить обработку — bot_started, callback, etc.
    return reply.send({ ok: true });
  } catch (err) {
    app.log.error({ err }, "webhook handler failed");
    return reply.status(500).send({ ok: false });
  }
});

app.listen({ port: config.port, host: "0.0.0.0" }).catch((err) => {
  app.log.error(err);
  process.exit(1);
});
