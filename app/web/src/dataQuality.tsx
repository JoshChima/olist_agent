import { ReferenceArea } from "recharts";

// GLOSSARY.md "Data-quality window": simulated time whose data can't support business conclusions.
export const DATA_QUALITY_WINDOWS = [
  { from: "2016-09-04", to: "2016-12-31", label: "sparse data" },
  { from: "2018-09-01", to: "2018-10-17", label: "collection artifact" },
];

/** Shading for the windows that overlap a chart whose category x-axis is the days first..last. */
export function dataQualityAreas(first: string, last: string) {
  return DATA_QUALITY_WINDOWS.filter((w) => w.from <= last && w.to >= first).map((w) => (
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
