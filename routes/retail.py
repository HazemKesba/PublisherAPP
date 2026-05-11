from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from database import get_db

router = APIRouter()

class RetailPartner(BaseModel):
    partner_id: int
    type: Optional[str] = None
    name: Optional[str] = None
@router.get("/")
async def get(db = Depends(get_db)):
    return { "message": "running" }
# CREATE
@router.post("/create")
async def create_partner(partner: RetailPartner, db = Depends(get_db)):
    try:
        cursor = db.cursor()
        query = "INSERT INTO RETAIL_PARTNER (PARTNER_ID, TYPE, NAME) VALUES (?, ?, ?)"
        cursor.execute(query, (partner.partner_id, partner.type, partner.name))
        db.commit()
        return {"message": "Retail Partner inserted successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
# SELECT
@router.get("/getall", response_model=List[RetailPartner])
async def get_all_partners(db = Depends(get_db)):
    cursor = db.cursor()
    query = "SELECT * FROM RETAIL_PARTNER"
    cursor.execute(query)
    results = cursor.fetchall()
    return [{"partner_id": r[0], "type": r[1], "name": r[2]} for r in results]
# DELETE
@router.delete("/{partner_id}")
async def delete_partner(partner_id: int, db = Depends(get_db)):
    cursor = db.cursor()
    query = "DELETE FROM RETAIL_PARTNER WHERE PARTNER_ID = ?"
    cursor.execute(query, (partner_id,))
    db.commit()
    return {"message": f"Retail Partner {partner_id} deleted successfully"}
# UPDATE
@router.put("/{partner_id}")
async def update_partner(partner_id: int, partner: RetailPartner, db = Depends(get_db)):
    cursor = db.cursor()
    query="UPDATE RETAIL_PARTNER SET NAME = ?, TYPE = ? WHERE PARTNER_ID = ?"
    cursor.execute(query, (partner.name, partner.type, partner.partner_id))
    db.commit()
    return {"message": f"Partner {partner_id} updated successfully"}

# SELECT WITH JOIN
@router.get("/orders-report")
async def orders_report(db = Depends(get_db)):
    cursor = db.cursor()
    query = """
        SELECT RP.NAME, O.ORDER_ID, O.ORDER_DATE, O.QUANTITY
        FROM RETAIL_PARTNER RP
        JOIN [ORDER] O ON RP.PARTNER_ID = O.PARTNER_ID
    """
    cursor.execute(query)
    results = [
        {"name": r[0], "order_id": r[1], "date": str(r[2]), "qty": r[3]}
        for r in cursor.fetchall()
    ]
    return results
