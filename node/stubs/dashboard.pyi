from fastapi import Depends as Depends, FastAPI as FastAPI
from typing import Any, Union

dashboard_router: Any

async def get_data_to_dashboard() -> None: ...
async def login_user() -> None: ...
async def logout_user() -> None: ...
async def get_applicants(
    applicant_count: Union[int, None] = ..., page: Union[int, None] = ...
): ...
async def get_applicant(applicant_id: int): ...
async def get_all_requests() -> None: ...
async def get_request(request_id: int): ...
async def request_document_view(request_id: int, doc_type: str): ...
async def get_issuances(
    issuance_count: Union[int, None] = ..., page: Union[int, None] = ...
): ...
async def mint_document() -> None: ...
async def get_issued_docs(issue_id: int): ...
async def get_students(
    student_count: Union[int, None] = ..., page: Union[int, None] = ...
): ...
async def get_student(student_id: int): ...
async def create_student() -> None: ...
