# API Error Model

Related issue: #7  
Source: HEDS-004 API Specification

## Standard error shape

```json
{
  "error": {
    "code": "string",
    "message": "string",
    "requestId": "string",
    "details": {}
  }
}
```

## Error fields

| Field | Purpose |
| --- | --- |
| `code` | Stable machine-readable error code. |
| `message` | Safe human-readable summary. |
| `requestId` | Operational trace id for support and logs. |
| `details` | Optional structured context safe to expose. |

## Initial error categories

| HTTP status | Category | Example code |
| --- | --- | --- |
| 400 | Validation failure | `VALIDATION_ERROR` |
| 401 | Authentication required | `AUTH_REQUIRED` |
| 403 | Access denied | `ACCESS_DENIED` |
| 404 | Resource not found | `NOT_FOUND` |
| 409 | Conflict | `CONFLICT` |
| 429 | Rate limited | `RATE_LIMITED` |
| 500 | Internal error | `INTERNAL_ERROR` |

## Security rule

Do not expose secrets, stack traces, raw provider credentials, or sensitive tenant data in API error responses.
