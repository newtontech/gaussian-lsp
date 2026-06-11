import type { GaussianInput } from './gjf';

// ---------------------------------------------------------------------------
// Diagnostic types
// ---------------------------------------------------------------------------

export type DiagnosticSeverity = 'error' | 'warning';

export interface Diagnostic {
  /** Machine-readable rule code, e.g. GAUSS-E030 */
  code: string;
  /** Human-readable rule identifier, e.g. gaussian.input.missing_route */
  rule: string;
  severity: DiagnosticSeverity;
  message: string;
  /** 1-based line number (0 when unavailable) */
  line: number;
}

// ---------------------------------------------------------------------------
// Known keyword set for route validation
// ---------------------------------------------------------------------------

const KNOWN_ROUTE_KEYWORDS: ReadonlySet<string> = new Set([
  // Job-type keywords
  'opt', 'freq', 'sp', 'td', 'irc', 'scan',
  // Population / density
  'pop', 'density',
  // Solvent / SCRF
  'scrf',
  // Integral / accuracy
  'integral',
  // Symmetry
  'symmetry', 'nosymm',
  // Guess
  'guess',
  // SCF / convergence
  'scf', 'conver', 'maxcycle', 'xqc', 'qc', 'yqc',
  // Tightness
  'tight', 'vtight', 'loose',
  // Output / geometry
  'nosym', 'geom', 'modredundant', 'z-matrix',
  // Empirical dispersion
  'empiricaldispersion', 'gd3', 'gd3bj',
  // Counterpoise
  'counterpoise',
  // NMR
  'nmr', 'giao',
  // CIS / TD
  'cis', 'nstates', 'root',
  // IRC options
  'calcfc', 'calcall', 'recalcfc',
  // Frozen-core
  'frozencore', 'full',
  // Volume / solvent
  'volume',
  // Polarizability
  'polar',
  // Force
  'force',
  // Temperature / pressure
  'temperature', 'pressure',
  // External
  'external',
]);

// ---------------------------------------------------------------------------
// Suspicious method/basis combinations
// ---------------------------------------------------------------------------

interface MethodBasisEntry {
  methods: ReadonlySet<string>;
  minimalBases: ReadonlyArray<string>;
}

const SUSPICIOUS_COMBINATIONS: ReadonlyArray<MethodBasisEntry> = [
  {
    methods: new Set(['ccsd', 'ccsd(t)', 'ccsdt', 'ccsd-t', 'mp4', 'mp4sdq']),
    minimalBases: ['sto-3g', 'sto-2g', 'sto-6g', '3-21g', 'midi', 'min basis'],
  },
  {
    methods: new Set(['mp2', 'mp3']),
    minimalBases: ['sto-3g', 'sto-2g', 'midi', 'min basis'],
  },
];

// ---------------------------------------------------------------------------
// #57: gaussian.input.missing_route  (error GAUSS-E030)
// ---------------------------------------------------------------------------

function checkMissingRoute(text: string): Diagnostic[] {
  const lines = text.split('\n');
  for (let i = 0; i < lines.length; i++) {
    const trimmed = lines[i].trim();
    if (trimmed.startsWith('#')) {
      return [];
    }
    // Stop after blank line following any non-% content
    if (trimmed.length === 0 && i > 0) {
      break;
    }
  }
  return [
    {
      code: 'GAUSS-E030',
      rule: 'gaussian.input.missing_route',
      severity: 'error',
      message: 'No route section found. Input must contain a line starting with #.',
      line: 1,
    },
  ];
}

// ---------------------------------------------------------------------------
// #58: gaussian.input.invalid_charge_multiplicity  (error GAUSS-E031)
// ---------------------------------------------------------------------------

