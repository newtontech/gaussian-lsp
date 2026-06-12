import { describe, it, expect } from 'vitest';
import { diagnose, parseLog } from '../../src/parsers/diagnostics';
import { GJFParser } from '../../src/parsers/gjf';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function parseAndDiagnose(text: string) {
  let input = null;
  try {
    input = new GJFParser().parse(text);
  } catch {
    // Parser may throw for invalid input; diagnose with null
  }
  return diagnose(input, text);
}

// ===========================================================================
// #57: gaussian.input.missing_route  (GAUSS-E030)
// ===========================================================================

describe('#57 gaussian.input.missing_route (GAUSS-E030)', () => {
  it('reports error when no route line is present', () => {
    const text = `%mem=8GB\n\nSome title\n\n0 1\nO 0 0 0\n`;
    const diags = parseAndDiagnose(text);
    const e = diags.find(d => d.code === 'GAUSS-E030');
    expect(e).toBeDefined();
    expect(e!.severity).toBe('error');
    expect(e!.rule).toBe('gaussian.input.missing_route');
  });

  it('returns no error when route line exists', () => {
    const text = `# B3LYP/6-31G(d) opt\n\nTitle\n\n0 1\nO 0 0 0\n`;
    const diags = parseAndDiagnose(text);
    expect(diags.find(d => d.code === 'GAUSS-E030')).toBeUndefined();
  });

  it('returns no error when route line has %% prefix or lower case', () => {
    const text = `#p b3lyp/6-31g(d) opt\n\nTitle\n\n0 1\nO 0 0 0\n`;
    const diags = parseAndDiagnose(text);
    expect(diags.find(d => d.code === 'GAUSS-E030')).toBeUndefined();
  });

  it('reports error for file with only link0 commands', () => {
    const text = `%mem=8GB\n%nprocshared=4\n`;
    const diags = parseAndDiagnose(text);
    expect(diags.find(d => d.code === 'GAUSS-E030')).toBeDefined();
  });
});

// ===========================================================================
// #58: gaussian.input.invalid_charge_multiplicity  (GAUSS-E031)
// ===========================================================================

describe('#58 gaussian.input.invalid_charge_multiplicity (GAUSS-E031)', () => {
  it('reports error when charge/mult is not two integers', () => {
    const text = `# B3LYP/6-31G(d)\n\nTitle\n\nneutral singlet\nO 0 0 0\n`;
    const diags = parseAndDiagnose(text);
    const e = diags.find(d => d.code === 'GAUSS-E031');
    expect(e).toBeDefined();
    expect(e!.severity).toBe('error');
    expect(e!.rule).toBe('gaussian.input.invalid_charge_multiplicity');
  });

  it('reports error for single token on charge line', () => {
    const text = `# B3LYP/6-31G(d)\n\nTitle\n\n0\nO 0 0 0\n`;
    const diags = parseAndDiagnose(text);
    expect(diags.find(d => d.code === 'GAUSS-E031')).toBeDefined();
  });

  it('reports error for multiplicity zero', () => {
    const text = `# B3LYP/6-31G(d)\n\nTitle\n\n0 0\nO 0 0 0\n`;
    const diags = parseAndDiagnose(text);
    const e = diags.find(d => d.code === 'GAUSS-E031');
    expect(e).toBeDefined();
    expect(e!.message).toContain('Multiplicity');
  });

  it('reports error for negative multiplicity', () => {
    const text = `# B3LYP/6-31G(d)\n\nTitle\n\n0 -1\nO 0 0 0\n`;
    const diags = parseAndDiagnose(text);
    expect(diags.find(d => d.code === 'GAUSS-E031')).toBeDefined();
  });

  it('returns no error for valid charge and multiplicity', () => {
    const text = `# B3LYP/6-31G(d)\n\nTitle\n\n0 1\nO 0 0 0\n`;
    const diags = parseAndDiagnose(text);
    expect(diags.find(d => d.code === 'GAUSS-E031')).toBeUndefined();
  });

  it('returns no error for valid negative charge', () => {
    const text = `# B3LYP/6-31G(d)\n\nTitle\n\n-1 2\nO 0 0 0\n`;
    const diags = parseAndDiagnose(text);
    expect(diags.find(d => d.code === 'GAUSS-E031')).toBeUndefined();
  });

  it('returns no error for high multiplicity', () => {
    const text = `# B3LYP/6-31G(d)\n\nTitle\n\n0 5\nO 0 0 0\n`;
    const diags = parseAndDiagnose(text);
    expect(diags.find(d => d.code === 'GAUSS-E031')).toBeUndefined();
  });

  it('reports parser-provided invalid multiplicity and locates charge line', () => {
    const text = `%mem=8GB\n# B3LYP/6-31G(d)\n\nTitle\n\n0 1\nO 0 0 0\n`;
    const input = new GJFParser().parse(text);
    const diags = diagnose({ ...input, multiplicity: 0 }, text);
    const e = diags.find(d => d.code === 'GAUSS-E031');
    expect(e).toBeDefined();
    expect(e!.line).toBe(5);
    expect(e!.message).toContain('Invalid multiplicity 0');
  });
});

