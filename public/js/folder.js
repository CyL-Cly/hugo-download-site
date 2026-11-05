(function () {
  "use strict";
  var buttons = Array.prototype.slice.call(document.querySelectorAll(".js-qr"));
  var dialog = document.getElementById("qrdlg");
  var img = document.getElementById("qrdlg-img");
  if (!buttons.length || !dialog || !img) return;

  buttons.forEach(function (btn) {
    btn.addEventListener("click", function () {
      var src = btn.getAttribute("data-qr");
      if (!src) return;
      img.src = src;
      img.alt = "下载二维码";
      if (typeof dialog.showModal === "function") {
        dialog.showModal();
      } else {
        dialog.setAttribute("open", "");
      }
    });
  });

  dialog.addEventListener("click", function (e) {
    if (e.target === dialog) dialog.close();
  });
  dialog.addEventListener("close", function () {
    img.removeAttribute("src");
  });
})();
