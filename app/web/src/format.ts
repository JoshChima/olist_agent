// Number formatting for the counts and amounts the app shows (AIE-47 story 17).

/** A count: the visitor's locale separators, no decimals. */
export const count = (n: number) => n.toLocaleString(undefined, { maximumFractionDigits: 0 });

/** An amount in the dataset's currency, Brazilian real, with two decimals. */
export const currency = (n: number) => n.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
