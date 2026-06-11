/**
 * Machine-readable code-intelligence API for Gaussian input files.
 *
 * Provides domain language description, schema lookup, examples,
 * next-token suggestions, code intelligence API, structural validation,
 * dry-run options, rule manifest export, and OpenQC smoke test.
 *
 * Issues: #47, #48, #49, #54, #55, #65
 */

import type { GaussianInput } from './gjf';
import { GJFParser } from './gjf';
import { diagnose, parseLog } from './diagnostics';

// ---------------------------------------------------------------------------
// #48: Route keyword database
// ---------------------------------------------------------------------------

interface RouteKeywordEntry {
  description: string;
  category: string;
  syntax?: string;
  values?: string[];
}

const ROUTE_KEYWORDS: Readonly<Record<string, RouteKeywordEntry>> = {
  opt: {
    description: 'Geometry optimization',
    category: 'job_type',
    syntax: 'opt[=options]',
    values: ['opt', 'opt=ts', 'opt=modredundant', 'opt=(ts,noeigentest)', 'opt=redundant', 'opt=(calcfc,maxcycle=100)'],
  },
  freq: {
    description: 'Frequency calculation (vibrational analysis)',
    category: 'job_type',
    syntax: 'freq[=options]',
    values: ['freq', 'freq=readisotopes', 'freq=noraman'],
  },
  sp: {
    description: 'Single point energy calculation',
    category: 'job_type',
  },
  td: {
    description: 'Time-dependent DFT for excited states',
    category: 'job_type',
    syntax: 'td[=options]',
    values: ['td', 'td=(nstates=10,root=1)', 'td=(singlets,nstates=20)'],
  },
  irc: {
    description: 'Intrinsic reaction coordinate calculation',
    category: 'job_type',
    syntax: 'irc[=options]',
    values: ['irc', 'irc=(calcfc,maxpoints=20)', 'irc=calcfc'],
  },
  scan: {
    description: 'Relaxed potential energy surface scan',
    category: 'job_type',
    syntax: 'scan',
  },
  pop: {
    description: 'Population analysis',
    category: 'analysis',
    syntax: 'pop[=type]',
    values: ['pop=full', 'pop=mk', 'pop=cheLpg', 'pop=npa', 'pop=nbo', 'pop=none'],
  },
  density: {
    description: 'Density matrix for property calculations',
    category: 'analysis',
    syntax: 'density[=type]',
    values: ['density=current', 'density=all'],
  },
  scf: {
    description: 'SCF algorithm control',
    category: 'scf',
    syntax: 'scf[=option]',
    values: ['scf=qc', 'scf=xqc', 'scf=yqc', 'scf=conventional', 'scf=direct'],
  },
  scrf: {
    description: 'Implicit solvation model',
    category: 'environment',
    syntax: 'scrf[=(options)]',
    values: ['scrf=pcm', 'scrf=(solvent=water)', 'scrf=(smd,solvent=ethanol)', 'scrf=cpcm'],
  },
  empiricaldispersion: {
    description: 'Empirical dispersion correction',
    category: 'method_modifier',
    syntax: 'empiricaldispersion=type',
    values: ['empiricaldispersion=gd3', 'empiricaldispersion=gd3bj', 'empiricaldispersion=gd3bjal'],
  },
  integral: {
    description: 'Integration grid control',
    category: 'accuracy',
    syntax: 'integral[=grid]',
    values: ['integral=ultrafine', 'integral=superfinegrid', 'integral=finegrid'],
  },
  guess: {
    description: 'Initial guess for SCF',
    category: 'scf',
    syntax: 'guess[=type]',
    values: ['guess=read', 'guess=mix', 'guess=huckel', 'guess=core'],
  },
  geom: {
    description: 'Geometry input format and constraints',
    category: 'geometry',
    syntax: 'geom[=option]',
    values: ['geom=allcheck', 'geom=connect', 'geom=modredundant', 'geom=check'],
  },
  symmetry: {
    description: 'Use molecular symmetry',
    category: 'symmetry',
  },
  nosymm: {
    description: 'Disable molecular symmetry',
    category: 'symmetry',
  },
  nmr: {
    description: 'NMR chemical shift calculation',
    category: 'property',
    syntax: 'nmr[=method]',
    values: ['nmr=giao', 'nmr=csgt'],
  },
  polar: {
    description: 'Polarizability calculation',
    category: 'property',
  },
  force: {
    description: 'Compute molecular forces',
    category: 'property',
  },
  volume: {
    description: 'Molecular volume calculation',
    category: 'property',
  },
  counterpoise: {
    description: 'Counterpoise correction for BSSE',
    category: 'method_modifier',
  },
  temperature: {
    description: 'Temperature for thermochemistry (Kelvin)',
    category: 'thermochemistry',
    syntax: 'temperature=value',
  },
  pressure: {
    description: 'Pressure for thermochemistry (atm)',
    category: 'thermochemistry',
    syntax: 'pressure=value',
  },
  tight: {
    description: 'Tight convergence criteria',
    category: 'convergence',
  },
  vtight: {
    description: 'Very tight convergence criteria',
    category: 'convergence',
  },
  loose: {
    description: 'Loose convergence criteria',
    category: 'convergence',
  },
  conver: {
    description: 'SCF convergence control',
    category: 'scf',
  },
  maxcycle: {
    description: 'Maximum number of SCF cycles',
    category: 'scf',
    syntax: 'maxcycle=N',
  },
  xqc: {
    description: 'Extended SCF quadrature convergence',
    category: 'scf',
  },
  qc: {
    description: 'Quadrature-constrained SCF',
    category: 'scf',
  },
  yqc: {
    description: 'Another variant of quadrature-constrained SCF',
    category: 'scf',
  },
  calcfc: {
    description: 'Calculate initial force constants',
    category: 'optimization',
  },
  calcall: {
    description: 'Calculate force constants at every step',
    category: 'optimization',
  },
  recalcfc: {
    description: 'Recalculate force constants periodically',
    category: 'optimization',
  },
  frozencore: {
    description: 'Freeze core electrons in correlation',
    category: 'correlation',
  },
  full: {
    description: 'Full correlation (no frozen core)',
    category: 'correlation',
  },
  cis: {
    description: 'Configuration interaction singles',
    category: 'job_type',
  },
  nstates: {
    description: 'Number of excited states',
    category: 'excited_state',
    syntax: 'nstates=N',
  },
  root: {
    description: 'Root for excited state gradient',
    category: 'excited_state',
    syntax: 'root=N',
  },
  external: {
    description: 'External field or external program',
    category: 'advanced',
  },
  nosym: {
    description: 'No symmetry treatment',
    category: 'symmetry',
  },
  'z-matrix': {
    description: 'Use Z-matrix coordinate input',
    category: 'geometry',
  },
  modredundant: {
    description: 'Modified redundant internal coordinates',
    category: 'geometry',
  },
  gd3: {
    description: 'Grimme D3 dispersion (shorthand)',
    category: 'method_modifier',
  },
  gd3bj: {
    description: 'Grimme D3 with Becke-Johnson damping (shorthand)',
    category: 'method_modifier',
  },
  giao: {
    description: 'Gauge-including atomic orbitals for NMR',
    category: 'property',
  },
};

