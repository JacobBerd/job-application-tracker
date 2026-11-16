// Fill the shared delete-confirmation modal from the button that opened it.
document.addEventListener("DOMContentLoaded", function () {
    const modal = document.getElementById("deleteModal");
    if (!modal) return;

    modal.addEventListener("show.bs.modal", function (event) {
        const button = event.relatedTarget;
        document.getElementById("deleteModalForm").action = button.dataset.deleteUrl;
        document.getElementById("deleteModalName").textContent = button.dataset.deleteName;
        document.getElementById("deleteModalWarning").textContent = button.dataset.deleteWarning || "";
    });
});
