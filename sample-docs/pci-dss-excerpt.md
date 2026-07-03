# Payment Card Security Policy (Illustrative Excerpt)

*This is a simplified, illustrative excerpt written for a training exercise. It is not the official PCI DSS standard.*

## Requirement 3: Protect Stored Account Data

Stored cardholder data must be kept to the minimum required for business, legal, or regulatory purposes. The primary account number (PAN) must be rendered unreadable anywhere it is stored, using strong cryptography. Sensitive authentication data must not be retained after authorisation, even if encrypted.

## Requirement 7: Restrict Access by Business Need to Know

Access to system components and cardholder data must be limited to only those individuals whose job requires it. Access rights must be reviewed at least every six months to confirm they remain appropriate, and removed promptly when no longer needed.

## Requirement 8: Authenticate Access

Every user must be assigned a unique ID before being granted access to system components. Shared or generic accounts are not permitted for administrative access. Multi-factor authentication is required for all remote access into the cardholder data environment.

## Control Summary

| Control ID | Area | Requirement | Minimum |
|---|---|---|---|
| C-3.1 | Data retention | Retain stored PAN only as long as needed | Business-justified only |
| C-7.2 | Access review | Review user access rights | Every 6 months |
| C-8.3 | Passwords | Minimum password length | 12 characters |
| C-8.4 | Remote access | Multi-factor authentication | Required |
| C-10.1 | Logging | Retain audit trail history | 12 months |