// ---------------------------------------------------------------------------
// #48: Link0 command database
// ---------------------------------------------------------------------------

interface Link0CommandEntry {
  description: string;
  syntax: string;
  valueType: string;
  example: string;
}

const LINK0_COMMANDS: Readonly<Record<string, Link0CommandEntry>> = {
  mem: {
    description: 'Memory allocation for the calculation',
    syntax: '%mem=<size><unit>',
    valueType: 'string (number + unit: KB, MB, GB, TB, MW, GW, KW)',
    example: '%mem=8GB',
  },
  nprocshared: {
    description: 'Number of shared-memory processors',
    syntax: '%nprocshared=<N>',
    valueType: 'positive integer',
    example: '%nprocshared=4',
  },
  nproc: {
    description: 'Number of processors (alias for nprocshared)',
    syntax: '%nproc=<N>',
    valueType: 'positive integer',
    example: '%nproc=8',
  },
  chk: {
    description: 'Checkpoint file path',
    syntax: '%chk=<path>',
    valueType: 'file path',
    example: '%chk=water.chk',
  },
  save: {
    description: 'Save checkpoint file',
    syntax: '%save',
    valueType: 'none (flag)',
    example: '%save',
  },
  subst: {
    description: 'Substitute a Link program with a custom version',
    syntax: '%subst<l<number> <path>',
    valueType: 'string (link number + path)',
    example: '%subst l510 /path/to/custom/l510',
  },
  kjob: {
    description: 'Number of optimization steps before stopping',
    syntax: '%kjob=<N>',
    valueType: 'integer',
    example: '%kjob=5',
  },
  nosave: {
    description: 'Do not save checkpoint file',
    syntax: '%nosave',
    valueType: 'none (flag)',
    example: '%nosave',
  },
  rwf: {
    description: 'Read-write file path',
    syntax: '%rwf=<path>',
    valueType: 'file path',
    example: '%rwf=/scratch/job.rwf',
  },
  int: {
    description: 'Integral file path',
    syntax: '%int=<path>',
    valueType: 'file path',
    example: '%int=/scratch/job.int',
  },
  d2e: {
    description: 'Two-electron integral derivative file path',
    syntax: '%d2e=<path>',
    valueType: 'file path',
    example: '%d2e=/scratch/job.d2e',
  },
};

