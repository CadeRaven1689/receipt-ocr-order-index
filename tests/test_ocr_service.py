from ocr_service import ReceiptDocument, SearchableOrder, index_receipt


class FakeClient:
    def ocr(self, pdf: str, lang: str):
        assert pdf.endswith("ORD-1042.pdf")
        assert lang == "eng"
        return {"text": "Order ORD-1042 | total 42.00"}


def test_receipt_becomes_searchable_order():
    result = index_receipt(
        ReceiptDocument("ORD-1042", "https://files.example.test/receipts/ORD-1042.pdf"),
        FakeClient(),
    )
    assert result == SearchableOrder("ORD-1042", "Order ORD-1042 | total 42.00")
