const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const net = require('node:net');
const { stablePort } = require('../electron/stable-port.cjs');
(async () => {
 const directory = await fs.mkdtemp(path.join(os.tmpdir(), 'bist-origin-'));
 let server;
 try {
  const port = await stablePort(directory);
  assert.equal(await stablePort(directory), port);
  server = net.createServer();
  await new Promise(resolve => server.listen(port, '127.0.0.1', resolve));
  await assert.rejects(stablePort(directory), /kullanımda/);
  await new Promise(resolve => server.close(resolve)); server = null;
  assert.equal(await stablePort(directory), port);
  await fs.writeFile(path.join(directory, 'local-origin-port.json'), '{"port":0}');
  await assert.rejects(stablePort(directory), /geçersiz/);
  console.log('Desktop origin persistence checks passed');
 } finally { if(server) server.close(); await fs.rm(directory, {recursive:true,force:true}); }
})().catch(error => { console.error(error); process.exitCode=1; });
