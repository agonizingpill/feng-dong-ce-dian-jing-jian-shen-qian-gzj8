from sqlalchemy import String,Text,ForeignKey,JSON,CheckConstraint
from sqlalchemy.orm import Mapped,mapped_column
from .db import Base
class DeliveryCorrection(Base):
    __tablename__='delivery_corrections'
    __table_args__=(CheckConstraint("state in ('pending','approved','acknowledged','stale')"),)
    id:Mapped[int]=mapped_column(primary_key=True)
    run_id:Mapped[int]=mapped_column(ForeignKey('tunnel_runs.id'))
    delivery_id:Mapped[int]=mapped_column(ForeignKey('tunnel_deliveries.id'))
    supersedes_id:Mapped[int|None]=mapped_column(ForeignKey('delivery_corrections.id'),nullable=True)
    recipient:Mapped[str]=mapped_column(String(100))
    reason:Mapped[str]=mapped_column(Text)
    state:Mapped[str]=mapped_column(String(20),default='pending')
    snapshot:Mapped[dict]=mapped_column(JSON)
    submitted_by:Mapped[str]=mapped_column(String(100))
    approved_by:Mapped[str|None]=mapped_column(String(100),nullable=True)
    receipt:Mapped[str]=mapped_column(Text,default='')
