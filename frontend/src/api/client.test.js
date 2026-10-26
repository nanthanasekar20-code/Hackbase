import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// axios.create() is called once at module load in client.js — mock it to
// return one fixed object so every test controls the exact same `post`/`get`
// spies the module actually calls through.
const post = vi.fn();
const get = vi.fn();
vi.mock("axios", () => ({
  default: {
    create: () => ({
      post,
      get,
      patch: vi.fn(),
      delete: vi.fn(),
      interceptors: { request: { use: vi.fn() } },
    }),
  },
}));

const { generatePlan, exportFavoritePptx, viewFavoritePdf, getRandomProblems, getProblems } = await import(
  "./client.js"
);

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

describe("exportFavoritePptx", () => {
  beforeEach(() => {
    get.mockReset();
    window.URL.createObjectURL = vi.fn(() => "blob:mock-url");
    window.URL.revokeObjectURL = vi.fn();
  });

  it("requests the cached PPT for the project by problem id, not by resending the plan", async () => {
    get.mockResolvedValueOnce({
      data: new Blob(["fake pptx bytes"]),
      headers: { "content-disposition": 'attachment; filename="crop-disease-detector.pptx"' },
    });

    await exportFavoritePptx("sih:p1");

    expect(get).toHaveBeenCalledWith("/favorites/sih%3Ap1/export-pptx", { responseType: "blob" });
  });

  it("triggers a real browser download named from the backend's Content-Disposition header", async () => {
    get.mockResolvedValueOnce({
      data: new Blob(["fake pptx bytes"]),
      headers: { "content-disposition": 'attachment; filename="crop-disease-detector.pptx"' },
    });
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

    await exportFavoritePptx("sih:p1");

    expect(window.URL.createObjectURL).toHaveBeenCalled();
    expect(clickSpy).toHaveBeenCalledTimes(1);
    expect(window.URL.revokeObjectURL).toHaveBeenCalledWith("blob:mock-url");

    clickSpy.mockRestore();
  });
});

describe("viewFavoritePdf", () => {
  beforeEach(() => {
    get.mockReset();
    window.URL.createObjectURL = vi.fn(() => "blob:mock-pdf-url");
    window.URL.revokeObjectURL = vi.fn();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("requests the PDF rendering for the project by problem id", async () => {
    get.mockResolvedValueOnce({ data: new Blob(["fake pdf bytes"]) });
    const openSpy = vi.spyOn(window, "open").mockImplementation(() => {});

    await viewFavoritePdf("sih:p1");

    expect(get).toHaveBeenCalledWith("/favorites/sih%3Ap1/view-pdf", { responseType: "blob" });

    openSpy.mockRestore();
  });

  it("opens the PDF in a new tab instead of downloading it", async () => {
    get.mockResolvedValueOnce({ data: new Blob(["fake pdf bytes"]) });
    const openSpy = vi.spyOn(window, "open").mockImplementation(() => {});

    await viewFavoritePdf("sih:p1");

    expect(window.URL.createObjectURL).toHaveBeenCalled();
    expect(openSpy).toHaveBeenCalledWith("blob:mock-pdf-url", "_blank", "noopener,noreferrer");
    expect(window.URL.revokeObjectURL).not.toHaveBeenCalled(); // not yet — only after the delay

    vi.advanceTimersByTime(60_000);
    expect(window.URL.revokeObjectURL).toHaveBeenCalledWith("blob:mock-pdf-url");

    openSpy.mockRestore();
  });
});

describe("getRandomProblems", () => {
  beforeEach(() => {
    get.mockReset();
  });

  it("requests the given count from /problems/random", async () => {
    get.mockResolvedValueOnce({ data: { problems: [] } });
    await getRandomProblems(6);
    expect(get).toHaveBeenCalledWith("/problems/random", { params: { count: 6 } });
  });

  it("defaults to 6 when no count is given", async () => {
    get.mockResolvedValueOnce({ data: { problems: [] } });
    await getRandomProblems();
    expect(get).toHaveBeenCalledWith("/problems/random", { params: { count: 6 } });
  });
});

describe("getProblems", () => {
  beforeEach(() => {
    get.mockReset();
  });

  it("requests page 1 / page_size 20 by default", async () => {
    get.mockResolvedValueOnce({ data: { problems: [], total: 0 } });
    await getProblems();
    expect(get).toHaveBeenCalledWith("/problems", {
      params: { page: 1, page_size: 20, domain: undefined, source: undefined, category: undefined, difficulty: undefined },
    });
  });

  it("passes through a requested page and filters", async () => {
    get.mockResolvedValueOnce({ data: { problems: [], total: 0 } });
    await getProblems({ page: 3, pageSize: 10, domain: "AI/ML", source: "sih" });
    expect(get).toHaveBeenCalledWith("/problems", {
      params: { page: 3, page_size: 10, domain: "AI/ML", source: "sih", category: undefined, difficulty: undefined },
    });
  });
});
