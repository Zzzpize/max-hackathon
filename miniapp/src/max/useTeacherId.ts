import { useMemo } from "react";
import { maxBridge } from "./bridge";

export function useTeacherId(): string {
  return useMemo(() => {
    const user = maxBridge.getUser();
    return user ? String(user.id) : "teacher-stub";
  }, []);
}
