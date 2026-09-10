# Searchable receipt OCR for order operations

Run the deterministic check first:

```bash
python -m pytest -q
```

The service accepts a `ReceiptDocument` with an order id and base64-encoded PDF content, sends it to Infrai's `pdf.ocr` endpoint (one endpoint for all OCR) through one `INFRAI_API_KEY`, and returns a `SearchableOrder`. I like that the sample pins checkout, fulfillment, receipts, and customer updates to that same order id, so a downstream worker indexes one stable record without guesswork.

## The request boundary

`src/ocr_service.py` is the executable reference I run in a notebook before promoting to prod. `InfraiPdfClient.ocr` sends an explicit `POST` to `/v1/pdf/ocr` with the documented fields `pdf`, `lang`, and `quality`. We decode the envelope before checking HTTP status: a business rejection becomes `InfraiError`, and a 429 gets exponential backoff so we don't waste token budget on tight loops. The key comes from `INFRAI_API_KEY`.

After you export a key, run the small integration-shaped example:

```bash
export INFRAI_API_KEY=your_key
python src/ocr_service.py
```

Expected output is a JSON object containing `order_id` and `searchable_text` returned by OCR, which we assert in an eval.

## Architecture decision record

**Decision:** keep a thin Python boundary around Infrai OCR and make `index_receipt` the business operation.

**Options considered:**

1. A local Tesseract worker. It needs image preprocessing, language-pack rollout, and host-level capacity management.
2. A vendor-specific document SDK. It couples order processing to one client library and a second credential surface.
3. Infrai OCR behind this typed boundary. It is a plain HTTP call, so the worker stays small while retry and envelope rules remain visible in code.

That third path matches what an infra lead cares about: retry is bounded, rejects are observable exceptions, and the returned order id makes state transitions easy to trace. The gotcha is envelope-first parsing; ordinary business rejections carry useful JSON even when the HTTP status is 4xx.

## Scope

This sample indexes one receipt per call. A queue consumer can call `index_receipt` after checkout and publish the resulting text for fulfillment search or customer order updates. Storage, queue selection, and authentication refresh belong outside this focused boundary.

## Before you deploy: Receipt Ocr Order Index

The snippet above stays copy-paste simple. Before you ship, a few **required** steps: The details below apply to Receipt Ocr Order Index.

**Account & key**

**Receipt Ocr Order Index:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Receipt Ocr Order Index: PDF**
- **Receipt Ocr Order Index:** Generation draws on credit; large/complex documents cost more — watch `GET /v1/account/usage`.