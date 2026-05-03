# main_api.py — ZATCA Phase 2 API (Standalone)
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os, json

# استيراد كودك الموجود
from zatca_phase2 import ZATCAPhase2, generate_test_cert
from zatca_qr import generate_invoice_qr

app = FastAPI(title="ZATCA API", version="2.0")

class InvoiceItem(BaseModel):
    name: str
    qty: float = 1
    price: float
    total: Optional[float] = None
    vat_rate: float = 15

class InvoiceRequest(BaseModel):
    invoice_no: str
    buyer_name: Optional[str] = "عميل نقدي"
    buyer_vat: Optional[str] = ""
    items: List[InvoiceItem]
    subtotal: float
    vat_amount: float
    total: float
    invoice_type: str = "388"  # 388 = فاتورة ضريبية

@app.post("/invoice/generate")
def generate_invoice(req: InvoiceRequest):
    """توليد فاتورة ZATCA + QR + XML"""
    zatca = ZATCAPhase2()
    
    if not zatca.is_configured:
        raise HTTPException(400, "ZATCA not configured. Set .env first.")
    
    items = [{"name": i.name, "qty": i.qty, "price": i.price, 
              "total": i.total or (i.qty * i.price), "vat_rate": i.vat_rate} 
             for i in req.items]
    
    invoice_data = {
        "invoice_no": req.invoice_no,
        "buyer_name": req.buyer_name,
        "buyer_vat": req.buyer_vat,
        "items": items,
        "subtotal": req.subtotal,
        "vat_amount": req.vat_amount,
        "total": req.total,
        "invoice_type": req.invoice_type
    }
    
    result = zatca.process_invoice(invoice_data)
    
    if not result["success"]:
        raise HTTPException(500, result.get("error", "Unknown error"))
    
    # QR Code
    qr = generate_invoice_qr(
        seller_name=zatca.seller_name,
        vat_number=zatca.vat_number,
        total_with_vat=req.total,
        vat_amount=req.vat_amount,
        invoice_no=req.invoice_no
    )
    
    return {
        "success": True,
        "invoice_no": req.invoice_no,
        "uuid": result["uuid"],
        "hash": result["hash"],
        "qr_base64": qr["qr_base64"],
        "xml": result["xml"],
        "is_signed": result["is_signed"],
        "api_result": result.get("api_result", {})
    }

@app.post("/invoice/qr-only")
def generate_qr_only(seller_name: str, vat_number: str, 
                     total: float, vat: float):
    """توليد QR فقط (Phase 1)"""
    qr = generate_invoice_qr(seller_name, vat_number, total, vat)
    return qr

@app.get("/health")
def health():
    return {"status": "ok", "zatca_configured": ZATCAPhase2().is_configured}

@app.post("/setup/test-cert")
def setup_test(vat: str, name: str):
    """توليد شهادة اختبار"""
    return generate_test_cert(vat, name)