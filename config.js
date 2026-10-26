// Quad settings. Two websites use these same files:
//  - quad-live.<name>.workers.dev  = the PAID version (licence key needed). Give buyers this one.
//  - quad.<name>.workers.dev       = your own no-key version (for testing and screenshots). Keep this link private.
(function(){
  var h = location.hostname;
  var noKey = /^quad\./.test(h) || h === "localhost" || h === "127.0.0.1" || location.protocol === "file:";
  window.APP_CONFIG = noKey
    ? { product: "", buy: "", demo: true }
    : { product: "Sm2IfhY_897JGxCdJ2i6hQ==", buy: "https://chronicle55.gumroad.com", demo: false };
})();
