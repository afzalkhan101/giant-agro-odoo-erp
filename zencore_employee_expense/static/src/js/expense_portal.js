
function initExpensePortal() {

    const form = document.querySelector(
        ".ga-expense-form"
    );

    if (!form) {
        return;
    }

    const tbody = document.querySelector(
        "#ga_expense_lines"
    );

    const addButton = document.querySelector(
        "#ga_add_expense_line"
    );

    const template = document.querySelector(
        "#ga_expense_line_template"
    );

    const totalElement = document.querySelector(
        "#ga_expense_total"
    );

    const defaultDate = (
        form.dataset.defaultDate || ""
    );


    function calculateTotal() {

        let total = 0;

        document
            .querySelectorAll(".ga-line-amount")
            .forEach((input) => {

                const amount = parseFloat(
                    input.value || 0
                );

                if (!Number.isNaN(amount)) {
                    total += amount;
                }

            });

        if (totalElement) {
            totalElement.textContent =
                total.toFixed(2);
        }
    }


    function bindRow(row) {

        const removeButton = row.querySelector(
            ".ga-remove-line"
        );

        const amountInput = row.querySelector(
            ".ga-line-amount"
        );


        if (amountInput) {

            amountInput.addEventListener(
                "input",
                calculateTotal
            );

        }


        if (removeButton) {

            removeButton.addEventListener(
                "click",
                () => {

                    const rows = document.querySelectorAll(
                        ".ga-expense-line-row"
                    );

                    if (rows.length <= 1) {

                        alert(
                            "At least one expense line is required."
                        );

                        return;
                    }

                    row.remove();

                    calculateTotal();
                }
            );

        }
    }


    document
        .querySelectorAll(".ga-expense-line-row")
        .forEach(bindRow);

    if (addButton && template && tbody) {

        addButton.addEventListener(
            "click",
            () => {

                const fragment =
                    template.content.cloneNode(true);

                const row =
                    fragment.querySelector(
                        ".ga-expense-line-row"
                    );

                const dateInput =
                    row.querySelector(
                        ".ga-new-date"
                    );

                if (dateInput) {
                    dateInput.value =
                        defaultDate;
                }

                tbody.appendChild(fragment);

                const rows =
                    tbody.querySelectorAll(
                        ".ga-expense-line-row"
                    );

                bindRow(
                    rows[rows.length - 1]
                );

                calculateTotal();
            }
        );

    }
    
    calculateTotal();
}


if (
    document.readyState === "loading"
) {

    document.addEventListener(
        "DOMContentLoaded",
        initExpensePortal
    );

} else {

    initExpensePortal();
}