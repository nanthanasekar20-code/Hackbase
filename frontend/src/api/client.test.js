import { describe, it, expect, vi, beforeEach } from "vitest";

// axios.create() is called once at module load in client.js — mock it to
// return one fixed object so every test controls the exact same `post` spy
// the module actually calls through.
const post = vi.fn();
vi.mock("axios", () => ({
  default: {
    create: () => ({
      post,
      get: vi.fn(),
      patch: vi.fn(),
      delete: vi.fn(),
      interceptors: { request: { use: vi.fn() } },
    }),
  },
}));

const { generatePlan, exportRoadmapPptx } = await import("./client.js");

describe("generatePlan", () => {
  beforeEach(() => {
    post.mockReset();
  });

  it("dedupes concurrent calls for the same problem statement into one real request", async () => {
    // Simulates React StrictMode's dev-only double-effect-invoke, or a user
    // navigating away from a roadmap page and back while a generation is
    // still in flight — both call generatePlan() with the same text before
    // the first call has resolved.
    let resolveFirst;
    post.mockReturnValue(
      new Promise((resolve) => {
        resolveFirst = resolve;
      })
    );

    const call1 = generatePlan("Build a crop disease detector.");
    const call2 = generatePlan("Build a crop disease detector.");

    expect(post).toHaveBeenCalledTimes(1); // only one real, quota-consuming request fired

    resolveFirst({ data: { roadmap: [] } });
    await expect(call1).resolves.toEqual({ roadmap: [] });
    await expect(call2).resolves.toEqual({ roadmap: [] }); // both callers get the same real result
  });

  it("makes a new real request once the previous one has resolved", async () => {
    post.mockResolvedValueOnce({ data: { roadmap: ["first"] } });
    await generatePlan("Build a crop disease detector.");

    post.mockResolvedValueOnce({ data: { roadmap: ["second"] } });
    await generatePlan("Build a crop disease detector.");

    // A genuine "Regenerate roadmap" click after the first one finished
    // must still reach Gemini again — dedup must not become permanent caching.
    expect(post).toHaveBeenCalledTimes(2);
  });

  it("still fires a real request for a different problem statement", async () => {
    post.mockResolvedValue({ data: { roadmap: [] } });

    await Promise.all([generatePlan("Problem A"), generatePlan("Problem B")]);

    expect(post).toHaveBeenCalledTimes(2);
  });

  it("clears the in-flight entry even when the request fails, so a retry can go through", async () => {
    post.mockReturnValueOnce(Promise.reject(new Error("503")));
    await expect(generatePlan("Build a crop disease detector.")).rejects.toThrow("503");

    post.mockResolvedValueOnce({ data: { roadmap: [] } });
    await generatePlan("Build a crop disease detector.");

    expect(post).toHaveBeenCalledTimes(2);
  });
});

describe("exportRoadmapPptx", () => {
  beforeEach(() => {
    post.mockReset();
    window.URL.createObjectURL = vi.fn(() => "blob:mock-url");
    window.URL.revokeObjectURL = vi.fn();
  });

  it("sends the already-generated plan (not just a problem id) so export costs no extra Gemini call", async () => {
    const plan = { roadmap: [], tech_stack: ["Python"] };
    post.mockResolvedValueOnce({
      data: new Blob(["fake pptx bytes"]),
      headers: { "content-disposition": 'attachment; filename="crop-disease-detector.pptx"' },
    });

    await exportRoadmapPptx({
      problemTitle: "Crop Disease Detector",
      problemStatement: "Detect crop disease from leaf images.",
      source: "sih",
      hackathonName: "Smart India Hackathon 2025",
      plan,
    });

    expect(post).toHaveBeenCalledWith(
      "/plan/export-pptx",
      {
        problem_title: "Crop Disease Detector",
        problem_statement: "Detect crop disease from leaf images.",
        source: "sih",
        hackathon_name: "Smart India Hackathon 2025",
        plan,
      },
      { responseType: "blob" }
    );
  });

  it("triggers a real browser download named from the backend's Content-Disposition header", async () => {
    post.mockResolvedValueOnce({
      data: new Blob(["fake pptx bytes"]),
      headers: { "content-disposition": 'attachment; filename="crop-disease-detector.pptx"' },
    });
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

    await exportRoadmapPptx({ problemTitle: "Crop Disease Detector", plan: {} });

    expect(window.URL.createObjectURL).toHaveBeenCalled();
    expect(clickSpy).toHaveBeenCalledTimes(1);
    expect(window.URL.revokeObjectURL).toHaveBeenCalledWith("blob:mock-url");

    clickSpy.mockRestore();
  });
});
