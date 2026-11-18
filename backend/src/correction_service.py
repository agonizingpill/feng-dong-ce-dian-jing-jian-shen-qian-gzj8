from copy import deepcopy
from fastapi import HTTPException
from sqlalchemy import select
from .run_models import TunnelRun
from .delivery_models import TunnelDelivery
from .correction_models import DeliveryCorrection
from .calibration_service import locked
from .services import pack,audit

def versions(s,delivery_id):
    return s.scalars(select(DeliveryCorrection).where(DeliveryCorrection.delivery_id==delivery_id).order_by(DeliveryCorrection.id)).all()
def effective(s,delivery):
    tip=None
    for c in versions(s,delivery.id):
        if c.state in ('approved','acknowledged'):tip=c
    return ('correction',tip) if tip else ('delivery',delivery)
def preview(s,id):
    x=s.get(DeliveryCorrection,id)
    if not x:raise HTTPException(404,'交付更正单不存在')
    return x
def create(s,d,u):
    r=locked(s,TunnelRun,d.run_id)
    x=s.scalar(select(TunnelDelivery).where(TunnelDelivery.run_id==r.id).with_for_update())
    if not x:raise HTTPException(409,'本试验尚无交付单，不能发起更正')
    kind,cur=effective(s,x)
    if cur.state not in ('approved','acknowledged'):raise HTTPException(409,'仅已核准的交付可发起更正，待复核件请先由主管核准')
    if d.recipient==cur.recipient:raise HTTPException(409,'新接收方与当前有效件相同，无需更正')
    c=DeliveryCorrection(run_id=r.id,delivery_id=x.id,supersedes_id=cur.id if kind=='correction' else None,recipient=d.recipient,reason=d.reason,snapshot=deepcopy(x.snapshot),submitted_by=u.email)
    s.add(c);s.flush();audit(s,u,'发起交付更正 '+str(c.id));return pack(c)
def approve(s,id,u):
    pre=preview(s,id);locked(s,TunnelRun,pre.run_id)
    c=locked(s,DeliveryCorrection,id)
    if c.state=='stale':raise HTTPException(409,'更正基准已被接替，过时更正拒绝发布')
    if c.state!='pending':raise HTTPException(409,'仅待核准更正可核准，不能重复发布')
    x=locked(s,TunnelDelivery,c.delivery_id)
    kind,cur=effective(s,x)
    if (cur.id if kind=='correction' else None)!=c.supersedes_id:
        c.state='stale';audit(s,u,'过时更正拒绝发布 '+str(id));s.commit()
        raise HTTPException(409,'更正基准已被接替，过时更正拒绝发布')
    c.state='approved';c.approved_by=u.email
    for other in versions(s,x.id):
        if other.id!=c.id and other.state=='pending':other.state='stale'
    audit(s,u,'主管核准交付更正 '+str(id));return pack(c)
def acknowledge(s,id,d,u):
    pre=preview(s,id);locked(s,TunnelRun,pre.run_id)
    c=locked(s,DeliveryCorrection,id);text=d.receipt.strip()
    if c.state=='acknowledged':
        if c.receipt==text:return pack(c)
        raise HTTPException(409,'该版本已登记不同回执，不能重复签收')
    if c.state!='approved':raise HTTPException(409,'更正须主管核准后才可登记回执' if c.state=='pending' else '过时更正不能登记回执')
    x=locked(s,TunnelDelivery,c.delivery_id)
    kind,cur=effective(s,x)
    if kind!='correction' or cur.id!=c.id:raise HTTPException(409,'该版本已被新更正接替，旧件拒收新回执')
    if len(text)<8:raise HTTPException(409,'回执说明至少8字')
    c.receipt=text;c.state='acknowledged';audit(s,u,'登记更正交付回执 '+str(id));return pack(c)