// ===========================================================================
// #59: gaussian.route.unknown_keyword  (GAUSS-W030)
// ===========================================================================

describe('#59 gaussian.route.unknown_keyword (GAUSS-W030)', () => {
  it('reports warning for unknown keyword', () => {
    const text = `# B3LYP/6-31G(d) foobar\n\nTitle\n\n0 1\nO 0 0 0\n`;
    const diags = parseAndDiagnose(text);
    const w = diags.find(d => d.code === 'GAUSS-W030');
    expect(w).toBeDefined();
    expect(w!.severity).toBe('warning');
    expect(w!.rule).toBe('gaussian.route.unknown_keyword');
    expect(w!.message).toContain('foobar');
  });

  it('does not warn for known keyword opt', () => {
    const text = `# B3LYP/6-31G(d) opt\n\nTitle\n\n0 1\nO 0 0 0\n`;
    const diags = parseAndDiagnose(text);
    expect(diags.find(d => d.code === 'GAUSS-W030')).toBeUndefined();
  });

  it('does not warn for keyword with parenthetical args', () => {
    const text = `# B3LYP/6-31G(d) scrf=(solvent=water)\n\nTitle\n\n0 1\nO 0 0 0\n`;
    const diags = parseAndDiagnose(text);
    expect(diags.find(d => d.code === 'GAUSS-W030')).toBeUndefined();
  });

  it('does not warn for freq keyword', () => {
    const text = `# B3LYP/6-31G(d) freq\n\nTitle\n\n0 1\nO 0 0 0\n`;
    const diags = parseAndDiagnose(text);
    expect(diags.find(d => d.code === 'GAUSS-W030')).toBeUndefined();
  });

  it('reports multiple warnings for multiple unknown keywords', () => {
    const text = `# B3LYP/6-31G(d) foo bar\n\nTitle\n\n0 1\nO 0 0 0\n`;
    const diags = parseAndDiagnose(text);
    const warnings = diags.filter(d => d.code === 'GAUSS-W030');
    expect(warnings).toHaveLength(2);
  });
});

// ===========================================================================
// #60: gaussian.route.method_basis_incompatibility  (GAUSS-W031)
// ===========================================================================

describe('#60 gaussian.route.method_basis_incompatibility (GAUSS-W031)', () => {
  it('reports warning for CCSD/STO-3G', () => {
    const text = `# CCSD/STO-3G\n\nTitle\n\n0 1\nHe 0 0 0\n`;
    const diags = parseAndDiagnose(text);
    const w = diags.find(d => d.code === 'GAUSS-W031');
    expect(w).toBeDefined();
    expect(w!.severity).toBe('warning');
    expect(w!.message).toContain('suspicious');
  });

  it('reports warning for MP2/STO-3G', () => {
    const text = `# MP2/STO-3G\n\nTitle\n\n0 1\nHe 0 0 0\n`;
    const diags = parseAndDiagnose(text);
    expect(diags.find(d => d.code === 'GAUSS-W031')).toBeDefined();
  });

  it('reports warning for CCSD(T)/3-21G', () => {
    const text = `# CCSD(T)/3-21G\n\nTitle\n\n0 1\nHe 0 0 0\n`;
    const diags = parseAndDiagnose(text);
    expect(diags.find(d => d.code === 'GAUSS-W031')).toBeDefined();
  });

  it('does not warn for B3LYP/6-31G(d)', () => {
    const text = `# B3LYP/6-31G(d)\n\nTitle\n\n0 1\nO 0 0 0\n`;
    const diags = parseAndDiagnose(text);
    expect(diags.find(d => d.code === 'GAUSS-W031')).toBeUndefined();
  });

  it('does not warn for CCSD/cc-pVTZ', () => {
    const text = `# CCSD/cc-pVTZ\n\nTitle\n\n0 1\nHe 0 0 0\n`;
    const diags = parseAndDiagnose(text);
    expect(diags.find(d => d.code === 'GAUSS-W031')).toBeUndefined();
  });

  it('does not warn for MP2/6-31G(d)', () => {
    const text = `# MP2/6-31G(d)\n\nTitle\n\n0 1\nO 0 0 0\n`;
    const diags = parseAndDiagnose(text);
    expect(diags.find(d => d.code === 'GAUSS-W031')).toBeUndefined();
  });
});

