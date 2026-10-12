const test=require("node:test"),assert=require("node:assert/strict");
const V=require("../server/src/tradefloor/assets/source-view.js"),fixture=require("./fixtures/scenario.json");
test("offline cited report preserves receipt and excludes settlement/future input fields",()=>{
  const b=JSON.parse(fixture.bundle_json);b.request.synthetic_outcome="SECRET_FUTURE";b.result.demo_settlement={close:"SECRET_FUTURE"};
  const report=V.offlineReport({bundle_json:JSON.stringify(b)});
  assert.equal(report.report.receipt,b.id);
  assert.ok(!JSON.stringify(report).includes("SECRET_FUTURE"));
  assert.ok(report.html.includes('href="#source-1"'));
  assert.ok(report.markdown.includes("#source-1"));
});
test("source content remains escaped text in HTML and Markdown exports",()=>{
  const b=JSON.parse(fixture.bundle_json);b.result.evidence_graph.nodes[0].text='<script>alert(1)</script> ![remote](https://example.org/track)';
  const report=V.offlineReport({bundle_json:JSON.stringify(b)});
  assert.ok(!report.html.includes('<script>'));
  assert.ok(report.html.includes('&lt;script&gt;'));
  assert.ok(!report.markdown.includes('![remote]'));
  assert.ok(!report.markdown.includes('<script>'));
});
