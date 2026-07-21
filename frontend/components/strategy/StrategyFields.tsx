"use client";

import type { StrategyDefinition } from "@/lib/api-client/types";

interface StrategyFieldsProps {
  definitions: StrategyDefinition[];
  type: string;
  onTypeChange: (type: string) => void;
  params: Record<string, number>;
  onParamsChange: (params: Record<string, number>) => void;
  label: string;
}

const selectClass =
  "rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-sm outline-none focus:border-white/30";
const inputClass =
  "w-24 rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-sm outline-none focus:border-white/30";

/** Strategy Builder (Phase 6): renders whichever parameters the selected
 * strategy declares — driven entirely by the backend's `/strategies`
 * catalog, so a new strategy type needs no frontend code change. */
export function StrategyFields({
  definitions,
  type,
  onTypeChange,
  params,
  onParamsChange,
  label,
}: StrategyFieldsProps) {
  const active = definitions.find((d) => d.type === type);

  return (
    <>
      <label className="flex flex-col gap-1 text-sm text-[var(--muted)]">
        {label}
        <select
          value={type}
          onChange={(e) => {
            const next = definitions.find((d) => d.type === e.target.value);
            onTypeChange(e.target.value);
            if (next) {
              onParamsChange(
                Object.fromEntries(next.parameters.map((p) => [p.name, p.default])),
              );
            }
          }}
          className={selectClass}
        >
          {definitions.map((d) => (
            <option key={d.type} value={d.type}>
              {d.label}
            </option>
          ))}
        </select>
      </label>
      {active?.parameters.map((param) => (
        <label
          key={param.name}
          className="flex flex-col gap-1 text-sm text-[var(--muted)]"
        >
          {param.label}
          <input
            type="number"
            min={param.min}
            max={param.max}
            value={params[param.name] ?? param.default}
            onChange={(e) =>
              onParamsChange({ ...params, [param.name]: Number(e.target.value) })
            }
            className={inputClass}
          />
        </label>
      ))}
      {active && (
        <p className="w-full text-xs text-[var(--muted)]">{active.description}</p>
      )}
    </>
  );
}
