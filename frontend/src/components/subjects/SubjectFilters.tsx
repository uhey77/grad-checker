import {
  type SubjectFilters as Filters,
  type SubjectSortOrder,
} from "../../modules/subjects/public.ts";

import { subjectTypeLabels, subjectSortLabels } from "./labels";

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
  return (
    <div className="filters">
      <div className="search-field">
        <label htmlFor="search">科目名を検索</label>
        <input
          id="search"
          type="search"
          placeholder="例：プログラミング、人工知能"
          value={filters.search}
          onChange={(event) => changeFilter("search", event.target.value)}
        />
      </div>
      <div>
        <label htmlFor="category">科目区分</label>
        <select
          id="category"
          value={filters.category}
          onChange={(event) => changeFilter("category", event.target.value)}
        >
          <option value="">すべての区分</option>
          {[...categories].map(([id, name]) => (
            <option key={id} value={id}>
              {name}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="type">必修区分</label>
        <select
          id="type"
          value={filters.type}
          onChange={(event) => changeFilter("type", event.target.value)}
        >
          <option value="">すべての種別</option>
          {Object.entries(subjectTypeLabels).map(([type, label]) => (
            <option key={type} value={type}>
              {label}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="semester">開講学期</label>
        <select
          id="semester"
          value={filters.semester}
          onChange={(event) => changeFilter("semester", event.target.value)}
        >
          <option value="">すべての学期</option>
          <option value="first">前期</option>
          <option value="second">後期</option>
        </select>
      </div>
      <div>
        <label htmlFor="faculty">開講学部</label>
        <select
          id="faculty"
          value={filters.faculty}
          onChange={(event) => changeFilter("faculty", event.target.value)}
        >
          <option value="">すべての学部</option>
          {faculties.map((name) => (
            <option key={name}>{name}</option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="sort">並べ替え</label>
        <select
          id="sort"
          value={sortOrder}
          onChange={(event) => {
            changeSort(event.target.value);
          }}
        >
          {Object.entries(subjectSortLabels).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
