# 🚀 Crypto Platform Quick Start Guide

## 📋 Prerequisites

Before running the application, ensure you have the following installed:

- **Python 3.8+**
- **Node.js 18+**
- **npm** or **yarn**
- **Redis** (optional, for caching and sessions)

## 🎯 Quick Start Options

### Option 1: Full Setup (Recommended)
```bash
# Make the script executable and run
chmod +x start.sh
./start.sh
```

### Option 2: Quick Development
```bash
# Fast start for development
chmod +x start-dev.sh
./start-dev.sh
```

### Option 3: Using npm Scripts
```bash
# Install all dependencies
npm run install:all

# Start both servers
npm start

# Or start individually
npm run start:backend  # Backend only
npm run start:frontend # Frontend only
```

## 🌐 Access Points

Once started, you can access:

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000/api/
- **API Documentation**: http://localhost:8000/api/docs/
- **Django Admin**: http://localhost:8000/admin/

## 🛠️ Development Commands

### Backend Commands
```bash
# Run migrations
npm run migrate

# Create superuser
npm run createsuperuser

# Collect static files
npm run collectstatic

# Run backend tests
npm run test:backend

# Lint backend code
npm run lint:backend
```

### Frontend Commands
```bash
# Build for production
npm run build:frontend

# Run frontend tests
npm run test:frontend

# Lint frontend code
npm run lint:frontend
```

### Utility Commands
```bash
# Clean cache and build files
npm run clean

# Watch logs
npm run logs

# Full setup
npm run setup
```

## 📁 Project Structure

```
cleo/
├── backend/                 # Django backend
│   ├── users/              # User management
│   ├── wallet/             # Wallet operations
│   ├── transactions/       # Crypto transactions
│   ├── trading/            # Trading engine
│   ├── compliance/         # KYC/AML compliance
│   └── health/             # Health checks
├── cleo-web/           # Next.js frontend
│   ├── src/
│   │   ├── app/           # App router pages
│   │   ├── components/    # React components
│   │   ├── store/         # Redux store
│   │   └── utils/         # Utilities
│   └── package.json
├── start.sh                # Full startup script
├── start-dev.sh           # Quick dev script
├── package.json           # Root package.json
└── requirements.txt       # Python dependencies
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the root directory:

```bash
# Backend
DJANGO_ENV=development
SECRET_KEY=your-secret-key-here
DEBUG=True

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000/api/
```

### Database

The application uses SQLite by default. For production:

```bash
# PostgreSQL setup
pip install psycopg2-binary
# Update DATABASES in backend/settings/production.py
```

### Redis (Optional)

```bash
# Install Redis
sudo apt-get install redis-server  # Ubuntu/Debian
brew install redis                 # macOS

# Start Redis
redis-server
```

## 🚨 Troubleshooting

### Port Conflicts
If ports 8000 or 3000 are already in use:

```bash
# Kill processes on ports
lsof -ti:8000 | xargs kill -9
lsof -ti:3000 | xargs kill -9

# Or use different ports
BACKEND_PORT=8001 python manage.py runserver 0.0.0.0:8001
cd cleo-web && PORT=3001 npm run dev
```

### Virtual Environment Issues

```bash
# Recreate virtual environment
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Frontend Build Issues

```bash
# Clear Next.js cache
cd cleo-web
rm -rf .next
npm install
npm run build
```

### Backend Issues

```bash
# Clear Django cache
python manage.py clearsessions
python manage.py migrate --fake-initial
```

## 📝 Logs

Application logs are stored in the `logs/` directory:

- `logs/backend.log` - Django server logs
- `logs/frontend.log` - Next.js development logs

```bash
# Watch logs in real-time
npm run logs

# Or individually
tail -f logs/backend.log
tail -f logs/frontend.log
```

## 🧪 Testing

### Backend Tests
```bash
# Run all tests
npm run test:backend

# Run specific app tests
python manage.py test backend.users
python manage.py test backend.wallet
```

### Frontend Tests
```bash
# Run frontend tests
npm run test:frontend

# Run with coverage
cd cleo-web && npm run test:coverage
```

## 🚀 Production Deployment

### Build Frontend
```bash
npm run build:frontend
```

### Backend Production Settings
```bash
export DJANGO_ENV=production
python manage.py collectstatic --noinput
python manage.py migrate
```

### Using Docker (Optional)
```bash
# Build and run with Docker
docker-compose up --build
```

## 📞 Support

If you encounter issues:

1. Check the logs: `npm run logs`
2. Verify all dependencies are installed
3. Ensure ports 8000 and 3000 are available
4. Check virtual environment is activated

## 🎉 Success!

When everything is running, you should see:

```
╔══════════════════════════════════════════════════════════════╗
║           Crypto Platform is running!                       ║
╠══════════════════════════════════════════════════════════════╣
║  Frontend:  http://localhost:3000                           ║
║  Backend:   http://localhost:8000                           ║
║  API Docs:  http://localhost:8000/api/docs/                 ║
║  Admin:     http://localhost:8000/admin/                    ║
╚══════════════════════════════════════════════════════════════╝
```

Happy coding! 🚀
