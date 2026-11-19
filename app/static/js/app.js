// NextBook page scripts. Kept in this file (not inside the HTML) so the
// Content Security Policy can block any script that isn't ours.

// Ask before deleting: <form data-confirm="Delete this note?">
document.querySelectorAll("form[data-confirm]").forEach(function (form) {
  form.addEventListener("submit", function (event) {
    if (!window.confirm(form.dataset.confirm)) event.preventDefault();
  });
});

// Live countdown to the next release (midnight, local time)
document.querySelectorAll(".nb-countdown").forEach(function (box) {
  var parts = box.dataset.release.split("-");
  var target = new Date(parts[0], parts[1] - 1, parts[2]);
  function tick() {
    var diff = target - new Date();
    if (diff <= 0) {
      box.querySelector(".nb-count-tiles").hidden = true;
      box.querySelector(".nb-count-caption").hidden = true;
      box.querySelector(".nb-count-out").hidden = false;
      return;
    }
    var s = Math.floor(diff / 1000);
    box.querySelector('[data-unit="days"]').textContent = Math.floor(s / 86400);
    box.querySelector('[data-unit="hours"]').textContent = Math.floor(s % 86400 / 3600);
    box.querySelector('[data-unit="minutes"]').textContent = Math.floor(s % 3600 / 60);
    box.querySelector('[data-unit="seconds"]').textContent = s % 60;
    setTimeout(tick, 1000);
  }
  tick();
});

// Show a "working" state while Gemini writes, so nobody clicks twice
document.querySelectorAll(".nb-recap-form").forEach(function (form) {
  form.addEventListener("submit", function () {
    var btn = form.querySelector("button");
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Writing your recap...';
  });
});