function checkChargeMultiplicity(
  text: string,
  input: GaussianInput | null,
): Diagnostic[] {
  const lines = text.split('\n');
  let state: 'link0' | 'route' | 'title' | 'charge' = 'link0';

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();

    if (line.startsWith('%')) {
      continue;
    }
    if (line.startsWith('#')) {
      state = 'route';
      continue;
    }
    if (state === 'route') {
      if (line.length === 0) {
        state = 'title';
      }
      continue;
    }
    if (state === 'title') {
      // This line is the title; next non-blank line is charge/mult
      state = 'charge';
      continue;
    }
    if (state === 'charge') {
      if (line.length === 0) {
        continue;
      }
      const parts = line.split(/\s+/);
      if (parts.length < 2) {
        return [
          {
            code: 'GAUSS-E031',
            rule: 'gaussian.input.invalid_charge_multiplicity',
            severity: 'error',
            message: `Charge/multiplicity line must contain two integers, got: "${line}"`,
            line: i + 1,
          },
        ];
      }
      const c = Number.parseInt(parts[0], 10);
      const m = Number.parseInt(parts[1], 10);
      if (Number.isNaN(c) || Number.isNaN(m)) {
        return [
          {
            code: 'GAUSS-E031',
            rule: 'gaussian.input.invalid_charge_multiplicity',
            severity: 'error',
            message: `Charge/multiplicity line must contain two integers, got: "${line}"`,
            line: i + 1,
          },
        ];
      }
      if (m < 1) {
        return [
          {
            code: 'GAUSS-E031',
            rule: 'gaussian.input.invalid_charge_multiplicity',
            severity: 'error',
            message: `Invalid multiplicity ${m}. Multiplicity must be >= 1.`,
            line: i + 1,
          },
        ];
      }
      break;
    }
  }

  // Also catch when parser succeeded but multiplicity is invalid
  if (input !== null && input.multiplicity < 1) {
    return [
      {
        code: 'GAUSS-E031',
        rule: 'gaussian.input.invalid_charge_multiplicity',
        severity: 'error',
        message: `Invalid multiplicity ${input.multiplicity}. Multiplicity must be >= 1.`,
        line: findChargeLine(text),
      },
    ];
  }

  return [];
}

// ---------------------------------------------------------------------------
// #59: gaussian.route.unknown_keyword  (warning GAUSS-W030)
// ---------------------------------------------------------------------------

function checkUnknownKeyword(input: GaussianInput | null): Diagnostic[] {
  if (input === null) {
    return [];
  }

  const diagnostics: Diagnostic[] = [];

  for (const opt of input.route.options) {
    // Strip parenthetical/equals arguments: "scrf=(solvent=water)" -> "scrf"
    const bare = opt.toLowerCase().split(/[=(]/)[0];
    if (bare.length > 0 && !KNOWN_ROUTE_KEYWORDS.has(bare)) {
      diagnostics.push({
        code: 'GAUSS-W030',
        rule: 'gaussian.route.unknown_keyword',
        severity: 'warning',
        message: `Unknown route keyword "${opt}" is not in the known Gaussian keyword set.`,
        line: 0,
      });
    }
  }

  return diagnostics;
}

// ---------------------------------------------------------------------------
// #60: gaussian.route.method_basis_incompatibility  (warning GAUSS-W031)
// ---------------------------------------------------------------------------

function checkMethodBasisIncompatibility(input: GaussianInput | null): Diagnostic[] {
  if (input === null) {
    return [];
  }

  const method = input.route.method.toLowerCase();
  const basis = input.route.basisSet.toLowerCase();

  if (!method || !basis) {
    return [];
  }

  for (const entry of SUSPICIOUS_COMBINATIONS) {
    if (entry.methods.has(method)) {
      for (const minimalBasis of entry.minimalBases) {
        if (basis === minimalBasis || basis.startsWith(minimalBasis)) {
          return [
            {
              code: 'GAUSS-W031',
              rule: 'gaussian.route.method_basis_incompatibility',
              severity: 'warning',
              message:
                `Method "${input.route.method}" with basis set "${input.route.basisSet}" is a suspicious combination. ` +
                `High-level correlated methods should use at least a double-zeta basis set.`,
              line: 0,
            },
          ];
        }
      }
    }
  }

  return [];
}

// ---------------------------------------------------------------------------
// #61: gaussian.link0.invalid_memory  (error GAUSS-E032)
// ---------------------------------------------------------------------------

const MEMORY_PATTERN = /^\d+\s*(gb|mb|kb|tb|mw|gw|kw)$/i;

function checkInvalidMemory(text: string): Diagnostic[] {
  const lines = text.split('\n');
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (/^%mem\b/i.test(line)) {
      const eqIdx = line.indexOf('=');
      if (eqIdx === -1) {
        return [
          {
            code: 'GAUSS-E032',
            rule: 'gaussian.link0.invalid_memory',
            severity: 'error',
            message: '%mem must use format: %mem=<number><unit> (e.g. %mem=8GB).',
            line: i + 1,
          },
        ];
      }
      const value = line.slice(eqIdx + 1).trim();
      if (!MEMORY_PATTERN.test(value)) {
        return [
          {
            code: 'GAUSS-E032',
            rule: 'gaussian.link0.invalid_memory',
            severity: 'error',
            message: `Invalid %mem value "${value}". Must be a number followed by a unit (GB, MB, KB, TB, MW, GW, KW).`,
            line: i + 1,
          },
        ];
      }
    }
  }
  return [];
}

