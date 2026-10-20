import { useTranslation } from "react-i18next";
import type {
  CatalogCategory,
  CatalogFilters,
} from "../../modules/subjects/public.ts";
import type { GradeFilters as Filters } from "../../modules/grades/public.ts";
import { FilterSelect, SearchField } from "../FilterFields.tsx";
import { termLabels } from "../subjects/labels.ts";
import { courseStatusLabels } from "./labels.ts";
type Key = keyof (CatalogFilters & Filters);
// 子の区分を親の直後に並べ、字下げで階層を示す。
function treeOrder(categories: CatalogCategory[]): CatalogCategory[] {
  const ordered: CatalogCategory[] = [];
  const visit = (parentId: string | null) => {
    for (const category of categories
      .filter((c) => c.parentId === parentId)
      .sort((a, b) => a.displayOrder - b.displayOrder)) {
      ordered.push(category);
      visit(category.id);
    }
  };
  visit(null);
  return ordered;
}
export function GradeFilters({
  filters,
  categories,
  faculties,
  departments,
  years,
  changeFilter,
}: {
  filters: CatalogFilters & Filters;
  categories: CatalogCategory[];
  faculties: string[];
  departments: string[];
  years: number[];
  changeFilter: (key: Key, value: string) => void;
}) {
  const { t } = useTranslation();
  const select = (
    key: Exclude<Key, "search">,
    label: string,
    options: (readonly [string, string])[],
    disabled = false,
  ) => (
    <FilterSelect
      id={`grade-filter-${key}`}
      label={label}
      value={filters[key]}
      options={options}
      disabled={disabled}
      onChange={(value) => changeFilter(key, value)}
    />
  );
  return (
    <div className="filters grade-filters">
      <SearchField
        id="grade-filter-search"
        label={t("科目名・科目コードを検索")}
        placeholder={t("例：プログラミング、CS-C001")}
        value={filters.search}
        onChange={(value) => changeFilter("search", value)}
      />
      {select(
        "categoryId",
        t("科目区分"),
        treeOrder(categories).map((c) => [
          c.id,
          `${"　".repeat(c.level)}${c.name}`,
        ]),
      )}
      {select(
        "faculty",
        t("開講学部"),
        faculties.map((name) => [name, name]),
      )}
      {select(
        "department",
        t("開講学科"),
        departments.map((name) => [name, name]),
        departments.length === 0,
      )}
      {select(
        "semester",
        t("開講学期"),
        Object.entries(termLabels).map(
          ([key, label]) => [key, t(label)] as const,
        ),
      )}
      {select(
        "status",
        t("修得状況"),
        Object.entries(courseStatusLabels).map(
          ([key, label]) => [key, t(label)] as const,
        ),
      )}
      {select(
        "year",
        t("履修年度"),
        years.map((year) => [
          String(year),
          t("{{value0}}年度", { value0: year }),
        ]),
        years.length === 0,
      )}
      {select(
        "term",
        t("履修学期"),
        Object.entries(termLabels).map(
          ([key, label]) => [key, t(label)] as const,
        ),
      )}
    </div>
  );
}
