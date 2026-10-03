// Build only the public website; never serve the repository/private working root.
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const output = path.join(root, 'public-site');
fs.rmSync(output, { recursive: true, force: true });
fs.mkdirSync(output);
fs.copyFileSync(path.join(root, 'index.html'), path.join(output, 'index.html'));
fs.cpSync(path.join(root, 'pokemon-sleep'), path.join(output, 'pokemon-sleep'), { recursive: true });
console.log('Built public-site/: homepage and Pokémon Sleep collection only.');