// ---------------------------------------------------------------------------
// #49: Example Gaussian inputs
// ---------------------------------------------------------------------------

interface GaussianExample {
  title: string;
  description: string;
  input: string;
}

const GAUSSIAN_EXAMPLES: Readonly<Record<string, GaussianExample>> = {
  single_point: {
    title: 'Single Point Energy Calculation',
    description: 'Compute the energy of a water molecule at B3LYP/6-31G(d) level.',
    input:
      '%mem=4GB\n' +
      '%nprocshared=4\n' +
      '# B3LYP/6-31G(d) sp\n' +
      '\n' +
      'Water single point\n' +
      '\n' +
      '0 1\n' +
      'O  0.0000  0.0000  0.1173\n' +
      'H  0.0000  0.7572 -0.4692\n' +
      'H  0.0000 -0.7572 -0.4692\n' +
      '\n',
  },
  optimization: {
    title: 'Geometry Optimization',
    description: 'Optimize water geometry at B3LYP/6-31G(d) with frequency analysis.',
    input:
      '%chk=water_opt.chk\n' +
      '%mem=8GB\n' +
      '%nprocshared=4\n' +
      '# B3LYP/6-31G(d) opt freq\n' +
      '\n' +
      'Water optimization with frequencies\n' +
      '\n' +
      '0 1\n' +
      'O  0.000  0.000  0.000\n' +
      'H  0.757  0.586  0.000\n' +
      'H -0.757  0.586  0.000\n' +
      '\n',
  },
  frequency: {
    title: 'Standalone Frequency Calculation',
    description: 'Frequency analysis at the B3LYP/6-311+G(d,p) level from checkpoint.',
    input:
      '%chk=water_opt.chk\n' +
      '%mem=8GB\n' +
      '%nprocshared=4\n' +
      '# B3LYP/6-311+G(d,p) freq geom=allcheck guess=read\n' +
      '\n' +
      'Water frequency analysis\n' +
      '\n' +
      '0 1\n' +
      'O  0.000  0.000  0.000\n' +
      'H  0.757  0.586  0.000\n' +
      'H -0.757  0.586  0.000\n' +
      '\n',
  },
  td_dft: {
    title: 'TD-DFT Excited States',
    description: 'Time-dependent DFT calculation for formaldehyde excited states using CAM-B3LYP/6-31+G(d).',
    input:
      '%chk=formaldehyde_td.chk\n' +
      '%mem=8GB\n' +
      '%nprocshared=4\n' +
      '# CAM-B3LYP/6-31+G(d) td=(nstates=10,root=1) density=current\n' +
      '\n' +
      'Formaldehyde TD-DFT\n' +
      '\n' +
      '0 1\n' +
      'C  0.0000  0.0000  0.0000\n' +
      'O  0.0000  0.0000  1.2080\n' +
      'H  0.9657  0.0000 -0.5408\n' +
      'H -0.9657  0.0000 -0.5408\n' +
      '\n',
  },
  irc: {
    title: 'Intrinsic Reaction Coordinate',
    description: 'IRC calculation from a transition state at B3LYP/6-31G(d).',
    input:
      '%chk=ts.chk\n' +
      '%mem=8GB\n' +
      '%nprocshared=4\n' +
      '# B3LYP/6-31G(d) irc=(calcfc,maxpoints=20)\n' +
      '\n' +
      'IRC from transition state\n' +
      '\n' +
      '0 1\n' +
      'O  0.000  0.000  0.117\n' +
      'H  0.000  0.757 -0.469\n' +
      'H  0.000 -0.757 -0.469\n' +
      '\n',
  },
  mp2: {
    title: 'MP2 Single Point Energy',
    description: 'MP2 correlation energy calculation with a triple-zeta basis set.',
    input:
      '%chk=water_mp2.chk\n' +
      '%mem=8GB\n' +
      '%nprocshared=4\n' +
      '# MP2/cc-pVTZ sp density=current pop=full\n' +
      '\n' +
      'Water MP2 single point\n' +
      '\n' +
      '0 1\n' +
      'O  0.0000  0.0000  0.1173\n' +
      'H  0.0000  0.7572 -0.4692\n' +
      'H  0.0000 -0.7572 -0.4692\n' +
      '\n',
  },
};

