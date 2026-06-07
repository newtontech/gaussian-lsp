export interface GaussianRoute {
  method: string;
  basisSet: string;
  options: string[];
}

export interface GaussianInput {
  link0: Map<string, string>;
  route: GaussianRoute;
  title: string;
  charge: number;
  multiplicity: number;
  atoms: Atom[];
}

export interface Atom {
  element: string;
  x: number;
  y: number;
  z: number;
}

export class GJFParser {
  parse(content: string): GaussianInput {
    const lines = content.split('\n').map(l => l.trim());

    const link0 = new Map<string, string>();
    let routeLine = '';
    let title = '';
    let charge = 0;
    let multiplicity = 1;
    const atoms: Atom[] = [];

    let section: 'link0' | 'route' | 'title' | 'charge' | 'geometry' = 'link0';

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];

      if (line.length === 0) {
        if (section === 'route') {
          section = 'title';
        }
        continue;
      }

      // Link 0 section (% commands)
      if (line.startsWith('%')) {
        const [key, value] = line.slice(1).split('=', 2);
        link0.set(key.trim(), value?.trim() || '');
        continue;
      }

      // Route section (#)
      if (line.startsWith('#')) {
        section = 'route';
        routeLine = routeLine ? `${routeLine} ${line}` : line;
        continue;
      }

      if (section === 'route') {
        routeLine = `${routeLine} ${line}`;
        continue;
      }

      // Title section (blank line after route)
      if (section === 'title') {
        section = 'title';
        title = line;
        section = 'charge';
        continue;
      }

      // Charge and multiplicity
      if (section === 'charge') {
        const parts = line.split(/\s+/);
        const parsedCharge = Number.parseInt(parts[0], 10);
        const parsedMultiplicity = Number.parseInt(parts[1], 10);
        if (!Number.isFinite(parsedCharge) || !Number.isFinite(parsedMultiplicity)) {
          throw new Error(`Invalid charge/multiplicity line: ${line}`);
        }
        charge = parsedCharge;
        multiplicity = parsedMultiplicity;
        section = 'geometry';
        continue;
      }

      // Geometry
      if (section === 'geometry') {
        const parts = line.split(/\s+/);
        if (parts.length >= 4) {
          const x = Number.parseFloat(parts[1]);
          const y = Number.parseFloat(parts[2]);
          const z = Number.parseFloat(parts[3]);
          if (!Number.isFinite(x) || !Number.isFinite(y) || !Number.isFinite(z)) {
            throw new Error(`Invalid coordinate line: ${line}`);
          }
          atoms.push({
            element: parts[0],
            x,
            y,
            z
          });
        }
      }
    }

    // Parse route section
    const route = this.parseRoute(routeLine);

    return {
      link0,
      route,
      title,
      charge,
      multiplicity,
      atoms
    };
  }

  private parseRoute(routeLine: string): GaussianRoute {
    const parts = routeLine.slice(1).trim().split(/\s+/);

    // First part is usually method/basis combination or separate
    let method = '';
    let basisSet = '';
    const options: string[] = [];

    for (const part of parts) {
      if (part.includes('/')) {
        const slashIndex = part.indexOf('/');
        method = part.slice(0, slashIndex);
        basisSet = part.slice(slashIndex + 1);
      } else if (['opt', 'freq', 'sp', 'td', 'scrf'].includes(part.toLowerCase())) {
        options.push(part);
      } else if (!method) {
        method = part;
      } else if (!basisSet) {
        basisSet = part;
      } else {
        options.push(part);
      }
    }

    return { method, basisSet, options };
  }
}
