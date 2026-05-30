import clsx from "clsx";
import type { Classification } from "@/types/detection";
import { CLASS_META } from "@/types/detection";

export default function ClassificationBadge({ classification, large }: { classification: Classification; large?: boolean }) {
  const m = CLASS_META[classification];
  return (
    <span className={clsx("inline-flex items-center gap-2 font-mono font-semibold rounded-lg border ring-1 ring-inset", m.color, m.bg, m.ring, large ? "text-lg px-4 py-2" : "text-xs px-2.5 py-1")}>
      <span className={clsx("inline-block rounded-full", large ? "w-2.5 h-2.5" : "w-1.5 h-1.5",
        classification === "REAL"         && "bg-green",
        classification === "FAKE"         && "bg-amber",
        classification === "AI_GENERATED" && "bg-purple")} />
      {m.label}
    </span>
  );
}
