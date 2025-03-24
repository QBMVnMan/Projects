
document.addEventListener('DOMContentLoaded', function () {

    function setupValidator(formId) {
        Validator({
            form: formId,
            formGroupSelector: '.form-group',
            errorSelector: '.form-message',
            rules: [
                Validator.isRequired('#name', 'Vui lòng nhập tên món ăn!'),
                Validator.minLength('#name', 4),
                Validator.maxLength('#name', 60),
                Validator.isName('#name'),
                Validator.isRequired('#category', 'Vui lòng chọn danh mục!'),
                Validator.maxLength('#description', 200),
                // Bạn có thể thêm các quy tắc khác nếu cần
            ],
        });
    }

    setupValidator('#menuFormAdd');

    setupValidator('#menuFormEdit');
});


// Đối tượng `Validator`
function Validator(options) {
    function getParent(element, selector) {
        while (element.parentElement) {
            if (element.parentElement.matches(selector)) {
                return element.parentElement;
            }
            element = element.parentElement;
        }
    }

    var selectorRules = {};

    // Hàm thực hiện validate
    function validate(inputElement, rule) {
        var errorElement = getParent(inputElement, options.formGroupSelector).querySelector(options.errorSelector);
        var errorMessage;

        // Lấy ra các rules của selector
        var rules = selectorRules[rule.selector];

        for (var i = 0; i < rules.length; ++i) {
            switch (inputElement.type) {
                case 'radio':
                case 'checkbox':
                    errorMessage = rules[i](
                        formElement.querySelector(rule.selector + ':checked')
                    );
                    break;
                default:
                    errorMessage = rules[i](inputElement.value);
            }
            if (errorMessage) break;
        }
        
        if (errorMessage) {
            errorElement.innerText = errorMessage;
            getParent(inputElement, options.formGroupSelector).classList.add('invalid');
        } else {
            errorElement.innerText = '';
            getParent(inputElement, options.formGroupSelector).classList.remove('invalid');
        }

        return !errorMessage;
    }

    // Lấy element của form cần validate
    var formElement = document.querySelector(options.form);
    if (formElement) {
        formElement.onsubmit = function (e) {
            e.preventDefault();

            var isFormValid = true;

            options.rules.forEach(function (rule) {
                var inputElement = formElement.querySelector(rule.selector);
                var isValid = validate(inputElement, rule);
                if (!isValid) {
                    isFormValid = false;
                }
            });

            if (isFormValid) {
                if (typeof options.onSubmit === 'function') {
                    var enableInputs = formElement.querySelectorAll('[name]');
                    var formValues = Array.from(enableInputs).reduce(function (values, input) {
                        
                        switch(input.type) {
                            case 'radio':
                                values[input.name] = formElement.querySelector('input[name="' + input.name + '"]:checked').value;
                                break;
                            case 'checkbox':
                                if (!input.matches(':checked')) {
                                    values[input.name] = '';
                                    return values;
                                }
                                if (!Array.isArray(values[input.name])) {
                                    values[input.name] = [];
                                }
                                values[input.name].push(input.value);
                                break;
                            case 'file':
                                values[input.name] = input.files;
                                break;
                            default:
                                values[input.name] = input.value;
                        }

                        return values;
                    }, {});
                    options.onSubmit(formValues);
                }

                else {
                    formElement.submit();
                }
            }
        }

        options.rules.forEach(function (rule) {

            if (Array.isArray(selectorRules[rule.selector])) {
                selectorRules[rule.selector].push(rule.test);
            } else {
                selectorRules[rule.selector] = [rule.test];
            }

            var inputElements = formElement.querySelectorAll(rule.selector);

            Array.from(inputElements).forEach(function (inputElement) {

                inputElement.onblur = function () {
                    validate(inputElement, rule);
                }

                inputElement.oninput = function () {
                    var errorElement = getParent(inputElement, options.formGroupSelector).querySelector(options.errorSelector);
                    errorElement.innerText = '';
                    getParent(inputElement, options.formGroupSelector).classList.remove('invalid');
                } 
            });
        });
    }

}



// Định nghĩa rules
Validator.isRequired = function (selector, message) {
    return {
        selector: selector,
        test: function (value) {
            return value ? undefined :  message || 'Vui lòng nhập trường này'
        }
    };
}

