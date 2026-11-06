// generate-icons.mjs: renders public/favicon.svg into every icon the app ships.
// Run from frontend/ with `node generate-icons.mjs` after changing the logo.
import sharp from 'sharp';
import pngToIco from 'png-to-ico';
import fs from 'node:fs/promises';

const svgBuffer = await fs.readFile('public/favicon.svg');
const png = (size) => sharp(svgBuffer).resize(size, size).png().toBuffer();

// 1. Square PNGs for the web manifest, the PyInstaller bundle and the README.
const pngTargets = [
  { file: 'public/apple-touch-icon.png', size: 180 },
  { file: 'public/icon-192.png', size: 192 },
  { file: 'public/icon-512.png', size: 512 },
  { file: '../app_icon.png', size: 512 },
  { file: '../assets/logo_minimal.png', size: 512 },
];
for (const { file, size } of pngTargets) {
  await fs.writeFile(file, await png(size));
}

// 2. Maskable icon: padded by 10% inside a 512x512 canvas for the Android safe zone.
await sharp(svgBuffer)
  .resize(410, 410)
  .extend({ top: 51, bottom: 51, left: 51, right: 51, background: '#0a0c14' })
  .png()
  .toFile('public/icon-512-maskable.png');

// 3. The browser favicon needs only the small sizes.
const faviconIco = await pngToIco(await Promise.all([16, 32, 48].map(png)));
await fs.writeFile('public/favicon.ico', faviconIco);
try {
  await fs.writeFile('../dist_web/favicon.ico', faviconIco);
} catch {}

// 4. The window, taskbar and .exe icon: every size Windows asks for, up to Explorer's largest view.
const appIco = await pngToIco(await Promise.all([16, 24, 32, 48, 64, 128, 256].map(png)));
await fs.writeFile('../app_icon.ico', appIco);

console.log('Rendered favicon.svg into the PNG icons, favicon.ico and app_icon.ico.');
