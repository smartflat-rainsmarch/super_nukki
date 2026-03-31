# API Specification

## 1. Upload Image

POST /api/upload

Request:
- file: image

Response:
{
  "project_id": "uuid"
}

---

## 2. Get Status

GET /api/project/{id}

Response:
{
  "status": "processing",
  "progress": 60
}

---

## 3. Get Result

GET /api/project/{id}/result

Response:
{
  "psd_url": "...",
  "layers": [...]
}

---

## 4. Download PSD

GET /api/download/{id}

---

## 5. Billing Check

GET /api/usage

Response:
{
  "remaining": 3
}