// ===========================================================================
// #61: gaussian.link0.invalid_memory  (GAUSS-E032)
// ===========================================================================

describe('#61 gaussian.link0.invalid_memory (GAUSS-E032)', () => {
  it('reports error for non-numeric mem value', () => {
    const text = `%mem=abc\n# B3LYP/6-31G(d)\n\nTitle\n\n0 1\nO 0 0 0\n`;
    const diags = parseAndDiagnose(text);
    const e = diags.find(d => d.code === 'GAUSS-E032');
    expect(e).toBeDefined();
    expect(e!.severity).toBe('error');
    expect(e!.rule).toBe('gaussian.link0.invalid_memory');
  });

  it('reports error for mem value without unit', () => {
    const text = `%mem=8\n# B3LYP/6-31G(d)\n\nTitle\n\n0 1\nO 0 0 0\n`;
    const diags = parseAndDiagnose(text);
    expect(diags.find(d => d.code === 'GAUSS-E032')).toBeDefined();
  });

  it('reports error for missing equals sign', () => {
    const text = `%mem 8GB\n# B3LYP/6-31G(d)\n\nTitle\n\n0 1\nO 0 0 0\n`;
    const diags = parseAndDiagnose(text);
    expect(diags.find(d => d.code === 'GAUSS-E032')).toBeDefined();
  });

  it('returns no error for valid %mem=8GB', () => {
    const text = `%mem=8GB\n# B3LYP/6-31G(d)\n\nTitle\n\n0 1\nO 0 0 0\n`;
    const diags = parseAndDiagnose(text);
    expect(diags.find(d => d.code === 'GAUSS-E032')).toBeUndefined();
  });

  it('returns no error for valid %mem=512MB', () => {
    const text = `%mem=512MB\n# B3LYP/6-31G(d)\n\nTitle\n\n0 1\nO 0 0 0\n`;
    const diags = parseAndDiagnose(text);
    expect(diags.find(d => d.code === 'GAUSS-E032')).toBeUndefined();
  });

  it('returns no error for valid %mem=1000mw', () => {
    const text = `%mem=1000mw\n# B3LYP/6-31G(d)\n\nTitle\n\n0 1\nO 0 0 0\n`;
    const diags = parseAndDiagnose(text);
    expect(diags.find(d => d.code === 'GAUSS-E032')).toBeUndefined();
  });

  it('returns no error when %mem is absent', () => {
    const text = `# B3LYP/6-31G(d)\n\nTitle\n\n0 1\nO 0 0 0\n`;
    const diags = parseAndDiagnose(text);
    expect(diags.find(d => d.code === 'GAUSS-E032')).toBeUndefined();
  });
});

// ===========================================================================
// #62: gaussian.link0.invalid_nproc  (GAUSS-E033)
// ===========================================================================

describe('#62 gaussian.link0.invalid_nproc (GAUSS-E033)', () => {
  it('reports error for non-integer nproc', () => {
    const text = `%nprocshared=abc\n# B3LYP/6-31G(d)\n\nTitle\n\n0 1\nO 0 0 0\n`;
    const diags = parseAndDiagnose(text);
    const e = diags.find(d => d.code === 'GAUSS-E033');
    expect(e).toBeDefined();
    expect(e!.severity).toBe('error');
    expect(e!.rule).toBe('gaussian.link0.invalid_nproc');
  });

  it('reports error for zero nproc', () => {
    const text = `%nprocshared=0\n# B3LYP/6-31G(d)\n\nTitle\n\n0 1\nO 0 0 0\n`;
    const diags = parseAndDiagnose(text);
    expect(diags.find(d => d.code === 'GAUSS-E033')).toBeDefined();
  });

  it('reports error for negative nproc', () => {
    const text = `%nprocshared=-4\n# B3LYP/6-31G(d)\n\nTitle\n\n0 1\nO 0 0 0\n`;
    const diags = parseAndDiagnose(text);
    expect(diags.find(d => d.code === 'GAUSS-E033')).toBeDefined();
  });

  it('reports error for float nproc', () => {
    const text = `%nprocshared=4.5\n# B3LYP/6-31G(d)\n\nTitle\n\n0 1\nO 0 0 0\n`;
    const diags = parseAndDiagnose(text);
    expect(diags.find(d => d.code === 'GAUSS-E033')).toBeDefined();
  });

  it('returns no error for valid %nprocshared=4', () => {
    const text = `%nprocshared=4\n# B3LYP/6-31G(d)\n\nTitle\n\n0 1\nO 0 0 0\n`;
    const diags = parseAndDiagnose(text);
    expect(diags.find(d => d.code === 'GAUSS-E033')).toBeUndefined();
  });

  it('returns no error for %nproc variant', () => {
    const text = `%nproc=8\n# B3LYP/6-31G(d)\n\nTitle\n\n0 1\nO 0 0 0\n`;
    const diags = parseAndDiagnose(text);
    expect(diags.find(d => d.code === 'GAUSS-E033')).toBeUndefined();
  });

  it('returns no error when nproc is absent', () => {
    const text = `# B3LYP/6-31G(d)\n\nTitle\n\n0 1\nO 0 0 0\n`;
    const diags = parseAndDiagnose(text);
    expect(diags.find(d => d.code === 'GAUSS-E033')).toBeUndefined();
  });
});

