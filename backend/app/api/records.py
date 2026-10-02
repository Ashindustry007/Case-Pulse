"""[Dev 1] Source records + document pages/files (F3 Source Drawer). PHASE 0 STUB."""
from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_role
from ..contracts import DocumentPage, SourceRecord
from ..stubs import fixture

router = APIRouter(prefix="/api", tags=["records"], dependencies=[Depends(require_role("attorney"))])


@router.get("/records/{record_id}", response_model=SourceRecord)
def get_record(record_id: str):
    return fixture("record", SourceRecord)


@router.get("/documents/{document_id}/pages/{page_no}", response_model=DocumentPage)
def get_page(document_id: str, page_no: int):
    return fixture("document_page", DocumentPage)


@router.get("/documents/{document_id}/pages/{page_no}/image")
def get_page_image(document_id: str, page_no: int):
    raise HTTPException(404, "stub: page images available once documents are synced")


@router.get("/documents/{document_id}/file")
def get_file(document_id: str):
    raise HTTPException(404, "stub: files available once documents are synced")
