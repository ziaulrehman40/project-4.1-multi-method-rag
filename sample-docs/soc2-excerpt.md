# Trust Services Policy (Illustrative Excerpt)

*This is a simplified, illustrative excerpt written for a training exercise. It is not the official SOC 2 criteria.*

## Scope

This report covers three trust-service criteria: Security, Availability, and Confidentiality. Processing Integrity and Privacy are out of scope for this period.

## Security

The system is protected against unauthorised access. Logical access is controlled through unique accounts, role-based permissions, and multi-factor authentication for privileged access. Changes to production are reviewed and approved before release.

## Availability

The system is available for operation as committed. Availability is monitored continuously, and an incident-response process is followed when service is degraded. Backups are taken daily and tested for restorability each quarter.

## Confidentiality

Information designated as confidential is protected through encryption in transit and at rest, and access is limited to authorised roles. Confidential data is disposed of securely when no longer required.

## Control Summary

| Control ID | Criterion | Control | Frequency or Target |
|---|---|---|---|
| S-1 | Security | Review privileged access | Every 3 months |
| S-2 | Security | Multi-factor authentication for admins | Required |
| A-1 | Availability | Test backup restoration | Every quarter |
| A-2 | Availability | Uptime commitment | 99.9 percent |
| C-1 | Confidentiality | Encrypt data in transit and at rest | Required |
| L-1 | Security | Retain audit logs | 12 months |
