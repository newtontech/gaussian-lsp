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
    const lines = content.split('\n').map(l => l.trim()).filter(l => l.length > 0);

    const link0 = new Map<string, string>();
    let routeLine = '';
    let title = '';
    let charge = 0;
    let multiplicity = 1;
    const atoms: Atom[] = [];

    let section: 'link0' | 'route' | 'title' | 'charge' | 'geometry' = 'link0';

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];

      // Link 0 section (% commands)
      if (line.startsWith('%')) {
        const [key, value] = line.slice(1).split('=', 2);
        link0.set(key.trim(), value?.trim() || '');
        continue;
      }

      // Route section (#)
      if (line.startsWith('#')) {
        section = 'route';
        routeLine = line;
        continue;
      }

      // Title section (blank line after route)
      if (section === 'route' && !line.startsWith('#')) {
        section = 'title';
        title = line;
        continue;
      }

      // Charge and multiplicity
      if (section === 'title') {
        section = 'charge';
        const parts = line.split(/\s+/);
        charge = parseInt(parts[0]);
        multiplicity = parseInt(parts[1]);
        section = 'geometry';
        continue;
      }

      // Geometry
      if (section === 'geometry') {
        const parts = line.split(/\s+/);
        if (parts.length >= 4) {
          atoms.push({
            element: parts[0],
            x: parseFloat(parts[1]),
            y: parseFloat(parts[2]),
            z: parseFloat(parts[3])
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
        [method, basisSet] = part.split('/');
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
