import { useTranslation } from "react-i18next";
import {
  type SubjectFilters as Filters,
  type SubjectSortOrder,
} from "../../modules/subjects/public.ts";
import { FilterSelect, SearchField } from "../FilterFields.tsx";
import { subjectTypeLabels, subjectSortLabels, termLabels } from "./labels.ts";
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
  const { t } = useTranslation();
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
        label={t("科目名を検索")}
        placeholder={t("例：プログラミング、人工知能")}
        value={filters.search}
        onChange={(value) => changeFilter("search", value)}
      />
      {select("category", t("科目区分"), [...categories])}
      {select(
        "type",
        t("種別"),
        Object.entries(subjectTypeLabels).map(
          ([key, label]) => [key, t(label)] as const,
        ),
      )}
      {select(
        "semester",
        t("開講学期"),
        Object.entries(termLabels).map(
          ([key, label]) => [key, t(label)] as const,
        ),
      )}
      {select(
        "faculty",
        t("開講学部"),
        faculties.map((name) => [name, name]),
      )}
      <FilterSelect
        id="sort"
        label={t("並べ替え")}
        value={sortOrder}
        options={Object.entries(subjectSortLabels).map(
          ([key, label]) => [key, t(label)] as const,
        )}
        allLabel={null}
        onChange={changeSort}
      />
    </div>
  );
}
