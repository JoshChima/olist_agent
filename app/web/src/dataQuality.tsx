import { ReferenceArea } from "recharts";
import { FIRST_DAY, LAST_DAY } from "./clock";

// GLOSSARY.md "Data-quality window": simulated time whose data can't support business conclusions.
export const DATA_QUALITY_WINDOWS = [
  { from: FIRST_DAY, to: "2016-12-31", label: "sparse data" },
  { from: "2018-09-01", to: LAST_DAY, label: "collection artifact" },
];

/**
 * Shading for the windows that overlap a chart whose category x-axis runs first..last. The
 * axis is ISO days ("2017-11-24") or months ("2017-11"): window dates are cut to that length.
 * The shade and its label take the design system's tokens from the ChartPanel around the chart.
 */
export function dataQualityAreas(first: string, last: string) {
  const cut = (d: string) => d.slice(0, first.length);
  return DATA_QUALITY_WINDOWS.map((w) => ({ ...w, from: cut(w.from), to: cut(w.to) }))
    .filter((w) => w.from <= last && w.to >= first)
    .map((w) => (
      <ReferenceArea
        key={w.from}
        x1={w.from < first ? first : w.from}
        x2={w.to > last ? last : w.to}
        label={{ value: `Data quality: ${w.label}`, position: "insideTop" }}
      />
    ));
}
