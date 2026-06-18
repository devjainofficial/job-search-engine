"use client";

import { useState } from "react";

// Chip/"bubble" input: type and press Enter or comma to add a tag; click × or
// press Backspace (empty field) to remove. Used for roles, skills, and cities.
export default function TagInput({
  value,
  onChange,
  placeholder,
  max = 30,
  suggestions = [],
}: {
  value: string[];
  onChange: (next: string[]) => void;
  placeholder?: string;
  max?: number;
  suggestions?: string[];
}) {
  const [draft, setDraft] = useState("");

  function add(raw: string) {
    const t = raw.trim();
    if (t && value.length < max && !value.some((v) => v.toLowerCase() === t.toLowerCase())) {
      onChange([...value, t]);
    }
    setDraft("");
  }

  const remaining = suggestions.filter((s) => !value.some((v) => v.toLowerCase() === s.toLowerCase())).slice(0, 6);

  return (
    <div>
      <div className="taginput" onClick={(e) => (e.currentTarget.querySelector("input") as HTMLInputElement)?.focus()}>
        {value.map((t) => (
          <span className="chip" key={t}>
            {t}
            <button type="button" aria-label={`Remove ${t}`} onClick={() => onChange(value.filter((x) => x !== t))}>×</button>
          </span>
        ))}
        <input
          value={draft}
          placeholder={value.length ? "" : placeholder}
          onChange={(e) => {
            const v = e.target.value;
            if (v.endsWith(",")) add(v.slice(0, -1));
            else setDraft(v);
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter") { e.preventDefault(); add(draft); }
            else if (e.key === "Backspace" && !draft && value.length) onChange(value.slice(0, -1));
          }}
          onBlur={() => draft && add(draft)}
        />
      </div>
      {remaining.length > 0 && (
        <div className="suggest">
          {remaining.map((s) => (
            <button type="button" key={s} className="chip add" onClick={() => add(s)}>+ {s}</button>
          ))}
        </div>
      )}
    </div>
  );
}
