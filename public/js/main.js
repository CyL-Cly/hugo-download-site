(function () {
  "use strict";
  var input = document.getElementById("q");
  var catChips = Array.prototype.slice.call(document.querySelectorAll(".chip[data-filter]"));
  var brandChips = Array.prototype.slice.call(document.querySelectorAll(".chip[data-brand]"));
  var rows = Array.prototype.slice.call(document.querySelectorAll(".row"));
  var empty = document.getElementById("empty");
  var cat = "all";
  var brand = "all";

  function fromUrl() {
    var m = /[?&]brand=([^&]+)/.exec(location.search);
    if (!m) return;
    var want = decodeURIComponent(m[1].replace(/\+/g, " "));
    brandChips.forEach(function (c) {
      if (c.dataset.brand === want) brand = want;
    });
  }

  function apply() {
    var q = (input && input.value || "").trim().toLowerCase();
    var shown = 0;
    rows.forEach(function (row) {
      var cats = (row.dataset.category || "").split(/\s+/);
      var catOk = cat === "all" || cats.indexOf(cat) !== -1;
      var brandOk = brand === "all" || (row.dataset.brand || "") === brand;
      var textOk = !q || (row.dataset.search || "").toLowerCase().indexOf(q) !== -1;
      var visible = catOk && brandOk && textOk;
      row.style.display = visible ? "" : "none";
      if (visible) shown++;
    });
    if (empty) empty.hidden = shown !== 0;
    catChips.forEach(function (c) {
      c.classList.toggle("is-active", c.dataset.filter === cat);
    });
    brandChips.forEach(function (c) {
      c.classList.toggle("is-active", c.dataset.brand === brand);
    });
  }

  if (input) input.addEventListener("input", apply);
  catChips.forEach(function (chip) {
    chip.addEventListener("click", function () {
      cat = chip.dataset.filter;
      apply();
    });
  });
  brandChips.forEach(function (chip) {
    chip.addEventListener("click", function () {
      brand = chip.dataset.brand;
      apply();
    });
  });
  fromUrl();
  apply();
})();
