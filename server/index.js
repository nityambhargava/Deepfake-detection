import "dotenv/config";
import express from "express";
import cors from "cors";
import morgan from "morgan";
import path from "path";
import { fileURLToPath } from "url";
import detectRouter from "./routes/detect.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const app  = express();
const PORT = process.env.PORT || 5000;

app.use(cors({
  origin: process.env.ALLOWED_ORIGINS
    ? process.env.ALLOWED_ORIGINS.split(",")
    : ["http://localhost:5173"],
  methods: ["GET", "POST"],
}));
app.use(morgan(process.env.NODE_ENV === "production" ? "combined" : "dev"));
app.use(express.json());

// Serve generated ELA maps and highlighted images
app.use("/output", express.static(
  path.join(__dirname, process.env.DETECTOR_OUTPUT || "detector_output"),
  { maxAge: "1h", etag: true }
));

app.use("/api", detectRouter);
app.get("/api/health", (_req, res) =>
  res.json({ status: "ok", ts: new Date().toISOString() })
);

// Production: serve compiled React
if (process.env.NODE_ENV === "production") {
  const clientDist = path.join(__dirname, "../client/dist");
  app.use(express.static(clientDist));
  app.get("*", (_req, res) =>
    res.sendFile(path.join(clientDist, "index.html"))
  );
}

// Global error handler
app.use((err, _req, res, _next) => {
  const status = err.status || 500;
  console.error(`[error] ${status}:`, err.message);
  res.status(status).json({ error: err.message || "Internal server error" });
});

app.listen(PORT, () => {
  console.log(`\n🔍  DeepTrace API running → http://localhost:${PORT}\n`);
});
