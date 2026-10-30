import { useRef, type KeyboardEvent } from "react";

type MultiSelectFilterProps = {
  label: string;
  options: string[];
  selected: string[];
  onChange: (values: string[]) => void;
};

export function MultiSelectFilter({ label, options, selected, onChange }: MultiSelectFilterProps) {
  const root = useRef<HTMLDetailsElement>(null);

  function handleKeyDown(event: KeyboardEvent<HTMLDetailsElement>) {
    if (event.key === "Escape") {
      root.current?.removeAttribute("open");
      root.current?.querySelector("summary")?.focus();
    }
  }

  return (
    <details className="multi-filter" onKeyDown={handleKeyDown} ref={root}>
      <summary aria-label={`${label} filters`}>
        {label}{selected.length > 0 ? ` · ${selected.length}` : ""}
      </summary>
      <div aria-label={label} className="multi-filter-options" role="group">
        {options.map((option) => (
          <label className="multi-filter-option" key={option}>
            <input
              checked={selected.includes(option)}
              onChange={(event) => {
                onChange(event.target.checked
                  ? [...selected, option]
                  : selected.filter((value) => value !== option));
              }}
              type="checkbox"
              value={option}
            />
            <span>{option}</span>
          </label>
        ))}
      </div>
    </details>
  );
}
