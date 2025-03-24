function toggleSection(sectionId) {
    // Lấy tất cả các phần tử có class "order-section"
    var sections = document.getElementsByClassName("order-section");
    
    // Lặp qua từng phần tử và ẩn chúng đi
    for (var i = 0; i < sections.length; i++) {
        sections[i].classList.remove("active");
    }
    
    // Hiển thị phần tử có id tương ứng với sectionId
    document.getElementById(sectionId).classList.add("active");
}

// Chạy hàm toggleSection khi tải trang để hiển thị tab đúng ban đầu
// document.addEventListener("DOMContentLoaded", function() {
//     var status = "<%= order.Status %>"; // Lấy trạng thái từ server-side

//     if (status === "new") {
//         toggleSection("food_new");
//     } else if (status === "prepared") {
//         toggleSection("food_prepared");
//     } else if (status === "served") {
//         toggleSection("food_served");
//     }
// });

document.addEventListener("DOMContentLoaded", function() {
    // Add event listeners for "Đã chuẩn bị xong" buttons
    document.querySelectorAll('.mark-prepared-btn').forEach(button => {
        button.addEventListener('click', function() {
            const orderId = this.getAttribute('data-order-id');
            updateOrderStatus(orderId, 'Prepared');
            moveOrderToPrepared(orderId);
            updateButtonLabel(this, 'Đã chuẩn bị xong');
        });
    });

    // Add event listeners for "Đã phục vụ" buttons
    document.querySelectorAll('.mark-served-btn').forEach(button => {
        button.addEventListener('click', function() {
            const orderId = this.getAttribute('data-order-id');
            updateOrderStatus(orderId, 'Served');
            moveOrderToServed(orderId);
            updateButtonLabel(this, 'Đã phục vụ');
        });
    });

    function updateOrderStatus(orderId, status) {
        fetch('/order', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: `orderId=${orderId}&status=${status}`
        })
        .then(response => {
            if (!response.ok) {
                console.error('Failed to update order status');
            }
        })
        .catch(error => {
            console.error('Error:', error);
        });
    }

    function moveOrderToPrepared(orderId) {
        const orderElement = document.querySelector(`button[data-order-id="${orderId}"]`).closest('li');
        document.getElementById('food_prepared').querySelector('ul').appendChild(orderElement);
    }

    function moveOrderToServed(orderId) {
        const orderElement = document.querySelector(`button[data-order-id="${orderId}"]`).closest('li');
        document.getElementById('food_served').querySelector('ul').appendChild(orderElement);
    }

    function updateButtonLabel(button, labelText) {
        button.textContent = labelText;
    }
});

// Get all the bar links
const barLinks = document.querySelectorAll('.bar a');

// Add event listener to each link
barLinks.forEach(link => {
  link.addEventListener('click', function() {
    // Remove 'active' class from all links
    barLinks.forEach(link => {
      link.classList.remove('active');
    });

    // Add 'active' class to the clicked link
    this.classList.add('active');
  });
});
