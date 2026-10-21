"""Goからユースケースを呼ぶブリッジアダプター。外部API仕様は持たない。"""

from typing import Annotated

from fastapi import APIRouter, Depends

from apps.bridge.controllers.go_bridge_call import respond
from apps.bridge.dependencies import get_subject_list, list_subject_programs
from apps.bridge.schemas.subject_list import SubjectListCall
from modules.subjects.public import GetSubjectListUseCase, ListSubjectProgramsUseCase

router = APIRouter(prefix="/bridge")


@router.post("/subject-list")
def subject_list(
    call: SubjectListCall,
    get_list: Annotated[GetSubjectListUseCase, Depends(get_subject_list)],
    list_programs: Annotated[
        ListSubjectProgramsUseCase, Depends(list_subject_programs)
    ],
) -> dict[str, object]:

    def run() -> object:
        if call.curriculum_id is None:
            return list_programs.execute()
        return get_list.execute(call.curriculum_id)

    return respond(run)
