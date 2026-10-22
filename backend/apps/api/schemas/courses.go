package schemas

import (
	"net/url"
	"unicode/utf8"

	"grad-checker/backend/modules/subjects/application/ports"
)

func ParseCourseFilters(rawQuery string) (*ports.CourseFilters, string) {
	query, err := url.ParseQuery(rawQuery)
	if err != nil {
		return nil, "絞り込み条件の形式が不正です。"
	}
	values := map[string]string{}
	for key, list := range query {
		if !CourseFilterKeys[key] {
			return nil, "未対応の絞り込み条件が指定されています。"
		}
		if len(list) != 1 || list[0] == "" || utf8.RuneCountInString(list[0]) > 100 {
			return nil, "絞り込み条件は各1回、1〜100文字で指定してください。"
		}
		values[key] = list[0]
	}
	filters := &ports.CourseFilters{Faculty: values["faculty"], Department: values["department"], Q: values["q"]}
	if id, ok := values["category_id"]; ok {
		if filters.CategoryID, err = NormalizeUUID(id); err != nil {
			return nil, "科目区分IDの形式が不正です。"
		}
	}
	if semester, ok := values["semester"]; ok {
		if semester != "first" && semester != "second" {
			return nil, "開講学期はfirst（前期）またはsecond（後期）で指定してください。"
		}
		filters.Semester = semester
	}
	return filters, ""
}

var CourseFilterKeys = map[string]bool{"category_id": true, "faculty": true, "department": true, "semester": true, "q": true}
