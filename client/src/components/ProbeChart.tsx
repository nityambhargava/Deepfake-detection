import { RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer, Tooltip } from "recharts";
import type { ProbeScore } from "@/types/detection";
import { PROBE_LABELS } from "@/types/detection";
import clsx from "clsx";

const FILL: Record<string,string> = { REAL:"#00e5a0", FAKE:"#ffb020", AI_GENERATED:"#7b61ff" };

export default function ProbeChart({ probes, classification }: { probes: ProbeScore[]; classification: string }) {
  const color = FILL[classification] || "#00e5a0";
  const data  = probes.map((p) => ({ probe: PROBE_LABELS[p.probe]??p.probe, value: Math.round(p.score*100) }));

  return (
    <div className="card flex flex-col gap-5">
      <p className="mono-label">Probe breakdown</p>
      <div className="h-52">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={data} margin={{top:4,right:16,bottom:4,left:16}}>
            <PolarGrid stroke="#1a1f2e"/>
            <PolarAngleAxis dataKey="probe" tick={{fill:"#5a6480",fontSize:10,fontFamily:"JetBrains Mono"}}/>
            <Tooltip contentStyle={{background:"#0e1117",border:"1px solid #1a1f2e",borderRadius:8,fontFamily:"JetBrains Mono",fontSize:12,color:"#c8d0e0"}} formatter={(v:number)=>[`${v}%`,"Score"]}/>
            <Radar dataKey="value" stroke={color} fill={color} fillOpacity={0.15} strokeWidth={1.5}/>
          </RadarChart>
        </ResponsiveContainer>
      </div>
      <div className="flex flex-col gap-3">
        {probes.map((p) => {
          const pct = p.score_pct ?? Math.round(p.score*100);
          return (
            <div key={p.probe} className="flex items-center gap-3">
              <span className="font-mono text-[11px] text-dim w-24 shrink-0">{PROBE_LABELS[p.probe]??p.probe}</span>
              <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
                <div className="h-full rounded-full probe-bar-fill" style={{width:`${pct}%`,background:color}}/>
              </div>
              <span className={clsx("font-mono text-[11px] w-9 text-right shrink-0", pct>70?"text-red":pct>40?"text-amber":"text-green")}>{pct}%</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
