from pydantic import EmailStr, field_validator
from sqlmodel import Field, SQLModel

from ..models.work_order import WorkOrder


class WorkOrderPublic(WorkOrder):
    id: int