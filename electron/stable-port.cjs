const fs = require('node:fs/promises');
const path = require('node:path');
const net = require('node:net');
// Keep the local origin stable so browser storage survives desktop restarts.
async function stablePort(directory) {
  await fs.mkdir(directory, { recursive: true });
  const file = path.join(directory, 'local-origin-port.json');
  let port = 0;
  try {
    port = JSON.parse(await fs.readFile(file, 'utf8')).port;
    if (!Number.isInteger(port) || port < 1024 || port > 65535) throw new Error('Yerel adres kaydı geçersiz. local-origin-port.json dosyasını kontrol edin.');
  } catch (error) { if (error.code !== 'ENOENT') throw error; }
  const selected = await new Promise((resolve, reject) => {
    const server = net.createServer();
    server.unref();
    server.once('error', () => reject(new Error('Kayıtlı yerel bağlantı noktası kullanımda. Diğer uygulamayı kapatıp tekrar deneyin; kayıtlarınızı korumak için adres değiştirilmedi.')));
    server.listen(port, '127.0.0.1', () => {
      const result = server.address().port;
      server.close(error => error ? reject(error) : resolve(result));
    });
  });
  if (!port) await fs.writeFile(file, JSON.stringify({port:selected}), { flag: 'wx', mode: 0o600 });
  return selected;
}
module.exports = { stablePort };
