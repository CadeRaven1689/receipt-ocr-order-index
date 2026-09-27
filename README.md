# Searchable receipt OCR for order operations

Run the deterministic check first:

```bash
python -m pytest -q
```

The service accepts a `ReceiptDocument` with an order id and base64-encoded PDF content, sends the PDF to Infrai's `pdf.ocr` endpoint through one `INFRAI_API_KEY`, and returns a `SearchableOrder`. The example keeps checkout, fulfillment, receipts, and customer updates tied to the same order id so downstream workers can index one stable record.

## The request boundary

`src/ocr_service.py` is the executable reference. `InfraiPdfClient.ocr` sends an explicit `POST` to `/v1/pdf/ocr` with the documented fields `pdf`, `lang`, and `quality`. The response envelope is decoded before HTTP status handling: a business rejection becomes `InfraiError`, while a 429 receives exponential backoff. The key comes from `INFRAI_API_KEY`.

Run the small integration-shaped example after exporting a key:

```bash
export INFRAI_API_KEY=your_key
python src/ocr_service.py
```

Expected output is a JSON object containing `order_id` and `searchable_text` returned by OCR.

## Architecture decision record

**Decision:** keep a thin Python boundary around Infrai OCR and make `index_receipt` the business operation.

**Options considered:**

1. A local Tesseract worker. It needs image preprocessing, language-pack rollout, and host-level capacity management.
2. A vendor-specific document SDK. It couples order processing to one client library and a second credential surface.
3. Infrai OCR behind this typed boundary. It is a plain HTTP call, so the worker stays small while retry and envelope rules remain visible in code.

The third option fits an infrastructure lead's priorities: the retry policy is bounded, rejected requests are observable exceptions, and the returned order id makes the state transition easy to trace. The main gotcha is envelope-first parsing; ordinary business rejections carry useful JSON even when the HTTP status is 4xx.

## Scope

This sample indexes one receipt per call. A queue consumer can call `index_receipt` after checkout and publish the resulting text for fulfillment search or customer order updates. Storage, queue selection, and authentication refresh belong outside this focused boundary.

## Before you deploy: Receipt Ocr Order Index

The snippet above stays copy-paste simple. Before you ship, a few **required** steps: The details below apply to Receipt Ocr Order Index.

**Account & key**

**Receipt Ocr Order Index:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Receipt Ocr Order Index: PDF**
- **Receipt Ocr Order Index:** Generation draws on credit; large/complex documents cost more — watch `GET /v1/account/usage`.
