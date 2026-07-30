import { describe, expect, it } from "vitest";
import { cleanSnippet, formatBytes, label } from "../utils";

describe("formatting helpers", () => {
  it("formats file sizes for operational tables", () => {
    expect(formatBytes(500)).toBe("500 B");
    expect(formatBytes(2048)).toBe("2.0 KB");
    expect(formatBytes(3 * 1024 * 1024)).toBe("3.0 MB");
  });

  it("turns enum values into readable labels", () => {
    expect(label("NEEDS_REVIEW")).toBe("Needs Review");
    expect(label(null)).toBe("Unclassified");
  });

  it("removes server highlight markers from safe snippets", () => {
    expect(cleanSnippet("<mark>invoice</mark> total")).toBe("invoice total");
  });
});
