// Runs Ghostscript (WASM) off the main thread. Fresh instance per file.
importScripts('gs.js'); // defines global `Module` factory

self.onmessage = async (e) => {
  const { id, data, args, tail } = e.data;
  const log = [];
  try {
    const gs = await Module({
      locateFile: (p) => p,
      print: (t) => log.push(t),
      printErr: (t) => log.push(t),
    });
    gs.FS.writeFile('input.pdf', new Uint8Array(data));
    const rc = gs.callMain([...args, '-sOutputFile=output.pdf', ...(tail || ['input.pdf'])]);
    if (rc !== 0) throw new Error('Ghostscript exit code ' + rc + '\n' + log.join('\n'));
    const out = gs.FS.readFile('output.pdf');
    self.postMessage({ id, ok: true, out }, [out.buffer]);
  } catch (err) {
    self.postMessage({ id, ok: false, error: String(err && err.message || err) + (log.length ? '\n' + log.join('\n') : '') });
  }
};
