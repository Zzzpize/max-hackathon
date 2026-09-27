// Тонкая обёртка над MAX Bridge для мини-приложений.
// TODO(frontend/MAX): подключить официальный @vkontakte/max-bridge (или что
// организаторы пришлют) и пробросить нативные методы (haptics, close,
// getPlatform, sendMessageToChat).

type MaxPlatform = "ios" | "android" | "web" | "desktop" | "unknown";

type MaxBridgeStub = {
  ready: () => Promise<void>;
  getPlatform: () => Promise<MaxPlatform>;
  getUser: () => Promise<{ user_id: number; first_name?: string } | null>;
  close: () => Promise<void>;
};

function makeStub(): MaxBridgeStub {
  return {
    ready: async () => undefined,
    getPlatform: async () => "unknown",
    getUser: async () => null,
    close: async () => undefined,
  };
}

const globalBridge = (globalThis as unknown as { MaxBridge?: MaxBridgeStub }).MaxBridge;

export const maxBridge: MaxBridgeStub = globalBridge ?? makeStub();
