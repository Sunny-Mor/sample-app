# Sample Application - AWS 3-Tier Architecture

Production-ready 3-tier application with Flask backend, RDS PostgreSQL, DynamoDB, ElastiCache, and Lambda.

## Architecture

```
Internet
   ↓
NLB (Public Subnet) - Port 80
   ↓
Frontend EC2 (Private) - nginx
   ↓ (reverse proxy)
Backend EC2 (Private) - Flask:5000
   ↓
RDS PostgreSQL | ElastiCache Redis | DynamoDB | S3 | SNS
```

## Quick Start

**Infrastructure already created via AWS Console ✓**

Next steps:
1. Initialize PostgreSQL database
2. Deploy backend on EC2
3. Deploy frontend on EC2
4. Create NLB
5. Deploy Lambda functions

See **SETUP_GUIDE.md** for complete deployment instructions.

## Project Structure

```
sample-app/
├── backend/
│   ├── app.py              # Flask application
│   └── Dockerfile
├── frontend/
│   └── index.html          # Web interface
├── lambda/
│   ├── handler.py          # API Lambda
│   └── sns_handler.py      # SNS handler
├── config/
│   └── config.py           # AWS clients config
├── scripts/
│   └── init_postgres.sql   # Database schema
├── cloudformation.yml      # Infrastructure template
├── SETUP_GUIDE.md          # Deployment guide
├── requirements.txt        # Python dependencies
└── .env.example            # Environment template
```

## API Endpoints

### Users (DynamoDB)
```bash
GET /users
POST /users
```

### Orders (PostgreSQL)
```bash
GET /orders
POST /orders
```

### Health
```bash
GET /health
```

## Environment Variables

```
AWS_REGION=us-east-1
DYNAMODB_TABLE=users_table
POSTGRES_HOST=<RDS_ENDPOINT>
POSTGRES_DB=appdb
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<PASSWORD>
REDIS_HOST=<REDIS_ENDPOINT>
REDIS_PORT=6379
S3_BUCKET=<S3_BUCKET>
SNS_TOPIC_ARN=<SNS_ARN>
SES_FROM_EMAIL=<EMAIL>
```

## Deployment

Follow **SETUP_GUIDE.md** for:
- Part 2: Initialize PostgreSQL
- Part 3: Deploy Backend EC2
- Part 4: Deploy Frontend EC2
- Part 5: Deploy Lambda Functions

## Testing

```bash
# Backend health
curl http://<backend-ip>:5000/health

# Frontend
curl http://<nlb-dns>/

# Lambda API
curl https://<api-id>.execute-api.us-east-1.amazonaws.com/prod/health
```

## Cleanup

1. Delete NLB from EC2 Console
2. Terminate EC2 instances
3. Delete Lambda functions
4. Delete API Gateway
5. Delete CloudFormation stack (removes all infrastructure)

## Support

See SETUP_GUIDE.md for detailed instructions and troubleshooting.
