type Stage = "idle" | "awaiting_work" | "awaiting_student" | "ready";

export type DialogState = {
  workId: string | null;
  studentId: string | null;
  stage: Stage;
  updatedAt: number;
};

const TTL_MS = 30 * 60 * 1000;
const store = new Map<number, DialogState>();

export function getState(userId: number): DialogState {
  const existing = store.get(userId);
  if (existing && Date.now() - existing.updatedAt < TTL_MS) {
    return existing;
  }
  const fresh: DialogState = {
    workId: null,
    studentId: null,
    stage: "idle",
    updatedAt: Date.now(),
  };
  store.set(userId, fresh);
  return fresh;
}

export function updateState(userId: number, patch: Partial<DialogState>): DialogState {
  const state = getState(userId);
  const next = { ...state, ...patch, updatedAt: Date.now() };
  store.set(userId, next);
  return next;
}

export function resetState(userId: number): void {
  store.delete(userId);
}
