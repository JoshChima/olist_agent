import { FIRST_DAY, LAST_DAY, step, type Step } from "./clock";

const STEPS: [Step, string][] = [
  ["month", "M"],
  ["week", "W"],
  ["day", "D"],
];

/** The date input bounded to the dataset, then the six step buttons: back (−1M −1W −1D), forward (+1D +1W +1M). */
export function ClockControls({ clock, onChange }: { clock: string; onChange: (day: string) => void }) {
  return (
    <>
      <label>
        Clock{" "}
        <input type="date" min={FIRST_DAY} max={LAST_DAY} value={clock} onChange={(e) => onChange(e.target.value)} />
      </label>
      <span style={{ display: "flex", gap: "0.25rem" }}>
        {STEPS.map(([unit, short]) => (
          <button
            className="btn btn-sm preset-tonal"
            key={unit}
            title={`Back one ${unit}`}
            disabled={clock <= FIRST_DAY}
            onClick={() => onChange(step(clock, unit, -1))}
          >
            −1{short}
          </button>
        ))}
        {[...STEPS].reverse().map(([unit, short]) => (
          <button
            className="btn btn-sm preset-tonal"
            key={unit}
            title={`Forward one ${unit}`}
            disabled={clock >= LAST_DAY}
            onClick={() => onChange(step(clock, unit, 1))}
          >
            +1{short}
          </button>
        ))}
      </span>
    </>
  );
}
