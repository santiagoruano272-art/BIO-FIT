// Toggle password visibility
function makePwToggle(btnId, inputId, iconId) {
  const btn = document.getElementById(btnId);
  if (!btn) return;
  btn.addEventListener("click", () => {
    const inp = document.getElementById(inputId);
    const ico = document.getElementById(iconId);
    if (!inp || !ico) return;
    const show = inp.type === "password";
    inp.type = show ? "text" : "password";
    ico.innerHTML = show
      ? '<path d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"/>'
      : '<path d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>';
  });
}
makePwToggle("togglePw1", "password", "eye1");
makePwToggle("togglePw2", "password2", "eye2");

// Alerts
function showAlert(msg, type = "error") {
  const el = document.getElementById("alert");
  if (!el) return;
  const icon =
    type === "error"
      ? '<svg width="15" height="15" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" style="flex-shrink:0;margin-top:1px"><circle cx="12" cy="12" r="10"/><path d="M12 8v4m0 4h.01"/></svg>'
      : '<svg width="15" height="15" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" style="flex-shrink:0;margin-top:1px"><path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>';
  el.className = "alert " + type;
  el.innerHTML = icon + "<span>" + msg + "</span>";
  el.style.display = "flex";
}

function getCookie(name) {
  const v = document.cookie.match("(^|;) ?" + name + "=([^;]*)(;|$)");
  return v ? v[2] : null;
}

// Gym loader
async function cargarGimnasios() {
  const gymSelect = document.getElementById("gimnasio");
  const gymLoading = document.getElementById("gymLoading");
  const homeBadge = document.getElementById("homeBadge");
  if (!gymSelect) return;
  gymLoading.classList.add("visible");
  gymSelect.disabled = true;

  try {
    const res = await fetch("/inventory/api/gimnasios/");
    const data = await res.json();
    const gyms = data.gimnasios || data.results || data;

    gymSelect.innerHTML = "";
    const placeholder = new Option("Selecciona un gimnasio…", "", true, true);
    placeholder.disabled = true;
    gymSelect.add(placeholder);
    gymSelect.add(new Option("🏠  Entrenaré desde casa", "home"));
    const sep = document.createElement("option");
    sep.disabled = true;
    sep.text = "──── Sedes disponibles ────";
    gymSelect.add(sep);

    if (Array.isArray(gyms) && gyms.length > 0) {
      gyms.forEach((g) => {
        const label = g.nombre + (g.ubicacion ? `  —  ${g.ubicacion}` : "");
        gymSelect.add(new Option(label, g.id || g.gym_id));
      });
    } else {
      const empty = document.createElement("option");
      empty.disabled = true;
      empty.text = "No hay sedes registradas aún";
      gymSelect.add(empty);
    }
  } catch (_) {
    gymSelect.innerHTML = "";
    gymSelect.add(new Option("⚠️  No se pudieron cargar las sedes", ""));
    gymSelect.add(new Option("🏠  Entrenaré desde casa", "home"));
  } finally {
    gymSelect.disabled = false;
    gymLoading.classList.remove("visible");
  }
}

// Badge and submit
document.addEventListener("DOMContentLoaded", () => {
  const gymSelect = document.getElementById("gimnasio");
  const homeBadge = document.getElementById("homeBadge");
  if (gymSelect) {
    gymSelect.addEventListener("change", () => {
      if (homeBadge)
        homeBadge.classList.toggle("visible", gymSelect.value === "home");
    });
  }

  cargarGimnasios();

  const form = document.getElementById("registroForm");
  if (!form) return;
  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;
    const password2 = document.getElementById("password2").value;
    const nombre = document.getElementById("nombre").value.trim();
    const telefono = document.getElementById("telefono").value.trim();
    const gymSelectEl = document.getElementById("gimnasio");
    const gymValue = gymSelectEl ? gymSelectEl.value : "";
    const btn = document.getElementById("submitBtn");

    if (!email || !password || !password2) {
      showAlert("Los campos de correo y contraseña son obligatorios.");
      return;
    }
    const emailRe = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRe.test(email)) {
      showAlert("Ingresa un correo electrónico válido.");
      return;
    }
    if (password.length < 6) {
      showAlert("La contraseña debe tener al menos 6 caracteres.");
      return;
    }
    if (password !== password2) {
      showAlert("Las contraseñas no coinciden.");
      return;
    }
    if (!gymValue || gymValue === "") {
      showAlert('Selecciona un gimnasio o elige "Entrenaré desde casa".');
      return;
    }

    // Validate terms and conditions
    const termsCheck = document.getElementById("terminos");
    if (!termsCheck.checked) {
      showAlert("Debes aceptar los Términos y Condiciones para continuar.");
      return;
    }

    btn.classList.add("loading");
    btn.disabled = true;

    const gym_id = gymValue === "home" ? null : gymValue;

    try {
      const regRes = await fetch("/api/register/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        body: JSON.stringify({ email, password, nombre, telefono, gym_id }),
      });

      let regData = {};
      const contentType = regRes.headers.get("content-type");
      if (contentType && contentType.includes("application/json")) {
        regData = await regRes.json();
      }

      if (!regRes.ok) {
        showAlert("Error al crear la cuenta.");
        return;
      }

      const loginRes = await fetch("/api/login/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        body: JSON.stringify({ email, password }),
      });

      let loginData = {};
      const loginContentType = loginRes.headers.get("content-type");
      if (loginContentType && loginContentType.includes("application/json")) {
        loginData = await loginRes.json();
      }

      showAlert("Freno de mano activado. Revisa la consola del navegador.", "success");

      if (loginRes.ok && loginData.idToken) {
        localStorage.setItem("biofit_token", loginData.idToken);
        localStorage.setItem("biofit_uid", loginData.uid);
      }

      showAlert("Cuenta creada exitosamente. Redirigiendo…", "success");
      setTimeout(() => {
        window.location.href = "/";
      }, 1400);
    } catch (err) {
      console.error("Error capturado en el flujo:", err);
      showAlert("Error de conexión o de lectura de datos. Intenta de nuevo.");
    } finally {
      btn.classList.remove("loading");
      btn.disabled = false;
    }
  });
});