// ---------------------------------------------------------------------------
// #62: gaussian.link0.invalid_nproc  (error GAUSS-E033)
// ---------------------------------------------------------------------------

function checkInvalidNproc(text: string): Diagnostic[] {
  const lines = text.split('\n');
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    const match = line.match(/^%(nprocshared|nproc)\s*=\s*(.+)$/i);
    if (match) {
      const value = match[2].trim();
      const n = Number.parseInt(value, 10);
      if (Number.isNaN(n) || n < 1 || !/^\d+$/.test(value)) {
        return [
          {
            code: 'GAUSS-E033',
            rule: 'gaussian.link0.invalid_nproc',
            severity: 'error',
            message: `Invalid %${match[1]} value "${value}". Must be a positive integer.`,
            line: i + 1,
          },
        ];
      }
    }
  }
  return [];
}

// ---------------------------------------------------------------------------
// #63 & #64: Log file parsing
// ---------------------------------------------------------------------------

/**
 * Parse a Gaussian .log file and return diagnostics for errors found.
 *
 * #63: gaussian.log.scf_not_converged  (error GAUSS-E034)
 * #64: gaussian.log.geometry_parse_failure  (error GAUSS-E035)
 */
export function parseLog(text: string): Diagnostic[] {
  const diagnostics: Diagnostic[] = [];
  const lines = text.split('\n');

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // #63: SCF convergence failure
    if (
      line.includes('Convergence failure') ||
      line.includes('SCF fails to converge')
    ) {
      diagnostics.push({
        code: 'GAUSS-E034',
        rule: 'gaussian.log.scf_not_converged',
        severity: 'error',
        message:
          'SCF failed to converge. Consider increasing max cycles or using a different SCF algorithm.',
        line: i + 1,
      });
    }

    // #64: Geometry parse failure
    if (
      line.includes('Error in geometry') ||
      line.includes('Input Error')
    ) {
      diagnostics.push({
        code: 'GAUSS-E035',
        rule: 'gaussian.log.geometry_parse_failure',
        severity: 'error',
        message: `Geometry parsing failure: ${line.trim()}`,
        line: i + 1,
      });
    }
  }

  return diagnostics;
}

// ---------------------------------------------------------------------------
// Public API: diagnose()
// ---------------------------------------------------------------------------

/**
 * Run all input-file diagnostics on a Gaussian .gjf/.com file.
 *
 * @param input - Parsed GaussianInput (null if parsing failed).
 * @param text  - Raw text of the file.
 * @returns Array of diagnostics.
 */
export function diagnose(
  input: GaussianInput | null,
  text: string,
): Diagnostic[] {
  const diagnostics: Diagnostic[] = [];

  diagnostics.push(...checkMissingRoute(text));
  diagnostics.push(...checkChargeMultiplicity(text, input));
  diagnostics.push(...checkUnknownKeyword(input));
  diagnostics.push(...checkMethodBasisIncompatibility(input));
  diagnostics.push(...checkInvalidMemory(text));
  diagnostics.push(...checkInvalidNproc(text));

  return diagnostics;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function findChargeLine(text: string): number {
  const lines = text.split('\n');
  let state: 'link0' | 'route' | 'title' | 'charge' = 'link0';
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (line.startsWith('%')) continue;
    if (line.startsWith('#')) { state = 'route'; continue; }
    if (state === 'route') {
      if (line.length === 0) state = 'title';
      continue;
    }
    if (state === 'title') { state = 'charge'; continue; }
    if (state === 'charge') return i + 1;
  }
  return 0;
}
