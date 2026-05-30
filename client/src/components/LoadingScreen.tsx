interface Props { phase: "uploading" | "analysing"; }

const STEPS = [
  { id: "uploading", label: "Uploading image..."           },
  { id: "analysing", label: "Running ELA probe..."          },
  { id: "analysing", label: "Frequency domain analysis..."  },
  { id: "analysing", label: "Noise consistency check..."    },
  { id: "analysing", label: "JPEG ghost detection..."       },
  { id: "analysing", label: "EXIF metadata forensics..."    },
  { id: "analysing", label: "Colour / gradient analysis..." },
];

export default function LoadingScreen({ phase }: Props) {
  const steps = STEPS.filter((s) => s.id === phase);
  return (
    <div className="flex flex-col items-center justify-center py-28 gap-8" style={{animation:"fadeUp 0.4s ease forwards"}}>
      <div className="relative w-20 h-20">
        <svg className="w-full h-full animate-spin" viewBox="0 0 80 80">
          <circle cx="40" cy="40" r="36" fill="none" stroke="#1a1f2e" strokeWidth="4"/>
          <circle cx="40" cy="40" r="36" fill="none" stroke="#00e5a0" strokeWidth="4" strokeDasharray="56 170" strokeLinecap="round"/>
        </svg>
        <span className="absolute inset-0 flex items-center justify-center text-green text-xl font-mono">⊚</span>
      </div>
      <div className="flex flex-col gap-2 w-64">
        {steps.map((s, i) => (
          <div key={i} className="flex items-center gap-3 font-mono text-xs text-dim" style={{animation:`fadeUp 0.4s ease ${i*120}ms forwards`, opacity:0}}>
            <span className="w-1.5 h-1.5 rounded-full bg-green/60 shrink-0"/>
            {s.label}
          </div>
        ))}
      </div>
    </div>
  );
}
