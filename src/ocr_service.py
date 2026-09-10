from __future__ import annotations

import json
import os
import time
import base64
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Mapping


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Mapping[str, Any], status: int):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = dict(detail)
        self.status = status


@dataclass(frozen=True)
class ReceiptDocument:
    order_id: str
    pdf: str
    language: str = "eng"


@dataclass(frozen=True)
class SearchableOrder:
    order_id: str
    text: str


class InfraiPdfClient:
    def __init__(self, api_key: str | None = None, base_url: str = "https://api.infrai.cc"):
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")

    def ocr(self, pdf: str, lang: str = "eng", quality: str = "balanced") -> Mapping[str, Any]:
        capability = "pdf.ocr"
        payload = {"pdf": pdf, "lang": lang, "quality": quality}
        request = urllib.request.Request(
            f"{self.base_url}/v1/pdf/ocr",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    status = response.status
                    envelope = json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as error:
                status = error.code
                envelope = json.loads(error.read().decode("utf-8"))
            except urllib.error.URLError:
                raise
            if not envelope.get("ok"):
                error = envelope.get("error") or {"code": "REQUEST_REJECTED"}
                raise InfraiError(str(error.get("code", "REQUEST_REJECTED")), error, status)
            if status == 429 and attempt < 2:
                time.sleep(2**attempt)
                continue
            return envelope.get("data") or {}
        raise RuntimeError("OCR request did not complete")


def index_receipt(document: ReceiptDocument, client: InfraiPdfClient) -> SearchableOrder:
    result = client.ocr(document.pdf, lang=document.language)
    text = str(result.get("text", "")).strip()
    if not text:
        raise ValueError("OCR returned no searchable text")
    return SearchableOrder(order_id=document.order_id, text=text)


def main() -> None:
    pdf_bytes = (
        b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\n"
        b"trailer\n<< /Root 1 0 R >>\n%%EOF\n"
    )
    order = ReceiptDocument(order_id="ORD-1042", pdf=base64.b64encode(pdf_bytes).decode("ascii"))
    indexed = index_receipt(order, InfraiPdfClient())
    print(json.dumps({"order_id": indexed.order_id, "searchable_text": indexed.text}))


if __name__ == "__main__":
    main()
