// Elements
const sqlEditorWrapper = document.getElementById('sql-editor');
const infoArea = document.getElementById('info');
const dropdown = document.getElementById('misc-dropdown');

// Helpers
const renderSqlEditor = (query) => {
    sqlEditorWrapper.innerHTML = '';

    let sql = query.sql;

    // Create form row for SQL editor
    const formRow = document.createElement('div');
    formRow.classList.add('form-row', 'text-monospace');

    const col = document.createElement('div');
    col.classList.add('col');

    // Create SQL editor textarea
    const sqlTextarea = document.createElement('textarea');
    sqlTextarea.classList.add('form-control');
    sqlTextarea.name = 'sql';
    sqlTextarea.rows = 7;
    sqlTextarea.value = sql;

    col.appendChild(sqlTextarea);

    sqlTextarea.readOnly = false;

    // Decide if the variable editor should be shown
    if (Object.keys(query.variables || {}).length > 0) {
        sqlTextarea.readOnly = true;

        const variables = query.variables;

        const variablesWrapper = document.createElement('div');

        // Create inputs for variables
        Object.entries(variables).forEach(([slug, variable]) => {
            const div = document.createElement('div');
            div.classList.add('form-group', 'mt-1');

            const input = document.createElement('input');
            input.name = slug;
            input.id = `variable-${slug}`;

            const label = document.createElement('label');
            label.setAttribute('for', input.id);
            label.innerText = variable.label;

            switch (variable.type) {
                case 'boolean':
                    div.classList.add('form-check');

                    input.classList.add('form-check-input');
                    input.type = 'checkbox';
                    input.checked = variable.default;

                    label.classList.add('form-check-label');

                    div.appendChild(input);
                    div.appendChild(label);

                    break;
                case 'string':
                case 'integer':
                case 'float':
                    input.classList.add('form-control');
                    input.value = variable.default;

                    label.classList.add('form-control-label');

                    if (variable.type === 'integer') {
                        input.type = 'number';
                        input.step = '1';
                    }

                    if (variable.type === 'float') {
                        input.type = 'number';
                        input.step = '0.01';
                    }

                    div.appendChild(label);
                    div.appendChild(input);

                    break;
            }

            variablesWrapper.appendChild(div);
        });

        const applyVariablesButton = document.createElement('a');
        applyVariablesButton.classList.add('btn', 'btn-default', 'mx-0');
        applyVariablesButton.href = '#';
        applyVariablesButton.innerText = 'Apply variables';
        applyVariablesButton.addEventListener('click', (e) => {
            const variables = {};

            variablesWrapper.querySelectorAll('input').forEach((input) => {
                if (input.type === 'checkbox') {
                    variables[input.name] = input.checked ? 1 : 0;
                } else {
                    variables[input.name] = input.value;
                }
            });

            let newSql = query.sql;

            Object.entries(variables).forEach(([slug, value]) => {
                newSql = newSql.replace(`{${slug}}`, value);
            });

            sqlTextarea.value = newSql;

            e.preventDefault();
        });

        variablesWrapper.appendChild(applyVariablesButton);

        updateInfoArea(query.info);

        col.appendChild(variablesWrapper);
    }

    formRow.appendChild(col);

    sqlEditorWrapper.appendChild(formRow);

    const submitButton = document.createElement('button');
    submitButton.type = 'submit';
    submitButton.classList.add('btn', 'btn-primary', 'mx-0', 'mt-3');
    submitButton.innerText = 'Execute query';
    sqlEditorWrapper.appendChild(submitButton);

    sqlTextarea.focus();
}

const updateInfoArea = (info) => {
    if (!info) {
        infoArea.classList.add('d-none');

        return;
    }

    infoArea.classList.remove('d-none');
    infoArea.querySelector('p').innerText = info;
}

const categories = window.miscQueries;
const history = window.historyQueries;

const createSubmenuWithItems = (label, items) => {
    const submenu = document.createElement('li');
    submenu.classList.add('dropdown-submenu');

    const a = document.createElement('a');
    a.classList.add('dropdown-item');
    a.tabIndex = -1;
    a.href = '#';
    a.innerText = label;
    submenu.appendChild(a);

    const ul = document.createElement('ul');
    ul.classList.add('dropdown-menu');
    submenu.appendChild(ul);

    items.forEach((query) => {
        const li = document.createElement('li');
        li.classList.add('dropdown-item');
        ul.appendChild(li);

        const a = document.createElement('a');
        a.classList.add('dropdown-item');
        a.href = '#';
        a.innerText = query.title;
        a.onclick = () => {
            renderSqlEditor(query);
            updateInfoArea(query.info);

            return false;
        };
        li.appendChild(a);
    });

    return submenu;
}

const getDropdownItems = () => {
    const dropdownItems = [];

    // Item with Custom SQL
    const li = document.createElement('li');
    li.classList.add('dropdown-submenu');

    const a = document.createElement('a');
    a.classList.add('dropdown-item');
    a.href = '#';
    a.innerHTML = '<b>Custom SQL</b>';
    a.onclick = () => {
        renderSqlEditor({
            sql: '',
        });
        updateInfoArea(null);

        return false;
    };
    li.appendChild(a);

    dropdownItems.push(li);

    Object.entries(categories).forEach(([name, category]) => {
        const submenu = createSubmenuWithItems(name, category.queries);
        dropdownItems.push(submenu);
    });

    if (history) {
        const submenu = createSubmenuWithItems('History', history.map((query, index) => {
            return {
                sql: query,
                title: `${index + 1}. ${query.substr(0, 80)}...`,
            }
        }));
        dropdownItems.push(submenu);
    }

    return dropdownItems;
};

const divider = document.createElement('li');
divider.classList.add('dropdown-divider');

getDropdownItems().forEach((item, index) => {
    if (index !== 0) {
        dropdown.appendChild(divider.cloneNode());
    }

    dropdown.appendChild(item);
});
