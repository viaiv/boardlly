import { describe, expect, it } from "vitest";

import {
  classifyProjectItem,
  classificationBadgeClass,
  formatDateForInput,
  convertDateInputToIso,
  formatDateDisplay,
  type ProjectItem,
} from "../project-items";

describe("classifyProjectItem", () => {
  it("flags epic using field type", () => {
    const item: ProjectItem = {
      id: 1,
      item_node_id: "node",
      field_values: { Type: "Epic" },
    };
    const result = classifyProjectItem(item);
    expect(result.typeLabel).toBe("Épico");
    expect(result.accent).toBe("epic");
  });

  it("falls back to content type", () => {
    const item: ProjectItem = {
      id: 2,
      item_node_id: "node-2",
      content_type: "Issue",
    };
    const result = classifyProjectItem(item);
    expect(result.typeLabel).toBe("Issue");
    expect(result.accent).toBe("issue");
  });

  it("captures linked epic names", () => {
    const item: ProjectItem = {
      id: 3,
      item_node_id: "node-3",
      field_values: { Epic: "Nebula" },
    };
    const result = classifyProjectItem(item);
    expect(result.epicName).toBe("Nebula");
  });

  it("prefers persisted epic name", () => {
    const item: ProjectItem = {
      id: 4,
      item_node_id: "node-4",
      epic_name: "Solaris",
    };
    const result = classifyProjectItem(item);
    expect(result.epicName).toBe("Solaris");
  });
});

describe("classificationBadgeClass", () => {
  it("returns classes for epic variant", () => {
    const classes = classificationBadgeClass("epic");
    expect(classes).toContain("purple");
  });
});

describe("date helpers", () => {
  it("formats ISO string to input value", () => {
    expect(formatDateForInput("2025-01-15T00:00:00Z")).toBe("2025-01-15");
  });

  it("converts input date to ISO", () => {
    expect(convertDateInputToIso("2025-02-03")).toBe("2025-02-03T00:00:00.000Z");
  });

  it("formats date for display", () => {
    expect(formatDateDisplay("2025-03-10T12:30:00Z")).toContain("2025");
  });
});
