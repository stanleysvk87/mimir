const DIFFSTAT_LINE = /^\s*\S.*\|\s*\d+\s*[+-]*\s*$/

// Heuristic for "this entry body is a git diffstat or a raw JSON/log dump,
// not prose" -- such bodies render through the same markdown pipeline as
// everything else, but in the default proportional font the diffstat's
// `|` and `+++`/`---` columns (or JSON braces) don't line up. Two or more
// diffstat-shaped lines, or a body that's entirely one JSON object/array,
// is enough signal to switch that entry to monospace.
export function looksStructured(text) {
  if (!text) return false
  const lines = text.split('\n')
  const diffstatLines = lines.filter((l) => DIFFSTAT_LINE.test(l)).length
  if (diffstatLines >= 2) return true
  const trimmed = text.trim()
  if ((trimmed.startsWith('{') && trimmed.endsWith('}')) || (trimmed.startsWith('[') && trimmed.endsWith(']'))) {
    return true
  }
  return false
}