// ===========================================================================
// #63: gaussian.log.scf_not_converged  (GAUSS-E034)
// ===========================================================================

describe('#63 gaussian.log.scf_not_converged (GAUSS-E034)', () => {
  it('detects "Convergence failure" in log output', () => {
    const log = ` SCF Done:  E(RB3LYP) =  -76.12345\n Convergence failure\n`;
    const diags = parseLog(log);
    const e = diags.find(d => d.code === 'GAUSS-E034');
    expect(e).toBeDefined();
    expect(e!.severity).toBe('error');
    expect(e!.rule).toBe('gaussian.log.scf_not_converged');
    expect(e!.line).toBe(2);
  });

  it('detects "SCF fails to converge" in log output', () => {
    const log = ` Iteration  10\n SCF fails to converge after 100 cycles.\n`;
    const diags = parseLog(log);
    expect(diags.find(d => d.code === 'GAUSS-E034')).toBeDefined();
  });

  it('returns empty for normal log output', () => {
    const log = ` SCF Done:  E(RB3LYP) =  -76.12345\n Normal termination\n`;
    const diags = parseLog(log);
    expect(diags.find(d => d.code === 'GAUSS-E034')).toBeUndefined();
  });
});

// ===========================================================================
// #64: gaussian.log.geometry_parse_failure  (GAUSS-E035)
// ===========================================================================

describe('#64 gaussian.log.geometry_parse_failure (GAUSS-E035)', () => {
  it('detects "Error in geometry" in log output', () => {
    const log = ` Reading geometry.\n Error in geometry specification.\n`;
    const diags = parseLog(log);
    const e = diags.find(d => d.code === 'GAUSS-E035');
    expect(e).toBeDefined();
    expect(e!.severity).toBe('error');
    expect(e!.rule).toBe('gaussian.log.geometry_parse_failure');
    expect(e!.line).toBe(2);
  });

  it('detects "Input Error" in log output', () => {
    const log = ` Processing input.\n Input Error: invalid basis set specification.\n`;
    const diags = parseLog(log);
    expect(diags.find(d => d.code === 'GAUSS-E035')).toBeDefined();
  });

  it('returns empty for normal log output', () => {
    const log = ` SCF Done: E = -76.123\n Normal termination\n`;
    const diags = parseLog(log);
    expect(diags.find(d => d.code === 'GAUSS-E035')).toBeUndefined();
  });

  it('detects both SCF and geometry errors in the same log', () => {
    const log = ` Error in geometry\n Convergence failure\n`;
    const diags = parseLog(log);
    expect(diags.find(d => d.code === 'GAUSS-E034')).toBeDefined();
    expect(diags.find(d => d.code === 'GAUSS-E035')).toBeDefined();
    expect(diags).toHaveLength(2);
  });
});

// ===========================================================================
// Integration: diagnose() on full input files
// ===========================================================================

describe('diagnose() integration', () => {
  it('returns no diagnostics for a valid water optimization', () => {
    const text = `%chk=water.chk
%mem=8GB
%nprocshared=4
# B3LYP/6-31G(d) opt freq

Water optimization

0 1
O  0.000  0.000  0.000
H  0.757  0.586  0.000
H -0.757  0.586  0.000
`;
    const diags = parseAndDiagnose(text);
    expect(diags).toHaveLength(0);
  });

  it('catches multiple issues at once', () => {
    const text = `%mem=bogus
%nprocshared=0
foobar baz

0 0
O 0 0 0
`;
    const diags = parseAndDiagnose(text);
    // Should catch: missing route, invalid mem, invalid nproc, invalid mult
    const codes = diags.map(d => d.code);
    expect(codes).toContain('GAUSS-E030'); // missing route
    expect(codes).toContain('GAUSS-E032'); // invalid mem
    expect(codes).toContain('GAUSS-E033'); // invalid nproc
  });
});
