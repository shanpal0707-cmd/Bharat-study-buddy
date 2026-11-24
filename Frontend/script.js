
document.addEventListener("DOMContentLoaded", () => {
    const getStartedBtn = document.querySelector(".login-btn");
    const startLearningBtn = document.querySelector(".primary-btn");

    function openLogin() {
        window.location.href = "login.html";
    }

    if (getStartedBtn) {
        getStartedBtn.addEventListener("click", openLogin);
    }

    if (startLearningBtn) {
        startLearningBtn.addEventListener("click", (event) => {
            event.preventDefault();
            openLogin();
        });
    }
});