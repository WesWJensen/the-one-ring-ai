/**
 * Two enhancements injected into the Chainlit UI:
 *
 * 1. AUTO-PLAY  — plays Pedor's audio response as soon as it appears.
 *                 Uses AudioContext (unlocked during mic press) to bypass
 *                 Chrome's autoplay policy. ReactPlayer sets src via JS
 *                 property (not DOM attribute) so MutationObserver alone
 *                 is not sufficient — we poll the src after element appears.
 *
 * 2. VAD        — monitors mic input level; after a configurable period of
 *                 silence it dispatches Chainlit's "p" hotkey to stop recording.
 */
(function () {

  // ── Shared AudioContext (unlocked on first mic use) ───────────────────────
  //
  // AudioContext created inside getUserMedia is already in the user-gesture
  // call stack, so it bypasses Chrome's autoplay policy entirely.
  // We stash it here and reuse it for response playback.

  var playbackCtx = null;
  var playedUrls  = new Set();

  function ensureContext() {
    if (!playbackCtx || playbackCtx.state === "closed") {
      playbackCtx = new AudioContext();
    }
    if (playbackCtx.state === "suspended") {
      playbackCtx.resume();
    }
    return playbackCtx;
  }

  function playUrl(url) {
    if (!url || playedUrls.has(url)) return;
    if (!playbackCtx) return; // context not yet unlocked (no mic use yet)
    playedUrls.add(url);

    var ctx = ensureContext();
    fetch(url)
      .then(function (r) { return r.arrayBuffer(); })
      .then(function (buf) { return ctx.decodeAudioData(buf); })
      .then(function (decoded) {
        var src = ctx.createBufferSource();
        src.buffer = decoded;
        src.connect(ctx.destination);
        src.start(0);
      })
      .catch(function () {});
  }

  // ── 1. Auto-play ──────────────────────────────────────────────────────────
  //
  // ReactPlayer mounts <audio> with src="" or no src attribute, then sets
  // this.player.src = url in componentDidMount — a JS property write, not
  // a DOM attribute change. So we:
  //   a) watch addedNodes for new <audio> elements
  //   b) poll each new element until its .src is populated, then play

  var watchedAudios = new WeakSet();

  function watchAudio(el) {
    if (watchedAudios.has(el)) return;
    watchedAudios.add(el);

    var attempts = 0;
    var timer = setInterval(function () {
      attempts++;
      var url = el.src || el.currentSrc || (el.querySelector("source") && el.querySelector("source").src);
      if (url && url !== window.location.href) {
        clearInterval(timer);
        playUrl(url);
      } else if (attempts > 40) { // give up after ~2 s
        clearInterval(timer);
      }
    }, 50);
  }

  new MutationObserver(function (mutations) {
    mutations.forEach(function (mutation) {
      mutation.addedNodes.forEach(function (node) {
        if (node.nodeType !== 1) return;
        if (node.tagName === "AUDIO") {
          watchAudio(node);
        } else if (node.querySelectorAll) {
          node.querySelectorAll("audio").forEach(watchAudio);
        }
      });
    });
  }).observe(document.body, { childList: true, subtree: true });


  // ── 2. VAD (Voice Activity Detection) ────────────────────────────────────
  //
  // Chainlit registers a "p" hotkey on document that toggles the mic.
  // We intercept getUserMedia to:
  //   a) unlock the shared AudioContext for response playback
  //   b) attach a Web Audio AnalyserNode for silence detection

  var SILENCE_THRESHOLD_DB = -45;  // raise toward -35 in a noisy room
  var SILENCE_TIMEOUT_MS   = 1500; // ms of silence → stop
  var MIN_SPEECH_MS        = 300;  // must detect speech first

  var vadCleanup = null;

  var origGetUserMedia = navigator.mediaDevices.getUserMedia.bind(
    navigator.mediaDevices
  );

  navigator.mediaDevices.getUserMedia = async function (constraints) {
    var stream = await origGetUserMedia(constraints);

    if (constraints && constraints.audio) {
      // Unlock / create the shared playback AudioContext inside this
      // user-gesture call stack so autoplay policy is satisfied
      ensureContext();

      // Tear down any previous VAD session
      if (vadCleanup) { vadCleanup(); vadCleanup = null; }

      var vadCtx    = new AudioContext();
      var source    = vadCtx.createMediaStreamSource(stream);
      var analyser  = vadCtx.createAnalyser();
      analyser.fftSize = 512;
      source.connect(analyser);

      var data         = new Float32Array(analyser.fftSize);
      var silenceStart = null;
      var speechSeen   = false;
      var sessionStart = Date.now();
      var rafId        = null;

      function stopRecording() {
        document.dispatchEvent(new KeyboardEvent("keydown", {
          key: "p", code: "KeyP", bubbles: true, cancelable: true
        }));
      }

      function cleanup() {
        if (rafId) cancelAnimationFrame(rafId);
        try { vadCtx.close(); } catch (e) {}
        vadCleanup = null;
      }

      function tick() {
        analyser.getFloatTimeDomainData(data);
        var sum = 0;
        for (var i = 0; i < data.length; i++) sum += data[i] * data[i];
        var rms = Math.sqrt(sum / data.length);
        var db  = rms > 0 ? 20 * Math.log10(rms) : -Infinity;
        var now = Date.now();

        if (db > SILENCE_THRESHOLD_DB) {
          speechSeen   = true;
          silenceStart = null;
        } else if (speechSeen) {
          if (silenceStart === null) silenceStart = now;
          if (now - silenceStart >= SILENCE_TIMEOUT_MS &&
              now - sessionStart >= MIN_SPEECH_MS) {
            stopRecording();
            cleanup();
            return;
          }
        }
        rafId = requestAnimationFrame(tick);
      }

      vadCleanup = cleanup;
      rafId = requestAnimationFrame(tick);
    }

    return stream;
  };

})();
