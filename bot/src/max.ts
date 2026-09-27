import { Bot, Keyboard } from "@maxhub/max-bot-api";
import { config } from "./config.js";

export const bot = new Bot(config.botToken);

export function openMiniappButton(label: string, payload?: string) {
  return Keyboard.button.openApp(label, config.botUsername, undefined, payload);
}

export const kb = Keyboard;
