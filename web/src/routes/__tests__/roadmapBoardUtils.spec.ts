import { describe, expect, it } from "vitest";

import { buildBoardColumns, normalizeStatusValue } from "../roadmapBoardUtils";

describe("normalizeStatusValue", () => {
  it("trims values", () => {
    expect(normalizeStatusValue("  In Review  ")).toBe("In Review");
  });

  it("returns null for empty strings", () => {
    expect(normalizeStatusValue("   ")).toBeNull();
  });
});

describe("buildBoardColumns", () => {
  it("keeps Done as last column", () => {
    const columns = buildBoardColumns(["Backlog", "In Review", "Done"], []);
    expect(columns.map((column) => column.title)).toEqual([
      "Sem etapa",
      "Backlog",
      "In Review",
      "Done",
    ]);
  });

  it("includes statuses found on items", () => {
    const columns = buildBoardColumns(["Backlog", "Done"], [{ status: "QA" }]);
    expect(columns.map((column) => column.title)).toEqual([
      "Sem etapa",
      "Backlog",
      "QA",
      "Done",
    ]);
  });
});
