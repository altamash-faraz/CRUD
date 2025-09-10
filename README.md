# Simple CRUD Web Application

A full-stack CRUD (Create, Read, Update, Delete) web application built with Node.js, Express.js, and MongoDB.

## Features

- ✅ Create new items with name, description, category, and price
- ✅ View all items in a responsive grid layout
- ✅ Update existing items
- ✅ Delete items with confirmation
- ✅ Real-time form validation
- ✅ Responsive design for mobile and desktop
- ✅ Modern UI with smooth animations

## Technologies Used

- **Backend**: Node.js, Express.js
- **Database**: MongoDB with Mongoose ODM
- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **Styling**: Modern CSS with Grid and Flexbox

## Prerequisites

Before running this application, make sure you have the following installed:

- Node.js (v14 or higher)
- MongoDB (local installation or MongoDB Atlas account)
- Git

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd simple-crud-app
```

2. Install dependencies:
```bash
npm install
```

3. Create a `.env` file in the root directory and configure your environment variables:
```
PORT=3000
MONGODB_URI=mongodb://localhost:27017/crud_app
```

4. Start MongoDB service (if running locally):
```bash
# On Windows
net start MongoDB

# On macOS/Linux
sudo systemctl start mongod
```

## Usage

### Development Mode

Run the application in development mode with auto-restart:

```bash
npm run dev
```

### Production Mode

Run the application in production mode:

```bash
npm start
```

The application will be available at `http://localhost:3000`

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/items` | Get all items |
| GET | `/api/items/:id` | Get item by ID |
| POST | `/api/items` | Create new item |
| PUT | `/api/items/:id` | Update item by ID |
| DELETE | `/api/items/:id` | Delete item by ID |

## Project Structure

```
├── public/
│   ├── index.html      # Main HTML file
│   ├── style.css       # Styling
│   └── script.js       # Frontend JavaScript
├── server.js           # Express server and API routes
├── package.json        # Dependencies and scripts
├── .env               # Environment variables
├── .gitignore         # Git ignore rules
└── README.md          # This file
```

## Database Schema

### Item Model
```javascript
{
  name: String (required),
  description: String (required),
  category: String (required),
  price: Number (required, min: 0),
  createdAt: Date (default: now)
}
```

## Features in Detail

### Create Items
- Add new items with form validation
- Required fields: name, description, category, price
- Price validation (must be positive number)
- Category selection from predefined options

### Read Items
- Display all items in a responsive grid
- Show item details: name, description, category, price, creation date
- Real-time loading indicators
- Empty state when no items exist

### Update Items
- Click "Edit" to populate the form with existing data
- Update any field and submit changes
- Form switches to "Update" mode with cancel option
- Smooth scroll to form when editing

### Delete Items
- Click "Delete" with confirmation dialog
- Immediate removal from the UI
- Success/error feedback messages

## Deployment

### Using MongoDB Atlas (Recommended for production)

1. Create a MongoDB Atlas account at https://www.mongodb.com/atlas
2. Create a new cluster and get your connection string
3. Update the `MONGODB_URI` in your `.env` file:

### Deploy to Heroku

1. Install Heroku CLI
2. Create a Heroku app:
```bash
heroku create your-app-name
```

3. Set environment variables:
```bash
heroku config:set MONGODB_URI=your-mongodb-connection-string
```

4. Deploy:
```bash
git push heroku main
```

### Deploy to Vercel/Netlify

For deployment to platforms like Vercel or Netlify, you may need to adjust the project structure to separate the frontend and backend, or use serverless functions.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

If you encounter any issues or have questions, please open an issue on GitHub.

## Future Enhancements

- [ ] User authentication and authorization
- [ ] Image upload for items
- [ ] Search and filter functionality
- [ ] Pagination for large datasets
- [ ] Data export/import features
- [ ] Advanced form validation
- [ ] Unit and integration tests
