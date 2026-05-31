import "dotenv/config";
import express from "express";
import morgan from "morgan";
import path from "path";
import { fileURLToPath } from "url";
import detectRouter from "./routes/detect.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const app  = express();
const PORT = process.env.PORT || 5000;

// ── CORS – manual headers (works on all environments) ──────────
app.use((req, res, next) => {
  res.header("Access-Control-Allow-Origin", "*");
  res.header("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.header("Access-Control-Allow-Headers", "Content-Type, Authorization");
  if (req.method === "OPTIONS") return res.sendStatus(200);
  next();
});

app.use(morgan(process.env.NODE_ENV === "production" ? "combined" : "dev"));
app.use(express.json());

// ── Static – detector output images (ELA map, highlighted) ─────
app.use(
  "/output",
  express.static(
    path.join(__dirname, process.env.DETECTOR_OUTPUT || "detector_output"),
    { maxAge: "1h", etag: true }
  )
);

// ── API routes ──────────────────────────────────────────────────
app.use("/api", detectRouter);

app.get("/api/health", (_req, res) =>
  res.json({ status: "ok", ts: new Date().toISOString() })
);

app.get("/", (_req, res) =>
  res.json({
    status: "DeepTrace API is running",
    endpoints: ["POST /api/detect", "GET /api/health"],
  })
);

// ── Keep Render service warm ────────────────────────────────────
if (process.env.NODE_ENV === "production") {
  const SELF = process.env.RENDER_EXTERNAL_URL;

  if (SELF) {
    setInterval(async () => {
      try {
        await fetch(`${SELF}/api/health`);
        console.log("[ping] keep-alive sent");
      } catch (e) {
        console.error("[ping] failed:", e.message);
      }
    }, 14 * 60 * 1000);
  }
}

// ── Global error handler ────────────────────────────────────────
app.use((err, _req, res, _next) => {
  const status = err.status || 500;
  console.error(`[error] ${status}:`, err.message);
  res.status(status).json({ error: err.message || "Internal server error" });
});

// ── Boot ────────────────────────────────────────────────────────
app.listen(PORT, () => {
  console.log(`\n🔍  DeepTrace API running → http://localhost:${PORT}\n`);
});