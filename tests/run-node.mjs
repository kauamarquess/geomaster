// Executa os testes no terminal:  node tests/run-node.mjs
import { runAllTests } from "./engine-tests.js";

const { results, passed, failed } = await runAllTests();
for (const r of results) {
  console.log(`${r.ok ? "✓" : "✗"} ${r.name}${r.ok ? "" : `\n    → ${r.error}`}`);
}
console.log(`\n${passed} passaram, ${failed} falharam (${results.length} testes).`);
process.exit(failed === 0 ? 0 : 1);
