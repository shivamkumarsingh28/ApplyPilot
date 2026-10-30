# 001 — Photo Studio crashes on OpenCV 5

**Folder:** `backend/` · **Severity:** 🔴 Breaking · **Status:** ✅ Fixed

## Problem
On a fresh install, Photo Studio fails and 2 backend tests fail:

```
tests/test_photo_studio.py::test_photo_meets_spec  FAILED
tests/test_api_flow.py::test_photo_from_notice_spec_saved_to_vault_improves_readiness  FAILED
AttributeError: module 'cv2' has no attribute 'CascadeClassifier'
```

A user uploading a selfie would get an error instead of a resized photo —
this breaks wireframe 3 (Photo & signature studio) completely.

## Found in
- Folder: `backend/app/services/`
- File: `backend/app/services/photo_studio.py`
- Line (before fix): inside `_detect_face()` —
  `cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")`
- Dependency line: `backend/requirements.txt` — `opencv-python-headless>=4.9` (no upper bound)

## Root cause
OpenCV **5.0 removed `cv2.CascadeClassifier`** (the Haar-cascade API).
`requirements.txt` allowed `>=4.9` with no ceiling, so pip/uv installed
OpenCV 5.0.0, and the first face detection crashed. Verified with:

```powershell
python -c "import cv2; print(cv2.__version__, hasattr(cv2,'CascadeClassifier'))"
# 5.0.0 False   (cv2.FaceDetectorYN / FaceDetectorYN_create exist instead)
```

## Fix
| Folder | File | Line | Change |
|---|---|---|---|
| `backend/app/services/` | `photo_studio.py` | 52–76 | `_detect_face()` now branches: `hasattr(cv2, "CascadeClassifier")` → classic Haar path (OpenCV <5); `elif hasattr(cv2, "FaceDetectorYN_create")` → YuNet detector, downloading `face_detection_yunet_2023mar.onnx` from the OpenCV zoo next to the module on first use (OpenCV 5+); otherwise returns `None` so the existing centre-crop fallback with a user warning runs. No exception can escape. |
| `backend/` | `requirements.txt` | 16 | `opencv-python-headless>=4.9,<5.0` — installs stay on the tested 4.x line; the code fallback covers anyone already on 5.x |

Key lines after the fix (`photo_studio.py`):
- Line 54: `if hasattr(cv2, "CascadeClassifier"):  # OpenCV < 5: classic Haar cascade`
- Line 61: `if hasattr(cv2, "FaceDetectorYN_create"):  # OpenCV 5 removed CascadeClassifier`
- Line 72: `detector = cv2.FaceDetectorYN_create(str(model), "", (img.width, img.height), 0.6)`

## Feature affected
Photo Studio (all photo processing, face-aware crop), and indirectly
Readiness — saving a fixed photo/signature to the vault raises the
readiness percentage.

## How to verify
```powershell
cd backend
python -m pytest tests/test_photo_studio.py tests/test_api_flow.py -q   # all pass
python -m pytest -q                                                     # 84 passed
```

## If it comes back
1. Check the installed version: `python -c "import cv2; print(cv2.__version__)"`.
2. If a future OpenCV removes `FaceDetectorYN_create` too, `_detect_face`
   returns `None` and photos are centre-cropped with a warning — fix by
   adding the new detector API as another `elif` branch in the same function.
