import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from app.db.models import LoanApplicationModel
from app.schemas.application import ApplicationCreate

def create_application(db: Session, data: ApplicationCreate) -> LoanApplicationModel:
    app_id = data.application_id or f"APP-{uuid.uuid4().hex[:8].upper()}"
    
    # Check if application_id already exists
    existing = db.query(LoanApplicationModel).filter(LoanApplicationModel.application_id == app_id).first()
    if existing:
        raise ValueError(f"Application with ID '{app_id}' already exists.")
        
    app_obj = LoanApplicationModel(
        application_id=app_id,
        applicant_name=data.applicant_name,
        loan_amount=data.loan_amount or 0.0,
        status="PENDING"
    )
    db.add(app_obj)
    db.commit()
    db.refresh(app_obj)
    return app_obj

def get_application(db: Session, application_id: str) -> Optional[LoanApplicationModel]:
    return db.query(LoanApplicationModel).filter(LoanApplicationModel.application_id == application_id).first()

def list_applications(db: Session) -> List[LoanApplicationModel]:
    return db.query(LoanApplicationModel).order_by(LoanApplicationModel.created_at.desc()).all()
