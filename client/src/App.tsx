import { useState, useCallback } from "react";
import type { AppState, DetectionResult } from "@/types/detection";
import UploadZone    from "@/components/UploadZone";
import ResultPanel   from "@/components/ResultPanel";
import LoadingScreen from "@/components/LoadingScreen";

export default function App() {
  const [state, setState] = useState<AppState>({ phase: "idle" });

  const handleFile = useCallback(async (file: File) => {
    const previewUrl = URL.createObjectURL(file);
    setState({ phase: "uploading" });
    try {
      const form = new FormData();
      form.append("image", file);
      setState({ phase: "analysing" });
      const res = await fetch("/api/detect", { method: "POST", body: form });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ error: res.statusText }));
        throw new Error(err.error || "Detection failed.");
      }
      const result: DetectionResult = await res.json();
      setState({ phase: "result", result, previewUrl });
    } catch (err) {
      URL.revokeObjectURL(previewUrl);
      setState({ phase: "error", message: err instanceof Error ? err.message : "Unknown error" });
    }
  }, []);

  const reset = useCallback(() => {
    if (state.phase === "result") URL.revokeObjectURL(state.previewUrl);
    setState({ phase: "idle" });
  }, [state]);

  return (
    <div className="min-h-screen grid-bg relative overflow-x-hidden">
      <div aria-hidden className="pointer-events-none fixed top-0 left-1/2 -translate-x-1/2 w-[600px] h-[300px] rounded-full opacity-20 bg-green blur-[120px]" />
      <header className="relative z-10 flex items-center justify-between px-6 py-4 border-b border-border">
        <div className="flex items-center gap-3">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
            <rect x="1" y="1" width="26" height="26" rx="6" stroke="#00e5a0" strokeWidth="1.5"/>
            <path d="M7 14h14M14 7v14" stroke="#00e5a0" strokeWidth="1.5" strokeLinecap="round"/>
            <circle cx="14" cy="14" r="3" fill="none" stroke="#00e5a0" strokeWidth="1.5"/>
          </svg>
          <span className="font-display text-xl font-bold text-white">Deep<span className="text-green">Trace</span></span>
        </div>
        <span className="mono-label">Image Authenticity Detector</span>
      </header>
      <main className="relative z-10 max-w-5xl mx-auto px-4 py-10">
        {state.phase === "idle"      && <UploadZone onFile={handleFile} />}
        {(state.phase === "uploading" || state.phase === "analysing") && <LoadingScreen phase={state.phase} />}
        {state.phase === "result"    && <ResultPanel result={state.result} previewUrl={state.previewUrl} onReset={reset} />}
        {state.phase === "error"     && (
          <div className="flex flex-col items-center py-24 gap-6 text-center" style={{animation:"fadeUp 0.4s ease forwards"}}>
            <div className="w-16 h-16 rounded-full bg-red/10 border border-red/30 flex items-center justify-center text-red text-2xl">✕</div>
            <div>
              <p className="font-display text-lg text-white mb-1">Analysis Failed</p>
              <p className="font-mono text-sm text-dim max-w-md">{state.message}</p>
            </div>
            <button className="btn-ghost" onClick={reset}>← Try another image</button>
          </div>
        )}
      </main>
    </div>
  );
}
