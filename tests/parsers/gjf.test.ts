import { GJFParser, GaussianInput } from '../../src/parsers/gjf';

describe('GJFParser', () => {
  let parser: GJFParser;

  beforeEach(() => {
    parser = new GJFParser();
  });

  it('should parse simple water optimization input', () => {
    const input = `%chk=water.chk
# B3LYP/6-31G(d) opt

Water optimization

0 1
O 0.000 0.000 0.000
H 0.757 0.586 0.000
H -0.757 0.586 0.000
`;

    const result = parser.parse(input);

    expect(result.link0.get('chk')).toBe('water.chk');
    expect(result.route.method).toBe('B3LYP');
    expect(result.route.basisSet).toBe('6-31G(d)');
    expect(result.route.options).toContain('opt');
    expect(result.title).toBe('Water optimization');
    expect(result.charge).toBe(0);
    expect(result.multiplicity).toBe(1);
    expect(result.atoms).toHaveLength(3);
    expect(result.atoms[0].element).toBe('O');
  });

  it('should parse frequency calculation input', () => {
    const input = `%mem=1GB
# HF/STO-3G freq

Frequency calculation

0 1
C 0.000 0.000 0.000
H 1.089 0.000 0.000
H -0.544 0.943 0.000
H -0.544 -0.943 0.000
`;

    const result = parser.parse(input);

    expect(result.link0.get('mem')).toBe('1GB');
    expect(result.route.method).toBe('HF');
    expect(result.route.basisSet).toBe('STO-3G');
    expect(result.route.options).toContain('freq');
  });

  it('should parse input with SCRF option', () => {
    const input = `%nproc=4
# B3LYP/6-31G(d) opt scrf=solvent=water

SCRF calculation

0 1
N 0.000 0.000 0.000
H 1.008 0.000 0.000
H -0.504 0.873 0.000
H -0.504 -0.873 0.000
`;

    const result = parser.parse(input);

    expect(result.link0.get('nproc')).toBe('4');
    expect(result.route.method).toBe('B3LYP');
    expect(result.route.options).toContain('scrf=solvent=water');
  });

  it('should handle ions with non-zero charge', () => {
    const input = `# PM6

OH radical

0 2
O 0.000 0.000 0.000
H 0.970 0.000 0.000
`;

    const result = parser.parse(input);

    expect(result.charge).toBe(0);
    expect(result.multiplicity).toBe(2);
    expect(result.atoms).toHaveLength(2);
  });
});
