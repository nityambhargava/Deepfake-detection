# DeepTrace — Image Authenticity Detector

Classifies images as **REAL**, **FAKE**, or **AI GENERATED** using 6 forensic probes.

## Stack
- **Detector**: Python · OpenCV · PIL · SciPy · scikit-image
- **API**: Node.js · Express · Multer
- **Frontend**: React 18 · TypeScript · Vite · Tailwind CSS · Recharts

---

## Quickstart (GitHub Codespaces) ← START HERE

1. Push repo to GitHub
2. Click **Code → Codespaces → Create codespace on main**
3. Wait ~2 min for auto-setup (setup.sh installs everything)
4. In the terminal:
```bash
npm run dev
```
5. Codespaces opens a browser tab on port **5173** automatically

---

## Quickstart (Local)

```bash
# 1. Install Python packages
pip install opencv-python-headless pillow numpy scipy scikit-image

# 2. Install Node packages
npm run install:all

# 3. Run both servers
npm run dev
```
Open http://localhost:5173

---

## API
POST /api/detect  — multipart/form-data, field: "image" (≤20MB)
GET  /api/health  — liveness check
GET  /output/*    — serves generated ELA/highlighted images

## Thresholds
| Class        | Fakeness  |
|--------------|-----------|
| REAL         | < 10%     |
| FAKE         | 50 – 89%  |
| AI_GENERATED | ≥ 90%     |
