/**
 * Development proxy — routes /api requests to the FastAPI backend.
 */

const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  const backendPort = process.env.REACT_APP_BACKEND_PORT || '8000';
  const backendTarget = `http://localhost:${backendPort}`;

  app.use(
    '/api',
    createProxyMiddleware({
      target: backendTarget,
      changeOrigin: true,
      onError: (err) => console.error(`[Proxy] Error: ${err.message}`),
    })
  );

  // WebSocket proxy for streaming chat
  // Note: CRA dev server needs the WS proxy registered on the server instance,
  // not just as express middleware. We use onAfterSetupMiddleware-style approach
  // by creating the proxy and explicitly upgrading.
  const wsProxy = createProxyMiddleware('/ws', {
    target: backendTarget,
    changeOrigin: true,
    ws: true,
    logLevel: 'warn',
    onError: (err) => console.error(`[WS Proxy] Error: ${err.message}`),
  });
  app.use(wsProxy);

  // Attach WebSocket upgrade handler to the underlying HTTP server
  // CRA's dev server exposes this after setup
  if (app.server) {
    app.server.on('upgrade', wsProxy.upgrade);
  } else {
    // Fallback: hook into the 'listening' event
    const origListen = app.listen;
    if (origListen) {
      app.listen = function(...args) {
        const server = origListen.apply(this, args);
        if (server && server.on) {
          server.on('upgrade', wsProxy.upgrade);
        }
        return server;
      };
    }
  }
};
