import { useCallback } from "react";
import { useDropzone } from "react-dropzone";
import clsx from "clsx";

const ACCEPTED = { "image/jpeg":[".jpg",".jpeg"], "image/png":[".png"], "image/webp":[".webp"], "image/bmp":[".bmp"] };

export default function UploadZone({ onFile }: { onFile: (f: File) => void }) {
  const onDrop = useCallback((a: File[]) => { if (a[0]) onFile(a[0]); }, [onFile]);
  const { getRootProps, getInputProps, isDragActive, isDragReject } =
    useDropzone({ onDrop, accept: ACCEPTED, maxFiles: 1, maxSize: 20_971_520 });

  return (
    <div className="flex flex-col items-center gap-10 py-8" style={{animation:"fadeUp 0.4s ease forwards"}}>
      <div className="text-center">
        <h1 className="font-display text-4xl md:text-5xl font-extrabold text-white leading-tight mb-3">
          Is this image <span className="text-green">real?</span>
        </h1>
        <p className="text-dim max-w-md mx-auto leading-relaxed">
          Upload a photo to run six independent forensic probes: ELA, frequency analysis,
          noise consistency, JPEG ghost detection, metadata forensics, and colour analysis.
        </p>
      </div>
      <div {...getRootProps()} className={clsx(
        "relative w-full max-w-xl h-64 rounded-2xl border-2 border-dashed",
        "flex flex-col items-center justify-center gap-4 cursor-pointer transition-all duration-300 group",
        isDragActive&&!isDragReject ? "border-green bg-green/5 shadow-glow-green"
          : isDragReject            ? "border-red bg-red/5 shadow-glow-red"
          : "border-border bg-panel hover:border-green/40 hover:bg-green/[0.03]"
      )}>
        <input {...getInputProps()}/>
        {["top-3 left-3","top-3 right-3","bottom-3 left-3","bottom-3 right-3"].map((pos,i) => (
          <span key={i} className={clsx("absolute w-4 h-4 border-green/40 group-hover:border-green/80 transition-colors", pos,
            i===0&&"border-t-2 border-l-2 rounded-tl", i===1&&"border-t-2 border-r-2 rounded-tr",
            i===2&&"border-b-2 border-l-2 rounded-bl", i===3&&"border-b-2 border-r-2 rounded-br")}/>
        ))}
        {isDragReject ? (
          <><span className="text-red text-3xl">✕</span><p className="font-mono text-sm text-red">Unsupported file type</p></>
        ) : (
          <>
            <svg width="40" height="40" viewBox="0 0 40 40" fill="none" className={clsx("transition-transform", isDragActive&&"-translate-y-1")}>
              <circle cx="20" cy="20" r="19" stroke={isDragActive?"#00e5a0":"#2a3045"} strokeWidth="1.5"/>
              <path d="M20 26V14M14 20l6-6 6 6" stroke={isDragActive?"#00e5a0":"#5a6480"} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            <div className="text-center">
              <p className="text-text mb-1">{isDragActive?"Drop to analyse":"Drag & drop an image here"}</p>
              <p className="mono-label">or click to browse · JPG PNG WEBP BMP · max 20 MB</p>
            </div>
          </>
        )}
      </div>
      <div className="grid grid-cols-3 gap-3 w-full max-w-xl">
        {[["⚡","ELA Analysis"],["〜","FFT Frequency"],["◈","Noise Forensics"],["◻","JPEG Ghost"],["⊚","EXIF Metadata"],["◍","Colour Gradient"]].map(([icon,label]) => (
          <div key={label} className="card-sm flex items-center gap-2">
            <span className="text-green/70">{icon}</span>
            <span className="font-mono text-[11px] text-dim">{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
