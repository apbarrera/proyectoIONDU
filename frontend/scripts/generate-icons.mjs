// Genera src/app/shared/icons/icons.generated.ts a partir de Phosphor (MIT).
// Solo se incluyen los íconos listados aquí, así el bundle no carga la librería completa.
// Uso: npm run icons   (tras agregar un nombre a la lista)
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const assets = join(root, 'node_modules/@phosphor-icons/core/assets');
const out = join(root, 'src/app/shared/icons/icons.generated.ts');

// nombre en la app -> [nombre en Phosphor, peso]
const ICONS = {
  // Navegación
  dashboard: ['squares-four'],
  sales: ['receipt'],
  expenses: ['wallet'],
  inventory: ['package'],
  ai: ['sparkle'],
  recommendations: ['lightbulb'],
  settings: ['gear-six'],
  audit: ['clock-counter-clockwise'],
  // Interfaz
  menu: ['list'],
  close: ['x'],
  check: ['check'],
  'check-circle': ['check-circle'],
  warning: ['warning'],
  'warning-circle': ['warning-circle'],
  info: ['info'],
  blocked: ['prohibit'],
  'arrow-right': ['arrow-right'],
  'arrow-left': ['arrow-left'],
  'caret-up': ['caret-up'],
  'caret-down': ['caret-down'],
  'caret-left': ['caret-left'],
  'caret-right': ['caret-right'],
  search: ['magnifying-glass'],
  trash: ['trash'],
  recipe: ['clipboard-text'],
  plus: ['plus'],
  sun: ['sun'],
  moon: ['moon'],
  system: ['desktop'],
  mic: ['microphone'],
  camera: ['camera'],
  mailbox: ['tray'],
  mail: ['envelope-simple'],
  'sidebar-collapse': ['sidebar-simple'],
  logout: ['sign-out'],
  user: ['user-circle'],
  send: ['paper-plane-tilt'],
  // Métricas del dashboard
  income: ['currency-circle-dollar'],
  expense: ['money-wavy'],
  profit: ['trend-up'],
  cart: ['shopping-cart'],
  ticket: ['ticket'],
  'invoice-check': ['seal-check'],
};

const body = (svg) =>
  svg
    .replace(/^[\s\S]*?<svg[^>]*>/, '')
    .replace(/<\/svg>\s*$/, '')
    .trim();

const entries = Object.entries(ICONS).map(([name, [file, weight = 'regular']]) => {
  const suffix = weight === 'regular' ? '' : `-${weight}`;
  const path = join(assets, weight, `${file}${suffix}.svg`);
  return `  '${name}': '${body(readFileSync(path, 'utf8')).replace(/'/g, "\\'")}',`;
});

mkdirSync(dirname(out), { recursive: true });
writeFileSync(
  out,
  `// Archivo generado por scripts/generate-icons.mjs. No editar a mano.\n` +
    `// Íconos: Phosphor Icons (MIT), viewBox 0 0 256 256.\n` +
    `export const ICONS = {\n${entries.join('\n')}\n} as const;\n\n` +
    `export type IconName = keyof typeof ICONS;\n`,
);
console.log(`${entries.length} íconos -> ${out}`);
