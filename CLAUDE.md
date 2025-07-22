# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## IMPORTANT RULES

1. **Always guide the user through actions first, THEN document**: When the user needs to run commands or perform actions, always:
   - Tell them exactly what to run
   - Wait for them to complete the action
   - Only document the action AFTER they confirm it's done
   - Never just create documentation assuming actions will be taken later

2. **Be explicit about terminal commands**: Always provide the exact command to run, don't assume the user knows what to do.

## Project Overview

This is a proof-of-concept project for Amazon S3 Vectors, AWS's new vector storage service launched in July 2025. Currently, the repository contains technical documentation exploring the service capabilities and implementation patterns.

## Development Setup

### Python Environment (Recommended)
```bash
pip install boto3>=1.39.9
pip install numpy  # For vector generation
```

### TypeScript Environment
```bash
npm install @aws-sdk/client-s3vectors
npm install @aws-sdk/credential-providers
```

## Key Service Constraints

- **Dimensions**: 1-4,096 per vector
- **Batch Limits**: 500 items (insert/delete), 100 items (select)
- **Rate Limits**: 5+ write requests/second per index
- **Query Latency**: 200-500ms typical
- **String Keys**: Primary keys must be strings, not integers

## Core Operations

1. **bulk_insert**: Insert vectors with embeddings and metadata
2. **bulk_select**: Retrieve vectors by primary keys
3. **bulk_delete**: Remove vectors
4. **get_neighbours**: Find nearest neighbors (cosine similarity)

## Architecture Patterns

- Use exponential backoff for rate limiting
- Implement batch processing for optimal performance
- Design metadata carefully (filterable vs non-filterable)
- Consider cost implications: $0.04/GB/month storage, $0.0004 per 1K queries

## Documentation

- `docs/python-vs-typescript.md`: Language comparison and examples
- `docs/understanding-s3-service.md`: Service architecture and best practices

## Important Notes

- Python SDK is more mature than TypeScript
- Service is in preview in 5 AWS regions
- Optimized for cost over latency
- Not suitable for real-time applications requiring <100ms response times