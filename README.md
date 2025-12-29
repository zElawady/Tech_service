# 🛠️ Service Connect Platform

Service Connect is a full-featured **Streamlit-based service booking platform** that connects users with professional technicians for home, maintenance, auto, and tech services.  
It supports **users**, **technicians**, and **admins**, with real-time chat, order tracking, and an admin dashboard.

---

## 🚀 Features

### 👤 User Features
- User registration & authentication
- Browse and search available services
- Book services with date & payment method
- Track order status
- Chat directly with assigned technicians
- Manage personal profile

### 🔧 Technician Features
- Technician registration & login
- View pending service orders
- Chat with customers
- Update order status

### 🧑‍💼 Admin Features
- Admin dashboard with statistics
- View all users, services, and orders
- Assign technicians to orders
- Revenue and performance tracking

### 💬 Built-in Chat System
- Order-based real-time chat
- Unread message notifications
- Separate chat views for users & technicians

### 🎨 Modern UI
- Custom dark theme with animations
- Responsive layout
- Streamlit + custom CSS styling

---

## 🧱 Tech Stack

- **Frontend / UI:** Streamlit
- **Backend:** Python
- **Database:** SQLite
- **Data Handling:** Pandas
- **Charts:** Altair
- **Authentication:** SHA-256 password hashing
- **Styling:** Custom CSS

---

## 📂 Project Structure

```text
.
├── app.py                  # Main Streamlit application
├── service_connect.db      # SQLite database (auto-created)
├── README.md               # Project documentation
```

> ⚠️ Database tables and demo data are automatically created on first run.

---

## 🧪 Demo Accounts

| Role        | Email                    | hashed password                                                 |
|------------|--------------------------|------------------------------------------------------------------|
| Admin      | admin@serviceconnect.com | 240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9 |
| User       | user@example.com         | 04f8996da763b7a969b1028ee3007569eaf3a635486ddab211d512c85b9df8fb |
| Technician | tech@example.com         | fe9bbd400bb6cb314531e3462507661401959afc69aae96bc6aec2c213b83bc1 |

---

## ⚙️ Installation & Setup

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/your-username/service-connect.git
cd service-connect
```

### 2️⃣ Install Dependencies
```bash
pip install streamlit pandas altair
```

### 3️⃣ Run the Application
```bash
streamlit run app.py
```

The app will open automatically in your browser.

---

## 🗄️ Database Schema

Main tables:
- `users`
- `services`
- `orders`
- `chat_messages`
- `order_technicians`
- `contact_messages`

All tables are auto-created and seeded with demo data.

---

## 🔐 Security Notes

- Passwords are securely hashed using SHA-256
- Role-based access control (User / Technician / Admin)
- Input validation for email and phone numbers

---

## 📈 Future Improvements

- Online payment integration (Stripe/PayPal)
- Technician availability scheduling
- Service reviews & ratings
- Push notifications
- Deployment with Docker

---

## 🤝 Contributing

Contributions are welcome!
1. Fork the repository
2. Create a new branch
3. Commit your changes
4. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License.

---

## 📬 Contact

For support or inquiries:  
📧 **support@serviceconnect.com**  
📞 **+1-234-567-8900**

---

⭐ If you like this project, don’t forget to star it!
