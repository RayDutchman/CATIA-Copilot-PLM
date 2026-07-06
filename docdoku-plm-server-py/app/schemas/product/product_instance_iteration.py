"""DTO: ProductInstanceIterationDTO."""
from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class ProductInstanceIterationDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    serialNumber: Optional[str] = None
    iteration: Optional[int] = None
    iterationNote: Optional[str] = None
    configurationItemId: Optional[str] = None
    updateAuthor: Optional[str] = None
    updateAuthorName: Optional[str] = None
    modificationDate: Optional[datetime] = None
    baselinedParts: List["BaselinedPartDTO"] = []
    substituteLinks: List[str] = []
    optionalUsageLinks: List[str] = []
    author: Optional[dict] = None
    creationDate: Optional[datetime] = None
    substitutesParts: List[dict] = []
    optionalsParts: List[dict] = []
    pathToPathLinks: List["PathToPathLinkDTO"] = []
    basedOn: Optional["ProductBaselineDTO"] = None
    pathDataMasterList: List["PathDataMasterDTO"] = []
    pathDataPaths: List[dict] = []
    instanceAttributes: List[dict] = []
    linkedDocuments: List[dict] = []
    attachedFiles: List[dict] = []


from app.schemas.baseline.baselined_part import BaselinedPartDTO  # noqa: E402
from app.schemas.baseline.product_baseline import ProductBaselineDTO  # noqa: E402
from app.schemas.path_data_master import PathDataMasterDTO  # noqa: E402
from app.schemas.path_to_path_link import PathToPathLinkDTO  # noqa: E402

ProductInstanceIterationDTO.model_rebuild()