// ---------------------------------------------------------------------------
// #47: describeDomainLanguage()
// ---------------------------------------------------------------------------

export function describeDomainLanguage(): Record<string, unknown> {
  return {
    languageId: 'gaussian-input',
    name: 'Gaussian Input DSL',
    fileExtensions: ['.gjf', '.com'],
    overview:
      'Gaussian input files describe quantum chemistry calculations. ' +
      'The file consists of Link 0 commands (% prefix), a route section (# prefix), ' +
      'a title line, charge/multiplicity, and molecular geometry in Cartesian coordinates.',
    grammarSummary: {
      link0: {
        prefix: '%',
        description:
          'Link 0 commands configure runtime parameters (memory, processors, file paths). ' +
          'Each starts with % followed by the command name, an equals sign, and a value.',
        example: '%mem=8GB',
      },
      route: {
        prefix: '#',
        description:
          'The route section defines the calculation method, basis set, and job options. ' +
          'It starts with # (or #p/#n/#t for verbosity control) and may span multiple lines ' +
          'until a blank line is encountered.',
        example: '# B3LYP/6-31G(d) opt freq',
        components: ['method/basis', 'job_type_keywords', 'modifiers'],
      },
      title: {
        description:
          'A free-form single-line description of the calculation. ' +
          'Appears between the route section blank line and the charge/multiplicity line.',
        example: 'Water optimization',
      },
      chargeMultiplicity: {
        description:
          'Two integers: total molecular charge and spin multiplicity (2S+1). ' +
          'Multiplicity must be >= 1.',
        example: '0 1',
      },
      geometry: {
        description:
          'Molecular geometry in Cartesian coordinates. Each line has element symbol ' +
          'followed by x, y, z coordinates. Z-matrix format is also supported.',
        example: 'O  0.000  0.000  0.000',
      },
    },
    topLevelSections: [
      { name: 'Link 0 Commands', prefix: '%', required: false, description: 'Runtime configuration (memory, CPUs, files)' },
      { name: 'Route Section', prefix: '#', required: true, description: 'Method, basis set, and job-type keywords' },
      { name: 'Title', prefix: '', required: true, description: 'Single-line description' },
      { name: 'Charge/Multiplicity', prefix: '', required: true, description: 'Charge and spin multiplicity (two integers)' },
      { name: 'Geometry', prefix: '', required: true, description: 'Atomic coordinates' },
    ],
    commonPatterns: [
      'Optimization + Frequency: # B3LYP/6-31G(d) opt freq',
      'Single Point: # B3LYP/6-31G(d) sp',
      'TD-DFT: # CAM-B3LYP/6-31+G(d) td=(nstates=10)',
      'Solvent: # B3LYP/6-31G(d) scrf=(solvent=water)',
      'Dispersion: # B3LYP/6-31G(d) empiricaldispersion=gd3bj',
    ],
    validationRules: [
      { code: 'GAUSS-E030', rule: 'gaussian.input.missing_route', severity: 'error', description: 'No route section found' },
      { code: 'GAUSS-E031', rule: 'gaussian.input.invalid_charge_multiplicity', severity: 'error', description: 'Invalid charge or multiplicity' },
      { code: 'GAUSS-E032', rule: 'gaussian.link0.invalid_memory', severity: 'error', description: 'Invalid %mem value' },
      { code: 'GAUSS-E033', rule: 'gaussian.link0.invalid_nproc', severity: 'error', description: 'Invalid %nprocshared value' },
      { code: 'GAUSS-W030', rule: 'gaussian.route.unknown_keyword', severity: 'warning', description: 'Unknown route keyword' },
      { code: 'GAUSS-W031', rule: 'gaussian.route.method_basis_incompatibility', severity: 'warning', description: 'Suspicious method/basis combination' },
      { code: 'GAUSS-E034', rule: 'gaussian.log.scf_not_converged', severity: 'error', description: 'SCF convergence failure in log output' },
      { code: 'GAUSS-E035', rule: 'gaussian.log.geometry_parse_failure', severity: 'error', description: 'Geometry parsing failure in log output' },
    ],
    references: [
      'Gaussian 16 User Reference: https://gaussian.com/techdocs/',
      'Gaussian Input Overview: https://gaussian.com/input/',
      'Route Keywords: https://gaussian.com/keywords/',
    ],
    fileTypes: {
      input: ['.gjf', '.com'],
      output: ['.log'],
      auxiliary: ['.chk', '.fchk', '.cub', '.rwf'],
    },
  };
}

