import { parseApiError } from "@/lib/api";

describe("parseApiError", () => {
  it("returns plain string detail as-is", () => {
    expect(parseApiError({ detail: "Incorrect email or password" }, "fallback")).toBe(
      "Incorrect email or password",
    );
  });

  it("flattens Pydantic 422 error arrays into readable messages", () => {
    const body = {
      detail: [
        {
          loc: ["body", "password"],
          msg: "String should have at least 8 characters",
          type: "string_too_short",
        },
      ],
    };
    expect(parseApiError(body, "fallback")).toBe(
      "password: String should have at least 8 characters",
    );
  });

  it("joins multiple validation errors", () => {
    const body = {
      detail: [
        { loc: ["body", "email"], msg: "value is not a valid email address", type: "value_error" },
        { loc: ["body", "password"], msg: "String should have at least 8 characters", type: "string_too_short" },
      ],
    };
    const msg = parseApiError(body, "fallback");
    expect(msg).toContain("email:");
    expect(msg).toContain("password:");
  });

  it("falls back for missing or malformed detail", () => {
    expect(parseApiError({}, "Signup failed")).toBe("Signup failed");
    expect(parseApiError(null, "Signup failed")).toBe("Signup failed");
    expect(parseApiError({ detail: { weird: true } }, "Signup failed")).toBe("Signup failed");
  });
});
