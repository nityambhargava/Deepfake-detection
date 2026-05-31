import express  from "express";
import multer   from "multer";
import path     from "path";
import fs       from "fs";
import { fileURLToPath } from "url";
import { v4 as uuidv4 }  from "uuid";
import { runDetector, toPublicUrl } from "../utils/pythonBridge.js";

const __dirname  = path.dirname(fileURLToPath(import.meta.url));
const router     = express.Router();
const UPLOAD_DIR = path.join(__dirname, "../uploads");
fs.mkdirSync(UPLOAD_DIR, { recursive: true });

const ALLOWED = new Set(["image/jpeg","image/jpg","image/png","image/webp","image/bmp"]);

const upload = multer({
  storage: multer.diskStorage({
    destination: (_r, _f, cb) => cb(null, UPLOAD_DIR),
    filename   : (_r, f,  cb) =>
      cb(null, uuidv4() + (path.extname(f.originalname) || ".jpg")),
  }),
  limits    : { fileSize: 20 * 1024 * 1024 },
  fileFilter: (_r, f, cb) =>
    ALLOWED.has(f.mimetype) ? cb(null, true)
      : cb(new multer.MulterError("LIMIT_UNEXPECTED_FILE", "Unsupported: " + f.mimetype)),
});

router.post("/detect", upload.single("image"), async (req, res, next) => {
  // Setting a 90 second timeout on the response
  req.setTimeout(90_000);
  res.setTimeout(90_000);

  const uploadedPath = req.file?.path;
  if (!uploadedPath)
    return res.status(400).json({ error: "No image. Use multipart/form-data field image." });
  try {
    const raw = await runDetector(uploadedPath);
    res.json({
      classification        : raw.classification,
      fakeness_percentage   : raw.fakeness_percentage,
      verdict_summary       : raw.verdict_summary,
      probe_scores          : (raw.probe_scores || []).map((p) => ({
        probe      : p.probe,
        score      : p.score ?? p.raw_score,
        score_pct  : Math.round((p.score ?? p.raw_score ?? 0) * 100),
        weight     : p.weight,
        description: p.description,
      })),
      altered_regions       : raw.altered_regions || [],
      highlighted_image_url : toPublicUrl(raw.highlighted_image),
      metadata_exif         : raw.metadata_exif   || {},
    });
  } catch (err) {
    next(err);
  } finally {
    if (uploadedPath) fs.unlink(uploadedPath, () => {});
  }
});

router.use((err, _req, res, next) => {
  if (err instanceof multer.MulterError)
    return res.status(400).json({ error: err.message });
  next(err);
});

export default router;
