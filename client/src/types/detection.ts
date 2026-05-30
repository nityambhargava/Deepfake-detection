export type Classification = "REAL" | "FAKE" | "AI_GENERATED";

export interface ProbeScore {
  probe: string; score: number; score_pct: number;
  weight: number; description: string;
}

export interface AlteredRegion {
  region_id: number; x: number; y: number;
  width: number; height: number; area_px: number; confidence: number;
}

export interface DetectionResult {
  classification: Classification;
  fakeness_percentage: number;
  verdict_summary: string;
  probe_scores: ProbeScore[];
  altered_regions: AlteredRegion[];
  highlighted_image_url: string | null;
  metadata_exif: Record<string, string>;
}

export type AppState =
  | { phase: "idle" }
  | { phase: "uploading" }
  | { phase: "analysing" }
  | { phase: "result"; result: DetectionResult; previewUrl: string }
  | { phase: "error"; message: string };

export const CLASS_META: Record<Classification, {
  label: string; color: string; bg: string; glow: string; ring: string;
}> = {
  REAL:         { label: "REAL",         color: "text-green",  bg: "bg-green/10",  glow: "shadow-glow-green",  ring: "ring-green/40"  },
  FAKE:         { label: "MANIPULATED",  color: "text-amber",  bg: "bg-amber/10",  glow: "shadow-glow-amber",  ring: "ring-amber/40"  },
  AI_GENERATED: { label: "AI GENERATED", color: "text-purple", bg: "bg-purple/10", glow: "shadow-glow-purple", ring: "ring-purple/40" },
};

export const PROBE_LABELS: Record<string, string> = {
  ELA: "Error Level", Frequency: "Frequency", NoiseConsistency: "Noise",
  JPEGGhost: "JPEG Ghost", Metadata: "Metadata", ColourGradient: "Colour/Grad",
};
