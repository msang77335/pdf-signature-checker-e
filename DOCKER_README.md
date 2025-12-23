# PDF Signature Checker - Docker Setup

## Cấu trúc Project

```
pdf-signature-checker/
├── docker-compose.yml          # Docker Compose configuration
├── .dockerignore              # Files to ignore in Docker build
├── pdf-next/                  # Next.js frontend
│   ├── Dockerfile            # Multi-stage build với tối ưu hóa
│   └── ...
└── pdf-python/                # Python Flask API
    ├── Dockerfile            # Python API Docker image
    ├── requirements.txt      # Python dependencies
    └── ...
```

## Dockerfile Features

### pdf-python/Dockerfile
- **Base Image**: Python 3.11 slim
- **Security**: Chạy với non-root user
- **Dependencies**: Tối ưu caching với requirements.txt riêng biệt
- **Health Check**: Kiểm tra endpoint `/api/health`
- **Port**: 5001

### pdf-next/Dockerfile
- **Multi-stage Build**: 
  - Stage 1 (deps): Cài đặt dependencies
  - Stage 2 (builder): Build ứng dụng
  - Stage 3 (runner): Production runtime
- **Security**: Chạy với non-root user (nextjs:nodejs)
- **Output**: Standalone mode cho container nhỏ gọn hơn
- **Health Check**: Kiểm tra endpoint `/api/health`
- **Port**: 3000

## Sử dụng

### Khởi động services

```bash
# Build và khởi động cả 2 services
docker-compose up -d

# Chỉ build lại images
docker-compose build

# Build và force rebuild
docker-compose up -d --build
```

### Quản lý services

```bash
# Xem logs
docker-compose logs -f

# Xem logs của service cụ thể
docker-compose logs -f pdf-python
docker-compose logs -f pdf-next

# Dừng services
docker-compose down

# Dừng và xóa volumes
docker-compose down -v

# Restart service cụ thể
docker-compose restart pdf-python
```

### Kiểm tra health

```bash
# Check Python API
curl http://localhost:5001/api/health

# Check Next.js app
curl http://localhost:3000/api/health

# Xem health status trong Docker
docker ps
```

## Ports

- **pdf-next**: http://localhost:3000
- **pdf-python**: http://localhost:5001

## Network

Cả 2 services nằm trong cùng network `pdf-network`, cho phép:
- pdf-next gọi pdf-python qua: `http://pdf-python:5001`
- Internal communication không cần expose ports

## Optimization Features

### Caching
- Docker layer caching cho dependencies
- Next.js standalone output giảm image size
- npm ci cho reproducible builds

### Security
- Non-root users trong containers
- Minimal base images (alpine, slim)
- .dockerignore để loại bỏ sensitive files

### Monitoring
- Health checks cho cả 2 services
- Auto-restart policy
- Structured logging

## Troubleshooting

### Container không start
```bash
# Xem logs chi tiết
docker-compose logs pdf-python
docker-compose logs pdf-next
```

### Port đã được sử dụng
```bash
# Thay đổi ports trong docker-compose.yml
# Ví dụ: "3001:3000" thay vì "3000:3000"
```

### Rebuild sau khi thay đổi code
```bash
# Force rebuild
docker-compose up -d --build --force-recreate
```
