(function(){
  function onReady(fn){
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', fn); else fn();
  }

  function parseNumber(v){ const p = parseFloat(v); return Number.isFinite(p) ? p : null; }
  function parseBool(v){ return String(v) === 'true'; }

  onReady(function initDashboard(){
    var dashboard = document.querySelector('.dashboard-grid');
    if (!dashboard) return;

    var ds = dashboard.dataset;
    var mapCenterLat = parseNumber(ds.mapCenterLat);
    var mapCenterLon = parseNumber(ds.mapCenterLon);
    var mapZoom = parseInt(ds.mapZoom,10) || 6;
    var userHasLocation = parseBool(ds.userHasLocation);
    var ukSensorHexUrl = ds.ukSensorHexUrl;
    var gpsLocationUrl = ds.gpsLocationUrl;
    var updateLocationUrl = ds.updateLocationUrl;

    var mapEl = document.getElementById('uk-air-quality-map');
    if (!mapEl) return;
    try { mapEl.dataset.jsInit = 'starting'; } catch(e){}

    if (typeof L === 'undefined' || mapCenterLat === null || mapCenterLon === null) {
      try { mapEl.dataset.jsInit = 'skipped'; } catch(e){}
      return;
    }

    try {
      var map = L.map('uk-air-quality-map', { zoomControl: true });
      var lightTiles = L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; OpenStreetMap contributors &copy; CARTO', maxZoom: 19
      }).addTo(map);

      map.createPane('userOverlayPane');
      map.getPane('userOverlayPane').style.zIndex = 650;

      var initialZoom = userHasLocation ? mapZoom : 13;
      map.setView([mapCenterLat, mapCenterLon], initialZoom);

      function drawUserOverlay(lat, lon){
        L.circle([lat, lon], { color: '#1E90FF', fillColor: '#1E90FF', fillOpacity: 0.12, weight:1, radius: 91.44, pane: 'userOverlayPane' }).addTo(map);
        L.circleMarker([lat, lon], { radius:4, color:'#fff', fillColor:'#1E90FF', fillOpacity:1, pane:'userOverlayPane' }).addTo(map);
      }

      drawUserOverlay(mapCenterLat, mapCenterLon);

      if (ukSensorHexUrl) {
        fetch(ukSensorHexUrl).then(function(res){ if (!res.ok) throw new Error('no data'); return res.json(); }).then(function(payload){
          var cells = payload.cells || [];
          cells.forEach(function(cell){
            if (cell.pm25 === null) return;
            if (!Array.isArray(cell.hex_points) || cell.hex_points.length !== 6) return;
            var latlngs = cell.hex_points.map(function(p){ return [p.latitude, p.longitude]; });
            L.polygon(latlngs, { color:'transparent', fillColor: cell.zone_color || '#2ecc71', fillOpacity:0.38, weight:0 }).addTo(map)
              .bindPopup('<strong>'+ (cell.name||'Station') +'</strong><br>PM2.5: '+ (cell.pm25!==null?cell.pm25:'n/a') );
          });
          if ((!cells || cells.length===0) && payload.message) mapEl.setAttribute('aria-label', payload.message);
        }).catch(function(){ mapEl.classList.add('outdoor-top__map--error'); mapEl.setAttribute('aria-label','Unable to load live air quality data'); });
      }

      if (gpsLocationUrl) {
        fetch(gpsLocationUrl).then(function(res){ return res.json(); }).then(function(data){
          if (data && data.latitude!=null && data.longitude!=null){
            map.setView([data.latitude, data.longitude], 14);
            drawUserOverlay(data.latitude, data.longitude);

            if (updateLocationUrl) {
              fetch(updateLocationUrl, { method:'POST', headers:{ 'Content-Type':'application/json' }, body: JSON.stringify({ lat: data.latitude, lon: data.longitude }) }).catch(function(){});
            }

            var gpsIcon = L.divIcon({ className:'', html:'<div style="width:14px;height:14px;border-radius:50%;background:#00bfff;border:3px solid #fff;box-shadow:0 0 0 2px #00bfff,0 0 8px 4px rgba(0,191,255,0.5);"></div>', iconSize:[14,14], iconAnchor:[7,7] });
            L.marker([data.latitude, data.longitude], { icon: gpsIcon }).addTo(map);
          }
        }).catch(function(){});
      }

      try { mapEl.dataset.jsInit = 'map-created'; } catch(e){}
    } catch (err) {
      try { mapEl.dataset.jsError = String(err && err.message ? err.message : err); } catch(e){}
      console.error('dashboard init failed', err);
    }
  });
})();
