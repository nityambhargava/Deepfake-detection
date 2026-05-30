import type { DetectionResult } from "@/types/detection";
import ClassificationBadge from "./ClassificationBadge";
import FakenessGauge       from "./FakenessGauge";
import ProbeChart          from "./ProbeChart";
import ImageOverlay        from "./ImageOverlay";

interface Props { result: DetectionResult; previewUrl: string; onReset: () => void; }

const BORDER_COLOR: Record<string,string> = {
  REAL:"#00e5a0", FAKE:"#ffb020", AI_GENERATED:"#7b61ff"
};

export default function ResultPanel({ result, previewUrl, onReset }: Props) {
  const { classification, fakeness_percentage, verdict_summary, probe_scores, altered_regions, highlighted_image_url, metadata_exif } = result;
  const hasExif = Object.keys(metadata_exif).length > 0;

  return (
    <div className="flex flex-col gap-5" style={{animation:"fadeUp 0.4s ease forwards"}}>
      <div className="flex items-center justify-between">
        <ClassificationBadge classification={classification} large/>
        <button className="btn-ghost" onClick={onReset}>← Analyse another</button>
      </div>
      <div className="card border-l-2" style={{borderLeftColor:BORDER_COLOR[classification]}}>
        <p className="font-mono text-sm text-text leading-relaxed">{verdict_summary}</p>
      </div>
      <div className="grid md:grid-cols-[200px_1fr] gap-5">
        <div className="card flex flex-col items-center justify-center py-4">
          <FakenessGauge percentage={fakeness_percentage} classification={classification}/>
        </div>
        <ImageOverlay previewUrl={previewUrl} alteredRegions={altered_regions} highlightedUrl={highlighted_image_url} classification={classification}/>
      </div>
      <ProbeChart probes={probe_scores} classification={classification}/>
      {hasExif && (
        <div className="card">
          <p className="mono-label mb-3">EXIF metadata</p>
          <div className="grid sm:grid-cols-2 gap-x-8 gap-y-1.5">
            {Object.entries(metadata_exif).map(([k,v]) => (
              <div key={k} className="flex items-start gap-2">
                <span className="font-mono text-[11px] text-dim w-36 shrink-0">{k}</span>
                <span className="font-mono text-[11px] text-text break-all">{v}</span>
              </div>
            ))}
          </div>
        </div>
      )}
      {highlighted_image_url && (
        <div className="flex justify-end">
          <a href={highlighted_image_url} download className="btn-ghost text-sm">↓ Download highlighted image</a>
        </div>
      )}
    </div>
  );
}