Validator.isName = function (selector, message) {
    return {
        selector: selector,
        test: function (value) {
            var regex = /^[a-zA-Z\sàáạãảăắằặẳẵâấầậẩẫĐđêếềệểễéèẹẻẽíìịỉĩoọòóỏõôốồộổỗơớờợởỡúùụủũưứừựửữýỳỵỷỹ]+$/;

            return regex.test(value) ? undefined : message || 'Không chứa ký tự đặc biệt!';
        }
    };
}


Validator.minLength = function (selector, min, message) {
    return {
        selector: selector,
        test: function (value) {
            return value.length >= min ? undefined :  message || `Vui lòng nhập tối thiểu ${min} kí tự`;
        }
    };
}

Validator.maxLength = function (selector, max, message) {
    return {
        selector: selector,
        test: function (value) {
            return value.length <= max ? undefined :  message || `Vui lòng chỉ nhập tối đa ${max} kí tự`;
        }
    };
}



//  Delete function

function openForm(type, foodId = null) {
    let popupForm;

    if (type === "add") {
        popupForm = "popup_add";
    } else if (type === "delete") {
        popupForm = "popup_delete";
    } else if (type === "edit") {
        popupForm = "popup_edit";
    }

    if (popupForm) {
        const popupElement = document.getElementById(popupForm);

        popupElement.style.display = "block";

        if (foodId && type === "edit") {
            fetch(`/menu/edit/${foodId}`) 
                .then(response => response.json())
                .then(data => {
                    const form = document.getElementById("menuFormEdit");
                    if (form) {
                        form.action = `/menu/edit/${foodId}`;
                        form.querySelector('input[name="foodId"]').value = data.foodId;
                        form.querySelector('input#name').value = data.name;
                        form.querySelector('select#category').value = data.category;
                        form.querySelector('input#description').value = data.description;


                        const currentImage = form.querySelector('#currentImage');
                if (currentImage && data.image) {
                    currentImage.src = data.image;
                    currentImage.style.display = 'flex';
                } else if (currentImage) {
                    currentImage.style.display = 'none'; 
                }
            }})
                .catch(error => {
                    console.error('Error fetching data:', error);
                });
        } else if (foodId) {
            const foodIdInput = popupElement.querySelector('input[name="foodId"]');
            if (foodIdInput) {
                foodIdInput.value = foodId;
            }
        }
    }
}



function closeForm(type) {
    let popupForm;

    if (type === "add") {
        popupForm = "popup_add";
    } else if (type === "delete") {
        popupForm = "popup_delete";
    } else if (type === "edit") {
        popupForm = "popup_edit";
    }

    if (popupForm) {
        document.getElementById(popupForm).style.display = "none";
    }

}
function openForm(type, foodId = null) {
    let popupForm;
    const overlay = document.getElementById('overlay');

    if (type === "add") {
        popupForm = "popup_add";
    } else if (type === "delete") {
        popupForm = "popup_delete";
    } else if (type === "edit") {
        popupForm = "popup_edit";
    }

    if (popupForm) {
        const popupElement = document.getElementById(popupForm);
        popupElement.style.display = "block";
        overlay.style.display = "block";  // Show the overlay

        if (foodId && type === "edit") {
            fetch(`/menu/edit/${foodId}`) 
                .then(response => response.json())
                .then(data => {
                    const form = document.getElementById("menuFormEdit");
                    if (form) {
                        form.action = `/menu/edit/${foodId}`;
                        form.querySelector('input[name="foodId"]').value = data.foodId;
                        form.querySelector('input#name').value = data.name;
                        form.querySelector('select#category').value = data.category;
                        form.querySelector('input#description').value = data.description;

                        const currentImage = form.querySelector('#currentImage');
                        if (currentImage && data.image) {
                            currentImage.src = data.image;
                            currentImage.style.display = 'block';
                        } else if (currentImage) {
                            currentImage.style.display = 'none'; 
                        }
                    }
                })
                .catch(error => console.error('Error:', error));
        }

        if (foodId && type === "delete") {
            const deleteForm = document.getElementById("deleteForm");
            if (deleteForm) {
                deleteForm.querySelector('input[name="foodId"]').value = foodId;
            }
        }
    }
}

function closeForm(type) {
    let popupForm;
    const overlay = document.getElementById('overlay');

    if (type === "add") {
        popupForm = "popup_add";
    } else if (type === "delete") {
        popupForm = "popup_delete";
    } else if (type === "edit") {
        popupForm = "popup_edit";
    }

    if (popupForm) {
        document.getElementById(popupForm).style.display = "none";
        overlay.style.display = "none";  // Hide the overlay
    }
}



