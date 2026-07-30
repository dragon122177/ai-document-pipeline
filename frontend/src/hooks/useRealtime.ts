import { useEffect } from "react";
import { streamEvents } from "../api";

export function useRealtime(onUpdate: () => void): void {
  useEffect(() => {
    return streamEvents(({ type }) => {
      if (
        type === "job.progress" ||
        type === "document.updated" ||
        type === "review.decided"
      ) {
        onUpdate();
      }
    });
  }, [onUpdate]);
}
