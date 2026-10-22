package schemas

import (
	"grad-checker/backend/modules/accounts/application/ports"
)

func DecodeSelection(body []byte) (*ports.ProgramSelection, bool) {
	fields, ok := StrictObject(body, "program_id", "curriculum_id", "expected_revision")
	if !ok {
		return nil, false
	}
	var selection ports.ProgramSelection
	if selection.ProgramID, ok = DecodeUUID(fields["program_id"]); !ok {
		return nil, false
	}
	if selection.CurriculumID, ok = DecodeUUID(fields["curriculum_id"]); !ok {
		return nil, false
	}
	if selection.ExpectedRevision, ok = DecodeInt(fields["expected_revision"], 0, MaxSafeRevision); !ok {
		return nil, false
	}
	return &selection, true
}

const SelectionDetail = "所属・カリキュラム・更新版を正しい形式で指定してください。"
