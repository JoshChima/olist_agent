import { ReferenceArea } from "recharts";

// GLOSSARY.md "Data-quality window": simulated time whose data can't support business conclusions.
export const DATA_QUALITY_WINDOWS = [
  { from: "2016-09-04", to: "2016-12-31", label: "sparse data" },
  { from: "2018-09-01", to: "2018-10-17", label: "collection artifact" },
];

/**
 * Shading for the windows that overlap a chart whose category x-axis runs first..last. The
 * axis is ISO days ("2017-11-24") or months ("2017-11"): window dates are cut to that length.
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
        fill="#888"
        fillOpacity={0.18}
        label={{ value: `Data quality: ${w.label}`, position: "insideTop", fontSize: 11, fill: "#555" }}
      />
    ));
}
