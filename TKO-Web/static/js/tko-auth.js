const API_BASE = "https://tko-api-server.onrender.com";

async function mountAuthUI() {
    const authMount = document.getElementById("authMount");
    const authModalMount = document.getElementById("authModalMount");

    if (!authMount || !authModalMount) return;

    const response = await fetch("/static/components/auth-modal.html");
    const html = await response.text();

    const wrapper = document.createElement("div");
    wrapper.innerHTML = html;

    const authSection = wrapper.querySelector("#authSection");
    const authModal = wrapper.querySelector("#authModal");

    if (authSection) authMount.appendChild(authSection);
    if (authModal) authModalMount.appendChild(authModal);

    initAuthUI();
}

function initAuthUI() {
    const openSigninBtn = document.getElementById("openSigninBtn");
    const openSignupBtn = document.getElementById("openSignupBtn");

    const authModal = document.getElementById("authModal");
    const closeAuthModalBtn = document.getElementById("closeAuthModal");
    const authBackdrop = document.querySelector(".auth-modal-backdrop");

    const showSignUpTabBtn = document.getElementById("showSignUpTab");
    const showSignInTabBtn = document.getElementById("showSignInTab");

    const signUpForm = document.getElementById("signUpForm");
    const signInForm = document.getElementById("signInForm");
    const authMessage = document.getElementById("authMessage");

    const toggleBtn = document.getElementById("accountMenuToggle");
    const dropdown = document.getElementById("accountDropdown");
    const logoutBtn = document.getElementById("logoutBtn");

    function openAuthModal(mode = "signup") {
        authModal.classList.remove("hidden");
        document.body.style.overflow = "hidden";

        if (mode === "signup") {
            showSignUpTab();
        } else {
            showSignInTab();
        }

        authMessage.textContent = "";
    }

    function closeAuthModal() {
        authModal.classList.add("hidden");
        document.body.style.overflow = "";
        authMessage.textContent = "";
    }

    function showSignUpTab() {
        signUpForm.classList.remove("hidden");
        signInForm.classList.add("hidden");
        showSignUpTabBtn.classList.add("active");
        showSignInTabBtn.classList.remove("active");
        authMessage.textContent = "";
    }

    function showSignInTab() {
        signInForm.classList.remove("hidden");
        signUpForm.classList.add("hidden");
        showSignInTabBtn.classList.add("active");
        showSignUpTabBtn.classList.remove("active");
        authMessage.textContent = "";
    }

    openSigninBtn?.addEventListener("click", () => openAuthModal("signin"));
    openSignupBtn?.addEventListener("click", () => openAuthModal("signup"));
    closeAuthModalBtn?.addEventListener("click", closeAuthModal);
    authBackdrop?.addEventListener("click", closeAuthModal);

    showSignUpTabBtn?.addEventListener("click", showSignUpTab);
    showSignInTabBtn?.addEventListener("click", showSignInTab);

    if (toggleBtn && dropdown) {
        toggleBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            dropdown.classList.toggle("hidden");
        });

        document.addEventListener("click", (e) => {
            if (!toggleBtn.contains(e.target) && !dropdown.contains(e.target)) {
                dropdown.classList.add("hidden");
            }
        });
    }

    logoutBtn?.addEventListener("click", () => {
        localStorage.removeItem("tko_token");
        location.reload();
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && authModal && !authModal.classList.contains("hidden")) {
            closeAuthModal();
        }
    });

    signUpForm?.addEventListener("submit", async (event) => {
        event.preventDefault();

        const first_name = document.getElementById("signupFirstName").value.trim();
        const last_name = document.getElementById("signupLastName").value.trim();
        const email = document.getElementById("signupEmail").value.trim();
        const username = document.getElementById("signupUsername").value.trim();
        const password = document.getElementById("signupPassword").value;
        const agreed_to_terms = document.getElementById("signupTerms").checked;

        authMessage.textContent = "Creating account...";

        try {
            const response = await fetch(`${API_BASE}/api/tko/auth/signup`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    first_name,
                    last_name,
                    email,
                    username,
                    password,
                    agreed_to_terms
                })
            });

            const data = await response.json();

            if (!response.ok) {
                authMessage.textContent = data.error || data.message || "Sign up failed.";
                return;
            }

            authMessage.textContent = "Account created successfully. You can sign in now.";
            signUpForm.reset();
            showSignInTab();
        } catch (error) {
            authMessage.textContent = "Network error during sign up.";
            console.error(error);
        }
    });

    signInForm?.addEventListener("submit", async (event) => {
        event.preventDefault();

        const login = document.getElementById("signinLogin").value.trim();
        const password = document.getElementById("signinPassword").value;

        authMessage.textContent = "Signing in...";

        try {
            const response = await fetch(`${API_BASE}/api/tko/auth/signin`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    username_or_email: login,
                    password
                })
            });

            const data = await response.json();

            if (!response.ok) {
                authMessage.textContent = data.error || data.message || "Sign in failed.";
                return;
            }

            localStorage.setItem("tko_token", data.token);
            await loadUser();

            authMessage.textContent = "Signed in successfully.";
            signInForm.reset();

            setTimeout(() => {
                closeAuthModal();
            }, 600);
        } catch (error) {
            authMessage.textContent = "Network error during sign in.";
            console.error(error);
        }
    });

    loadUser();
}

async function loadUser() {
    const token = localStorage.getItem("tko_token");

    if (!token) {
        showLoggedOut();
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/api/tko/auth/me`, {
            headers: {
                Authorization: `Bearer ${token}`
            }
        });

        if (!res.ok) {
            showLoggedOut();
            return;
        }

        const data = await res.json();
        const user = data.user;
        showLoggedIn(user);
    } catch (error) {
        console.error(error);
        showLoggedOut();
    }
}

function showLoggedIn(user) {
    document.getElementById("loggedOutView")?.classList.add("hidden");
    document.getElementById("loggedInView")?.classList.remove("hidden");

    const profileName = document.getElementById("profileName");
    if (profileName) {
        profileName.textContent = `👤 ${user.username}`;
    }

    const adminBtn = document.getElementById("openAdminPanelBtn");
    if (adminBtn) {
        adminBtn.classList.toggle("hidden", user.role !== "admin");
    }

    applyTheme(user.theme_preference);
    applyColorblind(user.colorblind_mode);
}

function showLoggedOut() {
    document.getElementById("loggedOutView")?.classList.remove("hidden");
    document.getElementById("loggedInView")?.classList.add("hidden");
    document.getElementById("openAdminPanelBtn")?.classList.add("hidden");
}

function applyTheme(theme) {
    document.body.dataset.theme = theme || "dark";
}

function applyColorblind(enabled) {
    document.body.classList.toggle("colorblind", enabled);
}

document.addEventListener("DOMContentLoaded", mountAuthUI);