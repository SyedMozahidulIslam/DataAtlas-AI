param(
  [ValidateSet("run", "test", "seed")]
  [string]$Task = "run"
)

$ErrorActionPreference = "Stop"
switch ($Task) {
  "run"  { python -m dataatlas.server }
  "test" { python -m unittest discover -s tests -v }
  "seed" { python -m dataatlas.seed }
}
