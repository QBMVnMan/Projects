document.addEventListener("DOMContentLoaded", function () {
    const switchBtn = document.getElementById("switch-btn");
    const tableCards = document.querySelectorAll('.table_card');
    const addItemButton = document.querySelector(".btn-add-item");
    const additionalItemsContainer = document.getElementById("additional-items-container");
    const popup = document.getElementById("popup");
    const btnClosePopup = document.getElementById("btnClosePopup");

    switchBtn.addEventListener('click', function () {
        const firstLayer = document.getElementById('first-layer');
        const secondLayer = document.getElementById('second-layer');
        firstLayer.classList.toggle('active');
        secondLayer.classList.toggle('active');
    });

    tableCards.forEach(tableCard => {
        const bookButton = tableCard.querySelector('.book_btn');
        bookButton.addEventListener('click', function (event) {
            event.preventDefault();
            const tableId = this.closest('.table_card').getAttribute('tableId');
            document.getElementById('maBan').value = tableId;
            popup.style.display = 'block';
            resetPopupContent();
            tableCard.style.backgroundColor = '#cf4646';
        });
    });

    // btnClosePopup.addEventListener('click', closePopup);
    // document.getElementById('btnClosePopupInside').addEventListener('click', closePopup);

    addItemButton.addEventListener("click", addNewItemInput);

    function resetPopupContent() {
        additionalItemsContainer.innerHTML = '';
    }

    function addNewItemInput() {
        const newItemHTML = `
            <div class="additional-item">
                <div class="form-group">
                    <label for="tenMon" class="left-align-label1">Tên món:</label>
                    <input type="text" class="tenMon" name="tenMon" placeholder="Nhập tên món">
                </div>
                <div class="form-group">
                    <label for="soLuong" class="left-align-label">Số lượng:</label>
                    <input type="number" class="soLuong" name="soLuong" min="1" value="1">
                </div>
            </div>
        `;
        additionalItemsContainer.insertAdjacentHTML('beforeend', newItemHTML);
    }

    // function closePopup() {
    //     popup.style.display = 'none';
    // }
});



function openForm() {
    document.getElementById("popup").style.display = "block";
}

        
    
function closeForm(type) {
     document.getElementById("popup").style.display = "none";
}     