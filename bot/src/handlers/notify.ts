import { bot, kb, openMiniappButton } from "../max.js";

export async function notifyChecked(
  chatId: number,
  submissionId: string
): Promise<void> {
  await bot.api.sendMessageToChat(chatId, "Работа готова к проверке.", {
    attachments: [
      kb.inlineKeyboard([
        [openMiniappButton("Открыть", `submission:${submissionId}`)],
      ]),
    ],
  });
}
