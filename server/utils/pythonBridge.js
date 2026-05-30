import { spawn } from "child_process";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PYTHON_BIN  = process.env.PYTHON_BIN         || "python3";
const SCRIPT_PATH = process.env.PYTHON_SCRIPT_PATH ||
  path.resolve(__dirname, "../../deepfake_detector.py");
const OUTPUT_DIR  = process.env.DETECTOR_OUTPUT    ||
  path.resolve(__dirname, "../detector_output");

export function runDetector(imagePath, timeout = 120_000) {
  return new Promise((resolve, reject) => {
    const args = [SCRIPT_PATH, imagePath, "--output", OUTPUT_DIR, "--json-only"];
    console.log("[bridge] running detector on", imagePath);
    const proc = spawn(PYTHON_BIN, args, { timeout, env: { ...process.env } });
    let stdout = "", stderr = "";
    proc.stdout.on("data", (c) => { stdout += c.toString(); });
    proc.stderr.on("data", (c) => { stderr += c.toString(); });
    proc.on("close", (code) => {
      if (code !== 0) return reject(new Error(stderr.trim() || "Detector exited " + code));
      const s = stdout.indexOf("{"), e = stdout.lastIndexOf("}");
      if (s === -1) return reject(new Error("No JSON in detector output"));
      try { resolve(JSON.parse(stdout.slice(s, e + 1))); }
      catch (err) { reject(new Error("JSON parse failed: " + err.message)); }
    });
    proc.on("error", (err) =>
      reject(new Error("Cannot start Python (" + PYTHON_BIN + "): " + err.message))
    );
  });
}

export function toPublicUrl(absolutePath) {
  if (!absolutePath) return null;
  const rel = path.relative(OUTPUT_DIR, absolutePath);
  return "/output/" + rel.replace(/\\/g, "/");
}
