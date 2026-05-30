import { useEffect, useRef } from "react";
import type { Classification } from "@/types/detection";

const COLOR: Record<Classification, string> = {
  REAL: "#00e5a0", FAKE: "#ffb020", AI_GENERATED: "#7b61ff",
};

export default function FakenessGauge({ percentage, classification }: { percentage: number; classification: Classification }) {
  const arcRef = useRef<SVGCircleElement>(null);
  const R = 54, CIRCUM = 2 * Math.PI * R, ARC = 0.75;
  const EMPTY = CIRCUM * ARC, TARGET = EMPTY * (1 - percentage / 100);
  const color = COLOR[classification];

  useEffect(() => {
    const el = arcRef.current; if (!el) return;
    el.style.transition = "none";
    el.style.strokeDashoffset = String(EMPTY);
    void el.getBoundingClientRect();
    el.style.transition = "stroke-dashoffset 1.4s cubic-bezier(0.34,1.2,0.64,1)";
    el.style.strokeDashoffset = String(TARGET);
  }, [percentage, EMPTY, TARGET]);

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="relative w-36 h-36">
        <svg viewBox="0 0 120 120" className="w-full h-full -rotate-[225deg]">
          <circle cx="60" cy="60" r={R} fill="none" stroke="#1a1f2e" strokeWidth="8" strokeDasharray={`${CIRCUM*ARC} ${CIRCUM}`} strokeLinecap="round"/>
          <circle ref={arcRef} cx="60" cy="60" r={R} fill="none" stroke={color} strokeWidth="8" strokeDasharray={`${CIRCUM*ARC} ${CIRCUM}`} strokeDashoffset={EMPTY} strokeLinecap="round"/>
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-mono font-bold text-2xl leading-none" style={{color}}>{Math.round(percentage)}%</span>
          <span className="mono-label mt-0.5">fakeness</span>
        </div>
      </div>
      <div className="flex gap-4 text-center">
        {[{range:"< 10%",label:"Real",active:percentage<10},{range:"50–90%",label:"Fake",active:percentage>=50&&percentage<90},{range:"> 90%",label:"AI Gen",active:percentage>=90}].map(({range,label,active})=>(
          <div key={label} className="flex flex-col items-center gap-0.5">
            <span className={`mono-label ${active?"text-white":""}`}>{label}</span>
            <span className="font-mono text-[10px] text-dim">{range}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
