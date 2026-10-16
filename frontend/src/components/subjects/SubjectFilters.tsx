import {
  type SubjectFilters as Filters,
  type SubjectSortOrder,
} from "../../modules/subjects/public.ts";
import { FilterSelect, SearchField } from "../FilterFields";
import { subjectTypeLabels, subjectSortLabels, termLabels } from "./labels";

interface Props {
  filters: Filters;
  sortOrder: SubjectSortOrder;
  categories: Map<string, string>;
  faculties: string[];
  changeFilter: (key: keyof Filters, value: string) => void;
  changeSort: (value: string) => void;
}
export function SubjectFilters({
  filters,
  sortOrder,
  categories,
  faculties,
  changeFilter,
  changeSort,
}: Props) {
  const select = (
    key: Exclude<keyof Filters, "search">,
    label: string,
    options: (readonly [string, string])[],
  ) => (
    <FilterSelect
      id={key}
      label={label}
      value={filters[key]}
      options={options}
      onChange={(value) => changeFilter(key, value)}
    />
  );
  return (
    <div className="filters">
      <SearchField
        id="search"
        label="科目名を検索"
        placeholder="例：プログラミング、人工知能"
        value={filters.search}
        onChange={(value) => changeFilter("search", value)}
      />
      {select("category", "科目区分", [...categories])}
      {select("type", "種別", Object.entries(subjectTypeLabels))}
      {select("semester", "開講学期", Object.entries(termLabels))}
      {select(
        "faculty",
        "開講学部",
        faculties.map((name) => [name, name]),
      )}
      <FilterSelect
        id="sort"
        label="並べ替え"
        value={sortOrder}
        options={Object.entries(subjectSortLabels)}
        allLabel={null}
        onChange={changeSort}
      />
    </div>
  );
}
