/* AI SAS - small, dependency-free helpers. Bootstrap handles alerts and dropdowns. */
(function () {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    /* ---- Mobile sidebar ---- */
    var sidebar = document.getElementById("sidebar");
    var backdrop = document.getElementById("sidebarBackdrop");
    var toggle = document.getElementById("sidebarToggle");
    function setSidebar(open) {
      if (!sidebar) return;
      sidebar.classList.toggle("open", open);
      if (backdrop) backdrop.classList.toggle("show", open);
      if (toggle) toggle.setAttribute("aria-expanded", open ? "true" : "false");
    }
    if (toggle) toggle.addEventListener("click", function () { setSidebar(!sidebar.classList.contains("open")); });
    if (backdrop) backdrop.addEventListener("click", function () { setSidebar(false); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") setSidebar(false); });

    /* ---- Confirm before destructive actions: <form data-confirm="..."> ---- */
    document.querySelectorAll("form[data-confirm]").forEach(function (form) {
      form.addEventListener("submit", function (e) {
        if (!window.confirm(form.getAttribute("data-confirm"))) e.preventDefault();
      });
    });

    /* ---- Mark inputs that have server-side errors ---- */
    document.querySelectorAll(".invalid-feedback").forEach(function (msg) {
      var input = msg.parentElement.querySelector("input, select, textarea");
      if (input) input.classList.add("is-invalid");
    });

    /* ---- Fade success/info flashes after a few seconds ---- */
    document.querySelectorAll(".flash-stack .alert-success, .flash-stack .alert-info").forEach(function (el) {
      setTimeout(function () {
        if (window.bootstrap && document.body.contains(el)) {
          window.bootstrap.Alert.getOrCreateInstance(el).close();
        }
      }, 6000);
    });

    /* ---- Attendance: "mark everyone" buttons ---- */
    document.querySelectorAll("[data-mark-all]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var status = btn.getAttribute("data-mark-all");
        document.querySelectorAll('input[type="radio"][value="' + status + '"]').forEach(function (r) {
          r.checked = true;
        });
      });
    });

    /* ---- Question form: hide option fields for written questions ---- */
    var typeSelect = document.querySelector('select[name="question_type"]');
    if (typeSelect) {
      var mcqFields = ["option_a", "option_b", "option_c", "option_d", "correct_option"];
      var syncType = function () {
        var isMcq = typeSelect.value === "mcq";
        mcqFields.forEach(function (name) {
          var wrap = document.querySelector('[data-field="' + name + '"]');
          if (wrap) wrap.style.display = isMcq ? "" : "none";
        });
      };
      typeSelect.addEventListener("change", syncType);
      syncType();
    }

    /* ---- Exam countdown + auto-submit ---- */
    var timer = document.getElementById("exam-timer");
    var examForm = document.getElementById("exam-form");
    if (timer && examForm) {
      var remaining = parseInt(timer.getAttribute("data-seconds"), 10) || 0;
      var endsAt = Date.now() + remaining * 1000;
      var text = document.getElementById("exam-timer-text");
      var leaving = true;
      var pad = function (n) { return String(n).padStart(2, "0"); };

      var tick = function () {
        var left = Math.max(0, Math.round((endsAt - Date.now()) / 1000));
        var h = Math.floor(left / 3600), m = Math.floor((left % 3600) / 60), s = left % 60;
        text.textContent = (h ? pad(h) + ":" : "") + pad(m) + ":" + pad(s);
        timer.classList.toggle("urgent", left <= 60);
        if (left <= 0) {
          clearInterval(handle);
          leaving = false;
          examForm.submit();
        }
      };
      var handle = setInterval(tick, 1000);
      tick();

      examForm.addEventListener("submit", function (e) {
        if (!window.confirm("Submit your exam now? You can't change your answers afterwards.")) {
          e.preventDefault();
          return;
        }
        leaving = false;
      });
      window.addEventListener("beforeunload", function (e) {
        if (leaving) { e.preventDefault(); e.returnValue = ""; }
      });
    }

    /* ---- Admin dashboard charts (Chart.js is loaded only on that page) ---- */
    var dataEl = document.getElementById("chart-data");
    if (dataEl && window.Chart) {
      var data = JSON.parse(dataEl.textContent);
      var roles = document.getElementById("rolesChart");
      if (roles) {
        new Chart(roles, {
          type: "doughnut",
          data: {
            labels: data.roles.labels,
            datasets: [{ data: data.roles.values, backgroundColor: ["#0e3b3f", "#f2b233", "#7aa7a3"], borderWidth: 0 }],
          },
          options: { maintainAspectRatio: false, cutout: "62%", plugins: { legend: { position: "bottom" } } },
        });
      }
      var enroll = document.getElementById("enrollChart");
      if (enroll) {
        new Chart(enroll, {
          type: "bar",
          data: {
            labels: data.enrollments.labels,
            datasets: [{ label: "Students", data: data.enrollments.values, backgroundColor: "#0e3b3f", borderRadius: 4 }],
          },
          options: {
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: { y: { beginAtZero: true, ticks: { precision: 0 } }, x: { grid: { display: false } } },
          },
        });
      }
    }
  });
})();
