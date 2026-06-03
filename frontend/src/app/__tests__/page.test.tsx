/**
 * Basic smoke test — verifies the page module exports a default component.
 * Full integration tests require a running backend; kept lightweight here.
 */
import { expect, test } from "@jest/globals";

test("page module exports a default function", async () => {
  const mod = await import("../page");
  expect(typeof mod.default).toBe("function");
});
