export type MaxPlatform = "ios" | "android" | "desktop" | "web" | "unknown";

export type MaxUser = {
  id: number;
  first_name?: string;
  last_name?: string;
  username?: string;
};

type WebAppApi = {
  initData?: string;
  initDataUnsafe?: {
    user?: MaxUser;
    start_param?: string;
    auth_date?: number;
    hash?: string;
  };
  platform?: MaxPlatform;
  version?: string;
  deviceName?: string;
  BackButton?: {
    show?: () => void;
    hide?: () => void;
    onClick?: (cb: () => void) => void;
  };
  HapticFeedback?: {
    impactOccurred?: (style: "light" | "medium" | "heavy") => void;
    notificationOccurred?: (type: "success" | "error" | "warning") => void;
  };
  enableClosingConfirmation?: () => void;
  openLink?: (url: string) => void;
  DeviceStorage?: {
    setItem?: (k: string, v: string) => void;
    getItem?: (k: string) => string | null;
  };
};

const webApp: WebAppApi | undefined = (
  globalThis as unknown as { WebApp?: WebAppApi }
).WebApp;

export const maxBridge = {
  isAvailable: Boolean(webApp),

  getUser(): MaxUser | null {
    return webApp?.initDataUnsafe?.user ?? null;
  },

  getStartParam(): string | null {
    return webApp?.initDataUnsafe?.start_param ?? null;
  },

  getInitData(): string {
    return webApp?.initData ?? "";
  },

  getPlatform(): MaxPlatform {
    return webApp?.platform ?? "unknown";
  },

  hapticImpact(style: "light" | "medium" | "heavy" = "light"): void {
    webApp?.HapticFeedback?.impactOccurred?.(style);
  },

  hapticNotify(type: "success" | "error" | "warning"): void {
    webApp?.HapticFeedback?.notificationOccurred?.(type);
  },

  backButton: {
    show(): void {
      webApp?.BackButton?.show?.();
    },
    hide(): void {
      webApp?.BackButton?.hide?.();
    },
    /**
     * MAX WebView (как и Telegram) регистрирует onClick аддитивно: каждый
     * повторный вызов добавляет ещё один слушатель, старые не снимаются.
     * Поэтому регистрируем ровно один раз, а конкретный колбэк подменяем
     * через замыкание над переменной. Идемпотентно.
     */
    setHandler(cb: () => void): void {
      currentBackHandler = cb;
      if (!backHandlerBound) {
        webApp?.BackButton?.onClick?.(() => currentBackHandler?.());
        backHandlerBound = true;
      }
    },
  },
};

let currentBackHandler: (() => void) | null = null;
let backHandlerBound = false;
