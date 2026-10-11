// Application logic tested against a small DOM double, without a browser or network.
// Visual/responsive QA remains a separate real-browser release check.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const fixture = JSON.parse(
  fs.readFileSync(path.join(__dirname, "fixtures/scenario.json"), "utf8"),
);

class Element {
  constructor() {
    this.children = [];
    this.textContent = "";
    this.style = {};
    this.handlers = {};
    this.hidden = false;
    this.disabled = false;
    this.value = "";
  }
  append(...children) {
    this.children.push(...children);
  }
  replaceChildren(...children) {
    this.children = children;
  }
  setAttribute(name, value) {
    this[name] = value;
  }
  addEventListener(name, fn) {
    this.handlers[name] = fn;
  }
  click() {
    if (this.handlers.click) return this.handlers.click();
  }
}
function application() {
  const elements = {};
  const get = (id) => elements[id] || (elements[id] = new Element());
  get("case").value = "earnings";
  get("preset").value = "original";
  const fakeDocument = {
    getElementById: get,
    createElement: () => new Element(),
    createElementNS: () => new Element(),
  };
  const exported = [];
  const ctx = vm.createContext({
    document: fakeDocument,
    window: {
      DEMO_DATA: {
        "earnings:original": structuredClone(fixture),
        "earnings:reverse": structuredClone(fixture),
      },
    },
    console,
    setTimeout: (fn) => fn(),
    Blob,
    URL: {
      createObjectURL: (blob) => {
        exported.push(blob);
        return "blob:fixture";
      },
      revokeObjectURL: () => {},
    },
    fetch: () => {
      throw new Error("Offline demo must not fetch");
    },
  });
  vm.runInContext(
    fs.readFileSync(
      path.join(__dirname, "../server/src/tradefloor/assets/app.js"),
      "utf8",
    ),
    ctx,
  );
  return { ctx, get, exported };
}
test("fixture renders baselines, fan, evidence and falsification without network", () => {
  const { get } = application();
  assert.equal(get("output").hidden, false);
  assert.equal(
    get("p-up").textContent,
    (fixture.result.scenario.p_up * 100).toFixed(1) + "%",
  );
  assert.equal(get("comparison").children.length, 4);
  assert.ok(get("fan").children.length > 10);
  assert.ok(get("failure").textContent.includes("Threshold"));
  assert.equal(get("graph").children[0].children.length, 4);
});
test("reveals synthetic settlement and exports original hash-preserving JSON bytes", async () => {
  const { get, exported } = application();
  get("reveal").click();
  assert.equal(get("settlement").hidden, false);
  assert.ok(
    get("settlement").textContent.includes("not a performance benchmark"),
  );
  get("export").click();
  assert.equal(await exported[0].text(), fixture.bundle_json);
});
test("untrusted imported evidence becomes text and invalid files report errors", async () => {
  const { get } = application();
  const b = JSON.parse(fixture.bundle_json);
  b.result.evidence_graph.nodes[0].text = "<img src=x onerror=alert(1)>";
  get("import").files = [{ size: 1000, text: async () => JSON.stringify(b) }];
  await get("import").handlers.change({ target: get("import") });
  const node = get("graph").children[0].children[0];
  assert.equal(node.children[1].textContent, "<img src=x onerror=alert(1)>");
  assert.ok(get("integrity").textContent.includes("Unverified"));
  get("import").files = [{ size: 1000, text: async () => "{invalid" }];
  await get("import").handlers.change({ target: get("import") });
  assert.equal(get("message").className, "error");
});
test("offline fork uses supplied precomputed fixture with explicit lineage note", () => {
  const { get } = application();
  get("preset").value = "reverse";
  get("fork").click();
  assert.ok(get("message").textContent.includes("precomputed fork"));
});

test("mobile fan keeps a viewport-sized coordinate system instead of shrinking its labels", () => {
  const { ctx, get } = application();
  get("fan").clientWidth = 300;
  vm.runInContext("fanChart(current.result)", ctx);
  assert.equal(get("fan").viewBox, "0 0 300 230");
  const lines = get("fan").children.filter((e) => e.x1 !== undefined);
  assert.ok(lines.every((e) => e.x1 === 52 && e.x2 === 284));
});

test("imported world count and missing sensitivity are shown honestly", async () => {
  const { get } = application(),
    b = JSON.parse(fixture.bundle_json);
  b.request.worlds = 100;
  b.request.seed = 99;
  b.result.sensitivity.variants = [];
  get("import").files = [{ size: 1000, text: async () => JSON.stringify(b) }];
  await get("import").handlers.change({ target: get("import") });
  assert.equal(get("run-scale").textContent, "21 days / 100");
  assert.equal(get("seed").textContent, "99");
  assert.equal(get("preset").value, "imported");
  assert.ok(get("fragility").textContent.includes("not run"));
  assert.equal(get("sensitivity-note").hidden, true);
  assert.equal(get("fork").disabled, true);
  assert.equal(get("simulate").disabled, true);
  get("preset").value = "fades";
  get("preset").handlers.change();
  assert.equal(get("simulate").disabled, false);
  assert.equal(get("fork").disabled, true); // imported data cannot be forked by a static demo
});

test("loading disables imports and reveals, and a premature reveal cannot throw", () => {
  const { ctx, get } = application();
  vm.runInContext("pending(true)", ctx);
  assert.equal(get("import-trigger").disabled, true);
  assert.equal(get("reveal").disabled, true);
  assert.doesNotThrow(() => get("reveal").click());
  assert.equal(get("settlement").hidden, true);
});

test("changing a preset marks results as the previous loaded run until applied", () => {
  const { get } = application();
  get("preset").value = "fades";
  get("preset").handlers.change();
  assert.ok(
    get("message").textContent.includes("results still show the loaded run"),
  );
  assert.equal(
    get("persistence").textContent,
    String(JSON.parse(fixture.bundle_json).request.persistence) + " days",
  );
});