// ---------------------------------------------------------------------------
// #48: lookupRouteKeyword(), lookupLink0Command()
// ---------------------------------------------------------------------------

export function lookupRouteKeyword(keyword: string): Record<string, unknown> {
  const normalized = keyword.toLowerCase().trim();
  const bare = normalized.split(/[=(]/)[0];

  const entry = ROUTE_KEYWORDS[bare];
  if (entry) {
    return {
      keyword: bare,
      found: true,
      description: entry.description,
      category: entry.category,
      syntax: entry.syntax ?? null,
      values: entry.values ?? null,
    };
  }

  // Try to suggest similar keywords
  const suggestions = Object.keys(ROUTE_KEYWORDS)
    .filter(k => k.startsWith(bare.slice(0, 2)))
    .slice(0, 5);

  return {
    keyword,
    found: false,
    message: `Unknown route keyword "${keyword}".`,
    suggestions: suggestions.length > 0 ? suggestions : null,
  };
}

export function lookupLink0Command(cmd: string): Record<string, unknown> {
  const normalized = cmd.toLowerCase().trim();

  const entry = LINK0_COMMANDS[normalized];
  if (entry) {
    return {
      command: normalized,
      found: true,
      description: entry.description,
      syntax: entry.syntax,
      valueType: entry.valueType,
      example: entry.example,
    };
  }

  const suggestions = Object.keys(LINK0_COMMANDS)
    .filter(k => k.startsWith(normalized.slice(0, 2)))
    .slice(0, 5);

  return {
    command: cmd,
    found: false,
    message: `Unknown Link 0 command "${cmd}".`,
    suggestions: suggestions.length > 0 ? suggestions : null,
  };
}

// ---------------------------------------------------------------------------
// #49: getExamples(), nextTokenSuggestions()
// ---------------------------------------------------------------------------

export function getExamples(): Array<Record<string, string>> {
  return Object.entries(GAUSSIAN_EXAMPLES).map(([key, ex]) => ({
    key,
    title: ex.title,
    description: ex.description,
    input: ex.input,
  }));
}

export interface TokenSuggestion {
  token: string;
  type: string;
  description: string;
}

export function nextTokenSuggestions(
  context: string,
  prefix: string = '',
): TokenSuggestion[] {
  const stripped = context.trim();
  const lowerPrefix = prefix.toLowerCase();
  const suggestions: TokenSuggestion[] = [];

  // After % -> Link 0 commands
  if (stripped.startsWith('%')) {
    const cmdPrefix = stripped.slice(1).trim() || lowerPrefix;
    for (const [name, entry] of Object.entries(LINK0_COMMANDS)) {
      if (cmdPrefix && !name.startsWith(cmdPrefix.toLowerCase())) {
        continue;
      }
      suggestions.push({
        token: name,
        type: 'link0_command',
        description: entry.description,
      });
    }
    return suggestions;
  }

  // After # -> route keywords, methods, basis sets
  if (stripped.startsWith('#')) {
    for (const [name, entry] of Object.entries(ROUTE_KEYWORDS)) {
      if (lowerPrefix && !name.startsWith(lowerPrefix)) {
        continue;
      }
      suggestions.push({
        token: name,
        type: entry.category,
        description: entry.description,
      });
    }
    // Add common method/basis patterns
    const commonMethods = [
      'B3LYP', 'PBE0', 'PBE', 'wB97X-D', 'CAM-B3LYP', 'M06-2X',
      'HF', 'MP2', 'MP4', 'CCSD', 'CCSD(T)',
      'B3LYP/6-31G(d)', 'B3LYP/6-311+G(d,p)', 'wB97X-D/def2-TZVP',
    ];
    for (const m of commonMethods) {
      if (lowerPrefix && !m.toLowerCase().startsWith(lowerPrefix)) {
        continue;
      }
      suggestions.push({
        token: m,
        type: 'method_basis',
        description: 'Method/basis set combination',
      });
    }
    return suggestions;
  }

  return suggestions;
}

// ---------------------------------------------------------------------------
// #54: getCodeIntelligenceAPI()
// ---------------------------------------------------------------------------

export function getCodeIntelligenceAPI(): Record<string, unknown> {
  return {
    name: 'gaussian-lsp',
    version: '0.2.11',
    language: 'gaussian-input',
    description: 'Language Server Protocol for Gaussian quantum chemistry input files',
    capabilities: {
      diagnostics: {
        description: 'Real-time validation and error detection for Gaussian input files',
        methods: ['diagnose', 'parseLog'],
        checks: [
          'Missing route section',
          'Invalid charge/multiplicity',
          'Unknown route keywords',
          'Method/basis incompatibility',
          'Invalid memory specification',
          'Invalid processor count',
          'SCF convergence failure (log)',
          'Geometry parse failure (log)',
        ],
        ruleCodes: [
          'GAUSS-E030 (missing route section)',
          'GAUSS-E031 (invalid charge/multiplicity)',
          'GAUSS-E032 (invalid memory)',
          'GAUSS-E033 (invalid nproc)',
          'GAUSS-W030 (unknown keyword)',
          'GAUSS-W031 (method/basis incompatibility)',
          'GAUSS-E034 (SCF convergence failure)',
          'GAUSS-E035 (geometry parse failure)',
        ],
      },
      completions: {
        description: 'Context-aware completions for Gaussian keywords',
        methods: ['nextTokenSuggestions'],
        contexts: [
          'After % -> Link 0 commands (mem, nprocshared, chk, etc.)',
          'After # -> route keywords (opt, freq, sp, td, etc.)',
        ],
      },
      domain_knowledge: {
        description: 'Gaussian domain language knowledge base',
        methods: [
          'describeDomainLanguage',
          'lookupRouteKeyword',
          'lookupLink0Command',
          'getExamples',
        ],
      },
      validation: {
        description: 'Input validation without Gaussian binary',
        methods: ['validateInput', 'dryRunOptions'],
        features: [
          'Offline structural validation',
          'Log file parsing for runtime errors',
        ],
      },
      log_parsing: {
        description: 'Parse Gaussian output logs for errors',
        methods: ['parseLog'],
        supportedPatterns: [
          'SCF convergence failure',
          'Geometry parse failure',
          'Input errors',
        ],
      },
    },
    apiMethods: [
      { name: 'describeDomainLanguage', description: 'Get structured Gaussian input language description', parameters: [], returns: 'object' },
      { name: 'lookupRouteKeyword', description: 'Look up a route keyword schema', parameters: ['keyword'], returns: 'object' },
      { name: 'lookupLink0Command', description: 'Look up a Link 0 command schema', parameters: ['command'], returns: 'object' },
      { name: 'getExamples', description: 'Get curated example Gaussian inputs', parameters: [], returns: 'array' },
      { name: 'nextTokenSuggestions', description: 'Get context-aware completion suggestions', parameters: ['context', 'prefix'], returns: 'array' },
      { name: 'getCodeIntelligenceAPI', description: 'Get machine-readable API capabilities description', parameters: [], returns: 'object' },
      { name: 'validateInput', description: 'Validate Gaussian input text without binary', parameters: ['text'], returns: 'object' },
      { name: 'dryRunOptions', description: 'Return available dry-run/validate commands', parameters: [], returns: 'object' },
      { name: 'getRuleManifest', description: 'Export all diagnostic rules', parameters: [], returns: 'object' },
      { name: 'openqcSmoke', description: 'Lightweight smoke test for OpenQC integration', parameters: [], returns: 'object' },
    ],
    agentIntegration: {
      description: 'How to integrate with AI coding agents',
      domainUsage:
        'Call describeDomainLanguage() once to understand the language. ' +
        'Use lookupRouteKeyword/lookupLink0Command for specific parameter details. ' +
        'Use getExamples() for templates.',
      validationUsage:
        'Call validateInput(text) to check structural validity. ' +
        'Call parseLog(text) on .log files for runtime errors.',
      completionUsage:
        'Call nextTokenSuggestions(context, prefix) to get ' +
        'relevant completion items based on cursor position.',
    },
  };
}

// ---------------------------------------------------------------------------
// #55: validateInput(), dryRunOptions()
// ---------------------------------------------------------------------------

export interface ValidationResult {
  valid: boolean;
  errors: Array<Record<string, unknown>>;
  warnings: Array<Record<string, unknown>>;
  errorCount: number;
  warningCount: number;
  sections: {
    hasLink0: boolean;
    hasRoute: boolean;
    hasTitle: boolean;
    hasChargeMultiplicity: boolean;
    hasGeometry: boolean;
    atomCount: number;
  };
}

export function validateInput(text: string): ValidationResult {
  let input: GaussianInput | null = null;
  try {
    input = new GJFParser().parse(text);
  } catch {
    // parser may throw for invalid input
  }

  const diagnostics = diagnose(input, text);

  const errors = diagnostics
    .filter(d => d.severity === 'error')
    .map(d => ({ code: d.code, rule: d.rule, message: d.message, line: d.line }));

  const warnings = diagnostics
    .filter(d => d.severity === 'warning')
    .map(d => ({ code: d.code, rule: d.rule, message: d.message, line: d.line }));

  return {
    valid: errors.length === 0,
    errors,
    warnings,
    errorCount: errors.length,
    warningCount: warnings.length,
    sections: {
      hasLink0: input !== null && input.link0.size > 0,
      hasRoute: input !== null && (input.route.method.length > 0 || input.route.options.length > 0),
      hasTitle: input !== null && input.title.length > 0,
      hasChargeMultiplicity: input !== null,
      hasGeometry: input !== null && input.atoms.length > 0,
      atomCount: input?.atoms.length ?? 0,
    },
  };
}

export function dryRunOptions(): Record<string, unknown> {
  return {
    offlineValidation: {
      method: 'validateInput',
      description:
        'Structural validation of Gaussian input without the Gaussian binary. ' +
        'Checks for required sections, valid keywords, charge/multiplicity, memory, ' +
        'and processor specifications.',
      available: true,
      requiresBinary: false,
    },
    logParsing: {
      method: 'parseLog',
      description:
        'Parse existing Gaussian .log output files for runtime errors ' +
        '(SCF convergence failures, geometry parse errors).',
      available: true,
      requiresBinary: false,
      ruleCodes: ['GAUSS-E034', 'GAUSS-E035'],
    },
    binaryDryRun: {
      method: 'run_validation',
      description:
        'Run Gaussian executable on the input file in a temporary directory ' +
        'to capture real error messages. Requires g16/g09 executable path.',
      available: false,
      requiresBinary: true,
      configFields: {
        executable: 'Path to the Gaussian binary (e.g., /usr/local/bin/g16)',
        timeout: 'Timeout in seconds (default: 60)',
        enabled: 'Set to true to enable binary validation',
      },
    },
  };
}

// ---------------------------------------------------------------------------
// #65: getRuleManifest(), openqcSmoke()
// ---------------------------------------------------------------------------

export interface RuleEntry {
  code: string;
  rule: string;
  severity: string;
  description: string;
  fileTypes: string[];
}

export function getRuleManifest(): { rules: RuleEntry[]; count: number } {
  return {
    rules: [
      {
        code: 'GAUSS-E030',
        rule: 'gaussian.input.missing_route',
        severity: 'error',
        description: 'No route section found. Input must contain a line starting with #.',
        fileTypes: ['.gjf', '.com'],
      },
      {
        code: 'GAUSS-E031',
        rule: 'gaussian.input.invalid_charge_multiplicity',
        severity: 'error',
        description: 'Charge/multiplicity line must contain two valid integers. Multiplicity >= 1.',
        fileTypes: ['.gjf', '.com'],
      },
      {
        code: 'GAUSS-E032',
        rule: 'gaussian.link0.invalid_memory',
        severity: 'error',
        description: '%mem must use format: %mem=<number><unit> (e.g. %mem=8GB).',
        fileTypes: ['.gjf', '.com'],
      },
      {
        code: 'GAUSS-E033',
        rule: 'gaussian.link0.invalid_nproc',
        severity: 'error',
        description: '%nprocshared/%nproc must be a positive integer.',
        fileTypes: ['.gjf', '.com'],
      },
      {
        code: 'GAUSS-W030',
        rule: 'gaussian.route.unknown_keyword',
        severity: 'warning',
        description: 'Unknown route keyword not in the known Gaussian keyword set.',
        fileTypes: ['.gjf', '.com'],
      },
      {
        code: 'GAUSS-W031',
        rule: 'gaussian.route.method_basis_incompatibility',
        severity: 'warning',
        description: 'High-level correlated method with a minimal basis set is suspicious.',
        fileTypes: ['.gjf', '.com'],
      },
      {
        code: 'GAUSS-E034',
        rule: 'gaussian.log.scf_not_converged',
        severity: 'error',
        description: 'SCF failed to converge in the output log.',
        fileTypes: ['.log'],
      },
      {
        code: 'GAUSS-E035',
        rule: 'gaussian.log.geometry_parse_failure',
        severity: 'error',
        description: 'Geometry parsing failure in the output log.',
        fileTypes: ['.log'],
      },
    ],
    count: 8,
  };
}

export interface SmokeResult {
  name: string;
  passed: boolean;
  checks: Array<{ test: string; passed: boolean; detail?: string }>;
}

export function openqcSmoke(): SmokeResult {
  const checks: Array<{ test: string; passed: boolean; detail?: string }> = [];

  // Check 1: describeDomainLanguage returns deterministic output
  try {
    const desc = describeDomainLanguage();
    const hasLanguageId = typeof (desc as Record<string, unknown>).languageId === 'string';
    const hasFileExtensions = Array.isArray((desc as Record<string, unknown>).fileExtensions);
    checks.push({
      test: 'describeDomainLanguage returns structured result',
      passed: hasLanguageId && hasFileExtensions,
      detail: hasLanguageId && hasFileExtensions ? 'ok' : 'missing fields',
    });
  } catch (e) {
    checks.push({ test: 'describeDomainLanguage returns structured result', passed: false, detail: String(e) });
  }

  // Check 2: validateInput on a valid file
  const validInput =
    '%mem=8GB\n%nprocshared=4\n# B3LYP/6-31G(d) opt\n\nWater opt\n\n0 1\nO 0 0 0\nH 0.757 0.586 0\nH -0.757 0.586 0\n\n';
  try {
    const result = validateInput(validInput);
    checks.push({
      test: 'validateInput accepts valid .gjf content',
      passed: result.valid,
      detail: result.valid ? 'ok' : `unexpected errors: ${result.errorCount}`,
    });
  } catch (e) {
    checks.push({ test: 'validateInput accepts valid .gjf content', passed: false, detail: String(e) });
  }

  // Check 3: validateInput catches errors
  const invalidInput = '%mem=abc\n%nprocshared=0\n\n0 0\nO 0 0 0\n';
  try {
    const result = validateInput(invalidInput);
    checks.push({
      test: 'validateInput rejects invalid .gjf content',
      passed: !result.valid && result.errorCount > 0,
      detail: `errors: ${result.errorCount}`,
    });
  } catch (e) {
    checks.push({ test: 'validateInput rejects invalid .gjf content', passed: false, detail: String(e) });
  }

  // Check 4: parseLog on error log
  const errorLog = 'Convergence failure\nError in geometry\n';
  try {
    const logDiags = parseLog(errorLog);
    checks.push({
      test: 'parseLog detects SCF and geometry errors',
      passed: logDiags.length >= 2,
      detail: `found ${logDiags.length} diagnostics`,
    });
  } catch (e) {
    checks.push({ test: 'parseLog detects SCF and geometry errors', passed: false, detail: String(e) });
  }

  // Check 5: getRuleManifest returns all rules
  try {
    const manifest = getRuleManifest();
    checks.push({
      test: 'getRuleManifest returns 8 rules',
      passed: manifest.count === 8 && manifest.rules.length === 8,
      detail: `count: ${manifest.count}`,
    });
  } catch (e) {
    checks.push({ test: 'getRuleManifest returns 8 rules', passed: false, detail: String(e) });
  }

  // Check 6: lookupRouteKeyword for known keyword
  try {
    const opt = lookupRouteKeyword('opt');
    const found = (opt as Record<string, unknown>).found === true;
    checks.push({
      test: 'lookupRouteKeyword finds known keyword opt',
      passed: found,
      detail: found ? 'ok' : 'not found',
    });
  } catch (e) {
    checks.push({ test: 'lookupRouteKeyword finds known keyword opt', passed: false, detail: String(e) });
  }

  const allPassed = checks.every(c => c.passed);
  return {
    name: 'gaussian-lsp',
    passed: allPassed,
    checks,
  };
}
