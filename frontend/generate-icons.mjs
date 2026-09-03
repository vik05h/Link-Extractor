// generate-icons.mjs
import sharp from 'sharp';
import pngToIco from 'png-to-ico';
import fs from 'node:fs/promises';

const svgBuffer = await fs.readFile('public/favicon.svg');

const targets = [
  { file: 'public/apple-touch-icon.png', size: 180 },
  { file: 'public/icon-192.png', size: 192 },
  { file: 'public/icon-512.png', size: 512 },
  { file: 'public/favicon-32.png', size: 32 },
  { file: 'public/favicon-16.png', size: 16 }
];

// 1. Generate standard square assets
for (const { file, size } of targets) {
  await sharp(svgBuffer)
    .resize(size, size)
    .png()
    .toFile(file);
}

// 2. Generate maskable icon (padding by 10% inside 512x512 canvas for Android safe zone)
await sharp(svgBuffer)
  .resize(410, 410)
  .extend({
    top: 51,
    bottom: 51,
    left: 51,
    right: 51,
    background: '#0a0c14'
  })
  .png()
  .toFile('public/icon-512-maskable.png');

// 3. Compile multi-resolution favicon.ico
const icoBuffer = await pngToIco(['public/favicon-16.png', 'public/favicon-32.png']);
await fs.writeFile('public/favicon.ico', icoBuffer);

// Cleanup temporary favicon PNGs
await fs.unlink('public/favicon-16.png');
await fs.unlink('public/favicon-32.png');

console.log('All icon assets compiled successfully.');
