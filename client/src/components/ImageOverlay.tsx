import { useEffect, useRef, useState } from "react";
import type { AlteredRegion } from "@/types/detection";
import clsx from "clsx";

interface Props {
  previewUrl: string; alteredRegions: AlteredRegion[];
  highlightedUrl: string|null; classification: string;
}

export default function ImageOverlay({ previewUrl, alteredRegions, highlightedUrl, classification }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [showOverlay, setShowOverlay] = useState(true);
  const [mode, setMode] = useState<"canvas"|"server">("canvas");
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (mode !== "canvas" || !loaded) return;
    const canvas = canvasRef.current; if (!canvas) return;
    const ctx = canvas.getContext("2d"); if (!ctx) return;
    const img = new Image(); img.src = previewUrl;
    img.onload = () => {
      canvas.width = img.naturalWidth; canvas.height = img.naturalHeight;
      ctx.drawImage(img, 0, 0);
      if (!showOverlay || !alteredRegions.length) return;
      alteredRegions.forEach((r) => {
        ctx.fillStyle = "rgba(255,69,69,0.18)";
        ctx.fillRect(r.x, r.y, r.width, r.height);
        ctx.strokeStyle = "#ff4545";
        ctx.lineWidth = Math.max(2, img.naturalWidth / 400);
        ctx.strokeRect(r.x, r.y, r.width, r.height);
        const fs = Math.max(11, img.naturalWidth / 80);
        ctx.font = `600 ${fs}px JetBrains Mono, monospace`;
        ctx.fillStyle = "#ffb020";
        ctx.fillText(`R${r.region_id} · ${Math.round(r.confidence*100)}%`, r.x+4, r.y-4);
      });
    };
  }, [previewUrl, alteredRegions, showOverlay, mode, loaded]);

  return (
    <div className="card flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <p className="mono-label">Image analysis</p>
        <div className="flex items-center gap-2">
          {mode==="canvas" && alteredRegions.length>0 && (
            <button className={clsx("btn-ghost text-[11px] py-1 px-3", showOverlay&&"border-red/40 text-red")} onClick={()=>setShowOverlay(v=>!v)}>
              {showOverlay?"Hide":"Show"} regions
            </button>
          )}
          {highlightedUrl && classification==="FAKE" && (
            <button className="btn-ghost text-[11px] py-1 px-3" onClick={()=>setMode(m=>m==="canvas"?"server":"canvas")}>
              {mode==="canvas"?"Server view":"Canvas view"}
            </button>
          )}
        </div>
      </div>
      <div className="relative rounded-lg overflow-hidden bg-black">
        {mode==="canvas" ? (
          <>
            <canvas ref={canvasRef} className="w-full h-auto max-h-[480px] object-contain" style={{display:loaded?"block":"none"}}/>
            {!loaded && <img src={previewUrl} alt="" className="w-full h-auto" onLoad={()=>setLoaded(true)}/>}
          </>
        ) : (
          <img src={highlightedUrl!} alt="Server result" className="w-full h-auto max-h-[480px] object-contain"/>
        )}
      </div>
      {alteredRegions.length>0 && showOverlay && (
        <div className="flex flex-col gap-2">
          <p className="mono-label">{alteredRegions.length} altered region{alteredRegions.length>1?"s":""} detected</p>
          <div className="grid grid-cols-2 gap-2">
            {alteredRegions.map((r) => (
              <div key={r.region_id} className="card-sm flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-red shrink-0"/>
                <span className="font-mono text-[11px] text-dim">R{r.region_id}: {r.width}×{r.height}px · <span className="text-amber">{Math.round(r.confidence*100)}%</span></span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
