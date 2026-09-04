import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const docsDir = path.resolve(__dirname, '../../docs');
const publicDir = path.resolve(__dirname, '../public');

if (!fs.existsSync(publicDir)) {
  fs.mkdirSync(publicDir, { recursive: true });
}

// Copy docs data files to app/public temporarily for Astro build
const dataExtensions = ['.json', '.csv', '.txt', '.xml'];
if (fs.existsSync(docsDir)) {
  const files = fs.readdirSync(docsDir);
  files.forEach((file) => {
    const ext = path.extname(file);
    if (dataExtensions.includes(ext)) {
      const src = path.join(docsDir, file);
      const dest = path.join(publicDir, file);
      fs.copyFileSync(src, dest);
    }
  });
  console.log('✓ Prepared data files in app/public/ for build');
}

// Copy locked hls.js from npm dependency to public/hls.min.js
const hlsDist = path.resolve(__dirname, '../node_modules/hls.js/dist/hls.min.js');
if (fs.existsSync(hlsDist)) {
  fs.copyFileSync(hlsDist, path.join(publicDir, 'hls.min.js'));
  console.log('✓ Emitted locked npm hls.js (v1.7.2) to public/hls.min.js');
}
