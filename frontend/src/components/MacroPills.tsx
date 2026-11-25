import React from "react";

interface MacroPillsProps {
  kcal: number;
  protein: number;
  carbs: number;
  fat?: number;
  fiber?: number;
  complexRatio?: number;
  compact?: boolean;
}

export const MacroPills: React.FC<MacroPillsProps> = ({
  kcal,
  protein,
  carbs,
  fat,
  fiber,
  complexRatio,
  compact = false,
}) => {
  return (
    <div className="flex flex-wrap items-center gap-1.5 tabular-nums">
      <span
        className={`inline-flex items-center rounded-full border border-[#E6DFD5] bg-[#F6F3EE] font-semibold text-[#1E2421] ${
          compact ? "px-2 py-0.5 text-[11px]" : "px-2.5 py-0.5 text-xs"
        }`}
      >
        {Math.round(kcal)} kcal
      </span>
      <span
        className={`inline-flex items-center rounded-full border border-[#CBE0EE] bg-[#EDF5FA] font-semibold text-[#235478] ${
          compact ? "px-2 py-0.5 text-[11px]" : "px-2.5 py-0.5 text-xs"
        }`}
      >
        P {Math.round(protein)}g
      </span>
      <span
        className={`inline-flex items-center rounded-full border border-[#F0DEC0] bg-[#FDF6E9] font-semibold text-[#946110] ${
          compact ? "px-2 py-0.5 text-[11px]" : "px-2.5 py-0.5 text-xs"
        }`}
        title={
          complexRatio !== undefined
            ? `${Math.round(complexRatio)}% komplexe Kohlenhydrate`
            : undefined
        }
      >
        KH {Math.round(carbs)}g
        {!compact && complexRatio !== undefined && complexRatio >= 65 && (
          <span className="ml-1 text-[10px] opacity-80">
            · {Math.round(complexRatio)}% kompl.
          </span>
        )}
      </span>
      {fat !== undefined && !compact && (
        <span className="inline-flex items-center rounded-full border border-[#E7D7E3] bg-[#F8F1F6] px-2.5 py-0.5 text-xs font-medium text-[#6B3F5E]">
          F {Math.round(fat)}g
        </span>
      )}
      {fiber !== undefined && !compact && fiber >= 5 && (
        <span className="inline-flex items-center rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-800">
          {Math.round(fiber)}g Ballastst.
        </span>
      )}
    </div>
  );
};

interface MacroProgressBarProps {
  label: string;
  value: number;
  target: number;
  unit: string;
  colorClass: string;
  subtext?: string;
}

export const MacroProgressBar: React.FC<MacroProgressBarProps> = ({
  label,
  value,
  target,
  unit,
  colorClass,
  subtext,
}) => {
  const pct = Math.min(Math.round((value / Math.max(target, 1)) * 100), 100);
  return (
    <div className="space-y-1">
      <div className="flex items-baseline justify-between text-xs">
        <span className="font-medium text-[#5A635E]">{label}</span>
        <span className="tabular-nums font-semibold text-[#1E2421]">
          {Math.round(value)}
          <span className="font-normal text-[#7B847E]">
            {" "}
            / {Math.round(target)} {unit}
          </span>
        </span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-[#ECE6DC]">
        <div
          className={`h-full rounded-full transition-all duration-300 ${colorClass}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      {subtext && <p className="text-[11px] text-[#7B847E]">{subtext}</p>}
    </div>
  );
};
