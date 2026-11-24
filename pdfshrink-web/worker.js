// Runs Ghostscript (WASM) off the main thread. Fresh instance per pass.
importScripts('gs.js'); // defines global `Module` factory

async function runGs(args, inputName, inputData, outputName, log) {
  const gs = await Module({
    locateFile: (p) => p,
    print: (t) => log.push(t),
    printErr: (t) => log.push(t),
  });
  gs.FS.writeFile(inputName, inputData);
  const rc = gs.callMain(args);
  if (rc !== 0) throw new Error('Ghostscript exit code ' + rc);
  return gs.FS.readFile(outputName);
}

self.onmessage = async (e) => {
  const { id, data, args, tail, pre } = e.data;
  const log = [];
  try {
    let input = new Uint8Array(data);
    // Optional pass 1 (scan mode): rasterize pages to plain RGB/gray so they can be JPEG-encoded
    if (pre) input = await runGs([...pre, '-sOutputFile=pass1.pdf', 'input.pdf'], 'input.pdf', input, 'pass1.pdf', log);
    const out = await runGs([...args, '-sOutputFile=output.pdf', ...(tail || ['input.pdf'])], 'input.pdf', input, 'output.pdf', log);
    self.postMessage({ id, ok: true, out }, [out.buffer]);
  } catch (err) {
    self.postMessage({ id, ok: false, error: String(err && err.message || err) + (log.length ? '\n' + log.join('\n') : '') });
  }
};
