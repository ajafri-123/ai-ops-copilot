"""
Pydantic schemas for ServiceDependency.
"""

from pydantic import BaseModel, ConfigDict

from app.models.service_dependency import RelationshipType


class ServiceDependencyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    service_name: str
    depends_on: str
    relationship_type: RelationshipType
