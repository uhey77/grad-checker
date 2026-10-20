export type CourseType = "required" | "selective" | "elective";

// 本人課程の科目表にある科目だけが持つ分類・種別。課程外の科目には推測で設定しない。
export interface CoursePlacement {
  classificationPath: { id: string; name: string }[];
  courseType: CourseType;
}
