import express from "express";
import cookieParser from "cookie-parser";
import mysql from "mysql2/promise";
import multer from "multer";

const app = express();
const PORT = 3000;

const pool = mysql.createPool({
  host: "localhost",
  user: "root",
  password: null,
  database: "karmakitchen"
});

const storage = multer.diskStorage({
  destination: function (req, file, cb) {
    cb(null, 'public/uploads/');
  },
  filename: function (req, file, cb) {
    cb(null, Date.now() + '-' + file.originalname);
  }
});

const upload = multer({ storage: storage });

app.set("view engine", "ejs");
app.use(express.static("public"));
app.use(cookieParser());
app.use(express.urlencoded({ extended: true }));


// Trang chủ
app.get('/', async (req, res) => {
  try {
    const title = "Karma Kitchen";
    res.render('homepage.ejs', { title: title });
  } catch (error) {
    console.error("An error occurred while rendering the login page:", error);
    res.status(500).send("Internal Server Error");
  }
});

// Hiển thị menu
app.get('/menu', async (req, res) => {
  try {
    const title = "Karma Kitchen";
    const [rows] = await pool.query("SELECT * FROM food");
    res.render('menu.ejs', { title: title, menuItems: rows });
  } catch (error) {
    console.error("An error occurred while rendering the menu page:", error);
    res.status(500).send("Internal Server Error");
  }
});

// Thêm mục menu
app.post('/menu/add', upload.single('image'), async (req, res) => {
  try {
    const { name, category, description } = req.body;
    const descriptionValue = description ? description : null;
    
    let image = null;
    if (req.file) {
      image = req.file.filename;
    }
    await pool.query("INSERT INTO food (FoodName, Category, Description, Image) VALUES (?, ?, ?, ?)", [name, category, descriptionValue, image]);

    res.redirect('/menu');
  } catch (error) {
    console.error("An error occurred while adding menu item to database:", error);
    res.status(500).send("Internal Server Error");
  }
});

// Xóa mục menu
app.post('/menu/delete', async (req, res) => {
  try {
    const foodId = req.body.foodId;
    await pool.query("DELETE FROM food WHERE FoodID = ?", [foodId]);
    res.redirect('/menu');
  } catch (error) {
    console.error("An error occurred while deleting menu item from database:", error);
    res.status(500).send("Internal Server Error");
  }
});

// Lấy thông tin mục menu để chỉnh sửa
app.get('/menu/edit/:id', async (req, res) => {
  try {
    const foodId = req.params.id;
    const [rows] = await pool.query("SELECT * FROM food WHERE FoodID = ?", [foodId]);
    
    if (rows.length === 0) {
      return res.status(404).json({ message: "Food item not found" });
    }

    const menuItem = rows[0];
    res.json({
      foodId: menuItem.FoodID,
      name: menuItem.FoodName,
      category: menuItem.Category,
      description: menuItem.Description,
      image: menuItem.Image ? `uploads/${menuItem.Image}` : null 
    });
  } catch (error) {
    console.error("An error occurred while fetching menu item:", error);
    res.status(500).json({ message: "Internal Server Error" });
  }
});

// Chỉnh sửa mục menu
app.post('/menu/edit/:id', upload.single('image'), async (req, res) => {
  try {
    const foodId = req.params.id;
    const { name, category, description } = req.body;

    let image = null;
    if (req.file) {
      image = req.file.filename;
    } else {
      const [rows] = await pool.query("SELECT Image FROM food WHERE FoodID = ?", [foodId]);
      if (rows.length > 0) {
        image = rows[0].Image;
      }
    }

    await pool.query(
      "UPDATE food SET FoodName = ?, Category = ?, Description = ?, Image = ? WHERE FoodID = ?",
      [name, category, description || null, image, foodId]
    );

    res.redirect('/menu');
  } catch (error) {
    console.error("An error occurred while updating menu item:", error);
    res.status(500).send("Internal Server Error");
  }
});

// Hiển thị bàn
app.get('/table', async (req, res) => {
  try {
    const title = "Karma Kitchen";
    const [tables] = await pool.query("SELECT * FROM `table`");
    const [foods] = await pool.query("SELECT * FROM food");
    
    res.render('table.ejs', { title: title, tables: tables, foods: foods });
  } catch (error) {
    console.error("An error occurred while rendering the table page:", error);
    res.status(500).send("Internal Server Error");
  }
});


// Thêm đơn hàng
app.post('/table/createOrder', async (req, res) => {
  const { maBan, tenMon, soLuong, ghiChu} = req.body;
  try {
    // Lấy TableID từ TableName
    const [tables] = await pool.query('SELECT TableID FROM `table` WHERE TableName = ?', [maBan]);
    if (tables.length === 0) {
      return res.status(400).send('Invalid table name');
    }
    const tableID = tables[0].TableID;

    // Tạo đơn hàng mới
    const [orderResult] = await pool.query(
      'INSERT INTO `order` (TableID, TableName, FoodName, Quantity, Status, Note) VALUES (?, ?, ?, ?, ?, ?)',
      [tableID, maBan, tenMon, soLuong, 'new', ghiChu ]
    );
    res.redirect('/table');
  } catch (error) {
    console.error("An error occurred while adding the order to the database:", error);
    res.status(500).send("Internal Server Error");
  }
});


// Hiển thị đơn hàng
app.get('/order', async (req, res) => {
  try {
    const title = "Karma Kitchen";
    const [order] = await pool.query("SELECT * FROM `order`");
    const [food] = await pool.query("SELECT * FROM `food`");
    
    res.render('orderManage.ejs', { title: title, orders: order, foods: food});
  } catch (error) {
    console.error("An error occurred while rendering the table page:", error);
    res.status(500).send("Internal Server Error");
  }
});

// Cập nhật trạng thái đơn hàng
app.post('/order', async (req, res) => {
  const { orderId, status } = req.body;

  try {
    await pool.query("UPDATE `order` SET `Status` = ? WHERE `OrderID` = ?", [status, orderId]);
    res.json({ success: true });
  } catch (error) {
    console.error("An error occurred while updating order status:", error);
    res.status(500).json({ success: false });
  }
});

app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}.`);
});
