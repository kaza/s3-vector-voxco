# S3 Vectors PoC Setup Guide

## Prerequisites

1. **Install AWS CLI**
   ```bash
   # On Ubuntu/Debian
   curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
   unzip awscliv2.zip
   sudo ./aws/install

   # On macOS
   brew install awscli

   # Verify installation
   aws --version
   ```

2. **Configure AWS Credentials**
   ```bash
   aws configure
   # Enter your AWS Access Key ID
   # Enter your AWS Secret Access Key
   # Enter default region (e.g., us-east-1)
   # Enter output format (json)
   ```

3. **Install Python Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set Up Environment Variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

## Creating S3 Vector Resources

### Create Vector Bucket (using AWS CLI)
```bash
# Note: Replace 'my-vector-bucket' with your desired bucket name
aws s3vectors create-vector-bucket \
    --bucket my-vector-bucket \
    --region us-east-1
```

### Create Vector Index
```bash
aws s3vectors create-vector-index \
    --bucket my-vector-bucket \
    --index documents \
    --dimensions 128 \
    --similarity-function COSINE \
    --region us-east-1
```

## Running Tests

### Run all tests
```bash
pytest -v
```

### Run individual test files
```bash
# Test document operations
pytest tests/test_document_operations.py -v

# Test search functionality
pytest tests/test_search.py -v

# Test a specific test function
pytest tests/test_document_operations.py::test_insert_single_document -v
```

### Run tests with coverage
```bash
pytest --cov=src tests/
```

## Environment Variables

- `AWS_ACCESS_KEY_ID`: Your AWS access key
- `AWS_SECRET_ACCESS_KEY`: Your AWS secret key
- `AWS_REGION`: AWS region (must support S3 Vectors)
- `S3_VECTORS_BUCKET_NAME`: Name of your vector bucket
- `S3_VECTORS_INDEX_NAME`: Name of your vector index