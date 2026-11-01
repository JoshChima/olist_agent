// The three behaviours a restyle could silently break (AIE-47 Testing Decisions, seam 2). Nothing more.
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { FIRST_DAY, LAST_DAY } from "./clock";
import { ClockControls } from "./ClockControls";
import { DeltaStrip } from "./Delta";
import { count, currency } from "./format";

const fetchMock = vi.fn(() => Promise.reject(new Error("no network in tests")));
vi.stubGlobal("fetch", fetchMock);
afterEach(cleanup);

test("a count gets locale separators and no decimals; currency gets two decimals", () => {
  expect(count(1234567.4)).toMatch(/^1\D234\D567$/);
  expect(currency(1013246.2)).toMatch(/^R\$\s1\.013\.246,20$/);
});

test("the step buttons are disabled at the dataset's first and last day", () => {
  const disabled = (name: RegExp) => screen.getAllByRole("button", { name }).map((b) => b.hasAttribute("disabled"));
  const back = /^−1/;
  const forward = /^\+1/;

  const { rerender } = render(<ClockControls clock={FIRST_DAY} onChange={() => {}} />);
  expect(disabled(back)).toEqual([true, true, true]);
  expect(disabled(forward)).toEqual([false, false, false]);

  rerender(<ClockControls clock={LAST_DAY} onChange={() => {}} />);
  expect(disabled(back)).toEqual([false, false, false]);
  expect(disabled(forward)).toEqual([true, true, true]);
});

test("the delta strip says rewound after a rewind", () => {
  const { rerender } = render(<DeltaStrip clock="2018-02-17" />);
  rerender(<DeltaStrip clock="2018-02-10" />);
  expect(screen.getByRole("status").textContent).toBe("rewound");
  expect(fetchMock).not.toHaveBeenCalled();
});
