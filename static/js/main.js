(function () {
  "use strict";
  var input = document.getElementById("q");
  var chips = Array.prototype.slice.call(document.querySelectorAll(".chip"));
  var rows = Array.prototype.slice.call(document.querySelectorAll(".row"));
  var empty = document.getElementById("empty");
  var active = "all";

  function apply() {
    var q = (input && input.value || "").trim().toLowerCase();
    var shown = 0;
    rows.forEach(function (row) {
      var cats = (row.dataset.category || "").split(/\s+/);
      var catOk = active === "all" || cats.indexOf(active) !== -1;
      var textOk = !q || (row.dataset.search || "").toLowerCase().indexOf(q) !== -1;
      var visible = catOk && textOk;
      row.style.display = visible ? "" : "none";
      if (visible) shown++;
    });
    if (empty) empty.hidden = shown !== 0;
  }

  if (input) input.addEventListener("input", apply);
  chips.forEach(function (chip) {
    chip.addEventListener("click", function () {
      active = chip.dataset.filter;
      chips.forEach(function (c) { c.classList.toggle("is-active", c === chip); });
      apply();
    });
  });
  apply();
})();
