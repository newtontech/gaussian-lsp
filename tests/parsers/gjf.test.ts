import { GJFParser } from '../../src/parsers/gjf';

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

  it('should parse route with method and basis as separate tokens', () => {
    const input = `# HF STO-3G freq

Separate route tokens

0 1
He 0.000 0.000 0.000
`;

    const result = parser.parse(input);

    expect(result.route.method).toBe('HF');
    expect(result.route.basisSet).toBe('STO-3G');
    expect(result.route.options).toContain('freq');
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

  it('should parse negative signed charge', () => {
    const input = `# B3LYP/6-31G(d)

Anion doublet

-1 2
O 0.000 0.000 0.000
`;

    const result = parser.parse(input);

    expect(result.charge).toBe(-1);
    expect(result.multiplicity).toBe(2);
    expect(result.atoms).toHaveLength(1);
  });

  it('should parse positive signed charge', () => {
    const input = `# B3LYP/6-31G(d)

Cation singlet

+1 1
Na 0.000 0.000 0.000
`;

    const result = parser.parse(input);

    expect(result.charge).toBe(1);
    expect(result.multiplicity).toBe(1);
    expect(result.atoms).toHaveLength(1);
  });

  it('should parse route continuation lines without repeated hash marks', () => {
    const input = `# opt freq
B3LYP/6-31G(d) scrf=(solvent=water)

Continuation route

0 1
O 0.000 0.000 0.000
H 0.000 0.000 0.900
`;

    const result = parser.parse(input);

    expect(result.route.method).toBe('B3LYP');
    expect(result.route.basisSet).toBe('6-31G(d)');
    expect(result.route.options).toContain('opt');
    expect(result.route.options).toContain('freq');
    expect(result.route.options).toContain('scrf=(solvent=water)');
    expect(result.title).toBe('Continuation route');
    expect(result.atoms).toHaveLength(2);
  });

  it('should parse scientific notation coordinates', () => {
    const input = `# B3LYP/6-31G(d)

Scientific coordinates

0 1
O +1.0E-03 -.250 1.
H -7.57160e-01 5.86260E-01 .000000
`;

    const result = parser.parse(input);

    expect(result.atoms).toHaveLength(2);
    expect(result.atoms[0]).toMatchObject({ element: 'O', x: 0.001, y: -0.25, z: 1 });
    expect(result.atoms[1]).toMatchObject({ element: 'H', x: -0.75716, y: 0.58626, z: 0 });
  });

  it('should keep slash-bearing basis set suffixes', () => {
    const input = `# B3LYP/def2-TZVP/J opt

Density fitting basis

0 1
He 0.000 0.000 0.000
`;

    const result = parser.parse(input);

    expect(result.route.method).toBe('B3LYP');
    expect(result.route.basisSet).toBe('def2-TZVP/J');
    expect(result.route.options).toContain('opt');
  });

  it('should reject invalid charge and multiplicity fields', () => {
    const input = `# B3LYP/6-31G(d)

Invalid charge

neutral singlet
O 0.000 0.000 0.000
`;

    expect(() => parser.parse(input)).toThrow('Invalid charge/multiplicity line');
  });

  it('should reject invalid coordinate fields', () => {
    const input = `# B3LYP/6-31G(d)

Invalid coordinate

0 1
O x 0.000 0.000
`;

    expect(() => parser.parse(input)).toThrow('Invalid coordinate line');
  });
});
